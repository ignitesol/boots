=================
Adding Endpoints 
=================

EndPoints are a gateway to the Server. They offer flexibility of adding routes (urls where HTTP can be served from), providing
parameter processing and validation capabilities.

An endpoint may be added to the server before/after start_server. 

Adding before start of server
------------------------------

Endpoints can be added while instantiating a server as shown below.
This enables the endpoint to receive requests at start of the server itself. 
::
	class EP(HTTPServerEndPoint):
		pass
	
	ep1 = EP()		
	main_server = HTTPServer(endpoints=[ep1])

We can specify a mountpoint while adding endpoints. 
If a mountpoint is specified for an endpoint, then all routes start from it: /<mountpoint>/<route>
Here, we need to call /conf/<route> instead of /<route>.
::

	my_server = HTTPServer(endpoints=[EP(mountpoint="conf")])


Adding after start of server TODO
----------------------------------

If added after start_server, it is assumed to be activated. 
This way multiple endpoints may be added to the server.
::

	db_ep = EP()
	self.add_endpoint(db_ep)