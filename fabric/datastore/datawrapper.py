from fabric.common.singleton import SingletonType
from threading import RLock
import logging

class Shared(object):
    def __init__(self):
        self._lock = RLock()
        # add your shared attributes here
        self.load = None
        self.server_state = None
        
        # ensure dirty initialization is the last line of __init__
        self._dirty = False
        
    def __setattr__(self, attr, value):
        if attr not in [ '_lock', '_dirty' ]:
            with self._lock:
                self._dirty = True
                super(Shared, self).__setattr__(attr, value)
        else:
            super(Shared, self).__setattr__(attr, value)
            
    @property
    def lock(self):
        return self._lock
    @property
    def dirty(self):
        with self._lock:
            return self._dirty
    @dirty.setter
    def dirty(self, val):
        with self._lock:
            self._dirty = val
            return self._dirty
            
class DSWrapperObject(object):
    '''
    This class is used to create and update the sticky relations per sticky keys 
    This loads the sticky keys values that exist and then update the new sticky key values those are 
    updated. These are then updated in db if the dirty flag is set(there has been change in the
    sticky mapping)
    
    Following params are class level attributes in the DSWapper object
    load - load : float - The load in float in % of the server
    server_state : json - The server state saved by the server, It will used to retrieve the state of the server in 
                          case of the abrupt shutdown and restart of the server
                          
    This object also provides 'lock' attribute. In the application whenever updating the mutables like load and server_state
    use the lock to maintain the integrity of the server
    '''    
    
    __metaclass__ = SingletonType

    def __init__(self, datastore, endpoint_key, endpoint_name, autosave=True, read_stickymappinglist=None):
        read_stickymappinglist = read_stickymappinglist or []
        self._lock = RLock()
        # add your shared attributes here
        self.datastore = datastore
        self.endpoint_key = endpoint_key
        self.endpoint_name = endpoint_name
        self.read_stickymappinglist = read_stickymappinglist
        self.write_stickymappinglist = []

        self.server_address = None
        self._autosave = autosave

        self.load = None
        self.server_state = None
        
        # ensure dirty initialization is the last line of __init__
        self._dirty = False
      
    def __setattr__(self, attr, value):
        if attr not in [ '_lock', '_dirty' ]:
            with self._lock:
                self._dirty = True
                super(DSWrapperObject, self).__setattr__(attr, value)
        else:
            super(DSWrapperObject, self).__setattr__(attr, value)
            
    @property
    def lock(self):
        return self._lock
    
    @property
    def dirty(self):
        with self._lock:
            return self._dirty
    @dirty.setter
    def dirty(self, val):
        with self._lock:
            self._dirty = val
            return self._dirty  
        
    def add_to_write_list(self, stickyvalues):
        '''
        This adds to write stikcy list
        :param stickyvalues: list
        '''
        logging.getLogger().debug("adding to write list : %s", stickyvalues)
        if stickyvalues is not None and type(stickyvalues) is list:
            self.write_stickymappinglist += stickyvalues
    
    def remove_from_write_list(self, stickyvalues):
        '''
        This method removes from the the write sticky list
        :param stickyvalues: list        
        '''
        logging.getLogger().debug("removing from write list : %s", stickyvalues)
        self.write_stickymappinglist =  [s for s in self.write_stickymappinglist if s not in stickyvalues]
