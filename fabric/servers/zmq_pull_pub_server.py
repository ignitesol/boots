'''
Created on 14-Jun-2012

@author: rishi
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
from fabric.endpoints.zmqendpoints.zmq_endpoints import ZMQSubscribeEndpoint,\
    ZMQJsonReply, ZMQJsonRequest, ZMQCallbackPattern

class ZMQPullPubServer(ZMQServer):
    '''
    classdocs
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
        self.send_from_endpoint(self.pub_endpoint.uuid, '1', args=(msg,), path='*')
    
    def start_main_server(self):
        print 'starting server'
        super(ZMQPullPubServer, self).start_main_server()
        
class ZMQSubscribeServer(ZMQServer):
    def __init__(self, sub_address, sub_filter, *args, **kargs):
        super(ZMQSubscribeServer, self).__init__(server=self, **kargs)
        
        self.sub_endpoint = ZMQSubscribeEndpoint(sub_address, callback_hash={'*': self.printme})
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