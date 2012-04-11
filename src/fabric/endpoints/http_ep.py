'''
Created on Mar 18, 2012

@author: AShah
'''
from fabric import concurrency

if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock
 
import logging
import bottle
import re
import inspect
from functools import wraps
from fabric.endpoints.endpoint import EndPoint
from fabric.common.utils import new_counter
import traceback
import sys
import os

# leverages bottle.

#######     BEWARE       ################
# Decorator writers - Beware.
# ensure you put the following code
#    self.plugin_post_apply(callback, wrapper)
# just before returning wrappers. This is essential for RequestParam to work since we need the signature
# of the function which decorators mask. 
# alternately, we can use the import decorator module
##############
class BasePlugin(object):
    ''' BasePlugin provides helper methods that propogate information across plugins as they are applied. All
    plugins should inherit from BasePlugin and invoke self.plugin_post_apply before returning the wrapper function
    (typically before return wrapper)
    '''
    def plugin_post_apply(self, callback, wrapper):
        '''
        This ensure that we copy any special attributes from callback for use by other plugins. This
        should be called as the last line of the apply before return wrapper. Its purpose is to hoist
        the signature and the reference to the 'self' of the method that actually implements the final callback.
        The signature is hoisted and kept as an attribute of the wrapper as *wrapper._signature*. The *self* of the 
        wrapper method is stored in an attribute *wrapper._callback_obj*
        
        :param callback: the callback passed to the decorator (i.e. the actual method/function that will be decorated)
        :param wrapper: the wrapper function that wraps callback (in plugins this is typically called *wrapper*)
        '''
        wrapper._signature = inspect.getargspec(callback) if not hasattr(callback, '_signature') else callback._signature
        wrapper._callback_obj = callback.im_self if not hasattr(callback, '_callback_obj') else callback._callback_obj
        

class RequestParams(BasePlugin):
    '''
    RequestParams processes parameters that are provided with an HTTP request. It works through introspection
    of the method/function that is handling the request (and hence, it requires access to the method's signature). Refer
    to the :py:class BasePlugin.
    
    With HTTPServers, RequestParams is automatically instantiated and users can directly use this.
    
    RequestParams extracts parameters from the GET, POST or ANY methods (as specified in :py:func:`methodroute`). RequestParams
    requires a context parameter called params (also specified with :py:func:`methodroute`
    '''
               
    def __init__(self):
        pass
    
    def setup(self, app):
        ''' Make sure that RequestParams is not already installed '''
        for other in app.plugins:
            if isinstance(other, RequestParams):
                raise bottle.PluginError("Found another RequestParams plugin")

    def apply(self, callback, context):
        params = context['config'].get('params', {})
        f_args, _, _, f_defaults = inspect.getargspec(callback) if not hasattr(callback, '_signature') else callback._signature
        if f_defaults is None: f_defaults = []
        f_args = list(filter(lambda x: x != 'self', f_args))
        mandatory_args, optional_args = f_args[:-len(f_defaults)], f_args[-len(f_defaults):]
        method = context['method']

        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            seek_args = filter(lambda x: x not in kargs, f_args)
            req_params = bottle.request.POST if method == 'POST' or method =='ANY' and len(bottle.request.POST.keys()) else bottle.request.GET
            for arg in seek_args:
                converter = params.get(arg, lambda x: x) # see if the parameter is specified, else conversion function is identity
                multivalue = type(converter) == list # see if we need single or multiple values
                if multivalue:
                    converter = converter[0] if len(converter) > 0 else lambda x: x # obtain the conversion function if any from the 1st ele
                    try:
                        values = [ converter(val) for val in filter(lambda x: x != '', req_params.getall(arg)) ]
                    except ValueError, Exception: 
                        bottle.abort(400, 'Wrong parameter format for: {}'.format(arg))
                    if len(values) != 0:  # not adding empty lists since either the default gets it or it should be flagged as error for mandatory
                        kargs[arg] = values
                else:
                    value = req_params.get(arg)
                    try:
                        if value is not None:
                            value = converter(value)
                    except ValueError, Exception: 
                        bottle.abort(400, 'Wrong parameter format for: {}'.format(arg))
                    if value is not None: # checking again after converter is applied
                        kargs[arg] = value
            missing_params = []
            for m in mandatory_args:
                if m not in kargs:
                    missing_params += [m]
            if len(missing_params) != 0:
                bottle.abort(400, 'Missing parameters: {}'.format(", ".join(missing_params)))
            return callback(*args, **kargs)
        
        self.plugin_post_apply(callback, wrapper)
        return wrapper

