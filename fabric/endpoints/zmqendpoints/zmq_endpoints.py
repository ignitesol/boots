'''
Created on 20-Jun-2012

@author: rishi
'''
import json
import zmq
import threading

from fabric.endpoints.zmqendpoints.zmq_base import ZMQBasePlugin,\
    ZMQListenEndPoint
        
class ZMQJsonReply(ZMQBasePlugin):
    """
    ZMQ RECEIVE Plugin that strips data before and after '{' and '}'
    and Jsonifies the data
    """
    _plugin_type_ = ZMQBasePlugin.RECEIVE
    
    def __init__(self, *args, **kargs):
        super(ZMQJsonReply, self).__init__(*args, **kargs)

    def __call__(self, msg):
        if msg.index('{') > -1 and msg.index('}') > -1:
            msg = '{' + msg.split('{',1)[1]
            msg = msg.rsplit('}',1)[0] + '}'
        msg = json.loads(msg)
        return msg
    
class ZMQJsonRequest(ZMQBasePlugin):
    """
    ZMQ SEND Plugin dumps the JSON data into a string
    And joins the non JSON data before the JSON data
    """
    _plugin_type_ = ZMQBasePlugin.SEND
    
    def __call__(self, *args, **kargs):
        msg = args and '-'.join(args)
        if kargs: msg = msg + ' ' + json.dumps(kargs)
        return msg, None

class ZMQCallbackPattern(ZMQBasePlugin):
    """
    ZMQ RECEIVE Plugin that expects a 'path' inside the received message
    Callbacks must be registered for that path using register_callback_path
    """
    _plugin_type_ = ZMQBasePlugin.RECEIVE
    
    def __init__(self, callback_hash):
        self._callback_hash = callback_hash
    
    def __call__(self, msg):
        try : path = msg['path']
        except KeyError:
            print 'No Path Found'
            return
        
        try: callback = self._callback_hash[path]
        except KeyError:
            print 'No Path Callback Found'
            return
        
        # Args should be sent as a tuple
        args = msg.get('args', None)
        # Kargs as a dictionary
        kwargs = msg.get('kwargs', None)
        
        if type(args) is not tuple: args = tuple(args)
        threading.Thread(target=callback, args=args, kwargs=kwargs).start()
    
    def register_callback_path(self, path, callback):
        """
        :param path: String path that to associate the callback with
        :type String
        :param callback: Callable to be associated with the path
        :type callable 
        """
        self.callback_hash[path] = callback

class ZMQSubscribeEndpoint(ZMQListenEndPoint):
    """
    Special ZMQListenEndpoint that creates a SUBSCRIBE Socket
    Subscribe sockets require filters to function
    """
    
    def __init__(self, address, bind=False, callback_hash=[], **kargs):
        super(ZMQSubscribeEndpoint, self).__init__(zmq.SUB, address, bind=bind, 
                                                   plugins=[ZMQJsonReply(), ZMQCallbackPattern(callback_hash=callback_hash)], **kargs)
    
    def add_filter(self, pattern):
        """
        :param pattern: The pattern to discern between which messages to drop and which to accept
        :type String
        """
        def _filter():
            self.socket.setsockopt(zmq.SUBSCRIBE, pattern)
        self.ioloop.add_callback(_filter)
#        self.ioloop.add_callback(functools.partial(self.socket.setsockopt, args=(zmq.SUBSCRIBE, pattern)))