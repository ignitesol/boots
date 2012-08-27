from sqlalchemy import create_engine, event
from sqlalchemy.interfaces import PoolListener
from sqlalchemy.orm import sessionmaker
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
    
    def __init__(self,\
                  dbtype='mysql', db_url="mysql://cluster:cluster@localhost:3306/cluster" , \
                  pool_size=100, max_overflow=0, connection_timeout=100):
        self.dbtype = dbtype
        self.db_url = db_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.connection_timeout = connection_timeout
        
            
class DatabaseEngine :
    '''
    This class contains all the configuration and connection to the database.
    This will contains all the setting like connection pooling etc
    '''
    engine = None
    Session = None # create a configured "Session" class
    
    def __init__(self, dbconfig):
        self.create_engine(dbconfig)
    
    def create_engine(self, dbconfig):
        '''
        This method creates the dbengine and Configured "Session" class
        @param dbconfig :dbconfig object , which cotains all the configuration 
        @type dbconfig : DBConfig  
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