'''
Created on 27-Feb-2013

@author: ashish
'''
from fabric.datastore.cluster_orm import ClusterORM
from functools import wraps
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import join
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm.util import aliased
from sqlalchemy.sql.expression import func, and_
from threading import RLock
import json
import logging
import time
def dbsessionhandler(wrapped_fn):
    '''
    This decorator handles the creation and closing of the session object.
    The parameter sess is passed in by default as the second parameter after self.
    We dont need to pass it explicitly to the method while making call to the decorated
    method.
    '''
    @wraps(wrapped_fn)
    def wrapped(self, *args, **kwargs):
        sess = self.get_session()
        try:
            retval = wrapped_fn(self, sess,  *args, **kwargs)
        finally:
            sess.close()
        return retval
    return wrapped       
    
    
class Retry(object):
    default_exceptions = (OperationalError,)
    def __init__(self, tries , exceptions=None, delay=0.01):
        """
        Decorator for retrying a function if exception occurs
        
        tries -- num tries 
        exceptions -- exceptions to catch
        delay -- wait between retries
        """
        self.tries = tries
        if exceptions is None:
            exceptions = Retry.default_exceptions
        self.exceptions =  exceptions
        self.delay = delay

    def __call__(self, f):
        def fn(*args, **kwargs):
            exception = None
            for _ in range(self.tries):
                try:
                    return f(*args, **kwargs)
                except self.exceptions, e:
                    time.sleep(self.delay)
                    exception = e
            #if no success after tries, raise last exception
            raise exception
        return fn


class ClusterDAL(ClusterORM):
    
    def __init__(self, cluster_db_ep, Base):
        
        self.cluster_db_ep = cluster_db_ep
        super(ClusterDAL, self).__init__(Base)
        
    def get_session(self):
        return self.cluster_db_ep.session
    
    internal_lock  = RLock()
        
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
                server = self.Server(servertype, server_adress, json.dumps({}), 0)
                sess.add(server)
                sess.commit()
            except IntegrityError:
                #This error will occur when we are in start mode. We will clear server_state by updating it to empty dict
                sess.rollback()
                sess.query(self.Server).filter(self.Server.unique_key == server_adress)\
                        .update({self.Server.load:0, self.Server.server_type:servertype, self.Server.server_state:json.dumps({})}, synchronize_session=False)
                sess.commit()
            return server.server_id

    @dbsessionhandler
    def get_server_id(self, sess, server_adress):
