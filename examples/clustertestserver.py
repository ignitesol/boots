import os
import sys
try:
    import fabric
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # this is unnecessary if fabric is installed in the site-packages or in PYTHONPATH
from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute
from fabric.servers.clusteredserver import ClusteredServer

class TestEP(HTTPServerEndPoint):
    def __init__(self, *args, **kwargs):
        super(TestEP, self).__init__(*args, **kwargs)

    @methodroute(params=dict(channel=str, host=str, port=int))
    def register(self, channel=None, host=None, port=None, datastructure = None):
        '''
        This is sample route to test the stickiness.
        '''
        #adds sticky value in the route, It's Application specific logic
        if channel and host and port:
            datastructure.add_sticky_value("client")
        return "Registered at : " + self.server.server_adress   
    
    @methodroute()
    def register1(self, clientid=None):
        my_server_address = self.server.server_adress  
        return "Registered - 1 at : " + my_server_address
    
class TestClusterServer(ClusteredServer):
    
    def __init__(self, *args, **kwargs ):
        super(TestClusterServer, self).__init__(*args, **kwargs)
        
    def get_new_load(self):
        '''
        This method defines how the load gets updated which each request being served or completed. It returns new load 
        :param load : percentage of load that exists at currently 
        '''
        return 10
    
application = TestClusterServer(
                                'TEST',  clustered=True, \
                                stickykeys=[ ('channel','host','port'), ('clientid')], \
                                endpoints=[TestEP()], cache=False, logger=True, ds='datastructure')

if __name__ == '__main__':
    application.start_server(standalone=True)