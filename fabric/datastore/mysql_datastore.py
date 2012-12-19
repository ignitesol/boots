'''
This is module for writing the data binding for cluster server
We will have either mysql  persistent type of data binding
'''
from fabric.datastore.dbengine import DBConfig
from sqlalchemy import Column, schema as saschema
from sqlalchemy.dialects.mysql.base import LONGTEXT
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import join, relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql.expression import func
from sqlalchemy.types import String, Integer, Float
import json
from fabric.endpoints.dbendpoints.db_base import DBConnectionEndPoint

    
def dbsessionhandler(wrapped_fn):
    '''
    This decorator handles the creation and closing of the session object.
    The parameter sess is passed in by default as the second parameter after self.
    We dont need to pass it explicitly to the method while making call to the decorated
    method.
    '''
    def wrapped(self, *args, **kwargs):
        sess = self.session
        retval = wrapped_fn(self, sess,  *args, **kwargs)
        sess.close()
        return retval
    return wrapped       
    
    
class MySQLBinding(DBConnectionEndPoint):
    
    def get_session(self):
        return self.session
    
    def __init__(self, dbconfig=None):
        if not dbconfig:
            #Read from ini files
            dbtype = "mysql"
            db_url = "mysql://cluster:cluster@localhost:3306/cluster"
            pool_size = 100
            max_overflow = 0
            connection_timeout = 30
            dbconfig = DBConfig(dbtype, db_url, pool_size, max_overflow, connection_timeout)
            #raise Exception("Mysql not configured properly . Config parameters from the mysql are not provided in ini")
        super(MySQLBinding, self).__init__(dbconfig=dbconfig)
        self.engine = self._engine
    
        
    @dbsessionhandler
    def createdata(self, sess, server_adress, servertype):
        '''
        This creates the entry for each server in the server table.
        We will come at this method only in-case of start mode. 
        Restarts should never reach here
        :param server_adress: address of the self/server itself, this will be unique entry 
        :param servertype: type of the server 
        '''
        try:
            server = Server(servertype, server_adress, '', 0)
            sess.add(server)
            sess.commit()
        except IntegrityError:
            #This error will occur when we are in start mode. We will clear server_state by updating it to empty dict
            sess.rollback()
            sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:0, Server.server_type:servertype, Server.server_state:json.dumps({})}, synchronize_session=False)
            sess.commit()
        
    
    @dbsessionhandler
    def get_server_state(self, sess, server_adress):
        '''
        This method get the data for the given server based on its server_address , which is the unique key per server
        :param server_adress: server address 
        :returns the jsoned value of the current server state in the blob
        '''
        state = '{}'
        try:
            server = sess.query(Server).filter(Server.unique_key == server_adress).one()
            state = server.server_state
            state = state or '{}'
        except NoResultFound:
            pass
        except MultipleResultsFound:
            pass
        return json.loads(state)
    
    @dbsessionhandler
    def set_server_state(self, sess, server_adress, server_state):
        '''
        This method set the server state for the given server based on its server_address , which is the unique key per server
        :param server_adress: server address 
        :param server_state : dict containing the server state at the moment.
        '''
        if type(server_state) is dict:
            server_state = json.dumps(server_state)
            
            sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({ Server.server_state:server_state}, synchronize_session=False)
            sess.commit()

    
    @dbsessionhandler
    def get_current_load(self, sess, server_address):
        '''
        This method returns the current load of the server as it exist in the datastore
        :param server_address:the address of the server which is the unique key
        '''
        try:
            server = sess.query(Server).filter(Server.unique_key == server_address).one()
            return server.load
        except NoResultFound:
            pass
    
        
    @dbsessionhandler
    def get_server_by_stickyvalue(self, sess, stickyvalues, endpoint_key):
        '''
        This method returns the server which handles the stickyvalue and 
        :param stickyvalue: the sticky value string.
        :param endpoint_key: unique value of the endpoint key
        '''
        if not stickyvalues:
            return None
        try:
            existing_mapping_list = sess.query(StickyMapping).filter(StickyMapping.sticky_value.in_(stickyvalues)).all()
        except Exception:
            pass
        if not existing_mapping_list:
            return None
        #TODO : Join was screwing up for some reason so , dirty code . Must  fix
        server = sess.query(Server).filter(Server.server_id == existing_mapping_list[0].server_id).one()
        return  (server, existing_mapping_list)
    
    
    @dbsessionhandler
    def save_updated_data(self, sess, server_adress, endpoint_key, endpoint_name, stickyvalues):
        '''
        This method adds the stickyvalue mapping for the server_address
        :param server_adress: the unique server_adress
        :param endpoint_key: unique key of the endpoint
        :param endpoint_name: name of the endpoint
        :param stickyvalues: list of new sticky values
        '''
        #other transaction is set of multiple individual db transactions that tries to add the sticky-key ONE-by-ONE if NOT already exist
        try:
            server = sess.query(Server).filter(Server.unique_key == server_adress).one()
            for stickyvalue in stickyvalues:
                try:
                    sticky_record = StickyMapping(server.server_id, endpoint_key, endpoint_name, stickyvalue)
                    sess.add(sticky_record)  
                    sess.flush()
                except Exception as e:
                    sess.rollback()
                #self._add_sticky_record(server.server_id, endpoint_key, endpoint_name, stickyvalue)
            sess.commit()
        except IntegrityError as e:
            sess.rollback()
            
    @dbsessionhandler
    def save_load_state(self, sess, server_adress, load, server_state):
        '''
        This method saves/update the load and the server state
        :param load: load percentage for this server
        :param server_state: jsonified server_state . This server_state blob needs to be updated
                             to the existing datablob. This is the datablob that we keep so that
                             server come back up the existing state when some failure occur
        '''
        try:
            if server_state:
                sess.query(Server).filter(Server.unique_key == server_adress)\
                        .update({Server.load:load, Server.server_state:server_state}, synchronize_session=False)
            else:
                sess.query(Server).filter(Server.unique_key == server_adress)\
                        .update({Server.load:load}, synchronize_session=False)
            sess.commit()
        except IntegrityError as e:
            sess.rollback()        
        
                
    @dbsessionhandler
    def save_stickyvalue(self, sess, server_adress, endpoint_key, endpoint_name, stickyvalue):  
        '''
        Save one stickyvalue
        '''
        try:
            server = sess.query(Server).filter(Server.unique_key == server_adress).one()
            sticky_record = StickyMapping(server.server_id, endpoint_key, endpoint_name, stickyvalue)
            sess.add(sticky_record)  
            sess.commit()
            #print "save sticky value : %s"%datetime.datetime.now()
        except IntegrityError as e:
            sess.rollback()
            
        
        
        
    @dbsessionhandler
    def _add_sticky_record(self, sess, server_id, endpoint_key, endpoint_name, stickyvalue):
        '''
    	This methods add the single sticky record in the database.
    	:param server_id: the unique server id
		:param endpoint_key: unique key of the endpoint
		:param endpoint_name: name of the endpoint
		:param stickyvalue: new sticky value, that we are trying to add
    	'''
        try:
            sticky_record = StickyMapping(server_id, endpoint_key, endpoint_name, stickyvalue)
            sess.add(sticky_record)  
            sess.commit()
        except IntegrityError:
            pass
            #print "Sticky mapping already exist with another server"
            
            
    @dbsessionhandler
    def remove_stickykeys(self, sess, server_adress, stickyvalues, load = None):
        '''
    	This method removes the list of the sticky keys for the given server 
    	:param server_adress: the unique server_adress
		:param stickyvalues: list of new sticky values
		:param load: load value that we want to update in datastore for this server
    	'''

        try:
            sticky_mappings = sess.query(StickyMapping).select_from(join(Server, StickyMapping))\
            					.filter(Server.unique_key == server_adress, StickyMapping.sticky_value.in_(stickyvalues)).all()
            if sticky_mappings:
                sess.query(StickyMapping).filter(StickyMapping.mapping_id.in_([sm.mapping_id for sm in sticky_mappings ]))\
                					.delete(synchronize_session='fetch')
            
            if load:
                sess.query(Server).filter(Server.unique_key == server_adress).update({Server.load:load}, synchronize_session=False)
            sess.commit()
        except Exception:
            pass
    
    
    @dbsessionhandler
    def remove_all_stickykeys(self, sess, server_adress, load = None):
        '''
    	This method removes all the sticky keys for this server and optionally update the load for this server
    	:param server_adress: the unique server_adress
		:param load: load value that we want to update in datastore for this server
    	'''
        try:
            sticky_mappings = sess.query(StickyMapping).select_from(join(Server, StickyMapping)).all()
            sess.query(StickyMapping).filter(StickyMapping.mapping_id.in_([sm.mapping_id for sm in sticky_mappings ]))\
            					.delete(synchronize_session='fetch')
            if load:
                sess.query(Server).filter(Server.unique_key == server_adress).update({Server.load:load}, synchronize_session=False)
            sess.commit()
        except Exception:
            pass
        

    @dbsessionhandler
    def get_least_loaded(self, sess, servertype):
        '''
        This method finds the least loaded server of the given type
        :param servertype: the server type for which we want to find the least loaded server. 
        '''
        min_loaded_server = None
        min_load = sess.query(func.min(Server.load)).filter(Server.server_type == servertype ).one()
        if(min_load[0] < 100):
            min_loaded_server = sess.query(Server).filter(Server.load == min_load[0] ).first()
        return min_loaded_server
    
    
    
