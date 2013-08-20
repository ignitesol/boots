============
Plugins
============


RequestParams: handling request parameters
-------------------------------------------
RequestParams is available implicitly with HTTPServer and it uses 'params' from @methodroute to get parameters.
@methodroute decorator leverages this plugin to get request parameters. 
A data type constraint can be imposed upon request parameters.

*val=bool* evaluates to True for any non empty value and False otherwise.
::

    @methodroute(path="/params", params=dict(name=str, val=bool))
    def params(self, name, val):
        print name, val

Another simple example:       
::

    @methodroute(path="/add", params=dict(a=int, b=int))
    def add(self, a, b):
        print a+b


WrapException: Generic exception handling
-------------------------------------------
WrapException is a special purpose plugin to intercept all exceptions on http routes.
A default handler to this plugin will service all exceptions unless we specify another handler in @methodroute.
It can be specified as folllows:

::

	ep1 = EP(plugins=[ WrapException(default_handler=simple_exception_handler)] )
	
A more specific handler can be specified in the methodroute. This will handle all exceptions in that route.

::
	
	@methodroute(path='/bad2', params=dict(a=int), handler=another_handler)
	

Hook
------
Hook lets you implement filters. 
A specific function can be executed pre and post to request processing. 

The behavior of a hook can be specified by overriding it's default handler or specifying a handler parameter. 
If no handler parameter is specified, Hook invokes *self.handler*.
The following hook has a pre request processing handler. 
 
::

	class my_hook(Hook):
	    
	    def handler(self, before_or_after, request_context, callback, url, **kargs):
	        print before_or_after, url
	        if before_or_after == "before":
	            print "Before request processing: " + str(val)

	
	
Other Plugins
--------------

* CrossOriginPlugin
	This plugin enables cross domain resource sharing. 


* ConditionalAccess
    ConditionalAccess plugin validates to check if certain conditions are met before request processing.  
    If the conditions are not met, it returns an error.

	