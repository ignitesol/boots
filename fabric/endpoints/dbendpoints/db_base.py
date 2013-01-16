'''
Created on 16-Nov-2012

@author: rishi
'''
from fabric.datastore.dbengine import DatabaseEngineFactory, DBConfig
from fabric.endpoints.endpoint import EndPoint
from sqlalchemy.ext.declarative import declarative_base
from inspect import getargspec
import logging

class DBConnectionEndPoint(EndPoint):
    '''
    An SQLAlchemy specific database Endpoint
    Current functionality is limited to Engine and session management
    '''
    def __init__(self, dbtype=None, db_url=None, dbconfig=None, **kargs):
        '''
        Constructor
        
        :param dbtype=None: A String denoting the type (usually MYSQL)
        :param db_url=None: A String providing the connection string for the database (eg. mysql://user:passwd@domain:port
        :param dbconfig=None: In case a custom :class:`DBConfig` needs to be loaded, the `dburl` and `dbconfig` may be ignored
        :param **kargs: Extra arguments either for the :class:`Endpoint` base class or :class:`DBConfig` to be created 
        '''
        dbargs = {}
        argspec = getargspec(DBConfig.__init__)
        for key in argspec.args[len(argspec.args) - len(argspec.defaults):]: 
            if kargs.get(key): dbargs[key] = kargs[key]
            
        self._dbconfig = DBConfig(dbtype, db_url, **dbargs) if not dbconfig else dbconfig
        self._engine = DatabaseEngineFactory(self._dbconfig)
        self._schema_base = declarative_base(bind=self._engine.engine)
        self._controlled_session = ControlledSession(self)
        
#        class BaseWrapper(_base):
#            __tablename__ = ""
#            
#            def __repr__(self):
#                return "<(%s)"%self.__tablename__ + " ".join([ "%s:%s"%(k, getattr(self, k)) for k in self.__table__.c.keys() ]) + ">"
        
        # Overwriting default __repr__ with setattr
        # since we cannot easily create a shell inheritance
        # due to the declarative base's strict metaclass
        def rep(s):
            return "<(%s)"%s.__tablename__ + " ".join([ "%s:%.200s"%(k, getattr(s, k)) for k in s.__table__.c.keys() ]) + ">"
        
        setattr(self._schema_base, '__repr__', rep)
        super(DBConnectionEndPoint, self).__init__(**kargs)
#    
    @property
    def Base(self):
        '''
        The declarative base class to be used for defining an ORM 
        based on this DBEngine connection
        '''
        return self._schema_base
    
    @property
    def session(self):
        '''
        Gets a scoped session for the currently running thread
        to communicate with the database
        '''
        return self._engine.get_scoped_session()
    
    @property
    def stint(self):
        '''
        Returns the ControlledSession to be used by the python 'with' statement
        **UNTESTED**
        '''
        return self._controlled_session
    
    @property
    def dbengine(self):
        return self._engine.engine
    
    def execute(self, expr):
        return self.engine.execute(expr)
    
    def addressing(self):
        return self._dbconfig.db_url
    
    def create_tables(self, clean=False):
        try:
            self.Base.metadata.create_all(checkfirst=(not clean))
        except:
            if clean:
                self.Base.metadata.drop_all(checkfirst=True)
                self.Base.metadata.create_all()
    
    def insession(self, commit=False):
        '''
        Decorator for creating and passing sessions into decorated methods
        :param commit=False: Whether or not to commit the session after method invocation
        '''
        def decorator(fn):
            def wrapper(*args, **kargs):
                session=self.session
                kargs['session'] = session
                ret = fn(*args, **kargs)
                if commit:
                    session.commit()
                return ret
                    
            return wrapper
        return decorator
        

class ControlledSession(object):
    '''
    A session meant to be used by the 'with' operator
    Must be a scoped session, else it is not thread safe
    '''
    def __init__(self, dbep):
        self.dbep = dbep
    
    def __enter__(self):
        return self.dbep.session
    
    def __exit__(self, etype, value, traceback):
        self.dbep.session.close()