'''
********************
The Simplest Program
********************

This example demonstrates the basic usage of a server and http endpoint components of the boots framework.

* Servers are entities that provide specific functionality and capability
* Servers consist of one or more endpoints (source or destinations of communication).

In this example, we demonstrate a simple http server that handles one request (/hello) and returns the string 'hello world'.

An endpoint to handle HTTP requests
===================================

A server needs a :py:class:`HTTPServerEndPoint` to be able to serve HTTP requests. We
first define our endpoint::

    from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute

    class EP(HTTPServerEndPoint):

        @methodroute(path='/')
        def hello(self):
            return 'hello world'


:py:class:`EP` defines a class whose objects will serve as HTTP endpoints. In other words, specific marked methods of EP will be invoked when
HTTP requests are made to this server.

:py:func:`methodroute` serves as a way to mark the methods it decorates to be handlers of HTTP requests. In our example,
*hello* is a method that will handle requests with the path **/**. Any time */* is invoked on this server, the response
will be 'hello world'

A simple server for our endpoint
================================

Endpoints are interfaces of servers. So, let's create a simple server to which we can associate our :py:class:`EP` endpoint::

    from boots.servers.httpserver import HTTPServer

    application = HTTPServer(endpoints=[EP()])

We've create *application* which has one endpoint :py:class:`EP`.

Starting our server
===================

Now that we have a server, let us start the server::

    if __name__ == "__main__":
        application.start_server(standalone=True, description='A hello world server for the boots framework')

Here, *standalone* indicates that this server is not being invoked from another WSGI container (such as mod_wsgi in apache) and that it should bind to the appropriate host and port.
The default host is *127.0.0.1* and the default port is *8080*. If you wish to specify other host/ports, you can change the code to::

    if __name__ == "__main__":
        application.start_server(standalone=True, description='A hello world server for the boots framework', defhost='localhost', defport=9999)

That's it. Now we are ready to run it.

Running our server
^^^^^^^^^^^^^^^^^^

Run the server as::

    $ python helloworld.py

Now invoke http://localhost:9999 from your browser and you should see::

    hello world
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

# associate the endpoint with a server. If this is invoked from apache with mod_wsgi, application is the typical endpoint
application = HTTPServer(endpoints=[EP()])

if __name__ == '__main__':
    application.start_server(defhost='localhost', defport=9999, standalone=True, description="A hello world server for the boots framework")
