'''
HTTP Client endpoints are (currently) unmanaged endpoints that provide easy convenience methods to make synchronous or asynchronous
HTTP calls. The classes and methods offer abstractions to callers of making simple method calls which internally handle all
marshalling of parameters and un-marshalling of results. Many methods exist to support direct get or post method calls or 
JSON marshalling of input parameters and un-marshalling of output responses 
'''
from fabric import concurrency
if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
elif concurrency == 'threading':
    pass

from functools import wraps
import json
import threading
import sys
import urlparse
import urllib2
from contextlib import closing

    
import logging
from fabric.endpoints.endpoint import EndPoint

class Header(dict):
    ''' Header is a helper class to allow easy additions of headers. Primarily, this formats multi-value headers 
        according to the HTTP specifications (i.e. ';' separated) which is a format suitable for passing to urllib calls
        
        Header supports all standard dict operations
    '''
       
    #FIXME: do we need __eq__ and __hash__?
     
    def __init__(self, *args, **kargs):
        self.update(*args, **kargs)

    def __setitem__(self, key, value):
        try:
            self[key]
        except KeyError:
            pass
        else:
            value = self[key] + ';' + value
        finally:
            super(Header, self).__setitem__(key, value)

    def update(self, *args, **kwargs):
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, got %d" % len(args))
            other = dict(args[0])
            for key in other:
                self[key] = other[key]
        for key in kwargs:
            self[key] = kwargs[key]

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]    
        

class Response(object):
    '''
    HTTP Responses are wrapped and returned using this object. This object provides two attributes
    *data* and *headers*
    '''
    def __init__(self, data, headers):
        '''
        :param data: The data given by response.read()
        
        :param headers: The response info given by response.info()
        '''
        
        #: self.data: contains the response (already read()) 
        self.data = data
        
        #: self.headers: contain the headers of the response
        self.headers = headers
    
    def __repr__(self, *args, **kwargs):
        return "Data:{}, Headers:{}".format(self.data, self.headers)
            
def dejsonify_response(func):
    '''
    a decorator that expects a :py:class:`Response` object from the wrapped function
    and performs a json.loads on the response.data 
    '''
    @wraps(func)
    def wrapper(*args, **kargs):
        response = func(*args, **kargs)
        response.data = json.loads(response.data)
        return response
    return wrapper

def jsonify_request(func):
    '''
    a decorator that takes all the keyword arguments and converts each argument to its JSON representation.
    these JSONed arguments are then individually passed to the wrapped function which typically sends each argument
    as an individual GET or POST parameter as part of the HTTP request 
    '''
    @wraps(func)
    def wrapper(*args, **kargs):
        try:
            headers = kargs['headers']
            del kargs['headers']
        except KeyError:
            headers = Header()
        return func(*args, headers=headers, **dict([ (k, json.dumps(v)) for k,v in kargs.iteritems() ]))
    return wrapper

