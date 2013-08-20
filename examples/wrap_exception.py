'''
This example demonstrates exception handling in http routes.
For this we use WrapException plugin.
A default exception handler can be provided to handle exceptions for all routes through an endpoint.  
'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, WrapException

#Exception handlers 
def another_handler(errstr, *args, **kargs):
    return 'Another error handler %s' % (errstr)

def simple_exception_handler(errstr, qstr, *args, **kargs):
    return "Exception %s: %s %s %s" % (errstr, qstr, args, kargs)
    
class EP(HTTPServerEndPoint):
    
#If a handler in not specified, the default handler handles exceptions for it.
    @methodroute(path='/bad', params=dict(a=int))
    def bad(self, a=0):
        1/0 # force an exception
        return 'if we get this string, it will be unusual'

#Since a handler is specified in @methodroute, this will service the exceptions for it.
    @methodroute(path='/bad2', params=dict(a=int), handler=another_handler)
    def bad2(self, a=0):
        1/0 # force an exception
        return 'if we get this string, it will be unusual'

#Provide WrapException plugin to the endpoint. This will handle exceptions for all routes through this endpoint. 
#A default handler to this will service all exceptions unless we specify another handler in @methodroute.
ep1 = EP(plugins=[ WrapException(default_handler=simple_exception_handler)] )
main_server = HTTPServer(endpoints=[ep1])

if __name__ == "__main__":
    main_server.start_server(standalone=True, description="Using request params", defhost="localhost", defport=8081)