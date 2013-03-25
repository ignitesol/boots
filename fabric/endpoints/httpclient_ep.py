'''
HTTP Client endpoints are (currently) unmanaged endpoints that provide easy convenience methods to make synchronous or asynchronous
HTTP calls. The classes and methods offer abstractions to callers of making simple method calls which internally handle all
marshalling of parameters and un-marshalling of results. Many methods exist to support direct get or post method calls or 
JSON marshalling of input parameters and un-marshalling of output responses 
'''

from functools import wraps
import json
import threading
import sys
import urlparse
import urllib2
from contextlib import closing
import StringIO
import re

    
import logging
from fabric.endpoints.endpoint import EndPoint

class Header(dict):
    ''' Header is a helper class to allow easy additions of headers. Primarily, this formats multi-value headers 
        according to the HTTP specifications (i.e. ';' separated) which is a format suitable for passing to urllib calls
        
        Header supports all standard dict operations
    '''
        
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
    
    def set_cookie(self, keyval):
        '''
        Adds cookie to be forward to the HTTP request. Note - this typically takes a cookie
        obtained from one request and forwards to another
        
        :param keyval: is a dict or a list of tuples in the form [ (key, val)... ]
        '''
        if type(keyval) == dict:
            keyval = keyval.iteritems()
        for k, v in keyval:
            self['Cookie'] = '='.join([k, v])
    
class HTTPUtils(object):
    
    @classmethod
    def get_cookies(cls, keys, cookies, header=None):
        '''
        Adds cookies to be forwarded with another HTTP request. Extracts
        cookies that have name as one of the elements of keys. 
        if header is None, a new Header object is created and returned
    
        :param keys: list of keynames which need to be extracted from cookies
        :param cookies: a dict containing name-value pairs that represent cookies
        :param headers: an existing Header object (or None). Defaults to None. If None is specified a new empty header object is created
        
        :returns: Header object with the cookies in the header set to the matching keys in cookies 
        '''
        headers = header or Header()
        if keys:
            for key in keys:
                headers['Cookie'] = key + '=' + cookies.get(key,'')
        return headers
  
        

class Response(object):
    '''
    HTTP Responses are wrapped and returned using this object. This object provides attributes
    *data* and *headers* (this is a Headers object) and *raw_headers* which provides headers as returned
    by the request
    '''
    def __init__(self, data, headers):
        '''
        :param data: The data given by response.read()
        
        :param headers: The response info given by response.info()
        '''
        
        #: self.data: contains the response (already read()) 
        self.data = data
        
        #: self.headers: contain the headers of the response
        self.raw_headers = headers
        self._headers = None
    
    def __repr__(self, *args, **kwargs):
        return "Data:{}, Headers:{}".format(self.data, self.headers)
    
    @property
    def headers(self):
        '''
        returns a :py:class:`Header` object with all the headers returned as part of this response
        trailing \r and \n are removed from each header
        '''
        if self._headers == None:
            head = StringIO.StringIO(self.raw_headers)
            self._headers = Header()
            
            for s in head:
                key, val = s.split(':', 1) # split at the 1st :
                val = val.rstrip('\r\n')
                self._headers[key] = val

        return self._headers
    
    def info(self):
        return self.raw_headers
        
    
    def extract_headers(self, keys=None, header=None):
        '''
        this returns a :py:class:`Header object populated with any header values returned from the request
        :param keys: an optional list of keys (defaults to None which implies all keys present in the response header). Keys are strings that take the regular expressions syntax. keys
        can also be a single key, i.e not a list
        :param header: the header object to append the extracted headers to. If None, a new Header object is created and returned. Header can be used as a dict 
        '''
        header = header or Header()
        if not keys:
            header.update(self.headers)
        else:
            if not hasattr(keys, '__iter__'): keys = [ keys ]  # if single key specified, make it a list
            for k in keys:
                regexp = re.compile(k, flags=re.IGNORECASE)
                header.update(filter(lambda item: regexp.match(item[0]), self.headers.iteritems()))
        return header
    
    def extract_cookies(self, keys=None):
        '''
        this returns a dict object populated with any cookies present in the response object
        :param keys: an optional list of keys (defaults to None which implies all keys present in the response header). Keys are strings that take the regular expressions syntax. keys
        can also be a single key, i.e not a list
        '''
        cookies = self.extract_headers('Set-Cookie')
        # TODO: obtain the cookies by splitting, extract the correct keys
            
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

