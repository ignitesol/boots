'''
Created on 18-Jun-2012

@author: rishi
'''
from fabric.common.utils import generate_uuid
import zmq
import threading
from fabric.endpoints.zmqendpoints.zmq_base import ZMQBaseEndPoint
from zmq.eventloop.ioloop import IOLoop

class ZMQLoopManagement(threading.Thread):
    '''
    classdocs
    '''
    _instance = None

    def __init__(self):
        '''
        Constructor
        '''
        if self.__class__._instance is not None:
            raise TypeError('ZMQLoopManagement is a Singleton Object, please use the instance() method')
        self.__class__._instance = self
        
        self._has_started = False
        self._callback_list = dict()
        self.worker = None
        
    @classmethod
    def instance(cls):
        if cls._instance is None: 
            cls._instance = ZMQLoopManagement()
        return cls._instance
    
    def register_socket(self, uuid, socket_type, address, bind=False):
        self.__class__._sockets.setdefault(uuid, [])
        self.__class__._sockets[uuid] = [socket_type, address, bind]
        if self._has_started:
            IOLoop.instance().add_callback(self.worker_create_socket)
#            self.internal_socket.send_multipart(['create', uuid, socket_type, address, bind])
    
    def register_callback_to_socket(self, uuid, callback, filter='*'):
        self._callback_list.setdefault(uuid, dict())
        self._callback_list[uuid][filter] = callback
        if self._has_started:
            IOLoop.instance().add_callback(self.worker_closure_callback)
#            self.internal_socket.send_multipart(['newcallback', uuid, filter, callback])
        
    def start(self):
        if self._has_started: raise Exception('Socket Management is already running')
        
        # The main worker thread that does the listen poll
        def worker_thread(sockets, internal_address, callback_list):
            loop = IOLoop.instance()
            endpoints = {}
            
            # Lets hope the callback dictionary stays closed
            # Because the KGB needs a key
            def closure_callback(sock, callbacks):
                def message_callback(sock, event):
                    msg = sock.recv_multipart()
                    # no filters for now only one callback
                    threading.Thread(target=callbacks['*'], args=(msg)).start()
                loop.add_handler(sock, message_callback, zmq.POLLIN)
            
            def create_socket(sockets):
                for ids in sockets:
                    # list is of the form [type, address, bind]
                    sock = ZMQBaseEndPoint(sockets[ids][0], sockets[ids][1], sockets[ids][2])
                    sock.setup()
                    sock.start()
                    endpoints[ids] = sock
                    if sock.socket_type in [zmq.PULL, zmq.REQ, zmq.REP, zmq.SUB]:
                        try: closure_callback(sock.socket, callback_list[ids])
                        except KeyError: pass
            
            # For the main thread to use as a callback
            # Closures should keep the threads honest
            self.worker_create_socket = create_socket
            self.worker_closure_callback = closure_callback
            
            # Directive Socket
            directive_socket = ZMQBaseEndPoint(zmq.PULL, internal_address)
            directive_socket.setup()
            directive_socket.start()
            
            # Special callback for internal directives
            def directive_callback(sock, event):
                msg = sock.recv_multipart()
                if msg[0] == 'create':
                    # create an endpoint from { uuid : [type, address, bind]}
                    create_socket({msg[1]:msg[2:]})
                elif msg[0] == 'newcallback':
                    # new callback for an endpoint
                    # Of the format [uuid]
                    callback_list[msg[1]][msg[2]] = msg[3]
                    closure_callback(endpoints[msg[1]], msg[3])
            
            loop.add_handler(directive_socket.socket, directive_callback, zmq.POLLIN)                        
            create_socket(sockets)
            loop.start()
        
        self.worker = threading.Thread(target=worker_thread, args=(self.__class__._sockets, self.internal_address, self._callback_list))
        self._has_started = True
        self.worker.start()
        