#        logging.getLogger().debug("The server address is passed :%s ", server_adress)
        assert server_adress is not None
        server = sess.query(self.Server).filter(self.Server.unique_key == server_adress).one()
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
            server = sess.query(self.Server).filter(self.Server.unique_key == server_adress).one()
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
            
            sess.query(self.Server).filter(self.Server.unique_key == server_adress)\
                    .update({ self.Server.server_state:server_state}, synchronize_session=False)
            sess.commit()


    
    @dbsessionhandler
    def get_current_load_db(self, sess, server_address):
        '''
        This method returns the current load of the server as it exist in the datastore
        :param server_address:the address of the server which is the unique key
        '''
        try:
            server = sess.query(self.Server).filter(self.Server.unique_key == server_address).one()
            return server.load
        except NoResultFound:
            return 0
    
    @Retry(3)
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
                    existing_mapping_list = sess.query(self.StickyMapping).filter(self.StickyMapping.sticky_value.in_(stickyvalues)).all()
                    sticky_found = True
                except Exception as e:
                    logging.getLogger().debug("Exception occurred in the stickymapping query : %s ", e)
            
            if not existing_mapping_list:
                min_loaded_server = None
                #Following query finds the minimum loaded server of the given type, with load less than 100%
                ParentServer = aliased(self.Server, name='parent_server')
                min_loaded_server = sess.query(self.Server, ParentServer).\
                            outerjoin(ParentServer, and_(self.Server.server_type==ParentServer.server_type, ParentServer.load < self.Server.load)).\
                            filter(and_(self.Server.server_type==servertype, ParentServer.load==None, self.Server.load < 100)).all()
                if min_loaded_server:
                    #logging.getLogger().debug("min loaded server found type : %s ", type(min_loaded_server))
                    s = None
                    for m in min_loaded_server:
                        if server_address == m[0].unique_key:
                            s=m[0]
                    server = s if s else min_loaded_server[0][0]
                    unique_key = server.unique_key
                    if unique_key == server_address:
                        try:
                            for s in stickyvalues:
                                sticky_record = self.StickyMapping(server.server_id, endpoint_key, endpoint_name, s)
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
                #logging.getLogger().debug("Already Sticky value found for: %s - servertype: %s. Sticky list is : %s", server_ids, servertype, existing_mapping_list)
                #The server_ids list above will be at most one server of each type even if sticky values for different type of servers are same
                server = sess.query(self.Server).filter(and_(self.Server.server_id.in_(server_ids), self.Server.server_type==servertype)).one()
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
                    sticky_record = self.StickyMapping(server_id, endpoint_key, endpoint_name, stickyvalue)
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
                sess.query(self.Server).filter(self.Server.unique_key == server_adress)\
                        .update({self.Server.load:load, self.Server.server_state:server_state}, synchronize_session=False)
            elif load is not None:
                #logging.getLogger().warn("Load value that needs to be updated inside dal : %f", load)
                sess.query(self.Server).filter(self.Server.unique_key == server_adress)\
                        .update({self.Server.load:load}, synchronize_session=False)
            elif server_state is not None:
                sess.query(self.Server).filter(self.Server.unique_key == server_adress)\
                        .update({self.Server.server_state:server_state}, synchronize_session=False)
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
            sticky_record = self.StickyMapping(server_id, endpoint_key, endpoint_name, stickyvalue)
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
#        logging.getLogger().debug("DB query remove: %s", stickyvalues)
        for s in stickyvalues:
            try:
                sess.begin_nested()
                sess.query(self.StickyMapping).filter(self.StickyMapping.sticky_value == s).delete(synchronize_session='fetch')
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
            sticky_mappings = sess.query(self.StickyMapping).select_from(join(self.Server, self.StickyMapping)).all()
            sess.query(self.StickyMapping).filter(self.StickyMapping.mapping_id.in_([sm.mapping_id for sm in sticky_mappings ]))\
                                .delete(synchronize_session='fetch')
#            if load:
#                sess.query(self.Server).filter(self.Server.unique_key == server_adress).update({self.Server.load:load}, synchronize_session=False)
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
        min_load = sess.query(func.min(self.Server.load)).filter(self.Server.server_type == servertype ).one()
        if(min_load[0] < 100):
            min_loaded_server = sess.query(self.Server).filter(self.Server.load == min_load[0] ).first()
        return min_loaded_server
    
    
    @dbsessionhandler
    def remove_server(self, sess, server_address):
        '''
        This clear the history of the server
        '''
        assert server_address is not None
        try:
            server = sess.query(self.Server).filter(self.Server.unique_key == server_address).one()
            server_id = server.server_id
            sess.query(self.Server).filter(self.Server.server_id == server_id).delete(synchronize_session='fetch')
            sess.commit()
        except Exception:
            sess.rollback()
            
    @dbsessionhandler
    def update_sticky_value(self, sess,  old, new, server_id, endpoint_name, endpoint_key):
        '''
        This will update the sticky value in the db for the correct 
        '''
        try:
            sess.query(self.StickyMapping).filter(self.StickyMapping.sticky_value == old).delete(synchronize_session='fetch')
            sticky_record = self.StickyMapping(server_id, endpoint_key, endpoint_name, new)
            sess.add(sticky_record)
            sess.commit()
        except IntegrityError as e:
            pass
        except Exception as e:
            logging.getLogger().exception("Exception occured while update sticky value : %s ", e)
             
