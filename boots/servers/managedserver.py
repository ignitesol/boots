'''
ManagedServer provides an abstraction for managing a servers configuration, performance and health
'''
from __future__ import division
from boots import concurrency
from boots.datastore.cluster_db_endpoint import ClusterDatabaseEndPoint
from boots.datastore.dbengine import DBConfig
import argparse
if concurrency == 'gevent':
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock

from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, Hook, Tracer, template    
from boots.servers.httpserver import HTTPServer
from boots.endpoints.cluster_ep import ManagedPlugin
from sqlalchemy.orm.exc import NoResultFound
import logging
import json
import time

# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())

def admin_auth(user, password):
    print "user:",user, "password:",password
    if user == "incharge" and password == "1gniter0cks":
        return True
    return False

class Stats(Hook):
    
    def create_request_context(self, **kargs):
        return super(Stats, self).create_request_context(**kargs), time.time()
    
    def handler(self, before_or_after, request_context, callback, url, result=None, exception=None, **kargs):
        if before_or_after == 'after':
            callback_obj = getattr(callback, '_callback_obj', None) or getattr(callback, 'im_self', None)
            server = getattr(callback_obj, 'server', None)
            if server and getattr(server, 'stats_collector', None):
                _, start_time = request_context
                end_time = time.time()
                server.stats_collector(callback.__name__, url, end_time - start_time, start_time, end_time, **kargs)
        return result

class ManagedEP(HTTPServerEndPoint):
    '''
    ManagedEP provides the endpoint for managed server to offer configuration, health and statistics monitoring
    Typically mounted on the servers '/admin' mountppoint
    '''
    def __init__(self, name=None, mountpoint='/admin', plugins=None, server=None, activate=False):
        super(ManagedEP, self).__init__(name=name, mountpoint=mountpoint, plugins=plugins, server=server, activate=activate)
        
    
    @template('adminui')
    @methodroute(path="/", skip_by_type=[Stats, Tracer])
#    @bottle.auth_basic(check=admin_auth, realm="admin", text="Admin interface access denied")    #Not working!!
    def admin(self):
        '''
        Returns the admin UI and the list of tabs that the UI has to load.
        '''
        tabs = self.server.config.keys()
        tabs.remove("_proj_dir")
        prefix = self.request.environ.get('REQUEST_URI',"")
        if tabs:
            prefix = prefix.split('/admin')[0].replace("//", "/")
            name = self.server.main_server.name or ""
            return dict(name=name, prefix=prefix, tabs=tabs)
        else:
            return dict(error="Error in getting tabs")
        
    @methodroute(params=dict(configuration=str), skip_by_type=[Stats, Tracer], method="POST")
    def updateconfig(self, configuration=None):
        '''
        Updates the current configuration with the new configuration that is received. 
        '''
        if configuration is not None:
            try:
                configuration = json.loads(configuration)
                self.server.config.update_config(configuration)
            except Exception as e:
                self.logger.exception("Exception in update:%s",e)
                return dict(error="Error in Updating")
        else:
            return dict(error="No configuration specified")
        return dict(status="Success")
    
    @template('configui')
    @methodroute(path="/config/<section>", skip_by_type=[Stats, Tracer], method="GET")
    def config(self, section="all"):
        '''
        Returns the configuration of the specified section.If no section is specified returns whole configuration.
        '''
        if section == "all":
            section_data = self.server.config
        else:
            section_data = self.server.config.get(section, None)
        if section_data:
            return dict(section=section, handler='', config=json.dumps(section_data))
        elif section == "all":
            return dict(error="No configuration found")
        else:
            return dict(error="Invalid Section")

    @template('loggingui')
    @methodroute(skip_by_type=[Stats, Tracer], method="ANY")
    def config__Logging(self):
        '''
        Returns the configuration of the 'Logging' section.
        '''
        section = "Logging"
        try: #@UndefinedVariable
            ret = logging.Logger.manager.getLoggerDict()   #@UndefinedVariable
            cfg = getattr(self.server, 'config', {})
            for key, val in ret.iteritems():
                val['handlers'] = cfg[section].get('loggers',{}).get(key, {}).get('handlers', [])
        except Exception as e:
            self.logger.exception(e)
            ret = {"Error in loading loggers": {}}
            
        log_ret = self.server.config[section].dict()
        log_ret["loggers"] = ret
        
        return dict(section=section, config=json.dumps(log_ret))
    
    @methodroute(skip_by_type=[Stats, Tracer])
    def stats(self):
        '''
        returns a dict with the statistics of the server. statistics are obtained by calling :py:meth:`ManagedServer.stats` 
        '''
        return self.server.stats()
    
    @methodroute(skip_by_type=[Stats, Tracer])
    def health(self):
        '''
        returns the health of the server. The health is obtained from the server's :py:meth:`boots.servers.server.health` method
        '''
        return self.server.health()
    
    
class StatsEntry(dict):
    
    def __init__(self):
        self['total_time'] = 0
        self['total_count'] = 0
        self['mean'] = None
        self['max'] = None
        self['min'] = None
        
    def add(self, val, url, **kargs):
        if isinstance(val, StatsEntry):
            self['total_time'] += val['total_time']
            self['total_count'] += val['total_count']
            self['mean'] = self['total_time'] / self['total_count']
#            self['max_url'] = url if self['max'] >= val['max'] else val['max_url']
#            self['max_args'] = kargs if self['max'] >= val['max'] else val['max_args']
            self['max'] = max(self['max'], val['max'])
            self['min'] = val['min'] if self['min'] is None else min(self['min'], val['min'])
        else:
            self['total_count'] += 1
            self['total_time'] += val
            self['mean'] = self['total_time'] / self['total_count']
