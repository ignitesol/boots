import os
import sys
try:
    import boots
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # this is unnecessary if boots is installed in the site-packages or in PYTHONPATH
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute
from boots.servers.clusteredserver import ClusteredServer
from boots.datastore.datawrapper import DSWrapperObject
import bottle
class TestEP(HTTPServerEndPoint):
    def __init__(self, *args, **kwargs):
        super(TestEP, self).__init__(*args, **kwargs)

    @methodroute(params=dict(channel=str, host=str, port=int), method='ANY')
    def register(self, channel=None, host=None, port=None):
        '''
        This is sample route to test the stickiness.
        '''
        #adds sticky value in the route, It's Application specific logic
        ds = DSWrapperObject.get_instance()
        if channel:
            ds.add_sticky_value("client")
        return "Registered at : " + self.server.server_adress
    
    @methodroute( method='ANY')
    def register1(self, clientid=None):
        my_server_address = self.server.server_adress
        return "Registered - 1 at : " + my_server_address
    
    @methodroute( method='ANY')
    def test(self):
        d = bottle.request.environ.items()
        for k,v in d:
            print "%s = %s"%(k, v)
        
    
class TestClusterServer(ClusteredServer):
    
    def __init__(self, *args, **kwargs ):
        super(TestClusterServer, self).__init__(*args, **kwargs)
        
    def get_new_load(self):
        '''
        This method defines how the load gets updated which each request being served or completed. It returns new load 
        :param load : percentage of load that exists at currently 
        '''
        return 10
    

if __name__ == '__main__':

    application = TestClusterServer('TEST',  clustered=True, stickykeys=[ ('channel'), ('clientid')], \
                                endpoints=[TestEP()], cache=False, logger=True)
    
    application.start_server(standalone=True)