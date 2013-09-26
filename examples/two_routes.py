'''
*************************
Two Routes In An Endpoint
*************************

Now that we have our basic server running, let's quickly add more routes to the endpoint.
A :py:class:`HTTPServerEndPoint` is a logical collection of routes. We'll come to why this is interesting.

In this example, we are going to show a few concepts:
* Multiple routes in an endpoint
* Endpoints are objects (so we can keep state in them)

Changing our endpoint
=====================

We are adding multiple methods with the decorator @methodroute. Each method becomes a route within that endpoint::

    from boot.endpoints.http_ep import HTTPServerEndPoint, methodroute 
    
    class EP(HTTPServerEndPoint):

        def __init__(self, *args, **kargs):
            self.total_requests = 0
            super(EP, self).__init__(*args, **kargs)

        @methodroute(path='/hello')
        def hello(self):
            self.total_requests += 1
            return 'Hello World. Total requests %s' % self.total_requests

        @methodroute(path='/bye')
        def bye(self):
            self.total_requests += 1
            return 'Goodbye. Total requests %s' % self.total_requests


Couple of things to observe. 
* *hello* and *bye* are routes that serve **/hello** and **/bye** respectively
* We have initialized some state for our endpoint in the *__init__*
* We keep a count of the total number of requests made. *Note:* This is not the same as session since session is unique per client. Also, *note*, this is purely to illustrate a point. This *may* run into thread race conditions in the face of multiple concurrent requests and will not work at all if multiple clustered servers are serving these endpoints.

'''

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute    

    
class EP(HTTPServerEndPoint):

    def __init__(self, *args, **kargs):
        self.total_requests = 0
        super(EP, self).__init__(*args, **kargs)

    @methodroute(path='/hello')
    def hello(self):
        self.total_requests += 1
        return 'Hello World. Total requests %s' % self.total_requests

    @methodroute(path='/bye')
    def bye(self):
        self.total_requests += 1
        return 'Goodbye. Total requests %s' % self.total_requests

# associate the endpoint with a server. If this is invoked from apache with mod_wsgi, application is the typical endpoint
application = HTTPServer(endpoints=[EP()])

if __name__ == '__main__':
    application.start_server(defhost='localhost', defport=9999, standalone=True, description="Two routes example")
