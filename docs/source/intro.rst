==============
Concepts
==============

Boots introduces two core concepts. Servers are logically independent entities that provide specific capabilities in the distributed system. Servers may have one or more 
endpoints that provide a termination (port) of inbound, outbound or peer-to-peer communication.

Servers
=======

Boots provides following servers:

:doc:`server/server`:
Provides basic abstractions for servers

:doc:`http_server/http_server`: A container for web servers

:doc:`zmq_server/zmq_server`: A container for messaging servers

:doc:`managed_server/managed_server`: Builds on :doc:`http_server/http_server` to provide management capabilities for servers

EndPoints
=========

Endpoints allow servers to communicate (or receive communications) from the outside world. In practical terms, endpoints are port-holes through which messages can flow into our out of a server. With multiple servers communicating through endpoints, a distribute system can be configured and clients can obtain services.

Some typical endpoints are:

* :doc:`http_server/http_ep`: Endpoint for serving http requests. 

* :doc:`http_server/httpclient_ep`: Endpoint for making sync, async http requests.

* zmq_endpoint: for zmq based message queueing (send and receive) services


