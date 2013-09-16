'''
Sessions and Caching
====================

Configuring and using sessions or caching is simple. boots leverages beaker_ for sessions and caching.
Setting up sessions and / or caching involves using the configuraiton ini file and then turning the feature on.

The ini file for session and caching (refer beaker_). Note: it is required to specify a session_key in the ini within the Session section::

    ... # Logging section removed for brevity
    [Session]
        session.key = session_key
        session.type = memory
        session.cookie_expires = True
        session.auto = True
    [Caching]
        cache.enabled = True
        cache.regions = datastore
        cache.datastore.type = ext:memcached
        cache.datastore.url = 127.0.0.1:11211
        cache.datastore.expire = 7200
        cache.datastore.lock_dir = /tmp/testcache

To turn on the feature, pass the appropriate booleans to *start_server*::

    main_server = HTTPServer(endpoints=[EP()], session=True, cache=True, logger=True)

The endpoint can refer to session as self.session and cache as self.server.cache.cache::

    @methodroute()
    def hello(self, name=None):
    
        @self.server.cache.cache()
        def capitalize(name):
            self.logger.info('capitalize called. should now be cached for %s', name)
            return name.capitalize()
            
        name = name or self.session.get('name', None) or 'world'  # the name is passed as an argument or obtained from the session
        self.session['name'] = name
        self.session['count'] = self.session.get('count', 0) + 1

        return 'hello %s - you have called me %d times' % (capitalize(name), self.session['count'])

`beaker <http://beaker.readthedocs.org/en/latest/>`_ 

'''

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute    
    
class EP(HTTPServerEndPoint):
    
    @methodroute()
    def hello(self, name=None):
        ''' 
        @methodroute converts this method to a route handler which 
        matches /hello or /hello/anyname since we have a keyword argument that takes a default value
        '''
        
        @self.server.cache.cache()
        def capitalize(name):
            self.logger.info('capitalize called. should now be cached for %s', name)
            return name.capitalize()
        
        name = name or self.session.get('name', None) or 'world'  # the name is passed as an argument or obtained from the session
        self.session['name'] = name
        self.session['count'] = self.session.get('count', 0) + 1
        print self.session

        return 'hello %s - you have called me %d times' % (capitalize(name), self.session['count'])
    

main_server = HTTPServer(endpoints=[EP()], session=True, cache=True, logger=True)

if __name__ == '__main__':
    main_server.start_server(defhost='localhost', proj_dir=".", defport=9999, standalone=True, description="A test server for the boots framework")
