'''
Endpoints represent an inbound or outbound port or interface for communication between servers or with clients. 
These can represent unicast, multicast or peer-to-peer communications. 

Endpoints are building block for :ref:`Servers` and servers can have one or more endpoints of multiple types. Fabric currently supports 

* HTTP server endpoints :py:class:`HTTPServerEndPoint` which allow the server that contains this endpoint to act as an HTTP Server
* HTTP client endpoints :py:class:`HTTPClient` and :py:class:`HTTPAsyncClient` which faciliate making HTTP requests to other servers or external systems
'''

class EndPoint(object):
    ''' A base class for all endpoints. ''' 
    pass

class EndPointException(Exception):
    '''
    A generic exception thrown by subclasses of :py:class:`EndPoint`
    '''
    pass

        
        