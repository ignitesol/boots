from fabric.common.singleton import Singleton
from fabric.servers.helpers.clusterenum import ClusterDictKeyEnum
import json
import redis
from fabric.servers.helpers import clusterenum


class RedisClient(Singleton):
    '''
    This class handles the logic of storing and retreiving data.
    Along with that it also tags and make search based on the tags as needed
    Tags are of two types
        channel tags : preceded with "channel:"
        key tags : preceded with "key:" 
    '''

    def __init__(self):
        self.pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
        self.red = redis.Redis(connection_pool=self.pool)
        
        
    def setdata(self, key, value, tags=[]):
        '''
        This method set the key to value. 
        Value MUST of type dict other we throw error.
        Key itself is added as part of the data , so its easy while we fetch and manupulate for updation 
        If tags are provided we tag this record with the tags 
        '''
        if not type(value) is dict:
            raise Exception("Value must be of type dict")
        try:
            value[ClusterDictKeyEnum.SERVER]
        except KeyError:
            value[ClusterDictKeyEnum.SERVER] = key
        
        #Send into Redis data store & put the relevant tags
        print "Data dumped into Redis ", json.dumps(value)
        self.red.set(key, json.dumps(value))
        for tag in tags:
            self.red.sadd(tag, key)
            
            
    def getdata(self, key):
        ret = json.loads(self.red.get(key))
        print "Data retrieved from Redis ", ret
        return json.loads(self.red.get(key))
            
    def update_channel(self, key ,channel, load):
        '''
        1) This updates the channel list
        2) Tags this server with channel
        3) set the new load
        '''
        value = self.red.get(key)
        print "Key is : ", key
        print "value fetched : ", value
        value = json.loads(value)
        if channel not in  value[ClusterDictKeyEnum.CHANNELS]:
            value[ClusterDictKeyEnum.CHANNELS] +=  [channel] 
            value[ClusterDictKeyEnum.LOAD] = int(value[ClusterDictKeyEnum.LOAD]) + int(load)
        #Add tag with channel for this server
        self.red.sadd(clusterenum.Constants.channel_tag_prefix + channel, key)
        
        #Send into Redis data store & put the relevant tags
        self.red.set(key, json.dumps(value))
        
    
    def get_server_with_tag(self, tag):
        return self.red.smembers(tag)
    
    def get_least_loaded(self, servertype):
        key_list = self.red.smembers(servertype)
        load, serverdata = min([(self.getdata(key)[ClusterDictKeyEnum.LOAD] , self.getdata(key)) for key in key_list if self.getdata(key)], key=lambda x:x[0])
        return serverdata