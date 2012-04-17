==============
Tutorial
==============

It is best to start learning the *fabric* framework through some examples. In this tutorial, we will
build a few examples that exercise many of the features of the fabric framework.

Our first fabric program: Hello World
======================================

.. automodule:: examples.helloworld

A server needs an :py:class:`HTTPServerEndPoint` to be able to serve HTTP requests. We
first define our endpoint::

	from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute 
	
	class EP(HTTPServerEndPoint):

		@methodroute()
		def hello(self, name=None):
			name = name or 'world'
			return 'hello %s' % (name,)

		