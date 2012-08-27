'''
Clustered server provides abstraction for managing the cluster of server and handling the load-balancing, stickiness to server.

Each server  registers itself to a common datastore when it comes up.
Also each server has access to common datastore 

'''
from __future__ import division
import os
from fabric import concurrency
from fabric.datastore.datamodule import MySQLBinding
from fabric.endpoints.http_ep import methodroute, HTTPServerEndPoint
from fabric.endpoints.cluster_ep import ClusteredPlugin
from fabric.servers.managedserver import ManagedServer
import logging

if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock
    
logging.getLogger().addHandler(logging.NullHandler())

STICKY_VALUE_SEP = ":"

class ClusteredEP(HTTPServerEndPoint):
    '''
    ClusteredEP provides the endpoint for clusterdserver 
    Typically mounted on the servers '/cluster' mountppoint
    '''
        
    def __init__(self, name=None, mountpoint='/cluster', plugins=None, server=None, activate=False):
        super(ClusteredEP, self).__init__(name=name, mountpoint=mountpoint, plugins=plugins, server=server, activate=activate)
        
    
    @methodroute()
    def status(self, channel=None):
        server_adress = self.server.server_adress
        print "we are at the status process id " + str(os.getpid())
        return "we are at the status process id " + str(os.getpid())  + " My end point is  : " + server_adress + "\n" + \
                "My load is : " + str(self.server.get_data(server_adress))
    
    @methodroute()
    def test(self):
        print os.getpid()
        return os.getpid()
        #return self.server.redisclient.red.get(self.server.server_adress)

        
class ClusterServerException(Exception):
    
    def __init__(self, value="ClusterServerException"):
        self.value = value
    
    def __str__(self):
        return repr(self.value)


class ClusteredServer(ManagedServer):
    '''
    ClusteredServer provides inbuilt capabilities over and above HTTPServer for clustering
    '''

    def __init__(self, server_adress, servertype, stickykeys =[], endpoints=None, **kargs):
        '''
        
        :param server_adress: defines the the endpoint for the server, this is unique per server
        :param servertype: this defines the server type 
        :param stickykeys: It contains the list of sticky keys. The stikcy key is used to identify the stcikiness or the affinity for particular
                           server when the request comes based on the sticky keys. The sticky value is stored by colon separated in persistent datastore
        :param endpoints: Endpoint definition provided by cluster server by itself
        '''
        self.datastore = MySQLBinding() # TODO : write a factory method to get the binding
        self.servertype = servertype
        self.server_adress = server_adress
        self.stickykeys = stickykeys or self.get_sticky_keys()
        
        endpoints = endpoints or []
        endpoints = endpoints + [ ClusteredEP()]
        super(ClusteredServer, self).__init__(endpoints=endpoints, **kargs)
        self.create_data(server_adress, servertype) # This will create data if doesn't exist else updates if update flag is passed 
        
    def get_standard_plugins(self, plugins):
        '''
        Adds the clusteredPlugin to all routes
        '''
        try:
            par_plugins = super(ClusteredServer, self).get_standard_plugins(plugins)
        except AttributeError:
            par_plugins = []
        return par_plugins + [ ClusteredPlugin() ] 
        

    def create_data(self, server_adress, servertype):
        '''
        This create DataStructure in Persistent data store
        '''
        self.datastore.setdata(server_adress, servertype )
        
    def get_data(self, server_adress):
        return self.datastore.getdata(server_adress)
    
    
    def update_data(self, server_adress, load=None, stickyvalue=None):
        self.datastore.update_server(server_adress, stickyvalue, load)
        
    def refreshed_load_on_update(self):
        '''
        This method defines how the load gets updated which each new request being served or completed
        It returns new load percentage
        '''
        pass
            
    def get_least_loaded(self, servertype):
        '''
        This method gets the least loaded server of the given servertype 
        :param servertype: this parameters contains the type of server
        '''
        server =  self.datastore.get_least_loaded(servertype)
        return server.unique_key if server else None
        
    
    def get_by_stickyvalue(self, stickyvalue):
        '''
        This method gets the server with the stickyvalue. The stickyvalue makes sure this request is handled
        by the correct server. 
        :param stickyvalue: stickyvalue which is handled by this server
        '''
        if not stickyvalue:
            return None
        server =  self.datastore.get_server_by_stickyvalue(stickyvalue)
        return server.unique_key if server else None
        

    def create_sticky_value(self, kargs):
        '''
        Creates sticky value from the parameters passed
        This method get the dict of all the parameters passed to the server.
        It extracts the all the sticky key values as specified by the given server and
        concatenates by a separator to form a unique key  
        :param kargs: is the map of the parameters those are passed to the server
        '''
        sticky_val = ''
        for key in self.get_sticky_keys():
            if sticky_val:
                sticky_val += STICKY_VALUE_SEP
            sticky_val = sticky_val + kargs[key]
        return sticky_val
            
    def get_sticky_keys(self):
        '''
        This method returns the sticky keys.
        Sticky keys may be list of individual keys , these are the params those are passed for the server request
        '''
        return self.stickykeys