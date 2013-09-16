'''
:py:class:`HTTPBaseServer` provides the appropriate execution environment for :py:class:`HTTPServerEndPoints`
including basic argument processing, activating all endpoints and starting up the server (using bottle)

:py:class:`HTTPServer` builds on HTTPServer to provide HTTP parameter processing,
basic exception handling for requests, session, cache and authorization for the server.
'''
from boots import concurrency
from boots.endpoints.http_ep import Tracer, WrapException, RequestParams,\
    HTTPServerEndPoint

import argparse
import beaker.middleware as bkmw
import beaker.cache as bkcache
import beaker.util as bkutil
from boots.servers.helpers.authorize import SimpleAuth
from boots.servers.server import Server
import bottle
import logging
from boots.common.dirutils import DirUtils
from string import Template

# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())

class HTTPBaseServer(Server):
    '''
    The base class for most HTTP servers, this provides simple argument processing and instantiating
    of the server. It leverages bottle_
    
    The :py:data:`boots.concurrency` controls whether the default server is *gevent* based or WSGIReference  
    '''

    def __init__(self,  name="", endpoints=None, parent_server=None, mount_prefix='', 
                 **kargs):
        '''
        Most arguments have the same interpretation as :py:class:`boots.servers.Server`. The additional parameters 
        specific to HTTPBaseServer are:
        
        :param mount_prefix: Since multiple servers may be composed in a single entity, each server may specify 
            a unique *mount_prefix* such that all requests with that url prefix will be routed for handling by
            that server (and subsequently by that server's endpoints). The default mount_prefix is the empty string.
            
            Essentially, a request URL is matched against (mount_prefix + mountpoint + methodroute)

        '''
        self.app = bottle.default_app() # this will get overridden by the callback handlers as appropriate
        super(HTTPBaseServer, self).__init__(name=name, endpoints=endpoints, parent_server=parent_server, **kargs)
        
    # make the object act like a WSGI server
    def __call__(self, environ, start_response):
        assert(self.app is not None)
        return self.app(environ, start_response)

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
        _argparser.add_argument('-i', '--host', dest='host', default=kargs.get('defhost', 'localhost'),
                                 help='hostname or ip address. (default: {})'.format(kargs.get('defhost', 'localhost')))
        _argparser.add_argument('-p', '--port', dest='port', type=int, default=kargs.get('defport', '8080'),
                                 help='port number. (default: {})'.format(kargs.get('defport', '8080'))),                                 
        _argparser.add_argument('--debug', action="store_true", help='start bottle server in debug mode')
        return _argparser
        
    def start_main_server(self, **kargs):
        '''
        starts the main server - in our case bottle. We will start the server only if self.standalone is 
        True. The specific bottle server is controlled by the boots.concurrency setting
        
        :param default_host: default host for the http server
        :param default_port: default port for the http server
        :param server to be passed to bottle. defaults to the inbuild WSGIReference server or gevent based
            on the concurrency setting
        '''
        if self.standalone:
            host = kargs.get('default_host', None) or self.cmmd_line_args['host'] or '127.0.0.1'
            port = kargs.get('default_port', None) or self.cmmd_line_args['port'] or '9000'
            server = kargs.get('server', 'wsgiref')
            quiet = kargs.get('quiet', True)
            if concurrency == 'gevent': server = 'gevent'
            bottle.debug(True)
            bottle.run(app=self, host=host, port=port, server=server)

    def activate_endpoints(self):
        '''
        Activate this server's endpoints
        '''
        [ endpoint.activate(server=self, mount_prefix=self.mount_prefix) for endpoint in self.endpoints if isinstance(endpoint, HTTPServerEndPoint)]
        super(HTTPBaseServer, self).activate_endpoints()


class HTTPServer(HTTPBaseServer):
    '''
    HTTPServer refines HTTPBaseServer by adding standard plugins and session, cache and authentication 
    configuration settings.
    
    The standard plugins are 
    
    * :py:class:`RequestParams` for parameter processing
    * :py:class:`WrapException` for generic exception handling. If a specific exception handler has been 
        added by the endpoint, this generic excaption handler is ignored 
    * :py:class:`Tracer` for request and response tracing/logging of http requests
    '''
    
    auth_classes = { '--no-key-specified': SimpleAuth } # subclasses should ADD to (NOT OVERWRITE) this dict
    config_callbacks = { }  # we can set these directly out of the class body or in __init__

    def __init__(self,  name=None, endpoints=None, parent_server=None, mount_prefix='',
                 session=False, cache=False, auth=False, handle_exception=False, **kargs):
        '''
        :params bool session: controls whether sessions based on configuration ini should be instantiated. sessions
            will be available through the HTTPServerEndPoint. If a string, implies the name of the config section. If session is a list of strings, 
            implies list of names of config sections identifying session configurations
        :params bool cache: controls whether cache based on configuration ini should be instantiated. 
            If a string, implies the name of the config section. If cache is a list of strings, 
            implies list of names of config sections identifying cache configurations
            A special member of each configuration section (cache_name) should be a string. The resulting cache is available as
            through self.<cache_name> (defaults to self.cache)
        :params bool auth: controls whether sessions based on configuration ini should be instantiated. Can be False (no auth) or True (using BootsAuth from the config file)
            or it can be a list of config sections that will be auth related (allowing multiple auth layers). Note, the last entry will challenge the user the 1st (i.e. it is 
            the outermost auth layer) 
        :params handle_exception: controls whether a default exception handler should be setup
        '''

        self.app = None
        self.mount_prefix = mount_prefix or ''
        
        # setup the callbacks for configuration
        if type(session) is not bool and session: # implies session_configs are being passed
            self.session_configs = session if type(session) in [ list, tuple ] else [ session ]
        elif session:
            self.session_configs = getattr(self, 'session_configs', [ 'Session' ])
        if session:
            for s in self.session_configs:
                self.config_callbacks[s] = self.session_config_update
        else:
            self.session_configs = []
                
        if type(cache) is not bool and cache: # implies cache_configs are being passed
            self.cache_configs = cache if type(cache) in [ list, tuple]  else [ cache ]
        elif cache:
            self.cache_configs = getattr(self, 'cache_configs', [ 'Caching' ])
        if cache:
            for s in self.cache_configs:
                self.config_callbacks[s] = self.cache_config_update
        else:
            self.cache_configs = []

        if type(auth) is bool: # i.e. if auth=True was passed, set the default BootsAuth
            auth = [ 'BootsAuth' ] if auth else False 
        elif type(auth) not in [ list, tuple ] :
            auth = [ auth ]
        if auth:
            self.auth_configs = auth
            for auth_config_section in self.auth_configs:
                self.config_callbacks[auth_config_section] = self.auth_config_update
        else:
            self.auth_configs = []
        
        self.login_templates = {}
        self.handle_exception = handle_exception
