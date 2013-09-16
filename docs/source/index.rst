.. Boots: Distributed Systems Framework documentation master file, created by
   sphinx-quickstart on Wed Apr 11 07:44:10 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Boots: Distributed Systems Framework's documentation!
=================================================================

Boots is a framework for simplifying the development of high volume, highly scalable managed distributed systems. Boots provides a set of building blocks that are wired together in an easy (and extensible) manner to build robust systems that serve, consume or participate in unicast or multicast network communications. Boots makes it easy to create uniform ways to configure, adminster, debug and compose servers.

* In the simplest cases, boots makes it easy to build web servers with configuration, logging, session, caching and error handling. 

* You can quickly increase the capabilities to include authentication and invoking HTTP services (from other servers) synchronously or asynchronously.

* Build on this even further to create Managed Servers that will provide load balancing, clustering, health monitoring and run time reconfiguration.

* Alternately, or in addition, support high volume, high efficiency multicast communication through boots' abstractions for message queueing. Add database persistence through boots' abstractions for databases.

* Build on these capabilities or add your own to support a managed infrastructure on which application logic can be built.


Contents:

.. toctree::
   :maxdepth: 1
   
   installation
   intro
   tutorial
   server/server
   http_server/http_server
   zmq_server/zmq_server
   managed_server/managed_server
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

