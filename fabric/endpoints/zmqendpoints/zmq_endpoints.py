'''
Custom ZMQ Endpoints and Plugins to be used within the ZMQ Servers

'''
import json
import zmq

from fabric.endpoints.zmqendpoints.zmq_base import ZMQBasePlugin,\
    ZMQListenEndPoint, ioloop_instance
from functools import wraps
from fabric.common.messenger import ZMQSPARXMessage
from twisted.python.reflect import isinst
        
class ZMQJsonReply(ZMQBasePlugin):
    """
    ZMQ RECEIVE Plugin that Jsonifies the data
    
    Expected argument list: message
    Expected message format: [.*, ...., {.*}]
    
    The leading and trailing strings outside the braces will be stripped
    Anything within the braces will be jsonified and returned including the braces themselves
    """
    _plugin_type_ = ZMQBasePlugin.RECEIVE

    def apply(self, msg): #@ReservedAssignment
#        if msg.index('{') > -1 and msg.index('}') > -1:
#            msg = '{' + msg.split('{',1)[1]
#            msg = msg.rsplit('}',1)[0] + '}'
        if type(msg) is list: msg[-1] = json.loads(msg[-1])
        msg = ZMQSPARXMessage(msg, index_hash=dict(filters=0, path=1))
        return msg
    
class ZMQJsonRequest(ZMQBasePlugin):
    """
    ZMQ SEND Plugin dumps the JSON data into a string
    
    Expected argument list: args, kargs
    
    All args converted to strings and joined via a '/' delimiter
    
    All kargs are made into a dictionary in a string format and appended to the joined arg list with a whitespace
    """
    _plugin_type_ = ZMQBasePlugin.SEND
    
    def apply(self, send_fn): #@ReservedAssignment
        @wraps(send_fn)
        def _wrapper(*args, **kargs):
            msg = ZMQSPARXMessage(args, index_hash=dict(filters=0, path=1))
            # msg['filters'] = reduce(lambda x, y: '%s/%s'%(x,y),args) if len(args) > 0 else ''
            msg[-1] = json.dumps(msg[-1])
            send_fn(msg)
        
        return _wrapper
    

class ZMQCallbackPattern(ZMQBasePlugin):
    """
    ZMQ RECEIVE Plugin that expects a 'path' inside the received json message
    Callbacks must be registered for that path using register_callback_path
    """
    _plugin_type_ = ZMQBasePlugin.RECEIVE
    _all_callbacks_hash = dict()
        
    def __init__(self, lookup_attr='path', callback_hash={}, callback_context=None, socket_key=None):
        """
        Constructor
        
        :param callback_hash: A :py:class:`Dictionary` holding *path* : *callback* key : value pairs
        :param callback_context: The context from which to call the callback method from
        """
        self._callback_hash = callback_hash
        self._callback_context = callback_context
        self._socket_key = socket_key
        self._lookup_attr = lookup_attr
        
    def setup(self, endpoint):
        try:
            if not self._callback_context: self._callback_context = endpoint
            for k,v in self.__class__._all_callbacks_hash[self._socket_key].iteritems():
                self._callback_hash[k] = getattr(self._callback_context, v.func_name) if self._callback_context else v
            for attr in vars(self._callback_context.__class__):
                callback = getattr(self._callback_context, attr, None)
                if type(getattr(callback, '_zmq_callback', None)) is tuple: 
                    self._callback_hash[getattr(callback, '_zmq_callback')[1]] = callback
                
        except AttributeError: pass
        except KeyError: pass
        super(ZMQCallbackPattern, self).setup(endpoint)
    
    def apply(self, msg): #@ReservedAssignment
        try : path = getattr(msg, self._lookup_attr)
        except KeyError:
            print 'No Path Found'
            return msg
        
        try: callback = self._callback_hash[path]
        except KeyError:
            print 'No Path Callback Found'
            return msg
        
        callback(msg)
        return msg
    
    @classmethod
    def ZMQPatternRoute(cls, pattern, socket_key=None):
        def decorator(fn):
            if socket_key is None: 
                fn._zmq_callback = (True, pattern)
            else: 
                cls._all_callbacks_hash.setdefault(socket_key, dict())
                cls._all_callbacks_hash[socket_key][pattern] = fn
            return fn
        return decorator
            
    def register_callback_path(self, path, callback):
        """
        :param path: String path that to associate the callback with
        :type path: String
        :param callback: Callable to be associated with the path
        :type callback: Callable
        """
        self._callback_hash[path] = callback
        