class HTTPClient(EndPoint):
    '''
    A (currently) unmanaged endpoint that provides simple abstractions to marshall, unmarshall and perform the http
    protocol in making requests.
    '''
    
    def __init__(self, url=None, data=None, headers=None, origin_req_host=None, method='POST'):
        '''
        :param str url: the url that this request object should bind to. This is optional and the url provided with
            :py:meth:`request` supercedes this value. The url will be urlquoted before sending
        :param dict data: the data to be sent to the server. in the form of key=value pairs. These elements will be urlencoded before sending  
        :param headers: optional headers to include with the request. headers is a dict or a :py:class:`Header` object
        :param origin_req_host: refer urllib2.Request
        :param str method: one of 'GET' or 'POST'
        '''
        
        self.url = url
        self.data = data or {}
        self.headers = Header(headers or {})
        self.method = method.upper()
        self.origin_req_host = origin_req_host
        
    def _request(self, url=None, data=None, headers=None, method=None):
        url = url or self.url
        headers = headers or self.headers
        data = data or self.data
        method = method or self.method
        if method is None: method = 'POST'
        if method.upper() != 'POST': method = 'GET'
        
        try:
            data = self._safe_urlencode(data, doseq=True)
        
            if method == 'GET':
                url += '?' + data
                data = None
    
            parsed = urlparse.urlparse(url)      #Making the path URL Quoted
            url = urlparse.urlunparse(parsed[:2]+(urllib2.quote(parsed.path.encode("utf8")),)+parsed[3:])
           
            request = urllib2.Request(url=url, data=data, headers=headers, origin_req_host=self.origin_req_host)
            with closing(urllib2.urlopen(request)) as req:
                rv = Response(data=req.read(), headers=req.info())
                return rv
        except urllib2.HTTPError as err:
            logging.getLogger().exception('HTTPError: %d', err.code)
            # FIXME: change logging to warning.warn
            raise
        except urllib2.URLError as err:
            logging.getLogger().exception('URLError: %d', err.reason)
            # FIXME: change logging to warning.warn
            raise

    def request(self, url, headers=None, **kargs):
        '''
        a method to make a simple get request. all keyword arguments are converted to the data for the request.

        :param headers: an optional dict or Header object
        :param kargs: all keyword arguments are converted to the data for the request
            method is POST by default but can be 'GET' by passing method='GET' as a keyword arg
        
        **Example**::
        
            HTTPClient().get_request('http://www.google.com', q="ignite solutions", method='GET')

        '''
        method = kargs.get('method', 'POST')
        try:
            del kargs['method']
        except KeyError:
            pass
        return self._request(url, data=kargs, headers=headers, method=method)
    
    @dejsonify_response
    def json_out_request(self, url, headers=None, **kargs):
        '''
        A special case of making a get or post request where the http request is expected to return a JSON encoded return value.
        Handles all marshaling, protocol and basic error processing of a post http request. The return value is converted from a JSON object to 
        a python object. Note - integer values when converted to JSON values are reconverted to string python values.
        
        :param url: the url that is the target for the request. 
        :param headers: a set of headers to be included as part of the request. None implies no headers. 
        :param kargs: a set of keyword arguments that will be converted to the post arguments for the request. 
            if method='GET' is a karg, the request is a GET request. the method argument is not packaged with the data
        :returns: :py:class:`Response` with response.data as a Python object obtained from loading a JSON string
        '''
        return self.request(url, headers=headers, **kargs)
    
    @jsonify_request
    def json_in_request(self, url, headers=None, **kargs):
        '''
        A special case of making a get or post request where each parameter to the request is individually converted to a JSON string.
        Handles all marshaling, protocol and basic error processing of a post http request. 

        :param url: the url that is the target for the request. 
        :param headers: a set of headers to be included as part of the request. None implies no headers. 
        :param kargs: a set of keyword arguments that will be converted to the post arguments for the request. if method='GET' is a karg, the request is a GET request
            the method argument is not packaged with the data
        :returns: :py:class:`Response`
        '''
        return self.request(url, headers=headers, **kargs)
        
    @jsonify_request
    @dejsonify_response
    def json_inout_request(self, url, headers=None, **kargs):
        '''
        a combination of :py:meth:`json_in_request` and :py:meth:`json_out_request`
        '''
        return self.request(url, headers=headers, **kargs)

    try:
            unicode
    except NameError:
        @staticmethod
        def _is_unicode(x):
            return False
    else:
        @staticmethod
        def _is_unicode(x):
            return isinstance(x, unicode)
    
    def _safe_urlencode(self, query, doseq=0):
        """
        A reimplementation of urllib2.urlencode with query being called instead of query_plus
        Encode a sequence of two-element tuples or dictionary into a URL query string.
    
        If any values in the query arg are sequences and doseq is true, each
        sequence element is converted to a separate parameter.
    
        If the query arg is a sequence of two-element tuples, the order of the
        parameters in the output will match the order of parameters in the
        input.
        """
        if query is None:
            return None
        
        if hasattr(query, "items"):
            # mapping objects
            query = query.items()
        else:
            # it's a bother at times that strings and string-like objects are
            # sequences...
            try:
                # non-sequence items should not work with len()
                # non-empty strings will fail this
                if len(query) and not isinstance(query[0], tuple):
                    raise TypeError
                # zero-length sequences of all types will get here and succeed,
                # but that's a minor nit - since the original implementation
                # allowed empty dicts that type of behavior probably should be
                # preserved for consistency
            except TypeError:
                ty,va,tb = sys.exc_info()
                raise TypeError, "not a valid non-string sequence or mapping object", tb
    
        l = []
        if not doseq:
            # preserve old behavior
            for k, v in query:
                k = urllib2.quote(str(k))
                v = urllib2.quote(str(v))
                l.append(k + '=' + v)
        else:
            for k, v in query:
                k = urllib2.quote(str(k))
                if isinstance(v, str):
                    v = urllib2.quote(v)
                    l.append(k + '=' + v)
                elif self._is_unicode(v):
                    # is there a reasonable way to convert to ASCII?
                    # encode generates a string, but "replace" or "ignore"
                    # lose information and "strict" can raise UnicodeError
                    v = urllib2.quote(v.encode("ASCII","replace"))
                    l.append(k + '=' + v)
                else:
                    try:
                        # is this a sufficient test for sequence-ness?
                        len(v)
                    except TypeError:
                        # not a sequence
                        v = urllib2.quote(str(v))
                        l.append(k + '=' + v)
                    else:
                        # loop over the sequence
                        for elt in v:
                            l.append(k + '=' + urllib2.quote(str(elt)))
        return '&'.join(l)
    
