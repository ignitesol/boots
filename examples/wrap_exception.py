'''
***************************************
Handling Exceptions from HTTP Requests 
***************************************

boots provides a way to capture any exception generated as part of a request and the handle it gracefully with an appropriate return code to the caller.

By default, boots will handle exceptions and return an appropriate error code and message just by turning on handle_exception in the start_server::

    main_server = HTTPServer(endpoints=[ep1], handle_exception=True)

In case more specific exception handling is required, boots provides ways to override this default behavior and even have specific exception handlers per request.

First, import  WrapException::
    
    from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, WrapException

Define your exception handlers::
    
    def another_handler(errstr, *args, **kargs):
        return 'Another error handler %s' % (errstr)

    def simple_exception_handler(errstr, qstr, *args, **kargs):
        return "Exception %s: %s %s %s" % (errstr, qstr, args, kargs)

Setup the endpoint to have a WrapException plugin. Optionally provide a default_handler to the WrapException plugin - this will be called when any route in this endpoint raises an exception::

    ep1 = EP(plugins=[ WrapException(default_handler=simple_exception_handler)] )
    main_server = HTTPServer(endpoints=[ep1])

If required, override the default_handler for specific routes::

    @methodroute(path='/bad2', params=dict(a=int), handler=another_handler)
    def bad2(self, a=0):
        1/0 # force an exception
        return 'if we get this string, it will be unusual'


'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, WrapException

# Exception handlers 
def another_handler(errstr, *args, **kargs):
    return 'Another error handler %s' % (errstr)

def simple_exception_handler(errstr, qstr, *args, **kargs):
    return "Exception %s: %s %s %s" % (errstr, qstr, args, kargs)
    
class EP(HTTPServerEndPoint):
    
    # If a handler in not specified, the default handler (in this case simple_exception_handler) handles exceptions for it.
    @methodroute(path='/bad', params=dict(a=int))
    def bad(self, a=0):
        1/0 # force an exception
        return 'if we get this string, it will be unusual'

    # Since a handler is specified in @methodroute, this will service the exceptions for it.
    @methodroute(path='/bad2', params=dict(a=int), handler=another_handler)
    def bad2(self, a=0):
        1/0 # force an exception
        return 'if we get this string, it will be unusual'

# Provide WrapException plugin to the endpoint. This will handle exceptions for all routes through this endpoint. 
# A default handler to this will service all exceptions unless we specify another handler in @methodroute.
ep1 = EP(plugins=[ WrapException(default_handler=simple_exception_handler)] )
main_server = HTTPServer(endpoints=[ep1])

if __name__ == "__main__":
    main_server.start_server(standalone=True, description="Handling Exceptions", defhost="localhost", defport=9999)