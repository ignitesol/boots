'''
Created on 20-Jun-2012

@author: rishi
'''
import zmq
from fabric.endpoints.zmqendpoints.zmq_base import ZMQEndPoint

class ZMQBasePlugin(object):
    
    def __init__(self):
        pass
    
class ZMQRequestParams(ZMQBasePlugin):
    
    def __init__(self, *args, **kargs):
        super(ZMQRequestParams, self).__init__(*args, **kargs)
    
    def __call__(self, msg):
        pass

class ZMQSubscribeEndpoint(ZMQEndPoint):
    
    def __init__(self, address, bind=False, **kargs):
        super(ZMQSubscribeEndpoint, self).__init__(zmq.SUB, address, bind=bind, **kargs)
    
    def add_filter(self, pattern):
        def _filter():
            self.socket.setsockopt(zmq.SUBSCRIBE, pattern)
        self.ioloop.add_callback(_filter)
#        self.ioloop.add_callback(functools.partial(self.socket.setsockopt, args=(zmq.SUBSCRIBE, pattern)))