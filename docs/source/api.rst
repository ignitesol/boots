.. highlight:: python

.. _bottle: http://bottlepy.org

==========================
API Reference
==========================
	
This is an auto-generated API Reference documentation. If you are new to :doc:`fabric <intro>` you might want to read the :doc:`intro`

.. _Servers:

Servers
=======

Endpoints
=========
.. automodule:: fabric.endpoints.endpoint

.. autoclass:: EndPoint
.. autoclass:: EndPointException

HTTP Server End Points
-----------------------
.. automodule:: fabric.endpoints.http_ep

.. autoclass:: HTTPServerEndPoint
	:members: activate, request, request_params, environ, response, abort

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
