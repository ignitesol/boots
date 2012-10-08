import os
import sys
try:
    import fabric
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # this is unnecessary if fabric is installed in the site-packages or in PYTHONPATH

from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute
from fabric.servers.clusteredserver import ClusteredServer
from fabric.servers.helpers.clusterenum import ClusterServerType
from optparse import OptionParser

usage="usage: %prog [options]"
parser = OptionParser(usage=usage, version="0.1")
parser.add_option("-p", "--port", dest="port", default="3000", help="port number of adapter")
parser.add_option("-r", "--restart", dest="restart", default=None, help="server is restarting if value is not None")

opt, args = parser.parse_args(sys.argv[1:])
if  not opt.port:
    exit;
    

host = "aurora.ignitelabs.local"
my_server_address = host + ':' + str(opt.port)
myport = opt.port
restartflag = True if opt.restart else False

print "Restart flag :" , opt.restart

class ClusterTestEP(HTTPServerEndPoint):
    def __init__(self, *args, **kwargs):
        super(ClusterTestEP, self).__init__(*args, **kwargs)

    @methodroute(params=dict(channel=str, host=str, port=int))
    def register(self, channel=None, host=None, port=None, ds = None):
        '''
        This is sample route to test the stickiness.
        Sticky key is defined as 'channel' param
        '''
        my_server_address = self.server.server_adress  
        
        #adds sticky value in the route
        #Application specific logic
        if channel and host and port:
            ds.add_sticky_value("client")
        return "Registered at : " + my_server_address + " serving from :" + myport
    
    @methodroute()
    def register1(self, clientid=None):
        my_server_address = self.server.server_adress  
        return "Registered - 1 at : " + my_server_address
    
    @methodroute()
    def test(self):
        return "this is test route"
    
print "My server adress : " , my_server_address

class TestClusterServer(ClusteredServer):
    
    def __init__(self, *args, **kwargs ):
        super(TestClusterServer, self).__init__(*args, **kwargs)
        
        
        
    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=[], 
                        conflict_handler='error', **kargs):
        '''
        Overridden to add the restart parameter
        '''
        _argparser = super(TestClusterServer, cls).get_arg_parser(*args, **kargs)
        _argparser.add_argument('-r', '--restart', dest='restart', type=str, default=kargs.get('restart', None), help='restart'),                                 
        return _argparser
        
        
    def get_new_load(self):
        '''
        This method defines how the load gets updated which each request being served or completed
        It returns new load 
        :param load : percentage of load that exists at currently 
        '''
        return 10
    
application = TestClusterServer(
                                my_server_address , ClusterServerType.MPEG,  clustered=True, \
                                stickykeys=[ ('channel','host','port'), ('clientid')], \
                                endpoints=[ClusterTestEP()], cache=False, logger=True, \
                                restart=restartflag)

if __name__ == '__main__':
    application.start_server(defhost=host, defport=int(opt.port), standalone=True)