class ZMQCoupling(ZMQBasePlugin):
    '''
    This is a :class:`ZMQBasePlugin` extension meant for quick iterations on multi device servers.
    Using a "coupling ID" attach this Plugin to both required :class:`ZMQEndPoint`'s.
    Use the :func:`CoupledProcess` decorator to wrap a processing function to manipulate data
    as it is rerouted through the coupling.
    
    example::
    
        @ZMQCoupling.CoupledProcess("some_id")
        def process(self, message):
            # Some processing
            return args, kargs
    
    '''
    _plugin_type_ = ZMQBasePlugin.RECEIVE
    _coupled_eps = {}
    _coupled_process = {}
    
    def __init__(self, couple_id, process_context=None, async=True):
        '''
        Constructor
        
        :param couple_id: Trivial ID to be shared between the two coupled :class:`ZMQEndPoint`'s and the process function
        :param process_context: The Context from which to execute itself from, example **self**
        '''
        self.couple_id = couple_id
        self._other_half = None
        
        self.__class__._coupled_eps.setdefault(self.couple_id, [])
        self.__class__._coupled_eps[self.couple_id].append(self)
        
        if None not in [ process_context , self.__class__._coupled_process.get(self.couple_id) ]: 
            self.__class__._coupled_process[self.couple_id] = getattr(process_context, self.__class__._coupled_process[self.couple_id].func_name)
    
    def apply(self, msg): #@ReservedAssignment
        if not self._other_half:
            self._other_half = self.__class__._coupled_eps[self.couple_id][0] if self.__class__._coupled_eps[self.couple_id][0] is not self else self.__class__._coupled_eps[self.couple_id][1]
        try: args, kargs = self.__class__._coupled_process.get(self.couple_id)(msg)
        except TypeError: args, kargs = (msg,), {}
        self._other_half.endpoint.send(*args, **kargs)
        return args, kargs
        
    
    @classmethod
    def CoupledProcess(cls, couple_id):
        def decorator(fn):
            cls._coupled_process[couple_id] = fn
            return fn
        return decorator
    
# Very incomplete
class ZMQRequestEndPoint(ZMQListenEndPoint):
    
    def __init__(self, address, **kargs):
        super(ZMQRequestEndPoint, self).__init__(zmq.REQ, address, **kargs)
        self.poller = None
    
    def setup(self, extended_setup=[]):
        def _setup():
            self.poller = zmq.Poller()
            
        extended_setup.append(_setup)
        super(ZMQRequestEndPoint, self).setup(extended_setup=extended_setup)
    
    def start(self, extended_start=[]):
        def _start():
            self.poller.register(self.socket, zmq.POLLIN|zmq.POLLOUT)
        
        extended_start.append(_start)
        super(ZMQRequestEndPoint, self).start(extended_start=extended_start)
    
    def send(self, *args, **kargs):
        def _send():
            p = dict(self.poller.poll(timeout=1)) #immediate
            if self.socket in p and p[self.socket] is zmq.POLLOUT:
                super(ZMQRequestEndPoint, self).send(*args, **kargs)
            # Do queueing
            
        ioloop_instance().add_callback(_send)
    
class ZMQSubscribeEndPoint(ZMQListenEndPoint):
    """
    Special ZMQListenEndpoint that creates a SUBSCRIBE Socket
    Subscribe sockets require filters to function
    """
    
    def __init__(self, address, bind=False, callback_hash={}, server=None, **kargs):
        super(ZMQSubscribeEndPoint, self).__init__(zmq.SUB, address, bind=bind, 
                                                   plugins=[ZMQJsonReply(), ZMQCallbackPattern(callback_hash=callback_hash, callback_context=server)], **kargs)
    