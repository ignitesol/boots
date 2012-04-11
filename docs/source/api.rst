==========================
API Reference
==========================
	
This is an auto-generated API. If you are new to fabric you might want to read the :doc:`intro`

Servers
=======

Endpoints
=========
.. module:: fabric.endpoints.endpoint

.. autoclass:: EndPoint
.. autoclass:: EndPointException

HTTP Server End Points
-----------------------
.. module:: fabric.endpoints.http_ep

.. autofunction:: methodroute(path=None, skip_by_type=None, plugins=None, params=None, handler=None, cleanup_funcs=None, **kargs)

.. autoclass:: HTTPServerEndPoint
	:members:
	
.. autoclass:: BasePlugin
	:members:
	
.. autoclass:: RequestParams