'''
Created on 20-Jun-2012

@author: rishi
'''
import zmq
from fabric.endpoints.zmqendpoints.zmq_base import ZMQListenEndPoint
import functools

class ZMQSubscribEndpoint(ZMQListenEndPoint):
    
    def __init__(self, address, bind=False):
        super(ZMQSubscribEndpoint, self).__init__(zmq.SUB, address, bind=bind)
    
    def add_filter(self, pattern):
        self.ioloop.add_callback(functools.partial(self.socket.setsockopt, args=(zmq.SUBSCRIBE, pattern)))