class Hook(BasePlugin):
    request_counter = new_counter() # allows requests and responses to be correlated
    
    def create_request_context(self, callback, url, **kargs):
        return (self.request_counter(), getattr(callback, '_callback_obj', None) or getattr(callback, 'imself', None))
    
    def __init__(self, handler=None):
        dummy_handler = lambda *args, **kargs: None
        self.handler = handler or dummy_handler
               
    def setup(self, app):
        ''' we can install multiple hooks of the same type if we want to check status before and after each plugin '''
        pass

    def apply(self, callback, context):
        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            request_context = self.create_request_context(callback=callback, url=bottle.request.url, **kargs)
            exception = None 
            self.handler(before_or_after='before', request_context=request_context, callback=callback, url=bottle.request.url, **kargs)
            try:
                result = callback(*args, **kargs)
            except Exception as e:
                exception = e
                result=None
            finally:
                self.handler(before_or_after='after', request_context=request_context, callback=callback, url=bottle.request.url, 
                             result=result, exception=exception, **kargs)
                if exception:
                    raise
            return result
        
        self.plugin_post_apply(callback, wrapper)
        return wrapper
    
class Tracer(Hook):
    
    def default_handler(self, before_or_after, request_context, callback, url, result=None, exception=None, **kargs):
        req_count, _ = request_context
        if filter(None, [ regex.match(url) for regex in self.tracer_paths ]) != []:
            if before_or_after == 'before':
                logging.getLogger().debug('Request: %s. url = %s, %s', req_count, url, kargs)
            elif exception:
                logging.getLogger().debug('Response: %s. Exception = %s. [ url = %s, %s ]', req_count, exception, url, kargs)
            else:
                logging.getLogger().debug('Response: %s. Result = %s. [ url = %s, %s ]', req_count, result, url, kargs)
        
    def __init__(self, tracer_paths='.*', handler=None):
        self.tracer_paths = map(re.compile, tracer_paths or [])
        handler = handler or self.default_handler
        super(Tracer, self).__init__(handler=handler)
    
class WrapException(BasePlugin):
               
    def __init__(self, default_handler=None):
        self.default_handler = default_handler
    
    def setup(self, app):
        ''' Make sure that WrapException is not already installed '''
        for other in app.plugins:
            if isinstance(other, WrapException):
                raise bottle.PluginError("Found another WrapException plugin")

    def apply(self, callback, context):
        '''
        to be used with bottle routes. It decorates the request handler, traps any exception thrown by the handler 
        and packages the exception as a message if an exception messager is provided. In the absence of an exception messager,
        it logs and raises the same exception back to the caller.
        @param exception_messenger: a callable (class or function) that will accept the request arguments (multidict), the error string and all other
        arguments passed to the handler and return a iterable that can be passed back to bottle  
        @param logger - optional argument for logging purposes. defaults to the root logger
        @param cleanup_funcs - an optional list of functions to be called to process cleanup on failure (e.g. removing the session). Each function is 
        passed the query argument (multidict) dictionary and all the other arguments passed to the handler.
        '''        
        handler = context['config'].get('handler', self.default_handler)
        cleanup_funcs = context['config'].get('cleanup_funcs', [])
        method = context['method']

        @wraps(callback)
        def wrapper(*args, **kargs):
            qstr = bottle.request.POST if method == 'POST' or method == 'ANY' and len(bottle.request.POST.keys()) else bottle.request.GET
            try:
                return callback(*args, **kargs)
            except (bottle.HTTPError, Exception) as err: # let's not handle HTTPError
                logging.getLogger().exception('Exception: %s', err)
                
                # FOR DEBUG
                tb = traceback.extract_tb(sys.exc_info()[2], 2)
                errstr = str(err) + '<br/>'
                for file, line, f, text in tb[1:]:
                    file = os.path.basename(os.path.splitext(file)[0])
                    errstr += "{}:{} in {}: {}<br/>".format(file, line, f, text)
    
                if handler:
                    err_ret=handler(errstr, qstr, *args, **kargs)
                for f in cleanup_funcs:
                    try:
                        f(qstr, *args, **kargs)
                    except:
                        pass
                if handler:
                    return err_ret
                else:
                    bottle.abort(code=500, text=errstr)

        self.plugin_post_apply(callback, wrapper)
        return wrapper
       


