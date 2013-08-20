'''
This example illustrates the use of session and caching in boots.
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
            print 'capitalize called. should now be cached for', name
            return name.capitalize()
        
        name = name or self.session.get('name', None) or 'world'  # the name is passed as an argument or obtained from the session
        self.session['name'] = name
        self.session['count'] = self.session.get('count', 0) + 1

        return 'hello %s - you have called me %d times' % (capitalize(name), self.session['count'])
    

# create an endpoint
ep1 = EP()
# associate the endpoint with a server
main_server = HTTPServer(endpoints=[ep1], session=True, cache=True, logger=True)

if __name__ == '__main__':
    main_server.start_server(defhost='localhost', proj_dir=".", defport=9998, standalone=True, description="A test server for the boots framework")
