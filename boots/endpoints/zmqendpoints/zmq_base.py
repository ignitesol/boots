'''
Created on 19-Jun-2012

@author: anand
'''
import functools
import logging
import socket
import re
from threading import Thread, RLock
from zmq.eventloop import ioloop

from boots import concurrency
if concurrency == 'gevent':
    import zmq.green as zmq
    ioloop.Poller = zmq.Poller
else:
    import zmq
    
from boots.common.threadpool import ThreadPool
from boots.endpoints.endpoint import EndPoint

class Locker(object):
    loop_lock = RLock()

class ZMQType:
    PUSH = zmq.PUSH
    PULL = zmq.PULL
    SUB = zmq.SUB
    PUB = zmq.PUB
    REP = zmq.REP
    REQ = zmq.REQ

# first, start a background ioloop thread and start ioloop
def iolooper():
    loop = ioloop_instance() # get the singleton
    logging.getLogger().debug('ioloop Started')
    loop.start()
    # This should execute once the start loop has ended
    # Which happens after its stop() method is called
    logging.getLogger().debug('ioloop Stopped')
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
t = Thread(target=iolooper, name="ZMQ_IOLOOP")
t.daemon = True
t.start()

class ZMQSocketTypeMap(object):
    types = {}
    __required__ = ['PUB', 'SUB', 'PUSH', 'PULL', 'REQ', 'REP']
    
    # The below two lines exist because incase of zmq.green
    # the true zmq.core elements are wrapped within
    # a fake zmq.core of zmq.green
    try: constants = zmq.core.constants
    except: constants = zmq.core.zmq.core.constants
    
    for k, v in vars(constants).iteritems():
        if type(v) is int and types.get(v) not in __required__: types[v] = k


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
        
        # split off the port to resolve hostname tcp://<host>:<port>
        gr = re.match("tcp://([^:]+):([0-9]+)", address)
        if gr is not None and len(gr.groups()) == 2:
            groups = gr.groups()
            address = "tcp://" + socket.gethostbyname(groups[0]) + ":" + groups[1] # No exception catching on purpose
            
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
        # self.server.logger.debug('Setup uuid: %s address: %s type: %s', self.uuid, self.address, ZMQSocketTypeMap.types[self.socket_type])
        self.socket = context_instance().socket(self.socket_type)
        return self.socket
    
    def start(self):
        """
        Binds or connects to the created socket as indicated by the constructor param bind
        Must only be called after setup
        """
        # self.server.logger.debug('Start uuid: %s address: %s type: %s bind: %s', self.uuid, self.address, ZMQSocketTypeMap.types[self.socket_type], self.bind)
        if self.bind: self.socket.bind(self.address)
        else: self.socket.connect(self.address)
        
    def send(self, data):
        """
        Sends data on the socket associated with this endpoint
        
        :param data: A string format message to send
        """
        if type(data) == str:
            data = [data]
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
            
        self.ioloop.add_callback(functools.partial(super(ZMQEndPoint, self).close, *(linger,), **kargs))

class ZMQListenEndPoint(ZMQEndPoint):
    """
    This is an Extension of the :class:`ZMQEndPoint` class.
    It implements a receive loop that runs the :attr:`ZMQBasePlugin.RECEIVE` Plugins serially
    """
    
    def __init__(self, socket_type, address, bind=False, plugins=[], threads=5, **kargs):
        """
        Constructor
        
        :param socket_type: Should be of a zmq socket type, no sanity checks are made
        :param address: The inproc, ipc, tcp or pgm address to use with the zmq socket
        :param bind=False: Instructs the zmq Socket to bind if set to True
        :param plugins: A list of plugins to be associated with this endpoint of the type ZMQBasePlugin
        :param threads: Number of threads to start the thread pool with
        """
        super(ZMQListenEndPoint, self).__init__(socket_type, address, bind=bind, plugins=plugins, **kargs)
        self.filters = []
        self._threads = threads
        self.receive_plugins = filter(lambda x: x.plugin_type & ZMQBasePlugin.RECEIVE, self.plugins)
        self._thread_pool = ThreadPool(processes=threads)
    
    def setup(self, extended_setup=[], **kargs):
        extended_setup += [(self._set_filter, [p]) for p in self.filters]
        super(ZMQListenEndPoint, self).setup(extended_setup=extended_setup , **kargs)
        
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
        #def _remove_handler():
        #    self.ioloop.remove_handler(self.socket)
        #extended_close.append(_remove_handler)
        super(ZMQListenEndPoint, self).close(linger=linger, extended_close=extended_close)
    
    def _recv_callback(self, socket, event):
        '''
        This will receive all messages
        '''
        # Ignore message that are not POLLIN
        if event is not zmq.POLLIN:
            return
        
        # Ignore messages on closed sockets
        if self.socket.closed:
            return
        
        try:
            n = self._threads
            while n:
                msg = socket.recv_multipart(flags=zmq.NOBLOCK)
                self._thread_pool.apply_async(self._recv_thread, args=(msg, self.receive_plugins))
                n -= 1
        except zmq.ZMQError as e: 
            if e.errno is not zmq.EAGAIN: 
                raise
    
    def _recv_thread(self, msg, plugins):
        for p in plugins:
            try: 
                msg = p.apply(msg)
            except Exception as e: self.server.logger.exception('Error %s - %s ', p, e)
        self.callback(msg)
    
    def add_filter(self, pattern):
        """
        :param pattern: The pattern to discern between which messages to drop and which to accept
        :type pattern: String
        """
        pattern = pattern.encode('utf-8')
        if self.socket_type != zmq.SUB: raise TypeError('Only subscribe sockets may have filters')
        if pattern not in self.filters: self.filters += [pattern]
        if self._activated:
            self.ioloop.add_callback(functools.partial(self._set_filter, pattern))
    
    def _set_filter(self, pattern):
        """
        :param pattern: The pattern to discern between which messages to drop and which to accept
        :type pattern: String
        """
        self.socket.setsockopt(zmq.SUBSCRIBE, pattern)
    
    def remove_filter(self, pattern):
        pattern = pattern.encode('utf-8')
        if self.socket_type != zmq.SUB: raise TypeError('Only subscribe sockets may have filters')
        if pattern in self.filters:
            self.filters.remove(pattern)
            if self._activated:
                self.ioloop.add_callback(functools.partial(self._drop_filter, pattern))
    
    def _drop_filter(self, pattern):
        """
        :param pattern: The pattern to discern between which messages to drop and which to accept
        :type pattern: String
        """
        self.socket.setsockopt(zmq.UNSUBSCRIBE, pattern)
    
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