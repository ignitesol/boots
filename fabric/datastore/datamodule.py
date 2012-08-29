'''
This is base module for writing the data binding for cluster server
We will have either mysql / redis or any other type of persistent type of data binding
'''
from dbengine import DatabaseEngine
from fabric.datastore.dbengine import DBConfig
from sqlalchemy import Column, schema as saschema, schema, types
from sqlalchemy.dialects.mysql.base import LONGTEXT
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.schema import UniqueConstraint, ForeignKey, ForeignKeyConstraint
from sqlalchemy.sql.expression import join, and_, func, outerjoin
from sqlalchemy.types import String, Integer, Float

class BaseDataBinding(object)  :
    
    def __init__(self, **kwargs):
        pass
    
    
    def setdata(self, server_adress, servertype):
        pass
    
    
    def getdata(self, server_adress):
        pass
    
    def update_server(self, server_adress, stickyvalue, load, data=None):
        pass
    
    def update_stickyvalue(self, server_adress, stickyvalue):
        pass
    
    
    def get_server_by_stickyvalue(self, stickyvalue):
        pass
    
    def get_least_loaded(self, servertype):
        pass
    
    
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
    
    
class StickyMappingWrapperObject(object):
    '''
    This class is used to create and update the sticky relations per sticky keys 
    This loads the sticky keys values that exist and then update the new sticky key values those are 
    updated. These are then updated in db if the dirty flag is set(there has been change in the
    sticky mapping)
    '''    
    
    def __init__(self, datastore, autosave=True, stickymappinglist=[]):
        
        print "StickyMappingWrapperObject : datstore engine ", datastore.engine
        
        self.datastore = datastore
        self.stickymappinglist = stickymappinglist

        self._dirty = False
        self._load = None
        self._data = None
        self._server_address = None
        self._endpoint_key = None
        self._endpoint_name = None
        
        self._autosave = autosave
        
    
    @property
    def dirty(self):
        return self._dirty
    
    @dirty.setter
    def dirty(self, value):
        self._dirty = value
    
    
    @property
    def data(self):
        return self._data
    
    @data.setter
    def data(self, value):
        self._data = value
    
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
    
    def get_session(self):
        '''
        This method get the session object for transaction start for this method
        '''
        self.datastore.get_session()
        
    def save(self):
        '''
        This method saves to datastore if _dirty flag is true and autosave is true.
        This method will be always called if  
        '''
        print "Autosave flag : " , self._autosave 
        print "dirty flag : " , self._dirty
        
        if self._autosave and self._dirty:
            self.datastore.\
                save_updated_data(self.server_address, self.data , self.load, self.endpoint_key, self.endpoint_name, self.stickymappinglist)

    
    def read_by_stickyvalue(self, stickyvalues):
        '''
        This method gets the server with the stickyvalue. The stickyvalue makes sure this request is handled
        by the correct server. 
        :param list stickyvalues: stickyvalues which is handled by this server
        :param str endpoint_key: uuid of the endpoint
        
        :rtype: returns the unique id or the server which is the sever address with port
        '''
        if stickyvalues is None:
            raise Exception("Sticky values passed cannot be empty or None")
        server =  self.datastore.get_server_by_stickyvalue(stickyvalues, self.endpoint_key)
        if server is None:
            raise Exception("No server is found sticked to this")
        self.server_address = server.unique_key
    
    def update(self, stickyvalues=[], load=None, datablob=None):
        '''
        This method update the wrapped mapping
        :param list stickyvalues: this is the list of stickyvalues
        :param float load: this is the new/current load for this server
        :param datablob: this is the blob that needs to be updated for recovery
        '''
        print "self.stickymappinglist ", self.stickymappinglist
        print  "stickyvalues ", stickyvalues 
        if stickyvalues is not None:
            for stickyvalue in stickyvalues:
                if stickyvalue not in self.stickymappinglist:
                    self.stickymappinglist += [stickyvalue]
                    self.dirty = True
        
        print "load " , self.load
        if load is not None:
            self.load = load
            self.dirty = True
        
        if datablob is not None:
            #TODO : this needs to be updated rather than 
            self.data = datablob
            self.dirty = True
            

    def add_sticky_value(self, stickyvalues):
        '''
        This will add the new sticky value to the existing list of params 
        :param stickyvalues: newly formed sticky values
        '''
        if stickyvalues:
            self._dirty = True
            self._stickymappinglist += [stickyvalues] if type(stickyvalues) is str else stickyvalues
        
        
    
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
            server = Server(servertype, server_adress, '', 0)
            self.sess.add(server)
            self.sess.commit()
        except IntegrityError as e:
            #Based on the type of mode : Start/Restart we might want to clear or update data
            self.sess.rollback()
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:0, Server.server_type:servertype}, synchronize_session=False)
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
        #un jsonify
        return server.data
    
    @dbsessionhandler
    def update_server(self, server_adress, endpoint_key, endpoint_name, stickyvalues, load, data=None):
        '''
        This method adds the stickyvalue mapping and the load for the server_address
        :param server_adress: the unique server_adress
        :param endpoint_key: unique key of the endpoint
        :param endpoint_name: name of the endpoint
        :param stickyvalues: list of new sticky values
        :param load: load percentage for this server
        '''
        #Complete transactional update
        if data:
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load, Server.data:data}, synchronize_session=False)
        else:
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load}, synchronize_session=False)
                    
        server = self.sess.query(Server).filter(Server.unique_key == server_adress).one()
        try:
            for stickyvalue in stickyvalues:
                self.sess.add(StickyMapping(server.server_id, endpoint_key, endpoint_name, stickyvalue))    
            self.sess.commit()  
        except IntegrityError:
            #Sticky mapping already exist. This condition should only if server is started and data was not cleared
            self.sess.rollback()
    
        
    @dbsessionhandler
    def get_server_by_stickyvalue(self, stickyvalues, endpoint_key):
        '''
        This method server which handles the stickyvalue passes
        :param stickyvalue: 
        '''
        # Server.server_id == StickyMapping.server_id
        stickymapping = None
        for stickyvalue in stickyvalues:
            try:
                stickymapping = self.sess.query(StickyMapping).filter(and_(StickyMapping.sticky_value == stickyvalue, \
                                                                           True)).one()
                break # we break when first one is found
            except NoResultFound:
                pass
        if stickymapping is None:
            return None
        #TODO : Join was screwing up for some reason so , dirty code . Must  fix
        server = self.sess.query(Server).filter(Server.server_id == stickymapping.server_id).one()
        
        #Now add all the other stickymapping ( to make sure secondary keys also exist)
        return server
    
    
    @dbsessionhandler
    def save_updated_data(self, server_adress, data , load, endpoint_key, endpoint_name, stickyvalues):
        '''
        '''
        #Complete transactional update
        if data:
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load, Server.data:data}, synchronize_session=False)
        else:
            self.sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load}, synchronize_session=False)
                    
        server = self.sess.query(Server).filter(Server.unique_key == server_adress).one()
        try:
            for stickyvalue in stickyvalues:
                self.sess.add(StickyMapping(server.server_id, endpoint_key, endpoint_name, stickyvalue))    
            self.sess.flush()  
        except IntegrityError:
            self.sess.rollback()
            #mapping already exists
            pass
        
        self.sess.commit()
        

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
    data = Column(LONGTEXT)
    load =  Column(Float)
    
    stickymapings = relationship("StickyMapping",
                collection_class=attribute_mapped_collection('sticky_mapping_key'),
                backref="server",
                cascade="all, delete-orphan")
   
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
    endpoint_key = Column(String(100))
    endpoint_name = Column(String(100))
    sticky_value = Column(String(500))
    
    __table_args__  = ( saschema.UniqueConstraint("server_id", "endpoint_key", "sticky_value", ), {} ) 
    
    @property
    def sticky_mapping_key(self):
        return (self.endpoint_key, self.sticky_value)
    
    def __init__(self, server_id, endpoint_key, endpoint_name, sticky_value):
        self.server_id = server_id
        self.endpoint_key = endpoint_key
        self.endpoint_name = endpoint_name
        self.sticky_value = sticky_value   
        
    def __repr__(self):
        return "<StickyMapping (server_id, endpoint_key, endpoint_name, sticky_value)('%s', '%s', '%s', '%s')>" % \
            (self.server_id, str(self.endpoint_key), str(self.endpoint_name), str(self.sticky_value))

    
def create_server(metadata):
    server = schema.Table('server', metadata,
    schema.Column('server_id', types.Integer,
        schema.Sequence('server_seq_id', optional=False), primary_key=True),
    schema.Column('server_type', types.VARCHAR(200), nullable=False),
    schema.Column('unique_key', types.VARCHAR(200), nullable=False),
    schema.Column('data', LONGTEXT , nullable=True),
    schema.Column('load', types.Float, nullable=True ), 
    mysql_engine='InnoDB'
    )
    server.append_constraint(UniqueConstraint("unique_key"))
    server.create(checkfirst=True)
    
def create_stickymapping(metadata):
    stickymapping = schema.Table('stickymapping', metadata,
    schema.Column('mapping_id', types.Integer,
                    schema.Sequence('stickymapping_seq_id', optional=False), primary_key=True),
    schema.Column('server_id', types.Integer, ForeignKey("server.server_id", ondelete="CASCADE"), onupdate="CASCADE"),
    schema.Column('endpoint_key', types.VARCHAR(100), nullable=True),
    schema.Column('endpoint_name', types.VARCHAR(100), nullable=True),
    schema.Column('sticky_value', types.VARCHAR(500), nullable=True),
    mysql_engine='InnoDB'
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