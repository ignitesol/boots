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
    ZMQJsonReply, ZMQJsonRequest, ZMQCallbackPattern, ZMQCoupling

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
                                                 plugins=[ZMQJsonReply(), ZMQCallbackPattern(callback_depth=ZMQCallbackPattern.SERVER), ZMQCoupling('pull_pub')], server=self)
        self.pub_endpoint = ZMQEndPoint(zmq.PUB, pub_address, bind=True, plugins=[ZMQJsonRequest(), ZMQCoupling('pull_pub', process_context=self)], server=self)
        
        self.add_endpoint(self.listen_endpoint)
        self.add_endpoint(self.pub_endpoint)
        
        self.start_main_server()
    
    def start_main_server(self):
        print 'starting server'
        super(ZMQPullPubServer, self).start_main_server()
    
    @ZMQCallbackPattern.ZMQPatternRoute(zmq.PULL, 'ipc:///tmp/zpydealer', 'benchmark')
    def callback_fn(self, msg):
        """
        Callback function of receiving a message with "path" : "benchmark"
        
        Re-routes message to the Publish Endpoint
        """
#        self.send_from_endpoint(self.pub_endpoint.uuid, '1', args=(msg,), path='*')
        pass
    
    @ZMQCoupling.CoupledProcess('pull_pub')
    def process_fn(self, msg):
        print msg
        msg['path'] = '*'
        return '', msg
        
        
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
        super(ZMQSubscribeServer, self).__init__(**kargs)
        
        self.sub_endpoint = ZMQSubscribeEndPoint(sub_address, server=self)
        self.add_endpoint(self.sub_endpoint)
        self.start_main_server()
        self.sub_endpoint.add_filter(sub_filter)
    
    @ZMQCallbackPattern.ZMQPatternRoute(zmq.SUB, 'tcp://127.0.0.1:9876', '*')
    def printme(self, msg):
        print 'Subscription received', msg
        
if __name__ == '__main__':
        
    zsubserver = ZMQSubscribeServer('tcp://127.0.0.1:9876', '')
    zpubserver = ZMQPullPubServer('tcp://*:9876', 'ipc:///tmp/wormhole-in')
        
    time.sleep(2000)
    
#    try: t.join()
#    except: pass