'''
Endpoints represent an inbound or outbound port or interface for communication between servers or with clients. 
These can represent unicast, multicast or peer-to-peer communications. 

Endpoints are building block for :ref:`Servers` and servers can have one or more endpoints of multiple types. Fabric currently supports 

* HTTP server endpoints :py:class:`HTTPServerEndPoint` which allow the server that contains this endpoint to act as an HTTP Server
* HTTP client endpoints :py:class:`HTTPClient` and :py:class:`HTTPAsyncClient` which faciliate making HTTP requests to other servers or external systems
'''
from fabric.common.utils import generate_uuid

class EndPoint(object):
    ''' A base class for all endpoints. '''
    def __init__(self, server=None, name=None, stickeykeys=None): 
        self.uuid = generate_uuid()
        self.server = server
        self.name = name
        self.stickeykeys = stickeykeys
    
    def close(self):
        pass
    
    def activate(self):
        self._activated = True

class EndPointException(Exception):
    '''
    A generic exception thrown by subclasses of :py:class:`EndPoint`
    '''
    pass

        
        