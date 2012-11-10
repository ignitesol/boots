'''
this is an example of the basic usage of the server and http endpoint components of the fabric framework
* Servers are entities that provide specific functionality and capability
* Servers consist of endpoints (source or destinations of communication) and optionally subservers
* this way, the main server is an arbitrary nesting of servers. Each server consist of one or more endpoints

In this example, we demonstrate a simple server with one endpoint

MainServer is our class that represents the main server. 
    The MainServer has 1 endpoint instances that serves two routes 
    /hello which takes an optional restful paramters (i.e. /hello and /hello/anand
    /getter showing how to use the RequestParam plugin to obtain get arguments
    /poster showing how to use the RequestParam plugin to obtain post arguments 
    /any showing how to use a single route to support get or post

Created on Mar 18, 2012

@author: AShah
'''
import sys
import os
try:
    import fabric
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Since fabric is not as yet installed into the site-packages

from fabric import concurrency
from fabric.servers.managedserver import ManagedServer
import time

if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
elif concurrency == 'threading':
    pass

from fabric.servers.httpserver import HTTPServer
from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute    
def another_handler(errstr):
    return 'Another error handler %s' % (errstr)
    
class EP(HTTPServerEndPoint):
    
    # methodroute automatically creates a route based on the name of the method
    # arguments to the method make it RESTful
    # keyword parameters with default values make optional RESTful parameters
    @methodroute()
    def hello(self, name=None):
        time.sleep(1)
        return 'hello %s' % (name,) if name else 'hello'

    # params is a dict to describe parameters in the request (get or post) and their types
    # currently, without path, methodroute gets confused between RESTful parameters and
    # mandatory request parameters (however, defaulted parameters are ok - see poster)
    # slist demonstrates how multi valued parameters can be obtained as a list 
    # invoke as
    #    http://localhost:9999/getter?a=10&s=hello&slist=1&slist=abc
    @methodroute(path='/getter', params=dict(a=int, s=str, slist=[str]))
    def getter(self, a, s, slist):
        return 'gotter: a = %d, type(a) = %s, s = %s, type(s) = %s, slist = %s, type(slist) = %s' % (a, type(a).__name__, s, type(s).__name__, slist, type(slist).__name__)
    
    # poster shows how RESTful and passed parameters can coexist
    # invoke as 
    #    curl -d a=10&s=hello&slist=1&slist=abc http://localhost:9999/poster/wow
    # and other variations of the url
    @methodroute(params=dict(a=int, s=str, slist=[str]), method='POST')
    def poster(self, restful_param, a=0, s='default-param', slist=None):
        return 'called poster/%s: a = %d, type(a) = %s, s = %s, type(s) = %s, slist = %s, type(slist) = %s' % (restful_param, a, type(a).__name__, s, type(s).__name__, slist, type(slist).__name__)

    # any is list poster except it works with get or post
    @methodroute(params=dict(a=int, s=str, slist=[str]), method='ANY')
    def any(self, restful_param, a=0, s='default-param', slist=None):
        return 'called any/%s: a = %d, type(a) = %s, s = %s, type(s) = %s, slist = %s, type(slist) = %s' % (restful_param, a, type(a).__name__, s, type(s).__name__, slist, type(slist).__name__)
    
# create an endpoint
ep1 = EP()
# associate the endpoint with a server
standalone = __name__ == '__main__'
main_server = ManagedServer(mount_prefix="/testing", endpoints=[ep1], logger=True)
main_server.start_server(defport=9999, standalone=standalone, description="A test server for the fabric framework")
application = main_server
