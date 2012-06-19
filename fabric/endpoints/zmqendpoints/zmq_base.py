'''
Created on 18-Jun-2012

@author: rishi
'''
import zmq
from fabric.endpoints.endpoint import EndPoint

class ZMQBaseEndPoint(EndPoint):
    '''
    classdocs
    '''

    def __init__(self, socket_type, address, bind=False):
        '''
        Constructor
        '''
        super(ZMQBaseEndPoint, self).__init__()
        self.bind = bind
        self.address = address
        self.socket_type = socket_type
        self.context = None
        self.socket = None
    
    def setup(self):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(self.socket_type)        
        
    def start(self):
        if self.bind: self.socket.bind(self.address)
        else: self.socket.connect(self.address)