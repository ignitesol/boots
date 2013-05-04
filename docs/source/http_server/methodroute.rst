=====================
Methodroute Decorator
=====================
@methodroute decorator leverages over Bottle's route to provide additional capabilities. It automatically creates a 
route based on the name of the method.
@methodroute converts this method to a route handler which matches /hello.
::

    @methodroute()
    def hello(self):
    	pass


@methodroute converts this method to a route handler which matches /hello/anyname since we have a keyword argument 
that takes a default value.
For example, it matches /hello/name=Alex.
::

    @methodroute()
    def hello(self, name):
    	pass

Here *name=None* makes this parameter optional.
For example, it matches /hello and /hello/name=Alex.
::

    @methodroute()
    def hello(self, name=None):
    	pass


    	
If a path is specified in the methodroute as in the following, the route handler will match /demo or /demo/anyname and not /hello.
::

    @methodroute(path="/demo")
    def hello(self, name=None):
    	pass

Expected request parameters and type of HTTP method can be specified in @methodroute.    	
::

    @methodroute(path='/hello', method='GET', params=dict(name=str, lastname=str))
    def foo(self, name, lastname=None):
        name = name or " World"
        return "Hi " + name + " " + lastname



      