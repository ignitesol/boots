'''
This is an example of the basic usage of the server and http endpoint components of the fabric framework

* Servers are entities that provide specific functionality and capability
* Servers consist of one or more endpoints (source or destinations of communication) and optionally sub-servers (more on this later)

In this example, we demonstrate a simple http server with one endpoint and one route within that endpoint.
'''
import sys
import os
import logging
try:
    import fabric
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # this is unnecessary if fabric is installed in the site-packages or in PYTHONPATH

from fabric.servers.httpserver import HTTPServer
from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute    
    
class EP(HTTPServerEndPoint):
    
    # methodroute automatically creates a route based on the name of the method
    # arguments to the method make it RESTful
    # keyword parameters with default values make optional RESTful parameters
    @methodroute()
    def hello(self, name=None):
        ''' 
        @methodroute converts this method to a route handler which 
        matches /hello or /hello/anyname since we have a keyword argument that takes a default value
        '''
        name = name or 'world'  # the name is passed as an argument
        logging.getLogger().debug('hello called with %s', name)
        return 'hello %s' % name

class EP_SUB(EP):
    @methodroute()
    def hello(self, name=None):
        ''' 
        @methodroute converts this method to a route handler which 
        matches /hello or /hello/anyname since we have a keyword argument that takes a default value
        '''
        name = name or 'world'  # the name is passed as an argument
        logging.getLogger().debug('HELLO called with %s', name)
        return 'HELLO %s' % name
    
# create an endpoint
ep1 = EP()
# associate the endpoint with a server
main_server = HTTPServer(endpoints=[ep1], logger=True)

if __name__ == '__main__':
    main_server.start_server(defhost='localhost', defport=9999, standalone=True, description="A test server for the fabric framework")
