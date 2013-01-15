'''
This is module for writing the data binding for cluster server
We will have either mysql  persistent type of data binding
'''
from fabric.datastore.dbengine import DBConfig
from fabric.endpoints.dbendpoints.db_base import DBConnectionEndPoint
from sqlalchemy import Column, schema as saschema
from sqlalchemy.dialects.mysql.base import LONGTEXT
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import join, relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm.util import aliased
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql.expression import func, and_
from sqlalchemy.types import String, Integer, Float
from threading import RLock
import json
import logging

    
def dbsessionhandler(wrapped_fn):
    '''
    This decorator handles the creation and closing of the session object.
    The parameter sess is passed in by default as the second parameter after self.
    We dont need to pass it explicitly to the method while making call to the decorated
    method.
    '''
    def wrapped(self, *args, **kwargs):
        sess = self.session
        try:
            retval = wrapped_fn(self, sess,  *args, **kwargs)
        finally:
            sess.close()
        return retval
    return wrapped       
    
    
class MySQLBinding(DBConnectionEndPoint):
    
    def get_session(self):
        return self.session
    
    internal_lock  = RLock()
    
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
        sess.flush()
        with self.__class__.internal_lock:
            try:
                server = Server(servertype, server_adress, json.dumps({}), 0)
                sess.add(server)
                sess.commit()
            except IntegrityError:
                #This error will occur when we are in start mode. We will clear server_state by updating it to empty dict
                sess.rollback()
                sess.query(Server).filter(Server.unique_key == server_adress)\
                        .update({Server.load:0, Server.server_type:servertype, Server.server_state:json.dumps({})}, synchronize_session=False)
                sess.commit()
            return server.server_id
        
    
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
    def get_current_load_db(self, sess, server_address):
        '''
        This method returns the current load of the server as it exist in the datastore
        :param server_address:the address of the server which is the unique key
        '''
        try:
            server = sess.query(Server).filter(Server.unique_key == server_address).one()
            return server.load
        except NoResultFound:
            return 0
    
        
    @dbsessionhandler
    def get_target_server(self, sess, stickyvalues, servertype, server_address, endpoint_name, endpoint_key):
        '''
        This method finds the target server who will handle this request based on stickyvalues or minimum load
        Logic: 
        -This method returns the server which handles the stickyvalue if found.
        -If not found , tries to find the minimum loaded server.
        -If current server is the minimum loaded servers, adds the corresponding sticky values instantly
        - At the end returns the dict server as a target server and stickymappings if found already existing stickyness.

        If return dict contains the server and existing_mapping_list ==> already sticked server found
        If existing_mapping_list is empty means this is newly found minimum loaded server (either self or some other server)
        
        :param stickyvalue: the sticky value string.
        :param servertype: the type of the server
        :param server_address: he address of the server which is the unique key
        :param endpoint_key: unique key of the endpoint
        :param endpoint_name: name of the endpoint
        '''
        sess.flush()
#        logging.getLogger().debug("Servertype passed : %s", servertype)
        server = None
        existing_mapping_list = None
        sticky_found = False
        with self.__class__.internal_lock:
            #logging.getLogger().debug("stickyvalues : %s ", stickyvalues)
            if stickyvalues:
                try:
                    existing_mapping_list = sess.query(StickyMapping).filter(StickyMapping.sticky_value.in_(stickyvalues)).all()
                    sticky_found = True
                except Exception as e:
                    logging.getLogger().debug("Exception occurred in the stickymapping query : %s ", e)
            
            if not existing_mapping_list:
                min_loaded_server = None
                #Following query finds the minimum loaded server of the given type, with load less than 100%
                ParentServer = aliased(Server, name='parent_server')
                min_loaded_server = sess.query(Server, ParentServer).\
                            outerjoin(ParentServer, and_(Server.server_type==ParentServer.server_type, ParentServer.load < Server.load)).\
                            filter(and_(Server.server_type==servertype, ParentServer.load==None, Server.load < 100)).first()
                if min_loaded_server:
