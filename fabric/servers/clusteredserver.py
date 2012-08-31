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

    def __init__(self, server_adress, servertype, endpoints=None, stickykeys=None, ds='ds', **kargs):
        '''
        
        :param server_adress: defines the the endpoint for the server, this is unique per server
        :param servertype: this defines the server type 
        :param endpoints: Endpoint definition provided by cluster server by itself
        :param stickykeys: It provides way to create the sticky value. This param can be a string param , or tuple of params or list of tuples or 
                           method that defines the creation of sticky value (the method will take all the parameters passed and will create the sticky 
                           value). If the list of tuple params are given, we form  the sticky value based on whicherver we find first and update based 
                           on all the sticky values created from the list of param-tuple
        :param str ds: This is the name of the paramter , which will be used to refer the datastoe_wrapper object. This gives the handle to the application
                        server to manipulate the data.
                    
        
        '''
        self.datastore = MySQLBinding() # TODO : write a factory method to get the binding
        self.servertype = servertype
        self.server_adress = server_adress
        self.stickykeys = stickykeys
        self.ds = ds
        
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
        return par_plugins + [ ClusteredPlugin(datastore=self.datastore, ds=self.ds) ] 
        

    def create_data(self):
        '''
        This create DataStructure in Persistent data store
        '''
        self.datastore.setdata(self.server_adress, self.servertype )
        
    def get_data(self):
        return self.datastore.getdata(self.server_adress)
    
    
    def update_data(self, load, endpoint_key, endpoint_name, stickyvalues=None, data=None):
        '''
        This update the sticky value for the 
        :param stickyvalues: list of stickyvalues
        '''
        #jsonify data
        self.datastore.update_server(self.server_adress, endpoint_key, endpoint_name, stickyvalues, load, data)
        
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
        
        :rtype: returns the unique id or the server which is the sever adress with ports
        '''
        servertype = servertype or self.servertype
        server =  self.datastore.get_least_loaded(servertype)
        return server.unique_key if server else None
        
    
    def get_by_stickyvalue(self, stickyvalues, endpoint_key):
        '''
        This method gets the server with the stickyvalue. The stickyvalue makes sure this request is handled
        by the correct server. 
        :param list stickyvalues: stickyvalues which is handled by this server
        :param str endpoint_key: uuid of the endpoint
        
        :rtype: returns the unique id or the server which is the sever address with port
        '''
        if stickyvalues is None:
            return None
        ret_val =  self.datastore.get_server_by_stickyvalue(stickyvalues, endpoint_key)
        server , clustermapping_list = ret_val
        return (server.unique_key, clustermapping_list) if ret_val else None
        

    def transform_stickyvalues(self, value_tuple):
        '''
        Creates sticky value from the parameters passed in the tuple.
        By default it uses the STICKY_VALUE_SEP (:)  as the separator. The application can choose to override
        this method to transform the stickyvalues in a way it needs
        :param value_tuple: the tuple of values to be converted
        
        :rtype: return the string of transformed stickyvalue
        '''
        return STICKY_VALUE_SEP.join(str(v) for v in value_tuple)
