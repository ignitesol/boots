.. _bottle: http://bottlepy.org

==========================
API Reference
==========================
	
This is an auto-generated API Reference documentation. If you are new to :doc:`fabric <intro>` you might want to read the :doc:`intro`

.. _Servers:

Servers
=======
.. automodule:: fabric.servers.server

.. autoclass:: Server
	:members: 
	
HTTPServer
----------
.. automodule:: fabric.servers.httpserver

.. autoclass:: HTTPServer
	:members: 


ManangedServer
---------------
.. automodule:: fabric.servers.managedserver

.. autoclass:: ManagedServer
	:members: 
	
.. autoclass:: ManagedEP
	:members:

Endpoints
=========
.. automodule:: fabric.endpoints.endpoint

.. autoclass:: EndPoint
.. autoclass:: EndPointException

HTTP Server End Points
-----------------------
.. automodule:: fabric.endpoints.http_ep

.. autoclass:: HTTPServerEndPoint
	:members: activate, request, request_params, environ, response, abort, session

Route Decorator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: methodroute(path=None, skip_by_type=None, plugins=None, params=None, handler=None, cleanup_funcs=None, **kargs)

Handy Plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: BasePlugin
	:members:
	
.. autoclass:: RequestParams

.. autoclass:: WrapException

.. autoclass:: Hook
	:members: handler
	
.. autoclass:: Tracer

HTTP Client End Points
-----------------------
.. automodule:: fabric.endpoints.httpclient_ep

.. autoclass:: HTTPClient
	:members:

.. autoclass:: HTTPAsyncClient

.. autoclass:: Header

.. autoclass:: HTTPUtils
	:members:

Related Classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: Header

.. autoclass:: Response
	:members:

Decorators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These decorators may be composed. 

.. autofunction:: dejsonify_response

.. autofunction:: jsonify_request
