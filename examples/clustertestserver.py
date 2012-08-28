import os
import sys
try:
    import fabric
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # this is unnecessary if fabric is installed in the site-packages or in PYTHONPATH

from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute
from fabric.servers.clusteredserver import ClusteredServer
from fabric.servers.helpers.clusterenum import AdapterTagEnum
from optparse import OptionParser

usage="usage: %prog [options]"
parser = OptionParser(usage=usage, version="0.1")
parser.add_option("-p", "--port", dest="port", default="7777", help="port number of adapter")

opt, args = parser.parse_args(sys.argv[1:])
if  not opt.port:
    exit;

host = "aurora.ignitelabs.local"
my_server_address = host + ':' + str(opt.port)


class EP(HTTPServerEndPoint):

    @methodroute()
    def register(self, channel=None, load=1):
        my_server_address = self.server.server_adress  
        return "Registered at : " + my_server_address
        
        
print "My server adress : " , my_server_address

class MpegCluterServer(ClusteredServer):
    
    def __init__(self, *args, **kwargs ):
        super(MpegCluterServer, self).__init__(*args, **kwargs)
        
        
    def refreshed_load_on_update(self, load):
        '''
        This method defines how the load gets updated which each request being served or completed
        It returns new load 
        :param load : percentage of load that exists at currently 
        '''
        return load+10
    
    
        
 
stickykeys = ['channel']
application = MpegCluterServer(my_server_address , AdapterTagEnum.MPEG,  stickykeys, endpoints=[EP()], cache=False, logger=True)


if __name__ == '__main__':
    application.start_server(defhost=host, defport=int(opt.port), standalone=True)