class HTTPClientEndPoint(EndPoint):
    '''
    A (currently) unmanaged endpoint that provides simple abstractions to marshall, unmarshall and perform the http
    protocol in making requests.
    '''
    
    def __init__(self, url=None, data=None, headers=None, origin_req_host=None, method='POST', server=None):
        '''
        :param str url: the url that this request object should bind to. This is optional and the url provided with
            :py:meth:`request` supercedes this value. The url will be urlquoted before sending
        :param dict data: the data to be sent to the server. in the form of key=value pairs. These elements will be urlencoded before sending  
        :param headers: optional headers to include with the request. headers is a dict or a :py:class:`Header` object
        :param origin_req_host: refer urllib2.Request
        :param str method: one of 'GET' or 'POST'
        :param Server server: (defaults None). A reference to the server object to which this endpoint belongs to
        '''
        
        super(HTTPClientEndPoint, self).__init__(server=server)
        self.url = url
        self.data = data
        self.headers = Header(headers or {})
        self.method = method.upper()
        self.origin_req_host = origin_req_host
        
    def _construct_url(self, url=None, data=None, headers=None, method=None):
        '''
        Constructs the url from the given url, data, headers and method.
         We dont need to pass headers and method, but tomorrow we may have some logic which may be changing the headers due to some kind of data, like ebif data.
        '''
        url = url or self.url
        headers = headers or self.headers
        data = data or self.data
        method = method or self.method
        if method is None: method = 'POST'
        # call a POST or DELETE http method if passed explicity (usecase for DELETE : unlike in facebook)
#        if method.upper() != 'POST' and method.upper() != 'DELETE' : method = 'GET'
        if headers.get('Content-Type', None) in [ "application/json"]:
            data = json.dumps(data)
        else:
            data = self._safe_urlencode(data, doseq=True)
            if method == 'GET' and data:
                url += '?' + data
                data = None
            parsed = urlparse.urlparse(url)      #Making the path URL Quoted
            url = urlparse.urlunparse(parsed[:2]+(urllib2.quote(parsed.path.encode("utf8")),)+parsed[3:])
        return url, data, headers, method
        
    def _request(self, url=None, data=None, headers=None, method=None):
        try:
            url, data, headers, method = self._construct_url(url=url, data=data, headers=headers, method=method)