#    @property
#    def server_address(self):
#        return self._server_address
#    
#    @server_address.setter
#    def server_address(self, value):
#        self.dirty = True
#        self._server_address = value
#        
#    @property
#    def endpoint_key(self):
#        return self._endpoint_key
#    
#    @endpoint_key.setter
#    def endpoint_key(self, value):
#        self.dirty = True
#        self._endpoint_key = value
#    
#    @property
#    def endpoint_name(self):
#        return self._endpoint_name
#      
#    @endpoint_name.setter
#    def endpoint_name(self, value):
#        self.dirty = True
#        self._endpoint_name = value  
     
    
    def _save(self):
        '''
        This method saves to datastore if _dirty flag is true and autosave is true.
        This method will be always called whenever there are new sticky keys updated and/or there is change in load 
        and/or there is some updates to data blob that we want to do.
        '''
        logging.getLogger().debug("save is called. dirty : %s, object : %s ", self.dirty, id(self))
        with self.lock:
            if self._autosave and self.dirty:
                self.dirty = False
                self.dirty = False
                logging.getLogger().debug("Saving into DB write_stickymappinglist : %s", self.write_stickymappinglist)
                self.datastore.save_updated_data(self.server_address, self.endpoint_key, self.endpoint_name, self.write_stickymappinglist)
                self.write_stickymappinglist = []
                self.datastore.save_load_state(self.server_address, self.load, self.server_state)

    
    def _save_stickyvalues(self):
        '''
        saves only the sticky values
        '''
        with self.lock:
            if self._autosave and self.dirty:
                for s in self.write_stickymappinglist:
                    self.datastore.save_stickyvalue(self.server_address, self.endpoint_key, self.endpoint_name, s)
                self.write_stickymappinglist = []
    
    def _read_by_stickyvalue(self, stickyvalues):
        '''
        This method gets the server with the stickyvalue. The stickyvalue makes sure this request is handled
        by the correct server. 
        :param list stickyvalues: stickyvalues which is handled by this server
        :param str endpoint_key: uuid of the endpoint
        
        :returns: returns the unique id or the server which is the sever address with port
        '''
        if stickyvalues is None:
            raise Exception("Sticky values passed cannot be empty or None")
        ret_val =  self.datastore.get_server_by_stickyvalue(stickyvalues, self.endpoint_key)
        if ret_val is None:
            raise Exception("No server is found sticked to this")
        server, cluster_mapping_list = ret_val
        self.server_address = server.unique_key

        for mapping in cluster_mapping_list:
            self.endpoint_key = mapping.endpoint_key
            self.endpoint_name = mapping.endpoint_name
            self.read_stickymappinglist += [ mapping.sticky_value] if mapping.sticky_value not in self.read_stickymappinglist else []
            
    
    def update_load(self, load, force=False):
        '''
        This method updates the load in datawrapper object
        :param float load: this is the new/current load for this server
        '''
        if load is not None:
            self.load = load
        #logging.getLogger().warn("Inside wrapper object update_load dirty : %s", self.dirty)
        if force and self.dirty:
            #force the update directly
            self.datastore.save_load_state(self.server_address, self.load, self.server_state) 
            
    
    def update(self, stickyvalues=None, datablob=None):
        '''
        This method update the wrapped mapping
        :param list stickyvalues: this is the list of stickyvalues
        :param float load: this is the new/current load for this server
        :param datablob: this is the blob that needs to be updated for recovery
        '''
        logging.getLogger().debug("update : %s , object : %s", stickyvalues, id(self))
        stickyvalues = stickyvalues or []
        new_sticky_values = (stickyvalue for stickyvalue in stickyvalues  if stickyvalue not in self.write_stickymappinglist) # generator expression 
        for stickyvalue in new_sticky_values:
            self.add_to_write_list([stickyvalue])
            self.dirty = True
        if datablob is not None:
            #TODO : this needs to be updated rather than insert . 
            self.data = datablob
            

    def add_sticky_value(self, stickyvalues):
        '''
        This will add the new sticky value to the existing list of params .
        :param stickyvalues: newly formed sticky values which are added to the DSWrapper object
        '''
        logging.getLogger().debug("adding sticky values to the datastructure : %s , object : %s", stickyvalues, id(self))
        if stickyvalues is not None:
            if type(stickyvalues) is str:
                if stickyvalues not in self.write_stickymappinglist: # if condition separated on purpose ,# else depends only on first if
                    self.add_to_write_list([stickyvalues])
                    self.dirty = True
            else:
                new_sticky_values = (stickyvalue for stickyvalue in stickyvalues if stickyvalue not in self.write_stickymappinglist) # generator expression 
                for stickyvalue in new_sticky_values:
                    self.add_to_write_list([stickyvalue] if type(stickyvalue) is str else stickyvalue)
                    self.dirty = True
                    
    def remove_sticky_value(self, stickyvalues):
        '''
        This will remove the sticky values from the db directly
        :param stickyvalues: list of sticky values to be deleted.
        '''
        try:
            #logging.getLogger().debug("Remove sticky values : %s, object : %s", stickyvalues, id(self))
            with self.lock:
                if type(stickyvalues) is not list:
                    stickyvalues = [ stickyvalues ] 
                self.datastore.remove_stickyvalues(stickyvalues)
                self.remove_from_write_list(stickyvalues)
                self.read_stickymappinglist = [ s for s in self.read_stickymappinglist if s not in stickyvalues ]
                logging.getLogger().debug("To be Written values in the object : %s", self.write_stickymappinglist)
        except Exception as e:
            logging.getLogger().debug("Exception in Remove sticky values : %s", e)
