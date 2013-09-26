'''
********************
Multiple Endpoints
********************

This example demonstrates an HTTP Server with multiple endpoints

An endpoint to handle HTTP requests
===================================

A server needs a :py:class:`HTTPServerEndPoint` to be able to serve HTTP requests. We
first define our endpoint::

    from boot.endpoints.http_ep import HTTPServerEndPoint, methodroute 
    
    class EP(HTTPServerEndPoint):

        @methodroute(path='/')
        def hello(self):
            return 'hello world'

Another endpoint to handle admin requests
===================================

Let's add another endpoint which will be mounted on '/admin'::

    class AdminEP(HTTPServerEndPoint):
        
        @methodroute(path='/health')
        def health_check(self):
            return 'server healthy'

A simple server for our endpoint
================================

Let's create our server and associte 2 endpoints with it. AdminEP will be mounted on /admin implying all requests to /admin/health will be routed to it::

    from boots.servers.httpserver import HTTPServer

    application = HTTPServer(endpoints=[EP(), AdminEP(mountpoint='/admin')])


Running our server
^^^^^^^^^^^^^^^^^^

Run the server as::

    $ python helloworld.py

Now invoke http://localhost:9999 from your browser and you should see::

    hello world
    
invoke http://localhost:9999/admin/health from your browser and you should see:

    server healthy
    
'''

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute    

    
class EP(HTTPServerEndPoint):
    '''
    An http server endpoint is a logical collection of related routes. It is a object so multiple calls to this endpoint will share any 
    state saved in the object. 
    
    In this case, this endpoint has just one route /
    '''

    @methodroute(path='/')
    def hello(self):
        ''' 
        @methodroute marks this method as an http route handler which matches /hello
        '''
        return 'hello world'
    
class AdminEP(HTTPServerEndPoint):
    
    @methodroute(path='/health')
    def health_check(self):
        return 'server healthy'

# associating 2 endpoints. One is mounted on '/' and the other is on '/admin'.
application = HTTPServer(endpoints=[EP(), AdminEP(mountpoint='/admin')])

if __name__ == '__main__':
    application.start_server(defhost='localhost', defport=9999, standalone=True, description="Multiple endpoints")
