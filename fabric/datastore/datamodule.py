'''
This is base module for writing the data binding for cluster server
We will have either mysql / redis or any other type of persistent type of data binding
'''
from dbengine import DatabaseEngine
from fabric.datastore.dbengine import DBConfig
from sqlalchemy import Column, schema as saschema, schema, types
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.schema import UniqueConstraint, ForeignKey, ForeignKeyConstraint
from sqlalchemy.sql.expression import join, and_, func, outerjoin
from sqlalchemy.types import String, Integer, Float
from sqlalchemy.dialects.mysql.base import LONGTEXT

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