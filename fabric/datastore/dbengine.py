from sqlalchemy import create_engine, event
from sqlalchemy.interfaces import PoolListener
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

class ForeignKeysListener(PoolListener):
    '''We needed to add this listener to enable the foreign key constraint for sqlite3'''
    
    def __init__(self,dbtype):
        self.dbtype = dbtype
    
    def connect(self, dbapi_con, con_record):
        if self.dbtype ==  'sqlite':
            db_cursor = dbapi_con.execute('pragma foreign_keys=ON')
            
class DBConfig(object):
    '''
    This contains the configurable elements for database
    '''
    
    def __init__(self, dbtype, db_url , pool_size=100, max_overflow=0, connection_timeout=100):
        self.dbtype = dbtype
        self.db_url = db_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.connection_timeout = connection_timeout
        
class _DatabaseEngine :
    '''
    This class contains all the configuration and connection to the database.
    This will contains all the setting like connection pooling etc
    '''
    
    def __init__(self, dbconfig):
        self.engine = None
        self.Session = None  # configured "Session" class
        self.create_engine(dbconfig)
    
    def create_engine(self, dbconfig):
        '''
        This method creates the dbengine and Configured "Session" class
        :param dbconfig :dbconfig object , which cotains all the configuration 
        '''
        dbtype = dbconfig.dbtype
        db_url = dbconfig.db_url
        pool_size = dbconfig.pool_size or 400
        max_overflow = dbconfig.max_overflow or 0
        #connection_timeout = DBConfig.connection_timeout or 3
        if not self.engine and db_url:
            self.engine = create_engine(db_url, poolclass=QueuePool,\
                       pool_size=pool_size, max_overflow=max_overflow, pool_recycle=3600,\
                       isolation_level='SERIALIZABLE', connect_args={ },\
                       listeners=[ForeignKeysListener(dbtype)]) 

            self.Session = sessionmaker(bind=self.engine, expire_on_commit=False) # create a configured "Session" class
            self._scoped_sessions = scoped_session(self.Session) 
   
            #: begin txn listener
            @event.listens_for(self.engine, "begin")
            def do_begin(conn):
                conn.execute("BEGIN")
    

    def get_engine(self ):
        if self.engine:
            return self.engine
        else:
            return self.create_engine()
        

    def get_session(self):
        '''Returns the session object . Assumes engine is already instantiated via create_engine'''
        sess = self.Session()
        sess.expire_on_commit = False
        return sess
    
    def get_scoped_session(self):
        '''
        Return a scoped session object locally for a thread, 
        can be used liberally within the same thread without deadlocks
        '''
        try: 
            return self._scoped_sessions()
        except (TypeError, AttributeError): 
            return None
    
    
class DatabaseEngineFactory(object):
    '''
    This is a factory method to use create the database engine.
    It makes sure only one DabaseEngine is created per db_url.
     
    '''
    # this dict keeps the mapping of the objects created per db_url (unique identofier for DB)
    dbengine_dict = {}
    
    def __new__(self, dbconfig, *args, **kwargs):
        '''
        :param DBConfig dbconfig: the config object , that contains all the configuration parameters for database interaction
        
        '''
        try:
            # dbconfig.db_url is unique key for this object, so we create a dict with this as a key
            database_engine = DatabaseEngineFactory.dbengine_dict[dbconfig.db_url]
        except KeyError:
            database_engine =  _DatabaseEngine(dbconfig, *args, **kwargs)
            DatabaseEngineFactory.dbengine_dict[dbconfig.db_url] = database_engine
        return database_engine
    
    