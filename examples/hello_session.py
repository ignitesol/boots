'''
This example illustrates the use of session and caching in boots

* It builds on the example helloworld

In this example, we demonstrate a simple http server with one endpoint and one route within that endpoint.
'''
import sys
import os
import logging
import pprint
try:
    import boots
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # this is unnecessary if boots is installed in the site-packages or in PYTHONPATH

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute    
    
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
        env = pprint.pformat(self.environ)
        logging.getLogger().debug("environ = %s", env)
        logging.getLogger().debug('server type = %s', type(self.server.app))
        logging.getLogger().debug('hello called with %s, session has name %s, session has count %d', name, 
                                  self.session.get('name', None), 
                                  self.session.get('count', 0))
        name = name or self.session.get('name', None) or 'world'  # the name is passed as an argument or obtained from the session
        self.session['name'] = name
        self.session['count'] = self.session.get('count', 0) + 1

        return 'hello %s - you have called me %d times' % (name, self.session['count'])

# create an endpoint
ep1 = EP()
# associate the endpoint with a server
main_server = HTTPServer(endpoints=[ep1], session=True, logger=True)

if __name__ == '__main__':
    main_server.start_server(defhost='localhost', defport=9998, standalone=True, description="A test server for the boots framework")