# Following defined ORM mapping with the relational database

#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

Base = declarative_base(bind = MySQLBinding().engine.engine)


class Server(Base):
    ''' mapping class for server table'''
    __tablename__ = 'server'
    server_id = Column(Integer, primary_key=True)
    server_type = Column(String(200))
    unique_key = Column(String(200))
    server_state = Column(LONGTEXT)
    load =  Column(Float)
    
    __table_args__  = ( saschema.UniqueConstraint("unique_key"), {} ) 
    stickymapping = relationship("StickyMapping",
                cascade="all, delete-orphan",
                passive_deletes=True,
                backref="server"
                )
    
    def __init__(self, server_type, unique_key, server_state, load ):
        self.server_type = server_type
        self.unique_key = unique_key
        self.server_state = server_state
        self.load = load
        
    def __repr__(self):
        return "<Server (server_type, unique_key, server_state, load)('%s', '%s', '%s', '%s')>" % \
            (self.server_type, str(self.unique_key), str(self.server_state), str(self.load))
        
class StickyMapping(Base):
    ''' mapping class for stickypping table'''
    __tablename__ = 'stickymapping'
    
    mapping_id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey('server.server_id', ondelete='CASCADE'))
    endpoint_key = Column(String(100))
    endpoint_name = Column(String(100))
    sticky_value = Column(String(500))
    

    __table_args__  = ( saschema.UniqueConstraint("server_id", "sticky_value" ),
                        saschema.UniqueConstraint("endpoint_name", "sticky_value" ), {} ) 

    
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

   
if __name__ == '__main__':
    try:
        Base.metadata.create_all(checkfirst=False)
    except OperationalError:
        Base.metadata.drop_all(checkfirst=True)
        Base.metadata.create_all(checkfirst=True)