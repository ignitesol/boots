'''
ManagedServer provides an abstraction for managing a servers configuration, performance and health
'''
from __future__ import division
from fabric import concurrency
if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock
    
import time
from fabric.servers.httpserver import HTTPServer
from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute, Hook,\
    WrapException, RequestParams, Tracer
import json

import logging
# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())

class Stats(Hook):
    
    def create_request_context(self, **kargs):
        return super(Stats, self).create_request_context(**kargs), time.time()
    
    @staticmethod
    def stat_handler(before_or_after, request_context, callback, url, result=None, exception=None, **kargs):
        if before_or_after == 'after':
            callback_obj = getattr(callback, '_callback_obj', None) or getattr(callback, 'im_self', None)
            server = getattr(callback_obj, 'server', None)
            if server and getattr(server, 'stats_collector', None):
                _, start_time = request_context
                end_time = time.time()
                server.stats_collector(callback.__name__, url, end_time - start_time, start_time, end_time, **kargs)
        
    def __init__(self):
        super(Stats, self).__init__(handler=self.stat_handler)

class ManagedEP(HTTPServerEndPoint):
    
    def __init__(self, name=None, mountpoint='/admin', plugins=None, server=None, activate=False, stat_class=None):
#        if plugins is None: plugins = []
#        elif type(plugins) != list: plugins = [ plugins ]
#        stat_class = stat_class or Stats
#        plugins = [ stat_class() ] + plugins
#        print plugins
        super(ManagedEP, self).__init__(name=name, mountpoint=mountpoint, plugins=plugins, server=server, activate=activate)


    @methodroute(params=dict(configuration=json.loads), skip_by_type=[Stats, Tracer])
    def config(self, configuration=None):
        if configuration is not None:
            self.config.update_config(configuration)
        
    @methodroute(skip_by_type=[Stats, Tracer])
    def stats(self):
        return self.server.stats()
    
    @methodroute(skip_by_type=[Stats, Tracer])
    def health(self):
        return self.server.health()
    
class StatsEntry(dict):
    
    def __init__(self):
        self['total_time'] = 0
        self['total_count'] = 0
        self['mean'] = None
        self['max'] = None
        self['min'] = None
        
    def add(self, val):
        if isinstance(val, StatsEntry):
            self['total_time'] += val['total_time']
            self['total_count'] += val['total_count']
            self['mean'] = self['total_time'] / self['total_count']
            self['max'] = max(self['max'], val['max'])
            self['min'] = val['min'] if self['min'] is None else min(self['min'], val['min'])
        else:
            self['total_count'] += 1
            self['total_time'] += val
            self['mean'] = self['total_time'] / self['total_count']
            self['max'] = max(self['max'], val)
            self['min'] = val if self['min'] is None else min(self['min'], val)

        
class StatsCollection(object):
    
    lock = RLock()
    statstable = {}
    
    @classmethod
    def get(cls):
        with cls.lock:
            return cls.statstable
        
    @classmethod
    def add(cls, name, delta):
        with cls.lock:
            cls.statstable.setdefault(name, StatsEntry()).add(delta)
    
class ManagedServer(HTTPServer):
    
    def stats(self):
        return self._stats.get()
        
    def stats_collector(self, handler_name, url, time_taken, start_time, end_time, **kargs):
        self._stats.add(handler_name, time_taken)
    
    def __init__(self,  endpoints=None, *args, **kargs):
        endpoints = endpoints or []
        endpoints = [ endpoints ] if type(endpoints) not in [list, tuple] else endpoints
        endpoints = endpoints + [ ManagedEP()]
        self._stats = StatsCollection()
        super(ManagedServer, self).__init__(*args, endpoints=endpoints, **kargs)

    def get_standard_plugins(self, plugins):
        try:
            par_plugins = super(ManagedServer, self).get_standard_plugins(plugins)
        except AttributeError:
            par_plugins = []
        return par_plugins + [ Stats() ] 
