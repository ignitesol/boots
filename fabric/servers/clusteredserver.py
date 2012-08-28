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
        return "we are at the status process id " + str(os.getpid())  + " My end point is  : " + server_adress + "\n" + \
                "My load is : " + str(self.server.get_data(server_adress))
    
        
class ClusteredServer(ManagedServer):
    '''
    ClusteredServer provides inbuilt capabilities over and above HTTPServer for clustering
    '''

    def __init__(self, server_adress, servertype, endpoints=None, **kargs):
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
        
        endpoints = endpoints or []
        endpoints = endpoints + [ ClusteredEP()]
        super(ClusteredServer, self).__init__(endpoints=endpoints, **kargs)
        self.create_data() # This will create data if doesn't exist else updates if update flag is passed 
        
    def get_standard_plugins(self, plugins):
        '''
        Adds the clusteredPlugin to all routes
        '''
        try:
            par_plugins = super(ClusteredServer, self).get_standard_plugins(plugins)
        except AttributeError:
            par_plugins = []
        return par_plugins + [ ClusteredPlugin() ] 
        

    def create_data(self):
        '''
        This create DataStructure in Persistent data store
        '''
        self.datastore.setdata(self.server_adress, self.servertype )
        
    def get_data(self):
        return self.datastore.getdata(self.server_adress)
    
    
    def update_data(self, load, endpoint_key, endpoint_name, stickyvalue=None, data=None):
        
        #jsonify data
        self.datastore.update_server(self.server_adress, endpoint_key, endpoint_name, stickyvalue, load, data)
        
    def get_current_load(self):
        '''
        This method defines how the load gets updated which each new request being served or completed
        It returns new load percentage
        '''
        return 0
    
    
    def cleanup(self):
        '''
        This method will cleanup the sticky mapping and update the new load.
        This needs to be called by the application when it is done with processing and stickyness is removed
        '''
        pass
            
    def get_least_loaded(self, servertype=None):
        '''
        This method gets the least loaded server of the given servertype 
        :param servertype: this parameters contains the type of server
        '''
        servertype = servertype or self.servertype
        server =  self.datastore.get_least_loaded(servertype)
        return server.unique_key if server else None
        
    
    def get_by_stickyvalue(self, stickyvalue):
        '''
        This method gets the server with the stickyvalue. The stickyvalue makes sure this request is handled
        by the correct server. 
        :param stickyvalue: stickyvalue which is handled by this server
        '''
        if stickyvalue is None:
            return None
        server =  self.datastore.get_server_by_stickyvalue(stickyvalue)
        return server.unique_key if server else None
        

    def create_sticky_value(self, sticky_keys, kargs):
        '''
        Creates sticky value from the parameters passed
        This method get the dict of all the parameters passed to the server.
        It extracts the all the sticky key values as specified by the given server and
        concatenates by a separator to form a unique key  
        :param sticky_keys: List of sticky keys for this end-point
        :param kargs: is the map of the parameters those are passed to the server
        '''
        try:
            return STICKY_VALUE_SEP.join([ kargs[key] for key in sticky_keys])
        except KeyError:
            return None
       
# Stickiness at the endpoint level , check if endpoint has this method . otherwise handled by this server             
#    def get_sticky_keys(self):
#        '''
#        This method returns the sticky keys.
#        Sticky keys may be list of individual keys , these are the params those are passed for the server request
#        '''
#        return self.stickykeys