class HTTPAsyncClient(HTTPClient, threading.Thread):
    '''
    A class that supports asynchronous HTTP requests. Currently, this does not use thread pooling so the user should be careful with 
    runaway creation of long-lived requests. Supports all the methods of :py:class:`HTTPClient`
    '''
    
    def __init__(self, url=None, headers=None, origin_req_host=None, method='POST', onsuccess=None, onerror=None, sync=False, timeout=None):
        '''
        
        :param str url: the url that this request object should bind to. This is optional and the url provided with
            :py:meth:`request` supercedes this value. The url will be urlquoted before sending
        :param headers: optional headers to include with the request. headers is a dict or a :py:class:`Header` object
        :param origin_req_host: refer urllib2.Request
        :param str method: one of 'GET' or 'POST'
        :param onsuccess: a function to be invoked on successful response from the request. This function is invoked with an instance of the :py:class:`Response` object
        :param onerror: a function to be invoked on failure of the request. Invoked with the exception that got raised.
        :param bool sync: whether this request should be synchronous (True) or async (default) 
        :param timeout: (currently not implemented). Whether to timeout if no response is received in a specified time.
        '''
        do_nothing = lambda x: None
        self.onsuccess = onsuccess or do_nothing
        self.onerror = onerror or do_nothing
        self.sync = sync
        self.timeout = timeout
        super(HTTPAsyncClient, self).__init__(url=None, headers=None, origin_req_host=None, method=method)
        threading.Thread.__init__(self)
        self.daemon = True

    def _request(self, url=None, data=None, headers=None, method=None):
        if self.sync:
            return super(HTTPAsyncClient, self)._request(url=None, data=None, headers=None, method=None)
        
        self.url = url or self.url
        self.headers = headers or self.headers
        self.data = data or self.data
        self.method = method or self.method
        if self.method is None: self.method = 'POST'
        if self.method.upper() != 'POST': self.method = 'GET'

        try:
            self.start()
        except RuntimeError:
            raise
    
    def run(self):
        
        try:
            rv = super(HTTPAsyncClient, self)._request(url=self.url, data=self.data, headers=self.headers, method=self.method)
            self.onsuccess(rv)
        except (urllib2.HTTPError, urllib2.URLError) as err:
            self.onerror(err)
            
if __name__ == '__main__':
    
    def success(rv): 
        print rv
        
    def error(err):
        print err
    
    headers = Header()
    headers['Cookie'] = 'helloworld=123'
    headers['Cookie'] = 'shakesphere=123456'
#    print 'get_request', HTTPClient(method='GET').request('http://localhost:9000/getter', headers=headers, a=10, b='hello', c=1.2)
#    print 'post_request', HTTPClient().request('http://localhost:9000/poster', headers=headers, a=10, b='hello', c=1.2)
#    print 'json_in_request', HTTPClient().json_in_request('http://localhost:9000/jsonin', headers=headers, a=10, b='hello', c=1.2, d=dict(x=1, y='hello', z=True, w=1.2))
#    print 'json_out_request', HTTPClient().json_out_request('http://localhost:9000/jsonout', headers=headers, a=10, b='hello', c=1.2)
#    print 'json_inout_request', HTTPClient().json_inout_request('http://localhost:9000/jsoninout', headers=headers, a=10, b='hello', c=1.2, d=dict(x=1, y='hello', z=True, w=1.2))
#    
    for i in range(5):
        HTTPAsyncClient(method='GET', onsuccess=success, onerror=error).request('http://localhost:9000/getter', headers=headers, a=10, b='hello', c=1.2)
        print 'done', i
        