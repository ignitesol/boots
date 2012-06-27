'''

'''

import os,sys
import zmq
import time

FILE = os.path.abspath(__file__) if not hasattr(sys, 'frozen') else os.path.abspath(sys.executable)  
DIR = os.path.dirname(FILE)
PROJ_DIR = os.path.abspath(DIR + os.sep + '../')  # we are 2 level deeper than the project root
os.chdir(PROJ_DIR)              # chdir one level up

PROJ_DIR = os.path.abspath(DIR + os.sep + '../..')  # we are 2 level deeper than the project root
sys.path.append(PROJ_DIR)  if not hasattr(sys, 'frozen') else sys.path.append(DIR)

from fabric.servers.zmqserver import ZMQServer
from fabric.endpoints.zmqendpoints.zmq_base import ZMQEndPoint, t,\
    ZMQListenEndPoint
from fabric.endpoints.zmqendpoints.zmq_endpoints import ZMQSubscribeEndPoint,\
    ZMQJsonReply, ZMQJsonRequest, ZMQCallbackPattern

class ZMQPullPubServer(ZMQServer):
    '''
    A :py:class:`ZMQServer` Extension, containing two :py:class:`ZMQEndPoint`'s
    
    1. :py:class:`ZMQListenEndPoint` of type :py:attr:`zmq.PULL`, `bind` is :py:attr:`True`
        **Plugins**
    
        - ZMQJsonReply
        - ZMQCallbackPattern
    2. :py:class:`ZMQEndPoint` of type :py:attr:`zmq.PUB`, `bind` is :py:attr:`True`
        **Plugins**
        
        - ZMQJsonRequest
    '''
    def __init__(self, pub_address, pull_address, *args, **kargs):
        '''
        Constructor
        '''
        super(ZMQPullPubServer, self).__init__(name="PullPubServer", **kargs)
        
        self.listen_endpoint = ZMQListenEndPoint(zmq.PULL, pull_address, bind=True, 
                                                 plugins=[ZMQJsonReply(), ZMQCallbackPattern(callback_hash={'benchmark': self.callback_fn})], server=self)
        self.pub_endpoint = ZMQEndPoint(zmq.PUB, pub_address, bind=True, plugins=[ZMQJsonRequest()], server=self)
        
        self.add_endpoint(self.listen_endpoint)
        self.add_endpoint(self.pub_endpoint)
        
        self.start_main_server()
    
    def callback_fn(self, msg):
        """
        Callback function of receiving a message with "path" : "benchmark"
        
        Re-routes message to the Publish Endpoint
        """
        self.send_from_endpoint(self.pub_endpoint.uuid, '1', args=(msg,), path='*')
    
    def start_main_server(self):
        print 'starting server'
        super(ZMQPullPubServer, self).start_main_server()
        
class ZMQSubscribeServer(ZMQServer):
    """
    A :class:`ZMQServer` Extension, containing one :class:`ZMQEndPoint`
    
    1. :class:`ZMQSubscribeEndPoint`
        **Plugins**
        
        - ZMQCallbackPattern
    """
    def __init__(self, sub_address, sub_filter, *args, **kargs):
        """
        Constructor
        
        :param sub_address: Subscribe address
        :param sub_filter: The default filter to be used on the Subscribe Socket
        """
        super(ZMQSubscribeServer, self).__init__(server=self, **kargs)
        
        self.sub_endpoint = ZMQSubscribeEndPoint(sub_address, callback_hash={'*': self.printme})
        self.add_endpoint(self.sub_endpoint)
        self.start_main_server()
        self.sub_endpoint.add_filter(sub_filter)
    
    def printme(self, msg):
        print 'Subscription received', msg
        
if __name__ == '__main__':
    zserver = ZMQSubscribeServer('tcp://127.0.0.1:9876', '')
    zserver = ZMQPullPubServer('tcp://*:9876', 'ipc:///tmp/zpydealer')
    time.sleep(2)
#    try: t.join()
#    except: pass