# decorators for allowing routes to be setup and handled by instance methods
# credit to http://stackoverflow.com/users/296069/skirmantas
def methodroute(path=None, params=None, **kargs):
    '''
    methodroute is a decorator that allows applying a bottle route to a method of a class. It cleanly manages bound instances
    and invokes the method of the correct object.
    
    If path is None, the method being decorated is introspected to obtain the set of possible routes (in a RESTFUL manner).
    params works in conjunction with the RequestParam plugin (which needs to be installed). params specification is optional. The plugin
    infers whether parameters are mandatory or optional from the signature of the function. 
    NOTE: currently, the restful version (path=None) and mandatory parameters do not work together.  
    If params is specified as a dict(argname=conversion-function), request parameters are checked for the right typed values. 
    If a parameter is specified in params as argname=[conversion-function] then multiple values (list of one or more elements) is passed
    If the function has a default-value, then the param is considered optional. 
    @param path: '/index' or similar. If path is None, follows bottle's route processing for None paths
    @type path: str or None
    @param params: optional dict of the form { 'name': conversion-function, 'name2': [func2], 'name3': [] }. If parameter is specified on
    the function signature and no conversion function is specified, it defaults to whatever the type of the value returned by the web-server is 
    @type params: dict
    '''
  
    kargs.setdefault('params', {}).update(params or {})
    
    def decorator(f):
        f._methodroute = path
        f._route_kargs = kargs
        f._signature = inspect.getargspec(f)
        return f
#    return decorator if type(route) in [ type(None), str ] else decorator(route)
    return decorator
    
class HTTPServerEndPoint(EndPoint):
    
    # class attributes
    _name_prefix = 'HTTPServer_'
    lock = RLock()
    http_server_end_points = {} # class attribute. Accessed in thread safe manner
    counter = new_counter(0)    # class attribute common to all subclasses of HTTPServerEndPoint
    
    self_remover = re.compile('/:self$|:self/')
    def routeapp(self):
        '''
        routeapp installs methodroute decorated methods as routes in the app.
        currently request_param does not work with the automatic yieldroutes version of the decorator
        '''
        
        for kw in dir(self): # for all varnames
            try:
                callback = getattr(self, kw)  # get the var value
            except AttributeError:
                callback = None
            if hasattr(callback, '_methodroute'): # only methodroute decorated methods will have this
                route_kargs = callback._route_kargs  # additional kargs passed on the decorator
                
                # implement skip by type and update skip for the route
                skip_by_type = route_kargs.setdefault('skip_by_type', [])
                skip_by_type = bottle.makelist(skip_by_type)
                skip = [ p for p in self.plugins if p.__class__ in skip_by_type ]
                route_kargs.setdefault('skip', [])
                route_kargs['skip'] += skip
                del route_kargs['skip_by_type']
                
                # explicitly find route combinations and remove :self - else bottle includes self in the routes
                path = callback._methodroute if callback._methodroute is not None else [ self.self_remover.sub('', s) for s in bottle.yieldroutes(callback)]
                self.app.route(path=path, callback=callback, **route_kargs)
                    
                
    def __init__(self, name=None, mountpoint='/', plugins=None, server=None, activate=False):
        '''
        @param name: a name for the endpoint
        @type name: str
        @param mountpoint: th prefix for all routes within this endpoint
        @type mountpoint: str
        @param plugins: plugins are applied to every HTTP request (except if the methodroute 
        skips them (read bottle's documentation). plugins are applied in reverse order (i.e.
        the 1st one is the outermost, the last one in the list is the innermost 
        @type plugins: list
        @param server: a reference to the server that contains this endpoint
        @type server: Server
        @param activate: whether to activate this endpoint on creation or later through an explicit 
        activate call
        @type activate: bool
        '''

        self.name = name = name or self._name_prefix + str(HTTPServerEndPoint.counter())
        self.mountpoint = mountpoint
        self.plugins = getattr(self, 'plugins', []) + (plugins or []) # in case plugins have already been set up
        if type(self.plugins) != list: self.plugins = [ self.plugins ]
        self.server = server
        self.mount_prefix = ''
        self.activated = False
        
        with self.lock:
            if self.http_server_end_points.get(self.name, None):
                logging.getLogger().warning('HTTPServerEndPoint: Overwriting endpoint %s', self.name)
            self.http_server_end_points[self.name] = self
        
        if activate:
            self.activate()
            
    def activate(self, server=None, mount_prefix=None):
        
        if self.activated:
            return

        self.mount_prefix = mount_prefix or self.mount_prefix
        self.server = server or self.server
        
        mountpoint = self.mount_prefix + self.mountpoint
        if mountpoint != '/':
            self.app = bottle.Bottle()
            bottle.default_app().mount(mountpoint, self.app)
        else:
            self.app = bottle.default_app()
        
        # apply all plugins
        self.std_plugins = self.server.get_standard_plugins(self.plugins)
        self.plugins = self.std_plugins + self.plugins
        [ self.app.install(plugin) for plugin in self.plugins ]
            
        self.routeapp() # establish any routes that have been setup by the @methodroute decorator
        self.activated = True

    
    def abort(self, code, text):
        bottle.abort(code, text)
        
    @property
    def request(self):
        return bottle.request

    @property
    def request_params(self):
        return bottle.request.GET if bottle.request.method == 'GET' else bottle.request.POST
    
    @property
    def response(self):
        return bottle.response
    
    @property
    def environ(self):
        return bottle.request.environ
