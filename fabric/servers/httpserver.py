'''
:py:class:`HTTPBaseServer` provides the appropriate execution environment for :py:class:`HTTPServerEndPoints`
including basic argument processing, activating all endpoints and starting up the server (using bottle_)

:py:class:`HTTPServer` builds on HTTPServer to provide HTTP parameter processing,
basic exception handling for requests, session, cache and authorization for the server.
'''
from fabric import concurrency
from fabric.endpoints.http_ep import Tracer, WrapException, RequestParams
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

class HTTPBaseServer(Server):
    '''
    The base class for most HTTP servers, this provides simple argument processing and instantiating
    of the server. It leverages bottle_
    
    The :py:data:`fabric.concurrency` controls whether the default server is *gevent* based or WSGIReference  
    '''

    def __init__(self,  name=None, endpoints=None, parent_server=None, mount_prefix='', 
                 **kargs):
        '''
        Most arguments have the same interpretation as :py:class:`fabric.servers.Server`. The additional parameters 
        specific to HTTPBaseServer are:
        
        :param mount_prefix: Since multiple servers may be composed in a single entity, each server may specify 
            a unique *mount_prefix* such that all requests with that url prefix will be routed for handling by
            that server (and subsequently by that server's endpoints). The default mount_prefix is the empty string.
            
            Essentially, a request URL is matched against (mount_prefix + mountpoint + methodroute)

        '''
        self.app = bottle.default_app() # this will get overridden by the callback handlers as appropriate
        super(HTTPBaseServer, self).__init__(name=name, endpoints=endpoints, parent_server=parent_server, **kargs)

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
        True. The specific bottle server is controlled by the fabric.concurrency setting
        
        :param default_host: default host for the http server
        :param default_port: default port for the http server
        :param server to be passed to bottle. defaults to the inbuild WSGIReference server or gevent based
            on the concurrency setting
        '''
        if self.standalone:
            host = kargs.get('default_host', None) or self.cmmd_line_args['host'] or '127.0.0.1'
            port = kargs.get('default_port', None) or self.cmmd_line_args['port'] or '9000'
            server = kargs.get('server', 'wsgiref')
            if concurrency == 'gevent': server = 'gevent'
    #        bottle.debug(True)
            bottle.run(host=host, port=port, server=server)

    def activate_endpoints(self):
        '''
        Activate this server's endpoints
        '''
        [ endpoint.activate(server=self, mount_prefix=self.mount_prefix) for endpoint in self.endpoints ]


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
    
    config_callbacks = { }  # we can set these directly out of the class body or in __init__

    def __init__(self,  name=None, endpoints=None, parent_server=None, mount_prefix='',
                 **kargs):
        '''
        :params bool session: controls whether sessions based on configuration ini should be instantiated. sessions
            will be available through the HTTPServerEndPoint
        :params bool cache: controls whether cache based on configuration ini should be instantiated. cache is available
            through self.cache
        :params bool auth: controls whether sessions based on configuration ini should be instantiated 
        :params handle_exception: controls whether a default exception handler should be setup
        '''

        self.app = None
        self.mount_prefix = mount_prefix or ''
        
        # setup the callbacks for configuration
        session, cache, auth = kargs.get('session', False), kargs.get('cache', False), kargs.get('auth', False)
        if session: self.config_callbacks['Session'] = self.session_config_update
        if cache: self.config_callbacks['Caching'] = self.cache_config_update
        if auth: self.config_callbacks['Auth'] = self.auth_config_update
        
        self.handle_exception = kargs.get('handle_exception', False)
        super(HTTPServer, self).__init__(name=name, endpoints=endpoints, parent_server=parent_server, **kargs)
        
    # make the object act like a WSGI server
    def __call__(self, environ, start_response):
        assert(self.app is not None)
        return self.app(environ, start_response)
        
    
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
        Called by Config to update the session Configuration.
        '''
        self.app = bkmw.SessionMiddleware(self.app, config_obj['Session'])
        logging.getLogger().debug('Server config updated')
    
    def cache_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the Cache Configuration.
        '''
        self.cache = bkcache.CacheManager(**bkutil.parse_cache_config_options(config_obj['Caching']))
        logging.getLogger().debug('Cache config updated')
        
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