'''
Created on 13-Jun-2012

@author: rishi
'''
from fabric.servers import server
from fabric.endpoints.zmqendpoints.zmq_base import ZMQBaseEndPoint, ZMQEndPoint
    
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
                self.ep_hash[ep].activate()
    
    def send_from_endpoint(self, uuid, *args, **kargs):
        assert self.ep_hash.has_key(uuid) and isinstance(self.ep_hash[uuid], ZMQBaseEndPoint)
        self.ep_hash[uuid].send(*args, **kargs)
            
    def add_endpoint(self, endpoint):
        assert self.ep_hash.get(endpoint.uuid) is None
        self.ep_hash[endpoint.uuid] = endpoint
        
if __name__ == '__main__':
    pass
