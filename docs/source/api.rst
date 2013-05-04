.. _bottle: http://bottlepy.org

==========================
API Reference
==========================
	
This is an auto-generated API Reference documentation. If you are new to :doc:`boots <intro>` you might want to read the :doc:`intro`

.. _Servers:



.. toctree::
   :maxdepth: 3
   
   servers
   


Endpoints
=========
.. automodule:: boots.endpoints.endpoint

.. autoclass:: EndPoint
.. autoclass:: EndPointException

HTTP Server End Points
-----------------------
.. automodule:: boots.endpoints.http_ep

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

ZMQ Server End Points
-----------------------
.. automodule:: boots.endpoints.zmqendpoints.zmq_base

.. autoclass:: ZMQBaseEndPoint
	:members:
	
.. autoclass:: ZMQEndPoint
	:members:

.. autoclass:: ZMQListenEndPoint
	:members:

Handy Plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: ZMQBasePlugin
    :members: 
    
.. automodule:: boots.endpoints.zmqendpoints.zmq_endpoints

.. autoclass:: ZMQJsonReply
    :members:
 
.. autoclass:: ZMQJsonRequest
    :members:

.. autoclass:: ZMQCoupling
    :members:

.. autoclass:: ZMQCallbackPattern
	:members:

HTTP Client End Points
-----------------------
.. automodule:: boots.endpoints.httpclient_ep

.. autoclass:: HTTPClientEndPoint
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


Plugins
========
.. autoclass:: boots.endpoints.http_ep.BasePlugin
	:members:
	
.. autoclass:: boots.endpoints.http_ep.RequestParams
	:members:
	
.. autoclass:: boots.endpoints.http_ep.WrapException
	:members:
	
.. autoclass:: boots.endpoints.http_ep.Tracer
	:members:

.. autoclass:: boots.endpoints.http_ep.Hook
	:members:
		
	