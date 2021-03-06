from boots.common.singleton import Singleton
from sqlalchemy.exc import SQLAlchemyError
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
            
class DSWrapperObject(Singleton):
    '''
    This class is used to create and update the sticky relations per sticky keys 
    This loads the sticky keys values that exist and then update the new sticky key values those are 
    updated. These are then updated in db if the dirty flag is set(there has been change in the
    sticky mapping)
    
    Some of the methods also provide directly writing to DB, instead updating at the end of the
    request
    
    DSWrapper object is a signleton. Each server will have only one object of this type. 
    
    This object will have 
    server_address : server adress which is represented as unique_key in server table
    server_id : The database id of the server
    endpoint_key : endpoint_key
    endpoint_name : endpoint name
    
    There are two list of stickyvalues
    1) read_stickymappinglist : These are read from the db for this server
    2) write_stickymappinglist : These are newly created values and needs to be written to the DB at the
                                 end of the request if _dirty flag is set
    
    Following params are class level attributes in the DSWapper object
    load - load : float - The load in float in % of the server
    server_state : json - The server state saved by the server, It will used to retrieve the state of the server in 
                          case of the abrupt shutdown and restart of the server
                          
    This object also provides 'lock' attribute. In the application whenever updating the mutables like load and server_state
    use the lock to maintain the integrity of the server
    '''    
    
    @classmethod
    def get_instance(cls):
        '''
        This method returns the signleton object of the this class
        '''
        ret_val = DSWrapperObject()
        #logging.getLogger().debug("DSWrapperObject id %s . Server address : %s ", id(ret_val), ret_val.server_address)
        assert ret_val.server_address is not None
        assert ret_val.server_id is not None
        return ret_val

    def __init__(self, datastore, server_address, server_id, endpoint_key, endpoint_name, autosave=True, read_stickymappinglist=None):
        read_stickymappinglist = read_stickymappinglist or []
        self._lock = RLock()
        # add your shared attributes here
        self.datastore = datastore
        self.endpoint_key = endpoint_key
        self.endpoint_name = endpoint_name
        self.read_stickymappinglist = read_stickymappinglist
        self.write_stickymappinglist = []

        self.server_address = server_address
        self.server_id = server_id
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
        This adds to write sticky list
        :param stickyvalues: list
        '''
#        logging.getLogger().debug("adding to write list : %s", stickyvalues)
        if stickyvalues is not None and type(stickyvalues) is list:
            self.write_stickymappinglist += stickyvalues
    
    def remove_from_write_list(self, stickyvalues):
        '''
        This method removes from the the write sticky list
        :param stickyvalues: list        
        '''
#        logging.getLogger().debug("removing from write list : %s", stickyvalues)
        self.write_stickymappinglist =  [s for s in self.write_stickymappinglist if s not in stickyvalues]
     
    
    def _save(self):
        '''
        This method saves to datastore if _dirty flag is true and autosave is true.
        This method will be always called whenever there are new sticky keys updated and/or there is change in load 
        and/or there is some updates to data blob that we want to do.
        '''
#        logging.getLogger().debug("save is called. dirty : %s, object : %s ", self.dirty, id(self))
        with self.lock:
            if self._autosave and self.dirty:
                self.dirty = False
#                logging.getLogger().debug("Saving into DB write_stickymappinglist : %s", self.write_stickymappinglist)
                self.datastore.save_stickyvalues(self.server_id, self.endpoint_key, self.endpoint_name, self.write_stickymappinglist)
                self.write_stickymappinglist = []
                self.datastore.save_load_state(self.server_address, self.load, self.server_state)

    
    def _save_stickyvalues(self):
        '''
        saves only the sticky values
        '''
        with self.lock:
            if self._autosave and self.dirty:
                for s in self.write_stickymappinglist:
#                    logging.getLogger().debug("Saving :%s",  s)
                    self.datastore.save_stickyvalue(self.server_id, self.endpoint_key, self.endpoint_name, s)
                self.write_stickymappinglist = []
    
    def _read_by_stickyvalue(self, stickyvalues, servertype):
        '''
        This method gets the server with the stickyvalue. The stickyvalue makes sure this request is handled
        by the correct server. 
        If there are no server handling these sticky values 
        :param list stickyvalues: stickyvalues which is handled by this server
        :param str servertype: the type of the server
        
        :returns: returns the unique id or the server which is the sever address with port
        '''
        try:
            d =  self.datastore.get_target_server(stickyvalues, servertype, self.server_address, self.endpoint_name, self.endpoint_key)
        except SQLAlchemyError as e:
            logging.getLogger().exception("Exception in while finding the correct server  : %s", e)
            raise Exception("Exception in while finding the correct server")
        cluster_mapping_list = None
        if d['sticky_found']:
            cluster_mapping_list = d['stickymapping']
        server = d['target_server']
        success = True #d['success']
        self.server_address = server.unique_key
        if success and cluster_mapping_list:
            for mapping in cluster_mapping_list:
                self.endpoint_key = mapping.endpoint_key
                self.endpoint_name = mapping.endpoint_name
                self.read_stickymappinglist += [ mapping.sticky_value] if mapping.sticky_value not in self.read_stickymappinglist else []
        return server.unique_key
            
    
    def update_load(self, load, force=False):
        '''
        This method updates the load in datawrapper object
        :param float load: this is the new/current load for this server
        :param boolean force: explicitly tells to write to database
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
#        logging.getLogger().debug("update : %s , object : %s", stickyvalues, id(self))
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
#        logging.getLogger().debug("adding sticky values to the datastructure : %s , object : %s", stickyvalues, id(self))
        if stickyvalues is not None:
            if type(stickyvalues) is str:
                if stickyvalues not in self.write_stickymappinglist and stickyvalues not in self.read_stickymappinglist: # if condition separated on purpose ,# else depends only on first if
                    self.add_to_write_list([stickyvalues])
                    self.dirty = True
            else:
                new_sticky_values = (stickyvalue for stickyvalue in stickyvalues if stickyvalue not in self.write_stickymappinglist and 
                                                                                        stickyvalue not in self.read_stickymappinglist) # generator expression 
                for stickyvalue in new_sticky_values:
                    self.add_to_write_list([stickyvalue] if type(stickyvalue) is str else stickyvalue)
                    self.dirty = True
        self._save_stickyvalues()
                    
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
#                logging.getLogger().debug("To be Written values in the object : %s", self.write_stickymappinglist)
        except Exception as e:
            logging.getLogger().debug("Exception in Remove sticky values : %s", e)
            
    def update_sticky_value(self, old , new, force=True):
        '''
        This will update the old sticky value to new sticky value, This takes effect directly into the db
        '''
        if force:
            self.datastore.update_sticky_value(old, new, self.server_id, self.endpoint_name, self.endpoint_key)
        self.read_stickymappinglist = [ x for x in self.read_stickymappinglist if x is not old ]
        self.write_stickymappinglist += [new]
            
