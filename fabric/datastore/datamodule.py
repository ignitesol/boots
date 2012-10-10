'''
This is base module for writing the data binding for cluster server
We will have either mysql / redis or any other type of persistent type of data binding
'''
from fabric.datastore.dbengine import DBConfig, DatabaseEngineFactory
from sqlalchemy import Column, schema as saschema
from sqlalchemy.dialects.mysql.base import LONGTEXT
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.schema import  ForeignKey
from sqlalchemy.sql.expression import and_, func, join
from sqlalchemy.types import String, Integer, Float
import json

class BaseDataBinding(object)  :
	
    '''
	These are the methods that any data store should define and do the exact logic
	in-order to be able to be used 
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
    
    
def dbsessionhandler(wrapped_fn):
    '''
    This decorator handles the creation and closing of the session object.
    The parameter sess is passed in by default as the second parameter after self.
    We dont need to pass it explicitly to the method while making call to the decorated
    method.
    '''
    def wrapped(self, *args, **kwargs):
        sess = self.get_session()
        retval = wrapped_fn(self, sess,  *args, **kwargs)
        sess.close()
        return retval
    return wrapped       
    
    
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
                save_updated_data(self.server_address, self.endpoint_key, self.endpoint_name, self.stickymappinglist, self.load, self.server_state)

    
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
            
    
    def _update(self, stickyvalues=[], load=None, datablob=None):
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
        #Load is update to new sent 
        if load is not None:
            self.load = load
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
            
    
class MySQLBinding(BaseDataBinding):
    
    def get_session(self):
        return self.engine.get_session()
    
    def __init__(self, dbconfig=None):
        super(MySQLBinding, self).__init__()
        if not dbconfig:
        	#Read from ini files
            dbtype = "mysql"
            db_url = "mysql://cluster:cluster@localhost:3306/cluster"
            pool_size = 100
            max_overflow = 0
            connection_timeout = 30
            dbconfig = DBConfig(dbtype, db_url, pool_size, max_overflow, connection_timeout)
            #raise Exception("Mysql not configured properly . Config parameters from the mysql are not provided in ini")
        self.engine = DatabaseEngineFactory(dbconfig)
    
        
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
        except IntegrityError as e:
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
            existing_mapping_list = sess.query(StickyMapping).filter(and_(StickyMapping.sticky_value.in_(stickyvalues), \
                                                                       True)).all()
        except Exception:
            pass
        if not existing_mapping_list:
            return None
        #TODO : Join was screwing up for some reason so , dirty code . Must  fix
        server = sess.query(Server).filter(Server.server_id == existing_mapping_list[0].server_id).one()
        return  (server, existing_mapping_list)
    
    
    @dbsessionhandler
    def save_updated_data(self, sess, server_adress, endpoint_key, endpoint_name, stickyvalues, load, server_state):
        '''
        This method adds the stickyvalue mapping and the load for the server_address
        :param server_adress: the unique server_adress
        :param endpoint_key: unique key of the endpoint
        :param endpoint_name: name of the endpoint
        :param stickyvalues: list of new sticky values
        :param load: load percentage for this server
        :param server_state: jsonified server_state . This server_state blob needs to be updated to the existing datablob. This is the datablob that we keep so that
                    server come back up the existing state when some failure occur
        '''
        #Two sub transactions .
        #first transaction updates the load and server_state
        #other transaction is set of multiple individual db transactions that tries to add the sticky-key ONE-by-ONE if NOT already exist
        server = sess.query(Server).filter(Server.unique_key == server_adress).one()
        if server_state:
            sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load, Server.server_state:server_state}, synchronize_session=False)
        else:
            sess.query(Server).filter(Server.unique_key == server_adress)\
                    .update({Server.load:load}, synchronize_session=False)
        sess.commit()
        for stickyvalue in stickyvalues:
            self._add_sticky_record(server.server_id, endpoint_key, endpoint_name, stickyvalue)
    
    @dbsessionhandler
    def _add_sticky_record(self, sess, server_id, endpoint_key, endpoint_name, stickyvalue):
        try:
            sticky_record = StickyMapping(server_id, endpoint_key, endpoint_name, stickyvalue)
            sess.add(sticky_record)  
            sess.commit()
        except IntegrityError as e:
            pass
            #print "Sticky mapping already exist with another server"
            
            
    @dbsessionhandler
    def remove_stickykeys(self, sess, server_adress, stickyvalues, load = None):

        try:
            sess.query(StickyMapping).select_from(join(Server, StickyMapping).onclause(Server.server_id == StickyMapping.server_id)).filter(Server.unique_key == 'aurora.ignitelabs.local:4000', StickyMapping.sticky_value == 'abcd:localhost:123').all() #.delete(synchronize_session='fetch')
            if load:
                sess.query(Server).filter(Server.unique_key == server_adress).update({Server.load:load}, synchronize_session=False)
            sess.commit()
        except Exception as e:
            print "Exception occured ", e
    
    
    @dbsessionhandler
    def remove_all_stickykeys(self, sess, server_adress, load = None):
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
    
    __table_args__  = ( saschema.UniqueConstraint("server_id", "endpoint_name", "sticky_value", ), {} ) 

    
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
        print 'Cluster: Dropping Tables and Re-Creating'
        Base.metadata.drop_all(checkfirst=True)
        Base.metadata.create_all(checkfirst=True)