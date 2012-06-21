'''
Created on 13-Jun-2012

@author: rishi
'''
from fabric.servers import server
from fabric.endpoints.zmqendpoints.zmq_base import ZMQBaseEndPoint,\
    ZMQListenEndPoint

class _SignallingConstants:
    send = "\FF"
    
class ZMQServer(server.Server):
    '''
    classdocs
    '''
    def __init__(self, name=None, endpoints=[], **kargs):
        '''
        Constructor
        '''
        self.ep_hash = {}
        super(ZMQServer, self).__init__(name=name, endpoints=endpoints, **kargs)
        for ep in endpoints:
            self.ep_hash[ep.uuid] = ep
            
    def start_main_server(self):
        self.activate_endpoints()
    
    def activate_endpoints(self):
        for ep in self.ep_hash:
            if isinstance(self.ep_hash[ep], ZMQBaseEndPoint):
                self.ep_hash[ep].setup()
                self.ep_hash[ep].start()
    
    def send_from_endpoint(self, uuid, msg):
        assert self.ep_hash.has_key(uuid) and isinstance(self.ep_hash[uuid], ZMQBaseEndPoint)
        self.ep_hash[uuid].send(msg)
            
    def add_endpoint(self, endpoint):
        assert self.ep_hash.get(endpoint.uuid) is None
        self.ep_hash[endpoint.uuid] = endpoint
    
    def register_path_callback(self, uuid, path, callback):
        assert uuid in self.ep_hash and isinstance(self.ep_hash[uuid], ZMQListenEndPoint)
        self.ep_hash[uuid].register_path_callback(path, callback)
    
if __name__ == '__main__':
    pass
