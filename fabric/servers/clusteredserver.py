'''
Clustered server provides abstraction for managing the cluster of server and handling the load-balancing, stickiness to server.

Each server  registers itself to a common datastore when it comes up.
Also each server has access to common datastore 

'''
from __future__ import division
import os
from fabric import concurrency
from fabric.datastore.datamodule import RedisBinding
from fabric.endpoints.http_ep import methodroute, HTTPServerEndPoint, \
    ClusteredPlugin
from fabric.servers.helpers import clusterenum
from fabric.servers.helpers.clusterenum import ClusterDictKeyEnum
from fabric.servers.managedserver import ManagedServer
import logging


if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock
    
logging.getLogger().addHandler(logging.NullHandler())

class ClusteredEP(HTTPServerEndPoint):
    '''
    ClusteredEP provides the endpoint for clusterdserver 
    Typically mounted on the servers '/cluster' mountppoint
    '''
        
    def __init__(self, name=None, mountpoint='/cluster', plugins=None, server=None, activate=False):
        super(ClusteredEP, self).__init__(name=name, mountpoint=mountpoint, plugins=plugins, server=server, activate=activate)
        
    
    @methodroute()
    def stop(self):
        '''
        This method route will stop this server
        '''
        pass
    
    
    @methodroute()
    def status(self, channel=None):
        my_end_point = self.server.my_end_point
        print "we are at the status process id " + str(os.getpid())
        return "we are at the status process id " + str(os.getpid())  + " My end point is  : " + my_end_point + "\n" + \
                "My load is : " + str(self.server.get_data(my_end_point))
    
    @methodroute()
    def test(self):
        print os.getpid()
        return os.getpid()
        #return self.server.redisclient.red.get(self.server.my_end_point)

        
class ClusterServerException(Exception):
    
    def __init__(self, value="ClusterServerException"):
        self.value = value
    
    def __str__(self):
        return repr(self.value)


class ClusteredServer(ManagedServer):
    '''
    ClusteredServer provides inbuilt capabilities over and above HTTPServer for clustering
    '''

    def __init__(self, my_end_point, servertype, endpoints=None, **kargs):
        '''
        :param type: defines the param type adapter MPEG, CODF etc
        '''
        self.datastore = RedisBinding()
        self.servertype = servertype
        self.my_end_point = my_end_point
        endpoints = endpoints or []
        endpoints = endpoints + [ ClusteredEP()]
        super(ClusteredServer, self).__init__(endpoints=endpoints, **kargs)
        self.create_data(my_end_point, servertype) # This will create data if doesn't exist else updates if update flag is passed 
        
    def get_standard_plugins(self, plugins):
        '''
        Adds the clusteredPlugin to all routes
        '''
        try:
            par_plugins = super(ClusteredServer, self).get_standard_plugins(plugins)
        except AttributeError:
            par_plugins = []
        print ( "Added the ClusteredPlugin to the server")
        return par_plugins + [ ClusteredPlugin() ] 
        

    def create_data(self, my_end_point, servertype):
        '''
        This create DataStructure in Redis
        '''
        data_dict = {ClusterDictKeyEnum.SERVER : my_end_point , 
                     ClusterDictKeyEnum.LOAD : 0 , 
                     ClusterDictKeyEnum.CHANNELS :[]}
        self.datastore.setdata(my_end_point, data_dict , servertype )
        
    def get_data(self, my_end_point):
        return self.datastore.getdata(my_end_point)
    
    
    def update_data(self, my_end_point, load=None, channel=[]):
        self.datastore.update_server(my_end_point, channel, load)
    
    def get_existing_or_free(self, key , servertype, **kargs):
        #TOBE OVERRIDDEN METHOD
        pass
            
    def get_least_loaded(self, servertype):
        pass
        
    
    def get_by_channel(self, channel, **kargs):
        '''
        This method get the server who is serving the given channel
            [ Channel for mpeg : <adapter-type>/<host:port:channel-id]
            [ Channel for CODF : <adapter-type>/<tune-id> ]
        '''
        key = self.datastore.get_server_of_type(clusterenum.Constants.channel_tag_prefix + channel)
        adapter = None
        #Assumption we have only one key 
        if key:
            adapter = self.datastore.getdata(list(key)[0])
        return adapter
        
    def get_by_key(self, key , **kargs):
        '''
        This method will get the server who is handling the request based on the key
        '''
        return self.datastore.get_server_of_type(key)
        
    def is_local(self, channel, **kwrags):
        '''
        This method checks if the request will be handled by this server or we need a redirect to the actual server.
        If we need to find the 
        '''
        #Check in data store if this channel is handled already
        #if its already handled we will redirect to that corresponding server
        record = self.datastore.getdata(self.my_end_point)
        return True if record and channel in record[ClusterDictKeyEnum.CHANNELS] else False
        
    
    def get_load(self, **kargs):
        '''
        This method return the load % on this server
        '''
        record = self.datastore.getdata(self.my_end_point)
        return record[ClusterDictKeyEnum.LOAD]
    