from fabric.servers.managedserver import ManagedServer
from fabric.servers.zmqserver import ZMQServer

class HybridServer(ManagedServer, ZMQServer):
    '''
        :py:class:`HybridServer` provides a simple server that supports multiple endpoints
        such as :py:class:`HTTPServerEndPoint` and :py:class:`ZMQEndPoint`. It is a simple
        inheritance of :py:class:`ManagedServer` and :py:class:`ZMQServer` 
    '''
    pass
        