#        self.handle_exception = kargs.get('handle_exception', False)
        super(HTTPServer, self).__init__(name=name, endpoints=endpoints, parent_server=parent_server, **kargs)
    
    def auth_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the Auth Server Configuration.
        
        BootsAuth relies on a session management middleware(i.e.Beaker) upfront in the stack. 
        '''
        auth_class_key = new_val.get('auth_class_key', '--no-key-specified--')
        self.AuthClass = self.auth_classes.get(auth_class_key) or SimpleAuth
        login_template = new_val.get('login_template', '')
        try:
            template = None
            if login_template != '':
                login_template = DirUtils().resolve_path(base_dir=config_obj['_proj_dir'], path=login_template)
                self.login_templates['.'.join(full_key)] = template = Template(DirUtils().read_file(login_template, None))
        except ValueError as e:
            self.logger.warning('Template dir is not within the project root: %s. Ignoring', login_template)
            template = None
        except (IOError, Exception) as e:
            self.logger.warning('Ignoring template file error %s', e)
            template = None
            
        conf = dict(new_val) # make a copy
        conf['logins'] = [ tuple(s.split(':', 1)) for s in conf.get('logins', [])]
        self.logger.debug("auth-config login %s", conf['logins'])
        
        conf['open_urls'] = list(set(conf.setdefault('open_urls', []))) # Making them unique
        conf['template'] = template
        conf.pop('auth_class_key')
        conf.pop('beaker', None) # remove beaker from the copied conf
        conf.pop('caching', None) # remove caching from the copied conf
        conf.pop('key', None) # remove auth cookie key from copied conf
        self.app = self.AuthClass(self.app, **conf)
        
        # a persistent, cookie based session
        self.app = bkmw.SessionMiddleware(self.app, new_val['beaker'], environ_key=new_val['session_key'])
        
        logging.getLogger().debug('Auth config updated for %s. Open urls %s', '.'.join(full_key), conf['open_urls'])
    
    def session_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the session Configuration.
        '''
        self.app = bkmw.SessionMiddleware(self.app, new_val, environ_key=new_val.get('session.key', full_key[-1]))
        logging.getLogger().debug('Session config updated for %s', '.'.join(full_key))
    
    def cache_creator(self, caching_config):
        return bkcache.CacheManager(**bkutil.parse_cache_config_options(caching_config))
    
    def cache_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the Cache Configuration.
        '''
        sanitized_config = dict(new_val)
        cache_name = sanitized_config.pop('cache_name', 'cache')
        setattr(self, cache_name, self.cache_creator(sanitized_config))
        logging.getLogger().debug('Cache config updated for %s available in self.%s with type %s', '.'.join(full_key), cache_name, type(getattr(self, cache_name)))
    
    def template_config(self, action, full_key, new_val, config_obj):
        self.logger.debug("Template Config updated for %s", full_key)
        sub_config_obj = config_obj
        for key in full_key:
            sub_config_obj = config_obj[key]
        for path in sub_config_obj.get("template_paths", []):
            self.add_template_path(path)
            
    def get_standard_plugins(self, plugins):
        '''
        get_standard_plugins returns a list of plugins that will be associated with every HTTPServerEndPoint 
        with this server. This can be overridden by a subclass to provide a set of standard plugins that a subclass
        servers may wish to instantiate. Subclasses should ensure that they invoke super().get_standard_plugins to 
        instantiate plugins of the super classes. Subclasses can also inspect the plugins that the endpoint
        has been explicitly provided to change their behavior.
        
        :py:class:`HTTPServer` instantiates :py:class:`Tracer`, :py:class:`RequestParams` and optionally (governed
        by self.handle_exception) :py:class:`WrapException`
        
        :param plugins: the list of plugins explicitly provided to an endpoint
        '''

        if self.config.get('Tracer', {}).get('enabled', False):
            tracer_paths = self.config.get('Tracer', {}).get('paths', None) or  ['.*']
            tracer_plugin = [ Tracer(tracer_paths) ]
        else:
            tracer_plugin = []

        exception_handler = [ WrapException() ] if WrapException not in plugins and self.handle_exception else []
        
        return exception_handler + [ RequestParams() ] + tracer_plugin  # outermost to innermost
    
    def add_template_path(self, template_path):
#        self.logger.debug("Adding template path:%s",template_path)
        bottle.TEMPLATE_PATH.append(template_path)
#        self.logger.debug("Added template path:%s",bottle.TEMPLATE_PATH)