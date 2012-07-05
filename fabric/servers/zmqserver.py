'''
Created on 13-Jun-2012

@author: rishi
'''
from fabric.servers import server
from fabric.endpoints.zmqendpoints.zmq_base import ZMQBaseEndPoint
    
class ZMQServer(server.Server):
    '''
    :py:class:`ZMQServer` is an extension of :py:class:`server.Server`. It serves the purpose of providing a base class
    for all ZMQ based Servers.
    
    For predictable performance, limit all endpoints to :py:class:`ZMQBaseEndpoint`, mixing endpoint
    types will result in unknown behaviour.
    '''
    def __init__(self, name=None, endpoints=[], **kargs):
        '''
        Constructor
        '''
        self.ep_hash = {}
        super(ZMQServer, self).__init__(name=name, endpoints=endpoints, **kargs)
        for ep in endpoints:
            self.ep_hash[ep.uuid] = ep
            
    def start_main_server(self, **kargs):
        super(ZMQServer, self).start_main_server(**kargs)
        self.activate_endpoints()
    
    def activate_endpoints(self):
        """
        Activates all ZMQBaseEndPoints registered with this server
        """
        for ep in self.ep_hash:
            if isinstance(self.ep_hash[ep], ZMQBaseEndPoint):
                self.ep_hash[ep].activate()
    
    def send_from_endpoint(self, uuid, *args, **kargs):
        """
        :param uuid: The UUID of the endpoint to send the message from, every endpoint has a probabilistically unique UUID
        :param args: To be used by the SEND Plugins of type :py:class:`ZMQBasePlugin`, this is sent by default
        :param kargs: To be used by the SEND Plugins of type :py:class:`ZMQBasePlugin`
        """
        assert self.ep_hash.has_key(uuid) and isinstance(self.ep_hash[uuid], ZMQBaseEndPoint)
        self.ep_hash[uuid].send(*args, **kargs)
            
    def add_endpoint(self, endpoint):
        assert self.ep_hash.get(endpoint.uuid) is None
        self.ep_hash[endpoint.uuid] = endpoint
        
if __name__ == '__main__':
    pass
