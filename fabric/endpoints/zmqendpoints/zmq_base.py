'''
Created on 19-Jun-2012

@author: anand
'''
from threading import Thread
import threading
import zmq
from zmq.eventloop import ioloop
from fabric.endpoints.endpoint import EndPoint
import functools

# first, start a background ioloop thread and start ioloop
def iolooper():
    loop = ioloop.IOLoop.instance() # get the singleton
    print 'ioloop Started', id(loop)
    loop.start()

# This eliminates the race condition within ioloops instance() method
# incase of threads
ioloop.IOLoop.instance() 
t = Thread(target=iolooper)
t.daemon = True
t.start()

class ZMQBaseEndPoint(EndPoint):
    '''
    The ZMQ Socket Base class
    All socket functionalities are wrapped within this and sub classes
    Keeping the complexity of the functionality away from server writers
    '''
    def __init__(self, socket_type, address, bind=False, **kargs):
        '''
        Constructor
        '''
        super(ZMQBaseEndPoint, self).__init__(**kargs)
        self.bind = bind
        self.address = address
        self.socket_type = socket_type
        self.socket = None
    
    def activate(self):
        self.setup()
        self.start()
    
    def setup(self):
        # should we be locking this
        print 'Setup ', self.uuid
        self.socket = zmq.Context.instance().socket(self.socket_type)
        return self.socket
    
    def start(self):
        print 'Start ', self.uuid
        if self.bind: self.socket.bind(self.address)
        else: self.socket.connect(self.address)
        
    def send(self, data):
        print 'sending', data
        self.socket.send(data)

class ZMQEndPoint(ZMQBaseEndPoint):
    '''
    This class leverages eventloops ioloop callbacks
    All ZMQBaseEndPoint methods are wrapped within the ioloop callbacks
    This ensures we run from the ioloop thread
    '''
    def __init__(self, socket_type, address, bind=False, plugins=[], **kargs):
        '''
        Constructor
        '''
        super(ZMQEndPoint, self).__init__(socket_type, address, bind=bind, **kargs)
        self.ioloop = ioloop.IOLoop.instance()
        self.plugins = plugins
        self.send_plugins = filter(lambda x: x.plugin_type & ZMQBasePlugin.SEND, self.plugins)
        print 'ioloop instance', id(self.ioloop)
        
    def setup(self):
        self.ioloop.add_callback(super(ZMQEndPoint, self).setup)

    def start(self):
        self.ioloop.add_callback(super(ZMQEndPoint, self).start)
    
    def send(self, *args, **kargs):
        for p in self.send_plugins: args, kargs = p(*args, **kargs)
        self.ioloop.add_callback(functools.partial(super(ZMQEndPoint, self).send, args))

class ZMQListenEndPoint(ZMQEndPoint):
    
    def __init__(self, socket_type, address, bind=False, plugins=[], **kargs):
        super(ZMQListenEndPoint, self).__init__(socket_type, address, bind=bind, plugins=plugins)
        self.receive_plugins = filter(lambda x: x.plugin_type & ZMQBasePlugin.RECEIVE, self.plugins)
        self._path_callbacks = dict()
        
    def start(self):
        super(ZMQListenEndPoint, self).start()
        # Closure is required here since we utilise the socket outside the loop thread
        def _add_handler():
            self.ioloop.add_handler(self.socket, self._recv_callback, zmq.POLLIN)
        self.ioloop.add_callback(_add_handler)
    
    def _recv_callback(self, socket, event):
        '''
        This will receive all messages
        '''
        assert event == zmq.POLLIN
        
        msg = socket.recv()
        for p in self.receive_plugins:
            try: msg = p(msg)
            except Exception as e: print 'Error', e

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
        
        if type(args) is not tuple: args = tuple(args)
        threading.Thread(target=callback, args=args, kwargs=kwargs).start()
        
    def register_path_callback(self, path, callback):
        self._path_callbacks[path] = callback

class ZMQBasePlugin(object):
    
    SEND, RECEIVE = 1, 2
    _plugin_type_ = None
    
    def __init__(self):
        if self.__class__._plugin_type_ is None: raise TypeError('The Plugin Class must have a _plugin_type_ set to either 1)SEND or 2)RECEIVE')
        
    @property
    def plugin_type(self):
        return self.__class__._plugin_type_
        
if __name__ == '__main__':
    pass
