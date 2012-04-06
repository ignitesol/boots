'''
Created on Mar 21, 2012

@author: AShah
'''
from fabric import concurrency
if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()

import argparse
import beaker.middleware as bkmw
import beaker.cache as bkcache
import beaker.util as bkutil
from fabric.servers.helpers.authorize import SparxAuth
from fabric.servers.server import Server
import bottle

import logging

# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())

class HTTPServer(Server):
    
    config_callbacks = { }  # we can set these directly out of the class body or in __init__

    def __init__(self,  name=None, endpoints=None, parent_server=None, mount_prefix='',
                 **kargs):
        '''
        kargs can be 'session' (bool), 'cache' (bool), 'auth' (bool) and control whether any related 
        configuration processing is to be done
        '''
        self.mount_prefix = mount_prefix or ''
        
        # setup the callbacks for configuration
        session, cache, auth = kargs.get('session', False), kargs.get('cache', False), kargs.get('auth', False)
        if session: self.config_callbacks['Session'] = self.session_config_update
        if cache: self.config_callbacks['Caching'] = self.cache_config_update
        if auth: self.config_callbacks['Auth'] = self.auth_config_update
        
        self.app = bottle.default_app() # this will get overridden by the callback handlers as appropriate

        super(HTTPServer, self).__init__(name=name, endpoints=endpoints, parent_server=parent_server, **kargs)
    
    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=[], 
                        conflict_handler='error', **kargs):
        _argparser = argparse.ArgumentParser(description=description, add_help=add_help, parents=parents, conflict_handler=conflict_handler) 
        _argparser.add_argument('-i', '--host', dest='host', default=kargs.get('defhost', 'localhost'),
                                 help='hostname or ip address. (default: {})'.format(kargs.get('defhost', 'localhost')))
        _argparser.add_argument('-p', '--port', dest='port', type=int, default=kargs.get('defport', '8080'),
                                 help='port number. (default: {})'.format(kargs.get('defport', '8080'))),                                 
        _argparser.add_argument('--debug', action="store_true", help='start bottle server in debug mode')
        return _argparser
        
    def start_main_server(self, default_host=None, default_port=None):
#        bottle.debug(True)
        if concurrency == 'gevent':
            bottle.run(host=self.cmmd_line_args['host'], port=self.cmmd_line_args['port'], server='gevent')
        else:
            bottle.run(host=self.cmmd_line_args['host'], port=self.cmmd_line_args['port'])

    def activate_endpoints(self):
        '''
        Activate this server's endpoints
        '''
        [ endpoint.activate(server=self, mount_prefix=self.mount_prefix) for endpoint in self.endpoints ]

    def auth_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the Auth Server Configuration.
        
        SPARXAuth relies on a session management middleware(i.e.Beaker) upfront in the stack. 
        '''
        logins = [('demo', 'demo')]     #TODO:Get it from a User DB.
    
        self.app = SparxAuth(self.app, users=logins, 
                             open_urls=config_obj['Auth']['open_urls'], 
                             session_key=config_obj['Auth']['key'])
        
        self.app = bkmw.SessionMiddleware(self.app, 
                                          config_obj['Auth']['beaker'], 
                                          environ_key=config_obj['Auth']['key'])
        
        logging.getLogger().debug('Auth config updated')
    
    def session_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the Server Configuration.
        '''
        self.app = bkmw.SessionMiddleware(self.app, config_obj['Session'])
        logging.getLogger().debug('Server config updated')
    
    def cache_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the Cache Configuration.
        '''
        self.cache = bkcache.CacheManager(**bkutil.parse_cache_config_options(config_obj['Caching']))
        logging.getLogger().debug('Cache config updated')