#            logging.getLogger().debug('url:%s, data:%s, headers:%s, origin_req_host:%s', url, data, headers, self.origin_req_host)
            request = urllib2.Request(url=url, data=data, headers=headers, origin_req_host=self.origin_req_host)
            # urllib2 doesn't support DELETE/PUT, so we are patching this object instance of request to support it
            if method.upper() not in ['POST', 'GET']:
                request.get_method = lambda: method
            with closing(urllib2.urlopen(request)) as req:
                rv = Response(data=req.read(), headers=req.info())
                return rv
        except urllib2.HTTPError as err:
            logging.getLogger().exception('HTTPError: %d, url:%s, data:%s, headers:%s, origin_req_host:%s', err.code, url, data, headers, self.origin_req_host)
            # FIXME: change logging to warning.warn
            raise
        except urllib2.URLError as err:
            logging.getLogger().exception('URLError: %s, url:%s, data:%s, headers:%s, origin_req_host:%s', err.reason, url, data, headers, self.origin_req_host)
            # FIXME: change logging to warning.warn
            raise

    def request(self, url=None, headers=None, method='POST', **kargs):
        '''
        a method to make a simple get request. all keyword arguments are converted to the data for the request.

        :param headers: an optional dict or Header object
        :param method: method is POST by default but can be 'GET' by passing method='GET' as a keyword arg
        :param kargs: all keyword arguments are converted to the data for the request
        
        **Example**::
        
            HTTPClientEndPoint().get_request('http://www.google.com', q="ignite solutions", method='GET')

        '''
        return self._request(url, data=kargs, headers=headers, method=method)
    
    @dejsonify_response
    def json_out_request(self, url, headers=None, method='POST', **kargs):
        '''
        A special case of making a get or post request where the http request is expected to return a JSON encoded return value.
        Handles all marshaling, protocol and basic error processing of a post http request. The return value is converted from a JSON object to 
        a python object. Note - integer values when converted to JSON values are reconverted to string python values.
        
        :param url: the url that is the target for the request. 
        :param headers: a set of headers to be included as part of the request. None implies no headers. 
        :param method: default POST. if method='GET' is a karg, the request is a GET request.
        :param kargs: a set of keyword arguments that will be converted to the post arguments for the request. 
        :returns: :py:class:`Response` with response.data as a Python object obtained from loading a JSON string
        '''
        return self.request(url, headers=headers, method=method, **kargs)
    
    @jsonify_request
    def json_in_request(self, url, headers=None, method='POST', **kargs):
        '''
        A special case of making a get or post request where each parameter to the request is individually converted to a JSON string.
        Handles all marshaling, protocol and basic error processing of a post http request. 

        :param url: the url that is the target for the request. 
        :param headers: a set of headers to be included as part of the request. None implies no headers. 
        :param method: default POST. if method='GET' is a karg, the request is a GET request.
        :param kargs: a set of keyword arguments that will be converted to the post arguments for the request. 
        :returns: :py:class:`Response`
        '''
        return self.request(url, headers=headers, method=method, **kargs)
        
    @jsonify_request
    @dejsonify_response
    def json_inout_request(self, url, headers=None, method='POST', **kargs):
        '''
        a combination of :py:meth:`json_in_request` and :py:meth:`json_out_request`
        '''
        return self.request(url, headers=headers, method=method, **kargs)
         
        
        
    #####
    # helpers
    #####

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
    
class HTTPAsyncClient(HTTPClientEndPoint, threading.Thread):
    '''
    A class that supports asynchronous HTTP requests. Currently, this does not use thread pooling so the user should be careful with 
    runaway creation of long-lived requests. Supports all the methods of :py:class:`HTTPClientEndPoint`
    '''
    
    def __init__(self, url=None, headers=None, origin_req_host=None, method='POST', onsuccess=None, onerror=None, sync=False, timeout=None, server=None):
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
        :param Server server: (defaults None). A reference to the server object to which this endpoint belongs to
        '''
        do_nothing = lambda x: None
        self.onsuccess = onsuccess or do_nothing
        self.onerror = onerror or do_nothing
        self.sync = sync
        self.timeout = timeout
        super(HTTPAsyncClient, self).__init__(url=None, headers=None, origin_req_host=None, method=method, server=server)
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
#    print 'get_request', HTTPClientEndPoint(method='GET').request('http://localhost:9000/getter', headers=headers, a=10, b='hello', c=1.2)
#    print 'post_request', HTTPClientEndPoint().request('http://localhost:9000/poster', headers=headers, a=10, b='hello', c=1.2)
#    print 'json_in_request', HTTPClientEndPoint().json_in_request('http://localhost:9000/jsonin', headers=headers, a=10, b='hello', c=1.2, d=dict(x=1, y='hello', z=True, w=1.2))
#    print 'json_out_request', HTTPClientEndPoint().json_out_request('http://localhost:9000/jsonout', headers=headers, a=10, b='hello', c=1.2)
#    print 'json_inout_request', HTTPClientEndPoint().json_inout_request('http://localhost:9000/jsoninout', headers=headers, a=10, b='hello', c=1.2, d=dict(x=1, y='hello', z=True, w=1.2))
#    
    for i in range(5):
        HTTPAsyncClient(method='GET', onsuccess=success, onerror=error).request('http://localhost:9000/getter', headers=headers, a=10, b='hello', c=1.2)
        print 'done', i
        