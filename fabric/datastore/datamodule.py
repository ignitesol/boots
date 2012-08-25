'''
This is base module for writing the data binding for cluster server
We will have either mysql / redis or any other type of persitent type of data binding
'''
from fabric.servers.helpers import clusterenum
from fabric.servers.helpers.clusterenum import ClusterDictKeyEnum
import json
import redis
class BaseDataBinding(object)  :
    
    def __init__(self, **kwargs):
        pass
    
    
    def setdata(self, key, value, servertype):
        pass
    
    
    def getdata(self, key):
        pass
    
    def update_server(self, key, channel, load = None):
        pass
    
    
    def get_server_of_type(self, tag):
        pass
        return self.red.smembers(tag)
    
    def get_least_loaded(self, servertype):
        pass
    
    
    
    
class RedisBinding(BaseDataBinding):
    '''
    This class binds using the Redis as data store.
    Redis needs to be configured and the end points must be specified along with any authentication if required
    '''
    
    def __init__(self, host='localhost', port=6379):
        super(RedisBinding, self).__init__()
        # localhost:6379
        self.pool = redis.ConnectionPool(host=host, port=port, db=0)
        self.red = redis.Redis(connection_pool=self.pool)
        
        
    def setdata(self, key, value, servertype):
        '''
        This method set the key to value. 
        Value MUST of type dict other we throw error.
        Key itself is added as part of the data , so its easy while we fetch and manupulate for updation 
        If tags are provided we tag this record with the tags 
        '''
        if not type(value) is dict:
            raise Exception("Value must be of type dict")
        # Add the key to the value part of the data
        try:
            value[ClusterDictKeyEnum.SERVER]
        except KeyError:
            value[ClusterDictKeyEnum.SERVER] = key
        
        #Send into Redis data store & put the relevant tags
        #print "Data dumped into Redis ", json.dumps(value)
        self.red.set(key, json.dumps(value))
        # Add the servertype as Tag
        self.red.sadd(servertype, key)
            
            
    def getdata(self, key):
        # ret = json.loads(self.red.get(key))
        # print "Data retrieved from Redis ", ret
        return json.loads(self.red.get(key))
            
    def update_server(self, key ,channel, load):
        '''
        1) This updates the channel list
        2) Tags this server with channel (Redis specific)
        3) set the new load
        '''
        value = self.red.get(key)
        value = json.loads(value)
        if channel not in  value[ClusterDictKeyEnum.CHANNELS]:
            value[ClusterDictKeyEnum.CHANNELS] +=  [channel] 
            value[ClusterDictKeyEnum.LOAD] = int(value[ClusterDictKeyEnum.LOAD]) + int(load)
        #Add tag with channel for this server
        self.red.sadd(clusterenum.Constants.channel_tag_prefix + channel, key)
        #Send into Redis data store & put the relevant tags
        self.red.set(key, json.dumps(value))
        
    
    def get_server_of_type(self, servertype):
        # get the type of the server based on the tags given ( servertype )
        return self.red.smembers(servertype)
    
    def get_least_loaded(self, servertype):
        key_list = self.red.smembers(servertype)
        load, serverdata = min([(self.getdata(key)[ClusterDictKeyEnum.LOAD] , self.getdata(key)) for key in key_list if self.getdata(key)], key=lambda x:x[0])
        return serverdata
    
    
    
class MySQLBinding(BaseDataBinding):
    pass
    #TODO : Later