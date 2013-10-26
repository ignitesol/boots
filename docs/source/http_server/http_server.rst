===========
HTTPServer 
===========

.. automodule:: boots.servers.httpserver

Instantiating Servers
=====================
When instantiating :py:class:`HTTPServer`, in addition to arguments expected by :py:class:`HTTPBaseServer` and :py:class:`Server`, a few additional arguments are worth mentioning

* *session*: boolean or a list of strings that indicates whether one or more sessions should be instantiated. The strings indicate the names of the config sections that will be used to instantiate sessions. Sessions are accessible from within endpoints using *get_session*
* *cache*: boolean or a list of strings that indicates whether the one or more cache regions should be instantiated. The strings indicate the names of the config sections that will be used to instantiate caches. A special key *cache_name* in the config will be used to create an attribute in the server object. Caches may be accessed by using *self.<cache_key>*
* *auth*: controls whether authentication based on configuration ini should be instantiated. Can be False (no auth) or True (using BootsAuth from the config file) or it can be a list of config sections that will be auth related (allowing multiple auth layers). Note, the last entry in the configuration file will challenge the user the 1st (i.e. it is the outermost auth layer)
* *handle_exception*: A boolean that indicated that the default exception wrapper should be set up for all endpoints or routes where no exception handler is already set up. 

Standard Plugins
================

Plugins mediate requests and responses. An example plugin may be a Tracer plugin - it traces all parameters, response codes and response values to every route that it is attached to. Multiple plugins may be attached to an endpoint or even a route. :py:class:`HTTPServer` provides a means to define standard plugins that may be associated with all endpoints of the server. Of course, an individual endpoint can add more plugins. An individual route can add or skip specific plugins. You can override standard plugins by overriding the :py:method:`HTTPServer.get_standard_plugins` method.

:py:class:`HTTPServer` instantiates the following plugins as standard plugins

* :py:class:`RequestParams`: Parameter processing with type checking, conversion, multi-value parameters,
* :py:class:`WrapException`: The default exception handler. This is enabled if *handle_exception* is passed as a true value when instantiating the server object. Moreover, if a specific exception handler has been added by the endpoint, this generic excaption handler is ignored 
* :py:class:Tracer`: A convenience plugin to log all requests that match a pattern (and their parameters) as well as the responses. 

Command Line Arguments
======================

:py:class:`HTTPBaseServer` accepts three default command line arguments that are processed if the server is started in *standalone* mode.

* --host: the host that the server will bind to
* --port: the port that the server will listen to
* --debug: should the server turn on the debug flag provided by bottle_

Using GEvent
============

For highly concurrent applications, gevent provides a microthreading library. Boots can easily utilize gevent. To use gevent instead of another python middleware, make sure you do the following as the first line in your primary python file::
	
	from boots.use_gevent

   http_ep
   methodroute
   auth

