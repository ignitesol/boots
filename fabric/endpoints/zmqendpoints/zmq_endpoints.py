'''
Custom ZMQ Endpoints and Plugins to be used within the ZMQ Servers

'''
import json
import zmq
import threading

from fabric.endpoints.zmqendpoints.zmq_base import ZMQBasePlugin,\
    ZMQListenEndPoint
import inspect
        
class ZMQJsonReply(ZMQBasePlugin):
    """
    ZMQ RECEIVE Plugin that Jsonifies the data
    
    Expected argument list: message
    Expected message format: .*{.*}.*
    
    The leading and trailing strings outside the braces will be stripped
    Anything within the braces will be jsonified and returned including the braces themselves
    """
    _plugin_type_ = ZMQBasePlugin.RECEIVE
    
    def setup(self, endpoint):
        pass

    def apply(self, msg):
        if msg.index('{') > -1 and msg.index('}') > -1:
            msg = '{' + msg.split('{',1)[1]
            msg = msg.rsplit('}',1)[0] + '}'
        msg = json.loads(msg)
        return msg
    
class ZMQJsonRequest(ZMQBasePlugin):
    """
    ZMQ SEND Plugin dumps the JSON data into a string
    
    Expected argument list: args, kargs
    
    All args converted to strings and joined via a '-' delimiter
    
    All kargs are made into a dictionary in a string format and appended to the joined arg list with a whitespace
    """
    _plugin_type_ = ZMQBasePlugin.SEND
    
    def setup(self, endpoint):
        pass
    
    def apply(self, *args, **kargs):
        msg = args and '-'.join('%s'%args)
        if kargs: msg = msg + ' ' + json.dumps(kargs)
        return msg, None

class ZMQCallbackPattern(ZMQBasePlugin):
    """
    ZMQ RECEIVE Plugin that expects a 'path' inside the received json message
    Callbacks must be registered for that path using register_callback_path
    """
    _plugin_type_ = ZMQBasePlugin.RECEIVE
    _all_callbacks_hash = dict()
    
    def __init__(self, callback_hash={}):
        """
        Constructor
        
        :param callback_hash: A :py:class:`Dictionary` holding *path* : *callback* key : value pairs
        """
        self._callback_hash = callback_hash
        
    def setup(self, endpoint):
        try:
            for k,v in self.__class__._all_callbacks_hash[(endpoint.socket_type, endpoint.address)].iteritems():
                self._callback_hash[k] = v
        except KeyError: pass
    
    def apply(self, msg):
        try : path = msg['path']
        except KeyError:
            print 'No Path Found'
            return msg
        
        try: callback = self._callback_hash[path]
        except KeyError:
            print 'No Path Callback Found'
            return msg
        
        # Args should be sent as a tuple
        args = msg.get('args', None)
        # Kargs as a dictionary
        kwargs = msg.get('kwargs', None)
        
        if type(args) is not tuple: args = tuple(args)
        threading.Thread(target=callback, args=args, kwargs=kwargs).start()
        
        return msg
    
    @classmethod
    def ZMQPatternRoute(cls, socket_type, socket_address, pattern):
        def decorator(fn):
            cls._all_callbacks_hash.setdefault((socket_type, socket_address), dict())
            cls._all_callbacks_hash[(socket_type, socket_address)][pattern] = fn
        return decorator
            
    def register_callback_path(self, path, callback):
        """
        :param path: String path that to associate the callback with
        :type path: String
        :param callback: Callable to be associated with the path
        :type callback: Callable
        """
        self.callback_hash[path] = callback

class ZMQSubscribeEndPoint(ZMQListenEndPoint):
    """
    Special ZMQListenEndpoint that creates a SUBSCRIBE Socket
    Subscribe sockets require filters to function
    """
    
    def __init__(self, address, bind=False, callback_hash={}, **kargs):
        super(ZMQSubscribeEndPoint, self).__init__(zmq.SUB, address, bind=bind, 
                                                   plugins=[ZMQJsonReply(), ZMQCallbackPattern(callback_hash=callback_hash)], **kargs)
    
    def add_filter(self, pattern):
        """
        :param pattern: The pattern to discern between which messages to drop and which to accept
        :type pattern: String
        """
        def _filter():
            self.socket.setsockopt(zmq.SUBSCRIBE, pattern)
        self.ioloop.add_callback(_filter)
