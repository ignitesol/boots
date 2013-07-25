'''
This example demonstrates basic logging.
'''
import sys
import os
import logging
try:
    import boots
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # this is unnecessary if boots is installed in the site-packages or in PYTHONPATH

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute    
    
class EP(HTTPServerEndPoint):

    @methodroute()
    def hello(self, name=None):
        name = name or 'world'  # the name is passed as an argument
        self.server.logger.debug('hello called with %s', name)
        return 'hello %s' % name
    

ep1 = EP()
main_server = HTTPServer(endpoints=[ep1], logger=True)
if __name__ == '__main__':
    main_server.start_server(defhost='localhost', proj_dir='.', defport=9996, standalone=True, description="A test server for the boots framework")
