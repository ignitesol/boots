==============
Introduction
==============

Boots is a framework for simplifying the development of high volume, highly scalable distributed systems. The framework is an extensible set of abstractions for
developing servers that serve, consume or participate in unicast or multicast network communications. Boots makes it easy to create uniform ways to configure, adminster, 
debug and compose servers.


Concepts
=========

Boots introduces two core concepts. Servers are logically independent entities that provide specific capabilities in the distributed system. Servers may have one or more 
endpoints that provide a termination (port) of inbound, outbound or peer-to-peer communication.

Boots provides following servers:

:doc:`server`

:doc:`http_server`

:doc:`mngd_server`

:doc:`zmq_server`