'''
Clustered server provides abstraction for managing the cluster of server and handling the load-balancing, stickiness to server
'''
from __future__ import division
from bottle import redirect
from fabric import concurrency
from fabric.endpoints.http_ep import methodroute, HTTPServerEndPoint, \
    ClusteredPlugin
from fabric.servers.helpers import redisclient, clusterenum
from fabric.servers.helpers.clusterenum import ClusterDictKeyEnum
from fabric.servers.managedserver import ManagedServer
import logging
import os
import uuid


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
        self.server.get_data('MPEG', new=True)
        return self.servt_sever_name()
    
    
    @methodroute()
    def service(self):
        '''
        This is the entry point for the server where we handle and do the checking logic
        '''
        pass
    
    @methodroute()
    def test(self):
        print os.getpid()
        return os.getpid()
        #return self.server.redisclient.red.get(self.server.my_end_point)

    
    
   
    
class DataStructure(object):
    '''
    This class used to maintain the data require on the Data-Store
    <UniqueId> per adapter
    <Adapter Type>
    <source-adapter-endpoint>
        State
        Load (%)
        Channels  - List
        Client-types - List 
    
    '''    
    
    def __init__(self, server_type, source_server_endpoint, load=0):
        self.uniqueid = str(uuid.uuid4())
        self._server_type = server_type
        self._source_server_endpoint = source_server_endpoint
        self._load = load
        self._channels = []
        
    @property
    def server_type(self):
        return self._server_type
    
    @server_type.setter
    def server_type(self, v):
        self._server_type = v     
        
    @property
    def source_server_endpoint(self):
        return self._source_server_endpoint
    
    @source_server_endpoint.setter
    def source_server_endpoint(self, v):
        self._source_server_endpoint = v      
        
    @property
    def load(self):
        return self._load
    
    @load.setter
    def load(self, v):
        self._load = v      
        
    @property
    def channels(self):
        return self._channels
    
    @channels.setter
    def channels(self, v):
        self._channels = v  
        
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
        self.redisclient = redisclient.RedisClient()
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
        print ( "Addded the ClusteredPlugin to the server")
        return par_plugins + [ ClusteredPlugin() ] 
        

    def create_data(self, my_end_point, servertype):
        '''
        This create DataStructure in Redis
        '''
        d = { ClusterDictKeyEnum.SERVER : my_end_point , 
              ClusterDictKeyEnum.LOAD : 0 , 
              ClusterDictKeyEnum.CHANNELS :[] }
        self.redisclient.setdata(my_end_point, d , tags =[servertype] )
        
    
    
    def get_data(self, my_end_point):
        return self.redisclient.getdata(my_end_point)
    
    
    def update_data(self, my_end_point, load=None, channel=[]):
        self.redisclient.update_channel(my_end_point, channel, load)
    
    
    def core_plugin_logic(self, channel, **kargs):
        '''
        This method will check if the server being requested is current server or any other.
        It will check is_local and if not try and find the request if it is 
        '''
        # Check if this request is handled by me is_local()
        # If not find the right server if already handled by somebody
        #            If handled : Redirect to corresponding server
        #            else : Find a new/existing (depending on adapter type)

        if not self.is_local(channel):
            print " this is not a local request"
            serverdata = self.get_by_channel(channel)
            if serverdata:
                #first check i am not the one
                if serverdata[ClusterDictKeyEnum.SERVER] != self.my_end_point:
                    redirect(serverdata[ClusterDictKeyEnum.SERVER], 303)
            else:
                #find by key if key is given (if this is re-usable adapter)
                try:
                    key = kargs['key']
                except KeyError:
                    key = None
                new_server_for_client = self.get_existing_or_free(key)
                #If its current server, do not redirect
                #first check i am not the one
                if new_server_for_client[ClusterDictKeyEnum.SERVER] != self.my_end_point:
                    redirect(new_server_for_client[ClusterDictKeyEnum.SERVER], 303) 
                                

    def get_existing_or_free(self, key , servertype, **kargs):
        #TOBE OVERRIDDEN METHOD
        print "get_existing_or_free "
        resusable = None
        if key:
            resusable =  self.get_by_key(key=key)
        if not resusable:
            #find server with least load
            resusable = self.redisclient.get_least_loaded(servertype)
        return resusable
            
    def get_least_loaded(self, servertype):
        return self.redisclient.get_least_loaded(servertype)
        
    
    def get_by_channel(self, channel, **kargs):
        '''
        This method get the server who is serving the given channel
            [ Channel for mpeg : <adapter-type>/<host:port:channel-id]
            [ Channel for CODF : <adapter-type>/<tune-id> ]
        '''
        key = self.redisclient.get_server_with_tag(clusterenum.Constants.channel_tag_prefix +channel)
        adapter = None
        #Assumption we have only one key 
        if key:
            adapter = self.redisclient.getdata(list(key)[0])
        return adapter
        
    def get_by_key(self, key , **kargs):
        '''
        This method will get the server who is handling the request based on the key
        '''
        return self.redisclient.get_server_with_tag(key)
        
    def is_local(self, channel, **krags):
        '''
        This method checks if the request will be handled by this server or we need a redirect to the actual server.
        If we need to find the 
        '''
        #Check in data store if this channel is handled already
        #if its already handled we will redirect to that corresponding server
        record = self.redisclient.getdata(self.my_end_point)
        return True if record and channel in record[ClusterDictKeyEnum.CHANNELS] else False
        
    
    def get_load(self, **kargs):
        '''
        This method return the load % on this server
        '''
        record = self.redisclient.getdata(self.my_end_point)
        return record[ClusterDictKeyEnum.LOAD]
    