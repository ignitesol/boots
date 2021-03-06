'''
Custom ZMQ Endpoints and Plugins to be used within the ZMQ Servers

'''
from boots import concurrency
if concurrency == 'gevent':
    import zmq.green as zmq
else:
    import zmq

from boots.endpoints.zmqendpoints.zmq_base import ZMQBasePlugin
#    ZMQListenEndPoint, ioloop_instance
import re

class ZMQCallbackPattern(ZMQBasePlugin):
    """
    ZMQ RECEIVE Plugin that expects a 'path' inside the received json message
    Callbacks must be registered for that path using register_callback_path
    """
    _plugin_type_ = ZMQBasePlugin.RECEIVE
    _all_callbacks_hash = dict()
        
    def __init__(self, lookup_attr='path', callback_list=[], callback_context=None, namespace=None):
        """
        Constructor
        
        :param callback_hash: A :py:class:`Dictionary` holding *path* : *callback* key : value pairs
        :param callback_context: The context from which to call the callback method from
        """
        self._callback_list = callback_list
        self._callback_context = callback_context
        self._namespace = namespace
        self._lookup_attr = lookup_attr
        
    def setup(self, endpoint):
        self.endpoint = endpoint
        contained_expressions = []
        try:
            if not self._callback_context: self._callback_context = endpoint
            
            if self._namespace and self.__class__._all_callbacks_hash.get(self._namespace):
                for k,v in self.__class__._all_callbacks_hash[self._namespace].iteritems():
                    if k not in contained_expressions:
                        contained_expressions.append(k)
                        t = (k, re.compile(k), getattr(self._callback_context, v[0].func_name) if self._callback_context else v[0], v[1])
                        self._callback_list.append(t)
                    
            for attr in dir(self._callback_context.__class__):
                callback = getattr(self._callback_context, attr, None)
                t = getattr(callback, '_zmq_callback', None) if callback else None
                if type(t) is tuple and t[0] not in contained_expressions: # already exists
                    contained_expressions.append(t[0])
                    self._callback_list.append((t[0], re.compile(t[0]), callback, t[1]))
            
            self._callback_list.sort(cmp=lambda x,y: y[3] - x[3]) # Largest first
                
        except AttributeError: pass
        except KeyError: pass
        super(ZMQCallbackPattern, self).setup(endpoint)
    
    def apply(self, msg): #@ReservedAssignment
        try : path = getattr(msg, self._lookup_attr)
        except KeyError:
            self.endpoint.server.logger.debug('No Path Found for %s in %s', self._lookup_attr, msg)
            return msg
        
        try: 
            callback = lambda x: x
            for t in self._callback_list:
                if t[1].match(path):
                    callback = t[2]
                    break
        except IndexError:
            self.endpoint.server.logger.debug('No Path Callback Found for %s in %s', path, self._callback_list)
            return msg
        
        callback(msg)
        return msg
    
    @classmethod
    def ZMQPatternRoute(cls, pattern, namespace=None, priority=-1):
        def decorator(fn):
            if namespace is None: 
                fn._zmq_callback = (pattern, priority)
            else: 
                cls._all_callbacks_hash.setdefault(namespace, dict())
                cls._all_callbacks_hash[namespace][pattern] = (fn, priority)
            return fn
        return decorator
    
    def add_callbackpath(self, context, fn, pattern, priority):
        self._callback_list.append(pattern, re.compile(pattern), getattr(context, fn.func_name), priority)
        
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
        
        # Drop the message if it is a None Type message
        if len(args) > 0 and args[0] is not None: 
            self._other_half.endpoint.send(*args, **kargs)
            
        return args, kargs
        
    
    @classmethod
    def CoupledProcess(cls, couple_id):
        def decorator(fn):
            cls._coupled_process[couple_id] = fn
            return fn
        return decorator
