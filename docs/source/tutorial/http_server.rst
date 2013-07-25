Showcasing HTTPServer
======================
This tutorial will demonstrate various HTTPServer capabilities:

Endpoints
^^^^^^^^^^
A typical scenario to create an HTTP Server is to define a subclass of the HTTPServerEndPoint and to define routes using the 
:py:func:`methodroute` decorator.
Refer :doc:`../http_server/methodroute` and :doc:`../server/add_ep` for further information.
 
	
	

RequestParams
^^^^^^^^^^^^^
RequestParams is available implicitly with HTTPServer and it uses 'params' from @methodroute to get parameters.
We can specify request parameters and their data types in @methodroute.

In the following example, *val=bool* evaluates to True for any non empty value and False otherwise.

::

	from boots.servers.httpserver import HTTPServer
	from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute
	
	class EP(HTTPServerEndPoint):
	    
	    @methodroute(path="/params", params=dict(name=str, val=bool))
	    def params(self, name, val):
	        print name, val





The data type constraints are specified in *@methodroute* decorator.
The following is a simple example for constraining request parameters to be an integer.
::
 
    @methodroute(path="/add", params=dict(a=int, b=int))
    def add(self, a, b):
        print a+b	         
	        

RequestParams is available as a default plugin. 
To print the default plugins available:
::
	
        def get_standard_plugins(self, plugins):
            par_plugins = super(MyServer, self).get_standard_plugins(plugins)
            print par_plugins
            


Session And Cache
^^^^^^^^^^^^^^^^^^


While instantiating a server, *session=True* starts a session and *cache=True* enables caching.
Session depends on it's configuration in the associated configuration file.
It is mandatory to mention a session key in the configuration file for a session to start. 
::

	main_server = HTTPServer(endpoints=[ep1], session=True, cache=True, logger=True)        



Decorator *self.server.cache.cache()* is used to specify caching of variables for a particular method as shown below.
For example, when /hello/Alex is invoked for the first time, *capitalize* is called. For any subsequent calls, it's cached result is used.

In the same example, we are using *session* to get count of times a route is called on that particular session.  	    

::
	       
    @methodroute()
    def hello(self, name=None):

        @self.server.cache.cache()
        def capitalize(name):
            print 'capitalize called. should now be cached for', name
            return name.capitalize()
        
        name = name or self.session.get('name', None) or 'world'  # the name is passed as an argument or obtained from the session
        self.session['name'] = name
        self.session['count'] = self.session.get('count', 0) + 1

        return 'hello %s - you have called me %d times' % (capitalize(name), self.session['count'])
    
       


Exceptions
^^^^^^^^^^

We need to import WrapException from *http_ep*.

::

	from boots.servers.httpserver import HTTPServer
	from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, WrapException



Provide WrapException plugin to the endpoint. This will handle exceptions for all routes through this endpoint. 
A default handler to this will service all exceptions unless we specify another handler in @methodroute.
	
::
	   
	   ep1 = EP(plugins=[ WrapException(default_handler=simple_exception_handler)] )


Writing handlers is simple. 
::
	
	#Exception handlers 
	def another_handler(errstr, *args, **kargs):
	    return 'Another error handler %s' % (errstr)
	
	def simple_exception_handler(errstr, qstr, *args, **kargs):
	    return "Exception %s: %s %s %s" % (errstr, qstr, args, kargs)
	    

If a handler in not specified, the default handler handles exceptions for it.
The default handler *simple_exception_handler* handles exceptions for */bad*.
Since a handler is specified for */bad2*, this will service the exceptions for it.	    
::

	class EP(HTTPServerEndPoint):

	    @methodroute(path='/bad', params=dict(a=int))
	    def bad(self, a=0):
	        1/0 # force an exception
	        return 'if we get this string, it will be unusual'

	    @methodroute(path='/bad2', params=dict(a=int), handler=another_handler)
	    def bad2(self, a=0):
	        1/0 # force an exception
	        return 'if we get this string, it will be unusual'
	

	
	   	    