
HTTP Server End Points
-----------------------
.. automodule:: boots.endpoints.http_ep

.. autoclass:: HTTPServerEndPoint
	:members: activate, request, request_params, environ, response, abort, session
 
Route Decorator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: methodroute(path=None, skip_by_type=None, plugins=None, params=None, handler=None, cleanup_funcs=None, **kargs)

Plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: boots.endpoints.http_ep.BasePlugin
	:members:
	
.. autoclass:: boots.endpoints.http_ep.RequestParams
	:members:
	
.. autoclass:: boots.endpoints.http_ep.WrapException
	:members:
	
.. autoclass:: boots.endpoints.http_ep.Tracer
	:members:

.. autoclass:: boots.endpoints.http_ep.Hook
	:members: handler
		

