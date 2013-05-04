======
Cache 
======

Boots leverages Beakers_ caching system to enable caching of data.
A cache decorator is used for this purpose.
Only the first request on a particular name on *capitalize* will use *name.capitalize()*. 
Every other request on the same name returns the cached result.   


.. _Beakers: http://beaker.readthedocs.org/en/latest/caching.html

::

    @methodroute()
    def hello(self, name=None):
        ''' 
        @methodroute converts this method to a route handler which 
        matches /hello or /hello/anyname since we have a keyword argument that takes a default value
        '''
        
        @self.server.cache.cache()
        def capitalize(name):
            print 'capitalize called. should now be cached for', name
            return name.capitalize()
        
        name = name or self.session.get('name', None) or 'world'  # the name is passed as an argument or obtained from the session
        self.session['name'] = name
        self.session['count'] = self.session.get('count', 0) + 1

        return 'hello %s - you have called me %d times' % (capitalize(name), self.session['count'])
    