#                    logging.getLogger().debug("min loaded server found are : %s ", min_loaded_server[0])
                    server = min_loaded_server[0]
                    unique_key = server.unique_key
                    if unique_key == server_address:
                        try:
                            for s in stickyvalues:
                                sticky_record = StickyMapping(server.server_id, endpoint_key, endpoint_name, s)
                                sess.add(sticky_record) 
                            sess.commit()
                        except Exception as e:
                            logging.getLogger().debug("Exception occurred while adding sticky values : %s ", e)
                            sess.rollback()
                else:
                    #TODO  : Indicate System is totally full all extractors are 100%
                    pass #session closing need to be taken care in case raising exception
                    #raise Exception
            else:
                pass
                #logging.getLogger().debug("found existing mapping")
            if server is None:
                server_ids = set([e.server_id for e in existing_mapping_list])
                #The server_ids list above will be at most one server of each type even if sticky values for different type of servers are same
                server = sess.query(Server).filter(and_(Server.server_id.in_(server_ids), Server.server_type==servertype)).one()
            return_dict = {'target_server' : server, 'stickymapping' : existing_mapping_list, 'sticky_found' : sticky_found}
            '''
            If return dict contains the server and existing_mapping_list ==> already sticked server found
            If existing_mapping_list is empty means this is newly found minimum loaded server (either self or some other server)
            '''
#        logging.getLogger().debug("returning the redirect server : %s", return_dict)
        return  return_dict
    
    
    @dbsessionhandler
    def save_stickyvalues(self, sess, server_id, endpoint_key, endpoint_name, stickyvalues):
        '''
        This method adds the list of stickyvalue mapping for the server_address.
        This method is called at the end of request in order to add any new sticky values which needs to be added
        along with the existing list
        :param int server_id: the server id of the current server as in DB
        :param str endpoint_key: unique key of the endpoint
        :param str endpoint_name: name of the endpoint
        :param list stickyvalues: list of new sticky values
        '''
        #we use subtransactions here so that if any query fails with integrity error we can rollback only that and outer transaction continues
        try:
            for stickyvalue in stickyvalues:
                try:
                    sess.begin_nested()
                    sticky_record = StickyMapping(server_id, endpoint_key, endpoint_name, stickyvalue)
                    sess.add(sticky_record)  
                    sess.commit()
                except Exception as e:
                    sess.rollback()
            sess.commit()
        except IntegrityError as e:
            sess.rollback()
            
    @dbsessionhandler
    def save_load_state(self, sess, server_adress, load, server_state):
        '''
        This method saves/update the load and the server state
        :param server_id: the server id of the current server as in DB
        :param load: load percentage for this server
        :param server_state: jsonified server_state . This server_state blob needs to be updated
                             to the existing datablob. This is the datablob that we keep so that
                             server come back up the existing state when some failure occur
        '''
        try:
            if server_state is not None and load is not None:
                #logging.getLogger().warn("server state and load  dal : %f", load)
                sess.query(Server).filter(Server.unique_key == server_adress)\
                        .update({Server.load:load, Server.server_state:server_state}, synchronize_session=False)
            elif load is not None:
                #logging.getLogger().warn("Load value that needs to be updated inside dal : %f", load)
                sess.query(Server).filter(Server.unique_key == server_adress)\
                        .update({Server.load:load}, synchronize_session=False)
            elif server_state is not None:
                sess.query(Server).filter(Server.unique_key == server_adress)\
                        .update({Server.server_state:server_state}, synchronize_session=False)
            sess.commit()
            #logging.getLogger().warn("Commit done inside dal : %f", load)
        except Exception as e:
            #logging.getLogger().warn("Exception occured while writing load to db ")
            sess.rollback()        
        
                
    @dbsessionhandler
    def save_stickyvalue(self, sess, server_id, endpoint_key, endpoint_name, stickyvalue):  
        '''
        Save one stickyvalue
        :param server_id: the server id of the current server as in DB
        :param endpoint_key: unique key of the endpoint
        :param endpoint_name: name of the endpoint
        :param stickyvalues: list of new sticky values
        '''
        try:
            sticky_record = StickyMapping(server_id, endpoint_key, endpoint_name, stickyvalue)
            sess.add(sticky_record)  
            sess.commit()
        except IntegrityError as e:
            sess.rollback()
            
            
    @dbsessionhandler
    def remove_stickyvalues(self, sess, stickyvalues):
        '''
    	This method removes the list of the sticky values for the given server 
    	:param server_adress: the unique server_adress
		:param stickyvalues: list of new sticky values
		:param load: load value that we want to update in datastore for this server
    	'''
        sess.flush()
        logging.getLogger().debug("DB query remove: %s", stickyvalues)
        for s in stickyvalues:
            try:
                sess.begin_nested()
                sess.query(StickyMapping).filter(StickyMapping.sticky_value == s).delete(synchronize_session='fetch')
                sess.commit()
            except Exception as e:
                sess.rollback()
                logging.getLogger().debug("Exception occured while removing the sticky value from the db : %s", e)
        sess.commit()
    
    
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
#            if load:
#                sess.query(Server).filter(Server.unique_key == server_adress).update({Server.load:load}, synchronize_session=False)
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
#TODO : Put the cluste_orm definition in separate file

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