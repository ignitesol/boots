==============
Tutorial
==============

It is best to start learning the *boots* framework through some examples. In this tutorial, we will
build a few examples that exercise many of the features of the boots framework.

Our first boots program: Hello World
======================================

.. automodule:: examples.helloworld

A server needs an :py:class:`HTTPServerEndPoint` to be able to serve HTTP requests. We
first define our endpoint::

	from boot.endpoints.http_ep import HTTPServerEndPoint, methodroute 
	
	class EP(HTTPServerEndPoint):

		@methodroute()
		def hello(self, name=None):
			name = name or 'world'
			return 'hello %s' % (name,)

		