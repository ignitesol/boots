'''
Created on 19-Jun-2012

@author: anand
'''
from threading import RLock, Thread
import threading
import zmq
from zmq.eventloop import ioloop
import time
from fabric.endpoints.endpoint import EndPoint
import functools
from zmq.utils import jsonapi

tdata = threading.local()

def get_threadlocal():
    global tdata
    return tdata

# first, start a background ioloop thread and start ioloop
def iolooper():
    data = get_threadlocal()
    data.sockhash = {}
    loop = ioloop.IOLoop.instance() # get the singleton
    print 'ioloop Started'
    loop.start()

t = Thread(target=iolooper)
t.daemon = True
t.start()
time.sleep(0.1)

class ZMQBaseEndPoint(EndPoint):
    '''
    The ZMQ Socket Base class
    All socket functionalities are wrapped within this and sub classes
    Keeping the complexity of the functionality away from server writers
    '''
    def __init__(self, socket_type, address, bind=False):
        '''
        Constructor
        '''
        super(ZMQBaseEndPoint, self).__init__()
        self.bind = bind
        self.address = address
        self.socket_type = socket_type
        self.socket = None
    
    def setup(self):
        # should we be locking this
        self.socket = zmq.Context.instance().socket(self.socket_type)
        return self.socket
    
    def start(self):
        if self.bind: self.socket.bind(self.address)
        else: self.socket.connect(self.address)
        
    def send(self, args, kargs):
        msg = args and reduce(lambda x, i: str(x)+' '+str(i), args)
        if kargs: msg = msg + ' ' + jsonapi.dumps(kargs)
        self.socket.send(msg)

class ZMQManagedEndPoint(ZMQBaseEndPoint):
    '''
    This class leverages eventloops ioloop callbacks
    All ZMQBaseEndPoint methods are wrapped within the ioloop callbacks
    This ensures we run from the ioloop thread
    '''

    lock = RLock()
    
    def __init__(self, socket_type, address, bind=False):
        '''
        Constructor
        '''
        super(ZMQManagedEndPoint, self).__init__(socket_type, address, bind=bind)
        self.ioloop = ioloop.IOLoop.instance()
        
    def setup(self):
        self.ioloop.add_callback(super(ZMQManagedEndPoint, self).setup)

    def start(self):
        self.ioloop.add_callback(super(ZMQManagedEndPoint, self).start)
    
    def send(self, *args, **kargs):
        self.ioloop.add_callback(functools.partial(super(ZMQManagedEndPoint, self).send, *args, **kargs))

class ZMQListenEndPoint(ZMQManagedEndPoint):
    
    def __init__(self, socket_type, address, bind=False):
        super(ZMQListenEndPoint, self).__init__(socket_type, address, bind=bind)
        self._path_callbacks = dict()
        
    def start(self):
        super(ZMQListenEndPoint, self).start()
        self.ioloop.add_callback(functools.partial(self.ioloop.add_handler, args=(self.socket, self._recv_callback, zmq.POLLIN)))
    
    def _recv_callback(self, socket, event):
        assert event == zmq.POLLIN
        
        msg = socket.recv_json()
        print msg
        
        try : path = msg['path']
        except KeyError:
            print 'No Path Found'
            return
        
        try: callback = self._path_callbacks[path]
        except KeyError:
            print 'No Path Callback Found'
            return
        
        # Args should be sent as a tuple
        args = msg.get('args', None)
        # Kargs as a dictionary
        kwargs = msg.get('kwargs', None)
            
        threading.Thread(target=callback, args=args, kwargs=kwargs).start()
        
    def register_path_callback(self, path, callback):
        self._path_callbacks[path] = callback

        
if __name__ == '__main__':
    pass
