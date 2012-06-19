'''
Created on 18-Jun-2012

@author: rishi
'''
from fabric.common.utils import generate_uuid
import zmq
import threading
from fabric.endpoints.zmqendpoints.zmq_base import ZMQBaseEndPoint
from zmq.eventloop.ioloop import IOLoop

class ZMQSocketManagement(threading.Thread):
    '''
    classdocs
    '''
    _instance = None
    _sockets = dict()

    def __init__(self):
        '''
        Constructor
        '''
        if self.__class__._instance is not None:
            raise TypeError('ZMQSocketManagement is a Singleton Object, please use the instance() method')
        self.__class__._instance = self
        
        self._has_started = False
        self._callback_list = dict()
        
        self.internal_address = "inproc://comm-%s"%generate_uuid()
        self.internal_socket = zmq.Context.instance().socket(zmq.REQ)
        self.internal_socket.bind(self.internal_address)
        
        self.register_socket(0, zmq.REQ, self.internal_address)
    
    @classmethod
    def instance(cls):
        if cls._instance is None: 
            cls._instance = ZMQSocketManagement()
        return cls._instance
    
    def register_socket(self, uuid, socket_type, address, bind=False):
        if not uuid: uuid = generate_uuid()
        self.__class__._sockets.setdefault(uuid, [])
        self.__class__._sockets[uuid] = [socket_type, address, bind]
    
    def register_callback_to_socket(self, uuid, callback, filter='*'):
        self._callback_list.setdefault(uuid, dict())
        self._callback_list[uuid][filter] = callback
        
    def start(self):
        if self._has_started: raise Exception('Socket Management is already running')
        self._has_started = True
        
        def worker_thread(sockets, internal_address):
            def message_callback(sock, event):
                pass
            
            loop = IOLoop.instance()
            endpoints = []
            
            for ids in sockets:
                # list is of the form [type, address, bind]
                sock = ZMQBaseEndPoint(sockets[ids][0], sockets[ids][1], sockets[ids][2])
                sock.setup()
                sock.start()
                if sock.socket_type in [zmq.PUSH, zmq.REQ, zmq.REP, zmq.SUB]:
                    loop.add_handler(sock, message_callback, zmq.POLLIN)
                
                