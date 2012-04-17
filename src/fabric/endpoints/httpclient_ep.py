'''
Created on Mar 26, 2012

@author: AShah
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
        

class Response(object):
    '''
    All Responses are packed using this Object.
    '''
    def __init__(self, data, headers):
        '''
        @param data: The data given by response.read()
        @type data: dict
        
        @param headers: The response info given by response.info()
        @type headers: str 
        '''
        self.data = data
        self.headers = headers
    
    def __repr__(self, *args, **kwargs):
        return "Data:{}, Headers:{}".format(self.data, self.headers)
            
def dejsonify_response(func):
    @wraps(func)
    def wrapper(*args, **kargs):
        response = func(*args, **kargs)
        response.data = json.loads(response.data)
        return response
    return wrapper

def jsonify_request(func):            #Need to rethink
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
    
    def __init__(self, url=None, data=None, headers=None, origin_req_host=None, method='POST'):
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
            data = self.safe_urlencode(data, doseq=True)
        
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
        a method to make a simple get request. all keywork arguments are converted to the data for the request.
        example HTTPClient().get_request('http://www.google.com', q='q=ignite+solutions'
        @param headers: an optional dict or Header object
        @param **kargs: all keywork arguments are converted to the data for the request
        '''
        return self._request(url, data=kargs, headers=headers)
    
    @dejsonify_response
    def json_out_request(self, url, headers=None, **kargs):
        '''
        A special case of making a post request where the http request is expected to return a JSON encoded return value.
        Handles all marshaling, protocol and basic error processing of a post http request. The return value is converted from a JSON object to 
        a python object. Note - integer values when converted to JSON values are reconverted to string python values.
        @param url: the url that is the target for the request
        @type url: string
        @param headers: a set of headers to be included as part of the request. None implies no headers. 
        @type headers: dict or Header object. 
        @param kargs: a set of keyword arguments that will be converted to the post arguments for the request
        '''
        return self.request(url, headers=headers, **kargs)
    
    @jsonify_request
    def json_in_request(self, url, headers=None, **kargs):
        return self.request(url, headers=headers, **kargs)
        
    @jsonify_request
    @dejsonify_response
    def json_inout_request(self, url, headers=None, **kargs):
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
    
    def safe_urlencode(self, query, doseq=0):
        """
        A reimplementation of urllib2.urlencode with query being called instead of query_plus
        Encode a sequence of two-element tuples or dictionary into a URL query string.
    
        If any values in the query arg are sequences and doseq is true, each
        sequence element is converted to a separate parameter.
    
        If the query arg is a sequence of two-element tuples, the order of the
        parameters in the output will match the order of parameters in the
        input.
        """
        
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
    
    def __init__(self, url=None, headers=None, origin_req_host=None, method='POST', onsuccess=None, onerror=None, sync=False, timeout=None):
        do_nothing = lambda x: None
        self.onsuccess = onsuccess or do_nothing
        self.onerror = onerror or do_nothing
        self.sync = sync
        self.timeout = timeout
        super(HTTPAsyncClient, self).__init__(url=None, headers=None, origin_req_host=None, method=method)
        threading.Thread.__init__(self)
        #self.daemon = True

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
        