'''
Clustered server provides abstraction for managing the cluster of server and handling the load-balancing, stickiness to server.

Each server  registers itself to a common datastore when it comes up.
Also each server has access to common datastore 

'''
from __future__ import division
from boots import concurrency
from boots.endpoints.cluster_ep import ClusteredPlugin
from boots.endpoints.http_ep import methodroute, HTTPServerEndPoint
from boots.servers.hybrid import HybridServer
from sqlalchemy.orm.exc import NoResultFound
import logging
import os

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
        name = name or 'ClusteredEP'
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

    def __init__(self, servertype=None, clustered=False, endpoints=None, stickykeys=None, **kargs):
        '''
        
        :param server_adress: defines the the endpoint for the server, this is unique per server #TODO : only needed when clustered
        :param servertype: this defines the server type #TODO :HOWTO?? only needed when clustered
        :param boolean clustered: this parameter defines whether we enable or disable the clustering
        :param endpoints: Endpoint definition provided by cluster server by itself
        :param stickykeys: It provides way to create the sticky value. This param can be a string param , or tuple of params or list of tuples or 
                           method that defines the creation of sticky value (the method will take all the parameters passed and will create the sticky 
                           value). If the list of tuple params are given, we form  the sticky value based on whichever we find first and update based 
                           on all the sticky values created from the list of param-tuple
        '''
        self.clustered = clustered
        endpoints = endpoints or []
        if self.clustered:
            self.server_adress = kargs.pop("server_address" , None)
            self.stickykeys = stickykeys
            endpoints = endpoints #+ [ ClusteredEP()]
        super(ClusteredServer, self).__init__(endpoints=endpoints, servertype=servertype, **kargs)
   
    
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
        #self.server_adress = self.cmmd_line_args['host'] + ':' + str(self.cmmd_line_args['port']) 
        #check if datastore is properly configured via init (in-case it is now , we default to  non-clustered module)
        if hasattr(self, 'datastore'):
            if self.cmmd_line_args['restart']:
                self.restart = True
#                logging.getLogger().debug("Server restarted after crash. read blob from db and set it to server_state")
                self.server_state = self.datastore.get_server_state(self.server_adress)
                self.prepare_to_restart(self.server_state)
                
#            else:
#                Cannot create data here because we dont have server information
#                self.create_data() # This will create data if doesn't exist else updates if update flag is passed
            
            
            
    def post_activate_hook(self):
        super(ClusteredServer, self).post_activate_hook()
        if hasattr(self, 'restart') and self.restart:
            self.process_restart(self.server_state)
        
        
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
#            logging.getLogger().debug("Adding the clustered plugin")
            par_plugins += [ ClusteredPlugin(datastore=self.datastore) ] 
        return par_plugins
        

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
        return self.datastore.get_current_load_db(self.server_adress)
    
    
    def cleanup(self, stickyvalues, load = None):
        '''
        This method will cleanup the sticky mapping and update the new load.
        This needs to be called by the application when it is done with processing and stickyness needs to be removed
        :param stickyvalues : List of sticky values that we want to untag from this server
        :param load : pass the new load , so that it can be updated. 
        '''
        if self.clustered:
            self.ds.remove_sticky_value(stickyvalues)
    
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
        return server.server_address
        #return server_adress if self.get_current_load() == server.load else server.server_address if server else None
        
    def update_new_load(self):
        '''
        This method get the current load and updates to db ( TODO : By add or update)
        '''
        pass
        #self.datastore.save_load_state(self.server_adress, 12.5)
    
   
    def  get_stickyvalues(self, sticky_keys,  paramdict):
        '''
        This method creates the stickyvalues based on the paramaters provided in the paramdict and the type of
        combination which defines the stciky keys as given in sticky_keys
        :param sticky_keys: list of sticky keys which are used to make the sticky_key_values . 
                            This can be string, list, tuple or a callable
        :param dict paramdict: this is the dict of all the parameters provided for this route
        
        :returns: returns the list of sticky values that needs to be updated to the datastore
        '''
        stickyvalues = [] # this is list of stickyvalues
        if type(sticky_keys) is str:
            try :
                stickyvalues += [ paramdict[sticky_keys] ]
            except KeyError:
                pass # If key not present no stickiness 
        elif type(sticky_keys) is tuple:
            value_tuple = self._extract_values_from_keys(sticky_keys, paramdict)
            stickyvalues += [ self.transform_stickyvalues(value_tuple) ]  if value_tuple else []
            #logging.getLogger().debug("sticky values on key : %s tuple : %s ", sticky_keys, stickyvalues)
        elif type(sticky_keys) is list:
            for sticky_key in sticky_keys:
                #recursive call
                stickyvalues += self.get_stickyvalues(sticky_key, paramdict)
#                value_tuple = self._extract_values_from_keys(sticky_key, paramdict)
#                stickyvalues += [ server.transform_stickyvalues(value_tuple) ]  if value_tuple else []
        elif hasattr(sticky_keys, '__call__'):
            val = sticky_keys(**paramdict)
            if val is not None:
                if type(val) is not list:
                    val = [val]
                stickyvalues += val
#        logging.getLogger().debug("Sticky values formed are : %s ", stickyvalues)
        return stickyvalues
    
    def _extract_values_from_keys(self, key_tuple, paramdict):
        '''
        This is internal method that extracts the values for the keys provided in the tuple from the param dict
        :param tuple key_tuple: the tuple of keys which are used for the extracting the corresponding values
        :param dict paramdict: the dict of param which contains the values if they exist
        
        :returns: return the tuple if all the values are present else return None
        '''
        try:
            return tuple([ paramdict[key] for key in key_tuple ])
        except KeyError:
            return None 
    

    def transform_stickyvalues(self, value_tuple):
        '''
        Creates sticky value from the parameters passed in the tuple.
        By default it uses the STICKY_VALUE_SEP (:)  as the separator. The application can choose to override
        this method to transform the stickyvalues in a way it needs
        :param value_tuple: the tuple of values to be converted
        
        :returns: the string of transformed stickyvalue
        '''
        return STICKY_VALUE_SEP.join(str(v) for v in value_tuple)
