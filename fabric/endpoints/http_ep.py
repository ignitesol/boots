'''
HTTP Servers are served through HTTPServerEndPoints. These end-points offer flexibility of adding routes (urls where HTTP can be served from), providing
parameter processing and validation capabilities, handling exceptions generically and other hooks that can be applied before and after each request. 

These endpoints also provide access the the http :py:meth:`request`, :py:meth:`environ` and :py:meth:`response` objects, in addition to the ability to :py:meth:`abort`
requests. Currently these endpoints are based on the bottle web microframework (http://bottlepy.org)

A typical scenario to create an HTTP Server is to define a subclass of the HTTPServerEndPoint and to define routes using the :py:func:`methodroute` decorator.

::

    class SimpleEP(HTTPServerEndPoint):
        
        @methodroute():
        def hello(self, name=None):
            """ matches /hello and /hello/anand """
            name = name or 'there'
            return 'hello ' + name
            
Refer to :doc:`tutorial` for further examples.
'''
from fabric import concurrency

if concurrency == 'gevent':
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock

from fabric.common.utils import new_counter
from fabric.endpoints.endpoint import EndPoint
from functools import wraps
import bottle
import inspect
import logging
import os
import re
import sys
import traceback

try: from collections import MutableMapping as DictMixin
except ImportError: # pragma: no cover
    from UserDict import DictMixin
 

# leverages bottle.

