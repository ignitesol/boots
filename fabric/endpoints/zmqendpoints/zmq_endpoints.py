'''
Created on 20-Jun-2012

@author: rishi
'''
import json
import zmq

from fabric.endpoints.zmqendpoints.zmq_base import ZMQBasePlugin,\
    ZMQListenEndPoint
        
class ZMQJsonReply(ZMQBasePlugin):
    
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
    
    _plugin_type_ = ZMQBasePlugin.SEND
    
    def __call__(self, *args, **kargs):
        msg = args and '-'.join(args)
        if kargs: msg = msg + ' ' + json.dumps(kargs)
        return msg, None

class ZMQSubscribeEndpoint(ZMQListenEndPoint):
    
    def __init__(self, address, bind=False, **kargs):
        super(ZMQSubscribeEndpoint, self).__init__(zmq.SUB, address, bind=bind, plugins=[ZMQJsonReply()], **kargs)
    
    def add_filter(self, pattern):
        def _filter():
            self.socket.setsockopt(zmq.SUBSCRIBE, pattern)
        self.ioloop.add_callback(_filter)
#        self.ioloop.add_callback(functools.partial(self.socket.setsockopt, args=(zmq.SUBSCRIBE, pattern)))