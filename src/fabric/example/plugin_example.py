'''
this is an example of the basic usage of the server and http endpoint components of the fabric framework
* Servers are entities that provide specific functionality and capability
* Servers consist of endpoints (source or destinations of communication) and optionally subservers
* this way, the main server is an arbitrary nesting of servers. Each server consist of one or more endpoints

In this example, we demonstrate a wrap exception plugin server with one endpoint

MainServer is our class that represents the main server. 
    The MainServer has 1 endpoint instances that serves two routes
    /bad which raises an exception handled by an endpoint wide handler
    /bad2 which raises an exception handled by a specific handler

Created on Mar 18, 2012

@author: AShah
'''
from fabric import concurrency

if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
elif concurrency == 'threading':
    pass

from fabric.servers.httpserver import HTTPServer
from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute,\
    RequestParams, WrapException

    
def another_handler(errstr, *args, **kargs):
    return 'Another error handler %s' % (errstr)
    
class EP(HTTPServerEndPoint):
    
    @methodroute(path='/bad', params=dict(a=int))
    def bad(self, a=0):
        1/0 # force an exception
        return 'if we get this string, it will be unusual'

    @methodroute(path='/bad2', params=dict(a=int), handler=another_handler)
    def bad2(self, a=0):
        1/0 # force an exception
        return 'if we get this string, it will be unusual'


def simple_exception_handler(errstr, qstr, *args, **kargs):
    return "Exception %s: %s %s %s" % (errstr, qstr, args, kargs)

# create an endpoint
ep1 = EP(plugins=[ WrapException(default_handler=simple_exception_handler), RequestParams() ] )
# associate the endpoint with a server
main_server = HTTPServer(endpoints=[ep1])

if __name__ == "__main__":
    main_server.start_server(file=__file__, defport=9999, description="A test server for the fabric framework")