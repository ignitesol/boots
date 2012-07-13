'''
Created on 19-Jun-2012

@author: anand
'''
from threading import Thread, RLock
import zmq
from zmq.eventloop import ioloop
from fabric.endpoints.endpoint import EndPoint
import functools
import threading
from multiprocessing.pool import ThreadPool
import multiprocessing

class Locker(object):
    loop_lock = RLock()

# first, start a background ioloop thread and start ioloop
def iolooper():
    loop = ioloop_instance() # get the singleton
    print 'ioloop Started', id(loop)
    loop.start()
    # This should execute once the start loop has ended
    # Which happens after its stop() method is called
    try: loop.close(True)
    except ValueError: pass 
    
def close_ioloop():
    ioloop_instance().stop()

def context_instance():
    return zmq.Context.instance()

def ioloop_instance():
    with Locker.loop_lock:
        return ioloop.IOLoop.instance()

def cleanup_zmq():
    close_ioloop()
    context_instance().destroy(linger=1)

# This eliminates the race condition within ioloops instance() method
# incase of threads
ioloop_instance() 
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
        
        :param socket_type: Should be of a zmq socket type, no sanity checks are made
        :param address: The inproc, ipc, tcp or pgm address to use with the zmq socket
        :param bind=False: Instructs the zmq Socket to bind if set to True
        '''
        super(ZMQBaseEndPoint, self).__init__(**kargs)
        self.bind = bind
        self.address = address
        self.socket_type = socket_type
        self.socket = None
        self._activated = False
    
    def activate(self):
        """
        Should be called when endpoints are being activated
        This is turn calls setup and start
        """
        if self._activated: return False
        
        self.setup()
        self.start()
        self._activated = True
        return True
    
    def setup(self):
        """
        Creates the zmq Socket with the socket_type given in the constructor
        """
        # should we be locking this
        print 'Setup ', self.uuid
        self.socket = context_instance().socket(self.socket_type)
        return self.socket
    
    def start(self):
        """
        Binds or connects to the created socket as indicated by the constructor param bind
        Must only be called after setup
        """
        print 'Start ', self.uuid
        if self.bind: self.socket.bind(self.address)
        else: self.socket.connect(self.address)
        
    def send(self, data):
        """
        Sends data on the socket associated with this endpoint
        
        :param data: A string format message to send
        """
        # print 'sending', data
        self.socket.send_multipart(data)
    
    def close(self, linger=1):
        self.socket.close(linger=linger)
        super(ZMQBaseEndPoint, self).close()

class ZMQEndPoint(ZMQBaseEndPoint):
    '''
    This class leverages eventloops ioloop callbacks
    All ZMQBaseEndPoint methods are wrapped within the ioloop callbacks
    This ensures we run from the ioloop thread
    '''
    def __init__(self, socket_type, address, bind=False, plugins=[], **kargs):
        '''
        Constructor
        
        :param socket_type: Should be of a zmq socket type, no sanity checks are made
        :param address: The inproc, ipc, tcp or pgm address to use with the zmq socket
        :param bind: Instructs the zmq Socket to bind if set to True
        :param plugins: A list of plugins to be associated with this endpoint of the type ZMQBasePlugin
        '''
        super(ZMQEndPoint, self).__init__(socket_type, address, bind=bind, **kargs)
        self.ioloop = ioloop_instance()
        self.plugins = plugins
        self.send_plugins = filter(lambda x: x.plugin_type & ZMQBasePlugin.SEND, self.plugins)
        self.send_fn = super(ZMQEndPoint, self).send
        
    def setup(self, extended_setup=[]):
        """
        Calls back the :class:`ZMQBaseEndpoint` :func:`setup` using the ioloop callback handler
        
        It also sets up the :class:`ZMQBasePlugin` extensions associated with this EndPoint and for all SEND Plugins
        does the :func:`apply`
        """
        self.ioloop.add_callback(super(ZMQEndPoint, self).setup)
        for s in extended_setup:
            if callable(s): self.ioloop.add_callback(s)
            elif type(s) is tuple and len(s) == 2: self.ioloop.add_callback(functools.partial(s[0], *s[1]))
            elif type(s) is tuple and len(s) == 3: self.ioloop.add_callback(functools.partial(s[0], *s[1], **s[2]))
             
        for p in self.plugins:
            p.setup(self) 
            if p in self.send_plugins: self.send_fn = p.apply(self.send_fn)

    def start(self, extended_start=[]):
        """
        Calls back the :class:`ZMQBaseEndpoint` :func:`start` using the ioloop callback handler
        """
        self.ioloop.add_callback(super(ZMQEndPoint, self).start)
        
        for s in extended_start:
            if callable(s): self.ioloop.add_callback(s)
            elif type(s) is tuple and len(s) == 2: self.ioloop.add_callback(functools.partial(s[0], *s[1]))
            elif type(s) is tuple and len(s) == 3: self.ioloop.add_callback(functools.partial(s[0], *s[1], **s[2]))
    
    def send(self, *args, **kargs):
        """
        Runs the SEND plugins associated with this endpoint
        Calls back the parent send using the ioloop callback handler
        
        :param args: Only this is sent to the parent send
        :param kargs: Should be consumed by the SEND plugins and formatted into the args paramater
        """
        self.ioloop.add_callback(functools.partial(self.send_fn, *args, **kargs))
    
    def close(self, linger=1, extended_close=[], **kargs):
        for s in extended_close:
            if callable(s): self.ioloop.add_callback(s)
            elif type(s) is tuple and len(s) == 2: self.ioloop.add_callback(functools.partial(s[0], *s[1]))
            elif type(s) is tuple and len(s) == 3: self.ioloop.add_callback(functools.partial(s[0], *s[1], **s[2]))
            
        self.ioloop.add_callback(functools.partial(super(ZMQEndPoint, self).close, (linger,), **kargs))

class ZMQListenEndPoint(ZMQEndPoint):
    """
    This is an Extension of the :class:`ZMQEndPoint` class.
    It implements a receive loop that runs the :attr:`ZMQBasePlugin.RECEIVE` Plugins serially
    """
    
    def __init__(self, socket_type, address, bind=False, plugins=[], threads=1, **kargs):
        """
        Constructor
        
        :param socket_type: Should be of a zmq socket type, no sanity checks are made
        :param address: The inproc, ipc, tcp or pgm address to use with the zmq socket
        :param bind=False: Instructs the zmq Socket to bind if set to True
        :param plugins: A list of plugins to be associated with this endpoint of the type ZMQBasePlugin
        :param threads: Number of threads to start the thread pool with
        """
        super(ZMQListenEndPoint, self).__init__(socket_type, address, bind=bind, plugins=plugins, **kargs)
        self._threads = threads
        self.receive_plugins = filter(lambda x: x.plugin_type & ZMQBasePlugin.RECEIVE, self.plugins)
        self._thread_pool = ThreadPool(processes=threads)
        
    def start(self, extended_start=[]):
        """
        call this to bind or connect the socket
        """
        super(ZMQListenEndPoint, self).start(extended_start=extended_start)
        # Closure is required here since we utilise the socket outside the loop thread
        def _add_handler():
            self.ioloop.add_handler(self.socket, self._recv_callback, zmq.POLLIN)
        self.ioloop.add_callback(_add_handler)
        
    def close(self, linger=1, extended_close=[]):
        """
        """
        def _remove_handler():
            self.ioloop.remove_handler(self.socket)
        extended_close.append(_remove_handler)
        super(ZMQListenEndPoint, self).close(linger=linger, extended_close=extended_close)
    
    def _recv_callback(self, socket, event):
        '''
        This will receive all messages
        '''
        assert event == zmq.POLLIN
        
        msg = socket.recv_multipart()
        self._thread_pool.apply_async(self._recv_thread, args=(msg, self.receive_plugins))
    
    def _recv_thread(self, msg, plugins):
        
        for p in plugins:
            try: msg = p.apply(msg)
            except Exception as e: print 'Error', p, e
        self.callback(msg)
    
    def add_filter(self, pattern):
        """
        :param pattern: The pattern to discern between which messages to drop and which to accept
        :type pattern: String
        """
        if self.socket_type != zmq.SUB: raise TypeError('Only subscribe sockets may have filters')
        def _filter():
            self.socket.setsockopt(zmq.SUBSCRIBE, pattern)
        self.ioloop.add_callback(_filter)
    
    def callback(self, msg):
        pass
        
class ZMQBasePlugin(object):
    """
    This is Base ZMQ Plugin class, inherit this for every Plugin class
    
    Plugins are of type :attr:`ZMQBasePlugin.SEND` and :attr:`ZMQBasePlugin.RECEIVE`,
    as should be represented by the internal :attr:`_plugin_type_` attribute
    
    :attr:`ZMQBasePlugin.SEND` type plugins are invoked serially before a message is sent on the ZMQ Socket
    
    :attr:`ZMQBasePlugin.RECEIVE` type plugins are invoked serially after a message is received on the ZMQ Socket
    """
    SEND, RECEIVE = 1, 2
    _plugin_type_ = None
    
    def __init__(self):
        """
        :raises: TypeError if _plugin_type_ is not defined in the Plugin Class
        """
        if self.__class__._plugin_type_ is None: raise TypeError('The Plugin Class must have a _plugin_type_ set to either 1)SEND or 2)RECEIVE')
    
    def setup(self, endpoint):
        """
        To be overwritten by the Plugin Class.
        This method will be called when the endpoint is instantiated
        
        :param endpoint: The endpoint instance containing this Plugin Class
        """
        self.endpoint = endpoint
        if self.__class__._plugin_type_ == self.__class__.SEND: self.apply(endpoint.send)
    
    def apply(self, *args, **kargs): #@ReservedAssignment
        """
        This method is called every time the Plugin is to be invoked.
        
        **In case of a** :attr:`ZMQBasePlugin.SEND` **type plugin**
        
        :param args: Iterable that is passed on from the :func:`ZMQEndpoint.send()` method or preceding Plugins, this is the final set sent from :func:`ZMQBaseEndpoint.send()`
        :param kargs: :class:`Dictionary` passed on from the :func:`ZMQEndpoint.send()` method, these are ignored by :func:`ZMQBaseEndpoint.send()`, any useful data must be integrated into the `args` parameter
        :returns: tuple (args, kargs)
        
        The :func:`apply` method MUST be of a decorator form, wrapping the send callback, for example::
        
            def apply(self, callback):
                '''
                The overridden apply function
                '''
                @wraps(callback)
                def _apply(*args, **kargs):
                    '''
                    Receiving args and kargs from previous plugins or from the server
                    As an example we want to send the message in the form 'args-kargs'
                    '''
                    msg = args and reduce(lambda x, y: '%s%s'%(x,y),args)
                    if kargs: msg = msg + '-' + json.dumps(kargs)
                    callback(msg) # This is the send callback to be invoked
        
        All the SEND Plugins are invoked from within the thread containing the ZMQ Socket, so using the Socket data structures is safe
        
        
        **In case of a** :attr:`ZMQBasePlugin.RECEIVE` **type plugin**
        
        :param msg: String data received form the ZMQ Socket, or any other type passed through from preceding Plugins
        
        :raises: AttributeError if not overridden by the Plugin Classes
        """
        raise AttributeError('The apply() method must be overridden by the Plugin Class')
        
    @property
    def plugin_type(self):
        return self.__class__._plugin_type_
        
if __name__ == '__main__':
    pass
