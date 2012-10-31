'''
Created on 11-Oct-2012

@author: ashish
'''
class BaseDatastore(object)  :
    '''
    These are the methods that any data store should define and do the exact logic
    in-order to be able to be pluggable into the clustering as data-storage mechanism 
    '''
    
    def __init__(self, **kwargs):
        pass
        
    def createdata(self, server_adress, servertype):
        pass
    
    def get_server_state(self, server_adress):
        pass
       
    def set_server_state(self, server_adress, server_state):
        pass
       
    def get_current_load(self, server_address):
        pass
       
    def get_server_by_stickyvalue(self, stickyvalues, endpoint_key):
        pass
     
    def save_updated_data(self, server_adress, endpoint_key, endpoint_name, stickyvalues, load, server_state):
        pass
       
    def remove_stickykeys(self, server_adress, stickyvalues, load):
        pass
       
    def remove_all_stickykeys(self, server_adress, load):
        pass
    
    def get_least_loaded(self, servertype):
        pass
