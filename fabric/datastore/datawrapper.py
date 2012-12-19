class DSWrapperObject(object):
    '''
    This class is used to create and update the sticky relations per sticky keys 
    This loads the sticky keys values that exist and then update the new sticky key values those are 
    updated. These are then updated in db if the dirty flag is set(there has been change in the
    sticky mapping)
    '''    
    
    def __init__(self, datastore, endpoint_key, endpoint_name, autosave=True, stickymappinglist=[]):
        
        self.datastore = datastore
        self.endpoint_key = endpoint_key
        self.endpoint_name = endpoint_name
        self.stickymappinglist = stickymappinglist

        self._load = None
        self._server_state = None
        self._server_address = None
        
        self._dirty = False
        self._autosave = autosave
        
    
    @property
    def dirty(self):
        return self._dirty
    
    @dirty.setter
    def dirty(self, value):
        self._dirty = value
    
    
    @property
    def server_state(self):
        return self._server_state
    
    @server_state.setter
    def server_state(self, value):
        self._server_state = value
    
    @property
    def load(self):
        return self._load
    
    @load.setter
    def load(self, value):
        self._load = value
        
    @property
    def server_address(self):
        return self._server_address
    
    @server_address.setter
    def server_address(self, value):
        self._server_address = value
        
    @property
    def endpoint_key(self):
        return self._endpoint_key
    
    @endpoint_key.setter
    def endpoint_key(self, value):
        self._endpoint_key = value
    
    @property
    def endpoint_name(self):
        return self._endpoint_name
      
    @endpoint_name.setter
    def endpoint_name(self, value):
        self._endpoint_name = value  
      
    #only getter for autosave, needs to be given value at initialization    
#    @property
#    def autosave(self):
#        return self.autosave
    
    def _save(self):
        '''
        This method saves to datastore if _dirty flag is true and autosave is true.
        This method will be always called whenever there are new sticky keys updated and/or there is change in load 
        and/or there is some updates to data blob that we want to do.
        '''
        if self._autosave and self._dirty:
            self.datastore.\
                save_updated_data(self.server_address, self.endpoint_key, self.endpoint_name, self.stickymappinglist)
            self.datastore.save_load_state(self.server_address, self.load, self.server_state)

    
    def _save_stickyvalues(self):
        '''
        saves only the sticky values
        '''
        if self._autosave and self._dirty:
            for s in self.stickymappinglist:
                self.datastore.save_stickyvalue(self.server_address, self.endpoint_key, self.endpoint_name, s)
    
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
            self.stickymappinglist += [ mapping.sticky_value] if mapping.sticky_value not in self.stickymappinglist else []
            
    
    def update_load(self, load, force=False):
        '''
        This method updates the load in datawrapper object
        :param float load: this is the new/current load for this server
        '''
        if load is not None:
            self.load = load
            self.dirty = True
        if force and self.dirty:
            #force the update directly
            self.datastore.save_load_state(self.server_address, self.load, self.server_state) 
            self.dirty = False
            
    
    def update(self, stickyvalues=[], datablob=None):
        '''
        This method update the wrapped mapping
        :param list stickyvalues: this is the list of stickyvalues
        :param float load: this is the new/current load for this server
        :param datablob: this is the blob that needs to be updated for recovery
        '''
        
        new_sticky_values = (stickyvalue for stickyvalue in stickyvalues  if stickyvalue not in self.stickymappinglist) # generator expression 
        for stickyvalue in new_sticky_values:
            self.stickymappinglist += [stickyvalue]
            self.dirty = True

        if datablob is not None:
            #TODO : this needs to be updated rather than insert . 
            self.data = datablob
            self.dirty = True
            

    def add_sticky_value(self, stickyvalues):
        '''
        This will add the new sticky value to the existing list of params .
                
        :param stickyvalues: newly formed sticky values
        '''
        if stickyvalues is not None:
            if type(stickyvalues) is str:
                if stickyvalues not in self.stickymappinglist: # if condition separated on purpose ,# else depends only on first if
                    self.stickymappinglist += [stickyvalues]
                    self.dirty = True
            else:
                new_sticky_values = (stickyvalue for stickyvalue in stickyvalues if stickyvalue not in self.stickymappinglist) # generator expression 
                for stickyvalue in new_sticky_values:
                    self.stickymappinglist += [stickyvalue] if type(stickyvalue) is str else stickyvalue 
                    self.dirty = True
                    
    def remove_sticky_value(self, stickyvalues):
        '''
        This will remove the sticky values
        '''
        self.datastore.remove_stickykeys(self, self.server_adress, stickyvalues)