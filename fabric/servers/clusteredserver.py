'''
Clustered server provides abstraction for managing the cluster of server and handling the load-balancing, stickiness to server.

Each server  registers itself to a common datastore when it comes up.
Also each server has access to common datastore 

'''
from __future__ import division
from fabric import concurrency
from fabric.datastore.datastore_manager import get_datastore
from fabric.endpoints.cluster_ep import ClusteredPlugin
from fabric.endpoints.http_ep import methodroute, HTTPServerEndPoint
from fabric.servers.hybrid import HybridServer
import argparse
import logging
import os
#from fabric.datastore import truncate_cluster_data

if concurrency == 'gevent':
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
    
        
class ClusteredServer(HybridServer):
    '''
    ClusteredServer provides inbuilt capabilities over and above HybridServer for clustering
    '''

    def __init__(self, servertype=None, clustered=False, endpoints=None, stickykeys=None, ds='ds', **kargs):
        '''
        
        :param server_adress: defines the the endpoint for the server, this is unique per server #TODO : only needed when clustered
        :param servertype: this defines the server type #TODO :HOWTO?? only needed when clustered
        :param boolean clustered: this parameter defines whether we enable or disable the clustering
        :param endpoints: Endpoint definition provided by cluster server by itself
        :param stickykeys: It provides way to create the sticky value. This param can be a string param , or tuple of params or list of tuples or 
                           method that defines the creation of sticky value (the method will take all the parameters passed and will create the sticky 
                           value). If the list of tuple params are given, we form  the sticky value based on whichever we find first and update based 
                           on all the sticky values created from the list of param-tuple
        :param ds: This is the name of the parameter , which will be used to refer the datastore_wrapper object. This gives the handle to the application
                        server to manipulate the data.
        '''
        self.clustered = clustered
        endpoints = endpoints or []
        if self.clustered:
            self.restart = False
            self.config_callbacks['MySQLConfig'] = self._dbconfig_config_update
            self.servertype = servertype
            self.stickykeys = stickykeys
            self.ds = ds
            endpoints = endpoints + [ ClusteredEP()]
        super(ClusteredServer, self).__init__(endpoints=endpoints, **kargs) 
   
    
    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=[], 
                        conflict_handler='error', **kargs):
        '''
        get_arg_parser is a classmethod that can be defined by any server. All such methods are called
        when command line argument processing takes place (see :py:meth:`parse_cmmd_line`)

        :param description: A description of the command line argument
        :param add_help: (internal) 
        :param parents: (internal)
        :param conflict_handler: (internal)
        '''
        _argparser = argparse.ArgumentParser(description=description, add_help=add_help, parents=parents, conflict_handler=conflict_handler) 
        _argparser.add_argument('-r', '--restart', dest='restart',  action="store_true", default=kargs.get('restart', False), help='restart'), 
        return _argparser
    
    
    def prepare_to_restart(self, server_state):
        '''
        The application needs to override this to make use of jsonified server_state.
        This will be called before the server is restarted
        '''
        pass
    
    def process_restart(self, server_state):
        '''
        The application needs to override this to make use of jsonified server_state
        This will be called after the server is restarted.
        '''
        pass
    
    def pre_activate_hook(self):
        super(ClusteredServer, self).pre_activate_hook()
        self.server_adress = self.cmmd_line_args['host'] + ':' + str(self.cmmd_line_args['port']) 
        #check if datastore is properly configured via init (in-case it is now , we default to  non-clustered module)
        if hasattr(self, 'datastore'):
            if self.cmmd_line_args['restart']:
                self.restart = True
                logging.getLogger().debug("Server restarted after crash. read blob from db and set it to server_state")
                self.server_state = self.datastore.get_server_state(self.server_adress)
                self.prepare_to_restart(self.server_state)
            else:
                self.create_data() # This will create data if doesn't exist else updates if update flag is passed
            
            
            
    def post_activate_hook(self):
        super(ClusteredServer, self).post_activate_hook()
        if hasattr(self, 'restart') and self.restart:
            self.process_restart(self.server_state)
        
    def _dbconfig_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the database Configuration.
        Once the DB Config is read , we create MySQL binding that allows to talk to MySQL
        This also checks if this start of the server is a restart, if it is then reads the server_state from server record
        This is set as server object. This state is used by the application to recover its original server state
        '''
        self.datastore = get_datastore( config_obj['Datastore']['datastore'] , config_obj)
        self.add_endpoint(self.datastore)
        if not self.datastore:
            #the server won't be clustered in-case the datastore configuration is messed
            self.clustered = False
            logging.getLogger().debug('Misconfigured datastore . Fallback to non-cluster mode.')
            #print 'Misconfigured datastore  . Fallback to non-cluster mode.'
        logging.getLogger().debug('Cluster database config updated')
        
    def get_standard_plugins(self, plugins):
        '''
        Adds the clusteredPlugin to all routes
        '''
        try:
            par_plugins = super(ClusteredServer, self).get_standard_plugins(plugins)
        except AttributeError:
            par_plugins = []
        #Adds the clustered plugin only if this is clustered server
        if self.clustered:
            logging.getLogger().debug("Adding the clustered plugin")
            par_plugins += [ ClusteredPlugin(datastore=self.datastore, ds=self.ds) ] 
        return par_plugins
        

    def create_data(self):
        '''
        This create DataStructure in Persistent data store
        '''
        self.datastore.createdata(self.server_adress, self.servertype )
        
    def get_server_state(self):
        '''
        This returns the server state, which was stored in the Server record.
        This is jsoned data. 
        The server state is used for storing all the information that is used by the server to recover 
        in case it crashed and came up and trying to regain its state.
        The Server instance  should write its logic using this data , so as how it will recover
        '''
        return self.datastore.get_server_state(self.server_adress)
    
    def set_server_state(self, server_state):
        '''
        This sets the server state as provided by the Server itself
        '''
        self.datastore.set_server_state(self.server_adress, server_state)
    

    def get_new_load(self):
        '''
        This method defines how the load gets updated which each new request being served or completed
        It returns new load percentage, this is neeeded to be handled by the 
        '''
        return 0
    
    def get_current_load(self):
        '''
        This method returns the existing load of this server as per it exists in the datastore
        '''
        return self.datastore.get_current_load(self.server_adress)
    
    
    def cleanup(self, stickyvalues, load = None):
        '''
        This method will cleanup the sticky mapping and update the new load.
        This needs to be called by the application when it is done with processing and stickyness needs to be removed
        :param stickyvalues : List of sticky values that we want to untag from this server
        :param load : pass the new load , so that it can be updated. 
        '''
        if self.clustered:
            self.datastore.remove_stickykeys(self.server_adress, stickyvalues, load)
    
    def cleanupall(self, load = None):
        '''
        This method removes all the sticky-ness present for this server 
        :param load: Optionally load is passed so it can be updated
        '''
        self.datastore.remove_all_stickykeys(self.server_adress, load)
            
    def get_least_loaded(self, servertype=None, server_adress=None):
        '''
        This method gets the least loaded server of the given servertype 
        :param servertype: this parameters contains the type of server
        
        :returns: the unique id or the server which is the sever address with ports
        '''
        servertype = servertype or self.servertype
        server =  self.datastore.get_least_loaded(servertype)
        return server.unique_key
        #return server_adress if self.get_current_load() == server.load else server.unique_key if server else None
        
    
    def get_by_stickyvalue(self, stickyvalues, endpoint_key):
        '''
        This method gets the server with the stickyvalue. The stickyvalue makes sure this request is handled
        by the correct server. 
        :param list stickyvalues: stickyvalues which is handled by this server
        :param endpoint_key: uuid of the endpoint
        
        :returns: the unique id or the server which is the sever address with port
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
        
        :returns: the string of transformed stickyvalue
        '''
        return STICKY_VALUE_SEP.join(str(v) for v in value_tuple)
