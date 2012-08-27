'''
This is base module for writing the data binding for cluster server
We will have either mysql / redis or any other type of persistent type of data binding
'''
from dbengine import DatabaseEngine
from fabric.datastore.dbengine import DBConfig
from fabric.servers.helpers import clusterenum
from fabric.servers.helpers.clusterenum import ClusterDictKeyEnum
from sqlalchemy import Column, schema as saschema, schema, types
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.schema import UniqueConstraint, ForeignKey, ForeignKeyConstraint
from sqlalchemy.sql.expression import join, and_, func, outerjoin
from sqlalchemy.types import String, Integer, Float
import json
import logging
import redis
class BaseDataBinding(object)  :
    
    def __init__(self, **kwargs):
        pass
    
    
    def setdata(self, server_adress, servertype):
        pass
    
    
    def getdata(self, server_adress):
        pass
    
    def update_server(self, server_adress, channel, load = None):
        pass
    
    
    def get_server_of_type(self, servertype):
        pass
    
    def get_server_by_stickykey(self, stickykey):
        pass
    
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
        
        
    def setdata(self, server_adress, servertype):
        '''
        This method set the key to value. 
        Value MUST of type dict other we throw error.
        Key itself is added as part of the data , so its easy while we fetch and manupulate for updation 
        If tags are provided we tag this record with the tags 
        '''
        value = {    ClusterDictKeyEnum.SERVER : server_adress , 
                     ClusterDictKeyEnum.LOAD : 0 , 
                     ClusterDictKeyEnum.CHANNELS :[]}
        
        if not type(value) is dict:
            raise Exception("Value must be of type dict")
        # Add the key to the value part of the data
        try:
            value[ClusterDictKeyEnum.SERVER]
        except KeyError:
            value[ClusterDictKeyEnum.SERVER] = server_adress
        
        #Send into Redis data store & put the relevant tags
        #print "Data dumped into Redis ", json.dumps(value)
        self.red.set(server_adress, json.dumps(value))
        # Add the servertype as Tag
        self.red.sadd(servertype, server_adress)
            
            
    def getdata(self, key):
        # ret = json.loads(self.red.get(key))
        # print "Data retrieved from Redis ", ret
        return json.loads(self.red.get(key))
            
    def update_server(self, key ,channel, stickykey, load):
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
        #Add tag with sticky-key for this server
        self.red.sadd(clusterenum.Constants.sticky_tag_prefix + stickykey, key) 
        #Send into Redis data store & put the relevant tags
        self.red.set(key, json.dumps(value))
        
    
    def get_server_of_type(self, servertype):
        # get the type of the server based on the tags given ( servertype )
        return self.get_by_tag(servertype)
    
    def get_server_by_stickykey(self, stickeykey):
        return self.get_by_tag(clusterenum.Constants.sticky_tag_prefix + stickeykey)
    
    def get_least_loaded(self, servertype):
        key_list = self.red.smembers(servertype)
        load, serverdata = min([(self.getdata(key)[ClusterDictKeyEnum.LOAD] , self.getdata(key)) for key in key_list if self.getdata(key)], key=lambda x:x[0])
        return serverdata
    
    
    def get_by_tag(self, tag):
        '''
            This is redis specific method. Tagging and retrieving by tag , redis specific
        '''
        return self.red.smembers(tag)
   
   

def dbsessionhandler(fn):
    '''
    This decorator handles the creation and closing of the session object.
    '''
    def wrapped(self, *args, **kwargs):
        self.sess = self.get_session()
        retval = fn(self, *args, **kwargs)
        self.sess.close()
        return retval
    return wrapped   
   
    
