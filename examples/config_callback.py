'''
This example demonstrates a simple config callback. 
A callback is registered on the config_obj and every read/update event on config file results in this callback to be called. 
'''

from boots.servers.managedserver import ManagedServer
from boots.servers.managedserver import ManagedEP, methodroute
 
class MyEP(ManagedEP):
    @methodroute()
    def update_conn(self, endpoint=None):
        updated_d = dict(self.server.config['Database'])
        updated_d['dbtype'] = 'MYSQL'
        self.server.config['Database'] = updated_d 
        return self.server.config 
    

class MyServer(ManagedServer):
    
    def setup_conn_pool(self, action, full_key, new_value, config_obj):
        '''
            :param action: action indicates whether callback is regarding a value being set on the attribute or a delete of the attribute. 
            Action is of type Config.Action (indicates onset or ondel)
            :param full_key: a list representing the full key of the attribute in the config dict that  resulted in this callback being
             called
            :param new_value: The value that was just set or in case action == ondel, None
            :param config_obj: a reference to the config_obj on which this callback was registered 
            
        '''
        # code to setup the connection pool
        print new_value
        
    def __init__(self, *args, **kargs):
        self.config_callbacks['Database'] = self.setup_conn_pool
        super(MyServer, self).__init__(*args, **kargs)
        
        

    

ep1 = MyEP(mountpoint="/")
mngd_server = MyServer(endpoints=[ep1])

if __name__ == '__main__':
    mngd_server.start_server(logger=True, defhost='localhost', defport=9998, standalone=True, proj_dir=".", description="A test server for the boots framework")