#######     BEWARE       ################
# Decorator writers - Beware.
# ensure you put the following code
#    self.plugin_post_apply(callback, wrapper)
# just before returning wrappers. This is essential for RequestParam to work since we need the signature and 
# callback_obj
# of the function which decorators mask. 
##############
class BasePlugin(object):
    ''' BasePlugin provides helper methods that propagate information across plugins as they are applied. All
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
#        wrapper._signature = inspect.getargspec(callback) if not hasattr(callback, '_signature') else callback._signature
#        wrapper._callback_obj = callback.im_self if not hasattr(callback, '_callback_obj') else callback._callback_obj
        pass
        
    def get_callback_obj(self, callback):
        '''
        this method, when passes a callback from within the plugin wrapper, returns the object reference of the callback
        object that was defined with @methodroute
        
        :param callback: A reference to the current callback within a plugin wrapper
        :returns: object whose method was wrapped with @methodroute
        '''
        return callback.im_self if not hasattr(callback, '_callback_obj') else callback._callback_obj
        

class RequestParams(BasePlugin):
    '''
    RequestParams processes parameters that are provided with an HTTP request. It works through introspection
    of the method/function that is handling the request (and hence, it requires access to the method's signature). Refer
    to the :py:class BasePlugin.
    
    With HTTPServers, RequestParams is automatically instantiated and users can directly use this.
    
    RequestParams extracts parameters from the GET, POST or ANY methods (as specified in :py:func:`methodroute`). RequestParams
    requires a context parameter called params (also specified with :py:func:`methodroute`). The params parameters with methodroute is
    optional. 
    
    :param dict params: params works in conjunction with the RequestParam plugin and is passed to the @methodroute decorator
        It specifies parameters names expects with the GET or POST and the type that those parameters are expected to be. The plugin
        infers whether parameters are mandatory or optional from the signature of the method that is serving the route. Option parameters
        are keyword parameters of the method, mandatory parameters are non-keyword parameters.
        
        The format of params is a dict with each key being the name of an expected parameter and the value being the conversion function
        that should be applied to the str format of the parameter to convert it to the required type. Each mandatory parameter (based on the 
        method signature) is required to be present. All parameters (mandatory and optional) are converted (if present) to the appropriate type.
        
        Multi-valued parameters are represented as a list. 
        
        
    **Example of RequestParams to obtain parameters**::
    
        @methodroute(path='/index', params=dict(a=int, b=str, slist=[str])
        def index(self, a, b='', slist=None):
            """
            index will be invoked with a mandatory parameter a of type int, an optional b of type str (defaults to empty string) 
            and an optional slist of type list of strings
            this can be invoked as 
                GET /index?a=10&slist=abc&b=hello&slist=def 
            and index will be called as 
                index(a=10, b='hello', slist=[ 'abc', 'def' ]) 
            """
            pass
        
    NOTE: currently, the restful version (path=None) and mandatory parameters do not work together.  
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
    '''
    A Hook is a convenience plugin to execute a specific function before a request is processed and after the processing is done. An examples of a Hook are
    :py:class:`Tracer` which logs the incoming url and parameters and the related response. The difference with the standard bottle hook is that this hook 
    is provided context such as the url, arguments, the callback method/function and a request context to correlate inbound requests with their corresponding
    responses.
    '''
    request_counter = new_counter() # allows requests and responses to be correlated
    
    def create_request_context(self, callback, url, **kargs):
        return (self.request_counter(), getattr(callback, '_callback_obj', None) or getattr(callback, 'imself', None))
    
    
    def handler(self, before_or_after, request_context, callback, url, result=None, exception=None, **kargs):
        '''
        The default (base) handler for any hook. The default handler does nothing. This behavior can be overridden by
        overriding this method in a subclass or explicitly passing a handler as an argument to the Hook (or subclass) 
        
        :param before_or_after: a string with the words 'before' or 'after' to indicate whether the hook is invoked prior to making the request or on the response
        :param request_context: A means to provide context to allow correlation of before and after calls for the same request. The default
            resource context is described in :py:meth:`create_request_context` and subclasses can override it to change the context behavior
        :param callback: the method/function that is (or just has) handled the callback for the request
        :param url: the full url of the request
        :param result: The result being returned. This will be None if before_or_after is 'before' or if the callback throws an exception
        :param exception: The exception that was thrown. Hook re-raises the same exception after calling the hook handler. This argument is None
            if no exception was thrown
        :param kargs: all the keyword arguments passed to the callback
        '''
        pass
    
    def __init__(self, handler=None):
        '''
        @param handler: a function that should have a signature similar to :py:meth:`handler`. If none, the hook invokes
            self.handler. The handling method may be overridden by overriding it in a subclass or explicitly passing it as an argument        
        '''
        if handler:
            self.handler = handler
               
    def setup(self, app):
        ''' we can install multiple hooks of the same type if we want to check status before and after each plugin '''
        pass

    def apply(self, callback, context):
        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            request_context = self.create_request_context(callback=callback, url=bottle.request.url, **kargs)
            exception = None 
            # ignore return value in before case
            self.handler(before_or_after='before', request_context=request_context, callback=callback, url=bottle.request.url, **kargs)
            try:
                result = callback(*args, **kargs)
            except Exception as e:
                exception = e
                result=None
            finally:
                result = self.handler(before_or_after='after', request_context=request_context, callback=callback, url=bottle.request.url, 
                             result=result, exception=exception, **kargs)
                if exception:
                    raise
            return result
        
        self.plugin_post_apply(callback, wrapper)
        return wrapper
    
class Tracer(Hook):
    '''
    A special hook that traces (i.e. logs) requests and responses. The tracer traces the 
    requests/responses on for calls whose full url matches one of the tracer_paths specified 
    (defaults to match-all). 
    
    Multiple instances of Tracer may be instantiated and will be called in callback plugin order 

    With HTTPServers, Tracer is automatically instantiated if enabled in configuraiton files and can directly be used. 
    It is governed by specific configuration settings (see :py:class:`HTTPServer`)
    '''
    
    def handler(self, before_or_after, request_context, callback, url, result=None, exception=None, **kargs):
        req_count, _ = request_context
        if filter(None, [ regex.match(url) for regex in self.tracer_paths ]) != []:
            if before_or_after == 'before':
                logging.getLogger().debug('Request: %s. url = %s, %s', req_count, url, kargs)
            elif exception:
                logging.getLogger().debug('Response: %s. Exception = %s. [ url = %s, %s ]', req_count, exception, url, kargs)
            else:
                logging.getLogger().debug('Response: %s. Result = %s. [ url = %s, %s ]', req_count, result, url, kargs)
        return result # just return what we got as result so it can be passed on
        
    def __init__(self, tracer_paths=['.*'], handler=None):
        '''
        :param tracer_paths: a list of regular expressions that will be matched with the url. None or empty list indicates match nothing. defaults to match everything. 
        :param handler: if required, a handler that will be invoked to trace the requests/responses
        '''
        if tracer_paths and type(tracer_paths) not in [ list, tuple ]:
            tracer_paths =  [ tracer_paths ]
        self.tracer_paths = map(re.compile, tracer_paths or [])
        super(Tracer, self).__init__(handler=handler)
        
class View(Hook):
    def handler(self, before_or_after, request_context, callback, url, result=None, exception=None, **kargs):
        if before_or_after == 'after' and isinstance(result, (dict, DictMixin)):
            tplvars = self.defaults.copy()
            tplvars.update(result)
            endpoint = callback.im_self
            tpl = os.path.join(endpoint.server.config["_proj_dir"], self.tpl_name)
            result = bottle.template(tpl, result)
        return result
        
    def __init__(self, tpl_name, **defaults):
        '''
        :param tracer_paths: a list of regular expressions that will be matched with the url. None or empty list indicates match nothing. defaults to match everything. 
        :param handler: if required, a handler that will be invoked to trace the requests/responses
        '''
        self.defaults = defaults
        self.tpl_name = tpl_name
        super(View, self).__init__(handler=self.handler)
    
class WrapException(BasePlugin):
    '''
    WrapException is a special purpose plugin to intercept all exceptions on http routes. Beyond basic interception,
    this plugin provides the capabilities to trap and handle the exceptions and also to perform cleanup functions that may have been specified.
    It decorates the request handler, traps any exception thrown by the handler 
    and packages the exception as a message if an exception messager is provided. In the absence of an exception messager,
    it logs and raises the same exception back to the caller.
    
    This plugin relies on parameters passed to each methodroute. It relies on 2 parameters
    
    :param handler: **to be used with @methodroute** a callable (class or function) that will accept the request arguments (multidict), the error string and all other
        arguments passed to the handler and return a iterable that can be passed back to bottle (and hence to the client)  
    :param cleanup_funcs: **to be used with @methodroute** an optional list of functions to be called to process cleanup on failure (e.g. removing the session). Each function is 
        passed the query argument (multidict) dictionary and all the other arguments passed to the handler.
    '''
               
    def __init__(self, default_handler=None):
        '''
        :param default_handler: **to be used with instantiating WrapException** a endpoint wide handler that will be used when no handler has been specified with the @methodroute.
            if this is None, no handler is invoked on exception
        '''
        self.default_handler = default_handler
    
    def setup(self, app):
        ''' Make sure that WrapException is not already installed '''
        for other in app.plugins:
            if isinstance(other, WrapException):
                raise bottle.PluginError("Found another WrapException plugin")

    def apply(self, callback, context):
        
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
                    err_ret = handler(errstr, qstr, exception=err, *args, **kargs)
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
def methodroute(path=None, **kargs):
    '''
    methodroute is a decorator that allows applying a bottle route to a method of a class. It cleanly manages bound instances
    and invokes the method of the correct object.
    
    It supports all capabilities of the bottle_ @route decorator. Some of these capabilities are:
    
    * introspection based route matching based on the method name. If path is None, the method being decorated is 
        introspected to obtain the set of possible routes (in a RESTFUL manner)
    * dynamic ReSTful syntax support with validation of dynamic route components
    * individual skipping or installation of plugins at a route level (though this is typically done at a server level in our framework)
    * specifying method such as GET, POST, ANY, PUT, HEAD
    
    Additionally, through the use of custom plugins, it provides rich 
    capabilities (some of which include)
    
    * GET/POST/ANY parameter validation and providing those as arguments to the method (:py:class:`RequestParams`)
    * custom exception handing and cleanup functions executed on exceptions (for example, deletion of session etc) 
        using (:py:class:`WrapException`)
    * Tracing of routes through logging on calls and responses (:py:class:`Tracer`)
    * Statistics of time taken for each route.  (:py:class:`Stats`)

    methodroute (similar to bottle_ @route) takes additional parameters that control the application (or skipping of) plugins
    or control the behavior of plugins. These are either processed by the route or are passed to the plugins as context. 
    Some of the common ones include:
    
    :param list skip_by_type: the *skip* parameter takes plugin instances to skip. *skip_by_type* skips plugins of a specific type
    :param dict params: see description at (:py:class:`RequestParams`)
    :param handler: see description at (:py:class:`WrapException`)
    :param list cleanup_funcs: see description at (:py:class:`WrapException`)
    
    **A few examples of methodroute**::
    
        @methodroute()
        def hello(self, name):
            """ matches /hello/anand. name is a mandatory route component """
            return 'hello ' + name
            
        @methodroute()
        def hello(self, name=None):
            """ matches /hello or /hello/anand. name is a optional route component """
            name = name or 'there'
            return 'hello ' + name
            
        @methodroute(path="/hello")
        def foo(self):
            """ matches /hello. The fu
            return '/hello'
            
        @methodroute(self, path='/hello', method='GET', params=dict(name=str, lastname=str))
        def foo(self, name, lastname=None):
            """ matches /hello?name=anand and /hello?name=anand&lastname=shah. lastname is an optional parameter """
    '''
  
    def decorator(f):
        f._methodroute = path
        f._route_kargs = kargs
        f._signature = inspect.getargspec(f)
        return f
#    return decorator if type(route) in [ type(None), str ] else decorator(route)
    return decorator
    
class HTTPServerEndPoint(EndPoint):
    '''
    The base class of serving HTTP requests. An HTTP Server may have one or more such endpoints (at least one required for any activity to happen). 
    A typical usage scenario is to subclass from HTTPServerEndPoint and define a few methods decorated with :py:func:`methodroute` decorator. This converts
    the methods to callback handlers when the route (specified implicitly or explicitly as per methodroute) is received by the server. 
    
    The server may have set up additional plugins (e.g. :py:class:`RequestParams`) to be activate on this endpoint. These provide additional convenience or
    capability to the endpoint (such as parameter processing, tracing, profiling statistics, etc).    
    '''
    
    # class attributes
    _name_prefix = 'HTTPServer_'
    lock = RLock()
    http_server_end_points = {} # class attribute. Accessed in thread safe manner
    _counter = new_counter(0)    # class attribute common to all subclasses of HTTPServerEndPoint
    
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
                self._endpoint_app.route(path=path, callback=callback, **route_kargs)
                    
                
    def __init__(self, name=None, mountpoint='/', plugins=None, server=None, activate=False):
        '''
        :param str name: a name for the endpoint
        :param str mountpoint: the prefix for all routes within this endpoint
        :param list plugins: plugins are applied to every HTTP request (except if the :py:func:`methodroute`  
            skips them. plugins are applied in reverse order (i.e.
            the 1st one is the outermost, the last one in the list is the innermost. Note, the :py:class:`HTTPServer` or
            :py:class:`ManagedServer` (or other servers) may apply plugins automatically  
        :param server: a reference to the server that contains this endpoint. This is typically passed in :py:meth:`activate` but would 
            be required here if activate is True
        :param bool activate: whether to activate this endpoint on creation or later through an explicit 
            :py:meth:`activate` call
        '''
        super(HTTPServerEndPoint, self).__init__(server=server)
        self.name = name = name or self._name_prefix + str(HTTPServerEndPoint._counter())
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
        '''
        activate an endpoint. This is typically invoked in start_server and it sets up the endpoint to start reciveing requests
        when the main server is started.
        
        :param server: A reference to the server to which this endpoint belongs to
        :param str mount_prefix: The server's mount_prefix. In effect, the url that this endpoint will honor is
            mount_prefix + mountpoint + individual route paths
        '''
        
        if self.activated:
            return

        self.mount_prefix = mount_prefix or self.mount_prefix
        self.server = server or self.server
        
        mountpoint = self.mount_prefix + self.mountpoint
        if mountpoint != '/':
            self._endpoint_app = bottle.Bottle()
            bottle.default_app().mount(mountpoint, self._endpoint_app)
        else:
            self._endpoint_app = bottle.default_app()
        
        # apply all plugins
        self.std_plugins = self.server.get_standard_plugins(self.plugins)
        self.plugins = self.std_plugins + self.plugins
        [ self._endpoint_app.install(plugin) for plugin in self.plugins ]

        self.routeapp() # establish any routes that have been setup by the @methodroute decorator
        self.activated = True

    
    def abort(self, code, text):
        '''
        Aborts the request that is being handled.
        
        :param int code: An HTTP error code
        :param str text: An error message that is sent back to the client
        '''
        bottle.abort(code, text)
        
    @property
    def request(self):
        '''
        returns a request object. (refer bottle_)
        '''
        return bottle.request

    @property
    def request_params(self):
        '''
        returns a MultiDict object having the GET or POST arguments. (refer bottle_)
        '''
        return bottle.request.POST if bottle.request.method == 'POST' or bottle.request.method == 'ANY' and len(bottle.request.POST.keys()) else bottle.request.GET
    
    @property
    def request_params_as_dict(self):
        '''
        returns request params as a dict instead of multidict. Multi-valued items will be returned as a list
        '''
        params = self.request_params
        d = {}
        for k in params.keys():
            d[k] = params.getall(k)
            if len(d[k]) == 1:
                d[k] = d[k][0] # drop the list of single valued params
        return d
    
    @property
    def session(self):
        '''
        returns a session related to this request if one is configured. Else, returns None
        '''
         
        try:
            return self.environ.get(self.server.config['Session']['session.key'])
        except KeyError:
            return self.environ.get('beaker.session', None)
        except AttributeError:
            return None
    
    @property
    def response(self):
        '''
        returns a reference to the response object. (refer bottle_)
        '''
        return bottle.response
    
    @property
    def environ(self):
        '''
        returns a reference to the WSGI environment object. (refer bottle_)
        '''
        return bottle.request.environ
    
    @property
    def cookies(self):
        ''' 
        returns a dict of cookies that were obtained as part of this request. (refer bottle_)
        '''
        return bottle.request.COOKIES
    
    @property
    def host(self):
        '''
        returns the scheme :// actual-host of the request. Note - this returns the host that was part of the original  
        query from the client (before load balancing and proxy manipulation if any)
        If you get confusing results, ensure X-Forwarded-Hosts is set properly
        '''
        scheme, host, _, _, _ = bottle.request.urlparts
        return '://'.join([scheme, host])  
        
    @property
    def server_name(self):
        '''
        returns the scheme :// original host of the request. 
        If you get confusing results, ensure X-Forwarded-Hosts
        is set properly
        '''
        scheme = bottle.request.urlparts()[0] 
        return '://'.join([scheme, self.environ['SERVER_NAME']])
    
    def selected_cookies(self, keys=None):
        '''
        returns a dict of selected cookies that match keys. keys can be a string, a regular expression, a list of strings or regular expressions
        if keys is None, returns all cookies
        
        :param keys: (default None which implies all cookies). A string/re or a list of string/re to match the cookie keys
        '''
        if not keys: keys = [ '.*' ] # match all
        if not hasattr(keys, '__iter__'): keys = [ keys ] # make a list if one does not exist
        return dict([ (ck, cv) for k in keys for (ck, cv) in self.cookies.iteritems() if re.match(k, ck, flags=re.IGNORECASE)])
