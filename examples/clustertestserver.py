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
my_end_Point = host + ':' + str(opt.port)


class EP(HTTPServerEndPoint):

    @methodroute()
    def register(self, channel=None, load=50):
        my_end_point = self.server.my_end_point
        self.server.update_data(my_end_point, load, channel=channel)
        return "Registered"
        
        
print "My end point : " , my_end_Point

class MpegCluterServer(ClusteredServer):
    
    def __init__(self, *args, **kwargs ):
        super(MpegCluterServer, self).__init__(*args, **kwargs)
        
    def get_existing_or_free(self, key , servertype, **kargs):
        #TOBE OVERRIDDEN METHOD
        resusable = None
        if key:
            resusable =  self.get_by_key(key=key)
        if not resusable:
            #find server with least load
            resusable = self.get_least_loaded(servertype)
        return resusable
            
    def get_least_loaded(self, servertype):
        return self.datastore.get_least_loaded(servertype)
        
stickykey = 'channel'
application = MpegCluterServer(my_end_Point , AdapterTagEnum.MPEG,  stickykey, endpoints=[EP()], cache=False, logger=True)


if __name__ == '__main__':
    application.start_server(defhost=host, defport=int(opt.port), standalone=True)