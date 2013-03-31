'''
Created on 19-Nov-2012

@author: ashish
'''
from fabric.endpoints.endpoint import EndPoint
from mongoalchemy import session
from pymongo.connection import Connection
from pymongo.database import Database
from pymongo.mongo_client import MongoClient


class LibType:
    mongoalchemy = 'MongoAlchemy'
    pymongo = "PyMongo"

class MongoConfig(object):
    '''
    This contains  all the configuration parameters required for mongo database
    '''
    
    def __init__(self, host , port, db_name, username , password, pool_size, *args, **kwargs):
        self._host = host
        self._username = username
        self._password = password
        self._db_name = db_name
        self.port = port
        self.pool_size = pool_size
        self.connection_string = 'mongodb://' + self._username + ':' + self._password + '@' + self._host + '/' + db_name

class _MongoConnectionFactory(object):
    '''
    This class is a factory of connection pooling for mongodb connections.
    connection pool created per mongodb connection-string which is one pool per mongodb server
    '''
    # this dict keeps the mapping of the connection pool created per mongodb connection-string which is one pool per mongodb server
    connection_pool = {}
    
    def __new__(self, mongoconfig, *args, **kwargs):
        '''
        :param MongoConfig mongoconfig: the config object , that contains all the configuration parameters for database interaction
        '''
        try:
            # dbconfig.db_url is unique key for this object, so we create a dict with this as a key
            connection = _MongoConnectionFactory.connection_pool[mongoconfig.connection_string]
        except KeyError:
            connection =  Connection(host=mongoconfig.connection_string, port=int(mongoconfig.port), max_pool_size=int(mongoconfig.pool_size), network_timeout=None, document_class=dict, tz_aware=False, _connect=True, **kwargs)
            _MongoConnectionFactory.connection_pool[mongoconfig.connection_string] = connection
        return connection
    
    
class _PyMongoConnectionFactory(object):  
    '''
    This class is a factory of connection pooling of pymongo connection
    connection pooling is here per mongodb host and mongodb port
    '''  
    # this dict keeps the mapping of the connection pool created per mongodb connection
    connection_pool = {}
    
    def __new__(self, mongoconfig, *args, **kwargs):
        '''
        PyMongoFactory connection pool 
        '''
        try:
            connection = _PyMongoConnectionFactory.connection_pool[mongoconfig.connection_string]
        except KeyError:
            connection = MongoClient(mongoconfig.connection_string, mongoconfig.port, mongoconfig.pool_size)
        return connection
    
    

class MongoEndPoint(EndPoint):
    '''
    This is the fabric wrapper over the mongoalchemy's session start , end
    It create connection pool to the mongo database with the given user configurations
    
    LibType : Defines the whether we use PyMongo or MongoAlchemy. 
    Its application's responsibility to to be able to use the respective library appropriately. Depneding on 
    whether it is using PyMongo or MongoAlchemy
    '''
    def __init__(self, mongoconfig, libtype=LibType.mongoalchemy, **kwargs):
        self.libtype = libtype
        if libtype is LibType.pymongo:
            self._connection = _PyMongoConnectionFactory(mongoconfig)
            self._db = mongoconfig._db_name
        else:
            #Defaulting to MongoAlchemy
            self._connection = _MongoConnectionFactory(mongoconfig)
            self._db = Database(self._connection, mongoconfig._db_name)
        super(MongoEndPoint, self).__init__(**kwargs)
    
    @property
    def session(self):
        '''
        Get the mongoalchemy session
        '''
        return self.get_session()
    
    def get_session(self):
        if self.libtype is LibType.pymongo:
            sess = self._connection[self._db]
        else:
            sess = session.Session(self._db, safe=True)
        return sess
    