#            if self['max'] >= val:
#                self['max_url'] = url 
#                self['max_args'] = kargs
            self['max'] = max(self['max'], val)
            self['min'] = val if self['min'] is None else min(self['min'], val)

        
class StatsCollection(object):
    '''
    the default stat collection class.
    '''
    
    lock = RLock()
    statstable = {}
    
    @classmethod
    def get(cls):
        with cls.lock:
            return cls.statstable
        
    @classmethod
    def add(cls, __name, __delta, __url, **kargs):
        with cls.lock:
            cls.statstable.setdefault(__name, StatsEntry()).add(__delta, __url, **kargs)
    
class ManagedServer(HTTPServer):
    '''
    ManagedServer provides inbuilt capabilities over and above HTTPServer such as statistics, health monitoring
    and configuration update management.
    
    ManagedServers support 3 routes as described by :py:class:`ManagedEP`
    '''
    
    def stats(self):
        '''
        returns a statistical data dict. this can be overriden by subclasses to provide a different
        view of statistics. This method is invoked
        by the /admin/stats route to obtain the statistics for this server
        '''
        return self._stats.get()
        
    def stats_collector(self, handler_name, url, time_taken, start_time, end_time, **kargs):
        '''
        stats_collector is invokved by the Stats plugin to collect statistics. Can be overriden by
        subclasses to redefine statistics collection
        '''
        self._stats.add(handler_name, time_taken, url, **kargs)
    
    def __init__(self,  endpoints=None, servertype=None, **kargs):
        self.config_callbacks['MySQLConfig'] = self._dbconfig_config_update
        self.config_callbacks['Template'] = self.template_config
        endpoints = endpoints or []
        endpoints = [ endpoints ] if type(endpoints) not in [list, tuple] else endpoints
        endpoints = endpoints + [ ManagedEP()]
        self._stats = StatsCollection()
        #Database entry for the server . If server is restarting we dont clear the the entry
        self.restart = False #if server is restarting after crash
        self._created_data = False #if entry for this server is already created (we creatte entry on first request to this server)
        self.servertype = self.get_servertype(servertype)
        super(ManagedServer, self).__init__(endpoints=endpoints, **kargs)
        
    def get_servertype(self, servertype=None):
        return servertype if servertype else self.servertype if hasattr(self, 'servertype') else self.__class__.__name__
        
    
    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=[], 
                        conflict_handler='error', **kargs):
        '''
        get_arg_parser is a classmethod that can be defined by any server. All such methods are called
        when command line argument processing takes place (see :py:meth:`parse_cmmd_line`)

        :param description: A description of the command line argument
        :param add_help: (internal) 
        :param parents: (internal)
        :param conflict_handler: (internal)
        '''
        _argparser = argparse.ArgumentParser(description=description, add_help=add_help, parents=parents, conflict_handler=conflict_handler) 
        _argparser.add_argument('-r', '--restart', dest='restart',  action="store_true", default=kargs.get('restart', False), help='restart'), 
        return _argparser

    def _dbconfig_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the database Configuration.
        Once the DB Config is read , we create MySQL binding that allows to talk to MySQL
        This also checks if this start of the server is a restart, if it is then reads the server_state from server record
        This is set as server object. This state is used by the application to recover its original server state
        '''
        clusterdb = config_obj['MySQLConfig']
        dbtype = clusterdb['dbtype']
        db_url = dbtype + '://'+ clusterdb['dbuser']+ ':' + clusterdb['dbpassword'] + '@' + clusterdb['dbhost'] + ':' + str(clusterdb['dbport']) + '/' + clusterdb['dbschema']
        dbconfig =  DBConfig(dbtype, db_url, clusterdb['pool_size'], clusterdb['max_overflow'], clusterdb['connection_timeout']) 
        db_ep = ClusterDatabaseEndPoint(dbtype=config_obj['Datastore']['datastore'] , dbconfig=dbconfig, name="ClusterDBEP")
        self.add_endpoint(db_ep)
        self.datastore = db_ep.dal
        
        if not self.datastore:
            #the server won't be clustered in-case the datastore configuration is messed
            self.clustered = False
            logging.getLogger().debug('Misconfigured datastore . Fallback to non-cluster mode.')
            #print 'Misconfigured datastore  . Fallback to non-cluster mode.'
        logging.getLogger().debug('Cluster database config updated')
    
    def create_data(self, force=False):
        '''
        This create DataStructure in Persistent data store
        '''
        server_id = None
        assert self.server_adress is not None
        if not self.restart and not self._created_data:
            # delete the previous run's history 
            #self.logger.debug("deleting server info : %s", self.server_adress)
            self._created_data = server_id = self.datastore.remove_server(self.server_adress, recreate=True)
        if force or not self._created_data: 
            #self.logger.debug("creating the server data - servertype : %s, server_adress : %s ", self.servertype, self.server_adress)
            self._created_data = server_id = self.datastore.createdata(self.server_adress, self.servertype )
        elif self._created_data:
            try:
                server_id = self.datastore.get_server_id(self.server_adress)
            except NoResultFound :
                self._created_data = server_id = self.datastore.createdata(self.server_adress, self.servertype )
        assert server_id is not None    
        return server_id    

    def get_standard_plugins(self, plugins):
        '''
        Adds the Stats plugin to all endpoints (except the ManagedEP)
        '''
        try:
            par_plugins = super(ManagedServer, self).get_standard_plugins(plugins)
        except AttributeError:
            par_plugins = []
        return par_plugins + [ Stats() ]  + [ ManagedPlugin(datastore=self.datastore)]
