'''
Created on 18-Jun-2012

@author: rishi
'''
from fabric.endpoints.zmqendpoints.zmq_base import ZMQBaseEndPoint
import zmq
from zmq.eventloop import ioloop
from fabric.common.zmq_socket_management import ZMQLoopManagement

class ZMQLoopEndPoint(ZMQBaseEndPoint):
    '''
    classdocs
    '''

    def __init__(self, socket_type, address, bind=False):
        '''
        Constructor
        '''
        super(ZMQLoopEndPoint, self).__init__(socket_type, address, bind=bind)
        self.loop = ioloop.IOLoop.instance()
    
    def add_message_handler(self, handler, events):
        self.loop.add_handler(self.socket, handler, events)
    
    def start(self):
        super(ZMQLoopEndPoint, self).start()
        self.loop.start()
        
    def stop(self):
        self.loop.stop()

class ZMQManagedLoopEndpoint(ZMQBaseEndPoint):
    
    def __init__(self, socket_type, address, internal_address, bind=False):
        super(ZMQManagedLoopEndpoint, self).__init__(socket_type, address, bind=bind)
        
        self.internal_address = internal_address
        self.in_socket = None
        self.out_socket = None
        self.manager = ZMQLoopManagement.instance()
        
    def setup(self):
        super(ZMQManagedLoopEndpoint, self).setup()
        self.in_socket = self.context.socket(zmq.PULL)
        self.in_socket.connect('inproc://req_%s'%self.internal_address)
        self.out_socket = self.context.socket(zmq.PUSH)
        self.out_socket.connect('inproc://rep_%s'%self.internal_address)
    
    def run(self):
        self.start()
        
    def start(self):
        self.setup()
        self.loop.add_handler(self.socket, self.forward_message, zmq.POLLIN)
        self.loop.add_handler(self.in_socket, self.handle_directive, zmq.POLLIN)
        super(ZMQManagedLoopEndpoint, self).start()
    
    def forward_message(self, sock, event):
        msg = ['forward']
        msg.extend(sock.recv_multipart())
        self.out_socket.send_multipart(msg)
    
    def add_message_handler(self, *args):
        raise TypeError('Cannot add direct handlers to a threaded ZMQ Endpoints')