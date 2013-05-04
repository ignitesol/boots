==================
HTTPServerEndPoint
==================
.. automodule:: boots.endpoints.http_ep

An endpoint can be added to the server before/after start_server. 
If added after start_server, it is assumed to be activated. ::

	self.add_endpoint(db_ep)