class MySQLBinding(BaseDataBinding):
    
    def get_session(self):
        return self.engine.get_session()
    
    def __init__(self, dbconfig=None):
        super(MySQLBinding, self).__init__()
        dbtype = "mysql"
        db_url = "mysql://cluster:cluster@localhost:3306/cluster"
        pool_size = 100
        max_overflow = 0
        connection_timeout = 30
        if not dbconfig:
            dbconfig = DBConfig(dbtype, db_url, pool_size, max_overflow, connection_timeout)
        self.engine = DatabaseEngine(dbconfig)
    
        
    @dbsessionhandler
    def setdata(self, server_adress, servertype):
        '''
        This creates the entry for each server in the server table
        :param server_adress: address of the self/server itself, this will be unique entry 
        :param servertype: type of the server 
        '''
        try:
            server = Server(servertype, server_adress, 'data', 0)
            self.sess.add(server)
            self.sess.commit()
        except IntegrityError as e:
            #Based on the type of mode : Start/Restart we might want to clear or update data
            print "IntegrityError exception caught ", e
            self.sess.rollback()
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:0, Server.server_type:servertype, Server.data:'updateddata'}, synchronize_session=False)
            self.sess.commit()
        
    
    @dbsessionhandler
    def getdata(self, server_adress):
        '''
        This method get thge data for the given server based on its server_address , which is the unique key per server
        :param server_adress: server address 
        '''
        server = None
        try:
            server = self.sess.query(Server).filter(Server.unique_key == server_adress).one()
        except NoResultFound:
            pass
        except MultipleResultsFound:
            pass
        return server
    
    @dbsessionhandler
    def update_server(self, server_adress, stickyvalue, load, data=None):
        '''
        This method adds the stickyvalue mapping and the load for the server_address
        :param server_adress: the unique server_adress
        :param stickyvalue: new sticky value
        :param load: load percentage for this server
        '''
        #Complete transactional update
        if data:
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load, Server.data:'updateddata_viaserver'}, synchronize_session=False)
        else:
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load}, synchronize_session=False)
                    
        server = self.sess.query(Server).filter(Server.unique_key == server_adress).one()
            
        stickymapping = StickyMapping(server.server_id, stickyvalue)      
        self.sess.add(stickymapping)
        self.sess.commit()  
    
    @dbsessionhandler
    def update_stickyvalue(self, server_adress, stickyvalue):
        '''
        This method adds stickyvalue mapping to the server , does not update the load
        :param server_adress: the unique server_adress
        :param stickyvalue: new sticky value
        '''
        server = self.sess.query(Server).filter(Server.unique_key == server_adress).one()
        stickymapping = StickyMapping(server.server_id, stickyvalue)      
        self.sess.add(stickymapping)
        self.sess.commit() 
        
        
    @dbsessionhandler
    def get_server_by_stickyvalue(self, stickyvalue):
        '''
        This method server which handles the stickyvalue passes
        :param stickyvalue: 
        '''
        # Server.server_id == StickyMapping.server_id
        try:
            stickymapping = self.sess.query(StickyMapping).filter(StickyMapping.sticky_value == stickyvalue).one()
        except NoResultFound:
            return None
        #TODO : Join was screwing up for some reason so , dirty code . Must  fix
        server = self.sess.query(Server).filter(Server.server_id == stickymapping.server_id).one()
        return server
        

    @dbsessionhandler
    def get_least_loaded(self, servertype):
        '''
        This method finds the least loaded server of the given type
        '''
        print "get the least loaded : servertype : ", servertype
        min_loaded_server = None
        min_load = self.sess.query(func.min(Server.load)).filter(Server.server_type == servertype ).one()
        if(min_load[0] < 100):
            min_loaded_server = self.sess.query(Server).filter(Server.load == min_load[0] ).first()
        return min_loaded_server
    
    
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
Base = declarative_base(bind = MySQLBinding().engine.engine)

class Server(Base):
    ''' mapping class for server table'''
    __tablename__ = 'server'
    server_id = Column(Integer, primary_key=True)
    server_type = Column(String(200))
    unique_key = Column(String(200))
    data = Column(String(500))
    load =  Column(Float)
   
    __table_args__  = ( saschema.UniqueConstraint("unique_key"), {} ) 
    
    def __init__(self, server_type, unique_key, data, load ):
        self.server_type = server_type
        self.unique_key = unique_key
        self.data = data
        self.load = load
        
    def __repr__(self):
        return "<Server (server_type, unique_key, data, load)('%s', '%s', '%s', '%s')>" % \
            (self.server_type, str(self.unique_key), str(self.data), str(self.load))
        
class StickyMapping(Base):
    ''' mapping class for stickypaping table'''
    __tablename__ = 'stickymapping'
    
    mapping_id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey('server.server_id', ondelete='CASCADE'))
    sticky_value = Column(String(200))
    
    __table_args__  = ( saschema.UniqueConstraint("server_id", "sticky_value"), {} ) 
    
    def __init__(self, server_id, sticky_value):
        self.server_id = server_id
        self.sticky_value = sticky_value   
        
    def __repr__(self):
        return "<StickyMapping (server_id, sticky_value)('%s', '%s')>" % \
            (self.server_id, str(self.sticky_value))

    
def create_server(metadata):
    server = schema.Table('server', metadata,
    schema.Column('server_id', types.Integer,
        schema.Sequence('server_seq_id', optional=False), primary_key=True),
    schema.Column('server_type', types.VARCHAR(200), nullable=False),
    schema.Column('unique_key', types.VARCHAR(200), nullable=False),
    schema.Column('data', types.Text, nullable=True),
    schema.Column('load', types.Float, nullable=True )
    )
    server.append_constraint(UniqueConstraint("unique_key"))
    server.create(checkfirst=True)
    
def create_stickymapping(metadata):
    stickymapping = schema.Table('stickymapping', metadata,
    schema.Column('mapping_id', types.Integer,
                    schema.Sequence('stickymapping_seq_id', optional=False), primary_key=True),
    schema.Column('server_id', types.Integer, ForeignKey("server.server_id", ondelete="CASCADE"), onupdate="CASCADE"),
    schema.Column('sticky_value', types.VARCHAR(500), nullable=True)
    )
    
    ForeignKeyConstraint(
                ['server_id'],
                ['server.server_id'],
                use_alter=True,
                name='fk_server_id',
                onupdate="CASCADE",
                ondelete="CASCADE"
            )
    stickymapping.append_constraint(UniqueConstraint("server_id", "sticky_value"))
    stickymapping.create(checkfirst=True)
    
if __name__ == '__main__':
    
    db = MySQLBinding().engine.engine
    db.echo = True
    metadata = schema.MetaData(db)
    
    create_server(metadata)
    create_stickymapping(metadata)