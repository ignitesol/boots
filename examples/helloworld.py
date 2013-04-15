
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute    
    
class EP(HTTPServerEndPoint):
    '''
    An http server endpoint with just one route supporting /hello
    '''

    # methodroute automatically creates a route based on the name of the method unless path is specified
    @methodroute(path='/')
    def hello(self):
        ''' 
        @methodroute marks this method as an http route handler which matches /hello
        '''
        return 'hello world'

# associate the endpoint with a server
main_server = HTTPServer(endpoints=[EP()])

if __name__ == '__main__':
    main_server.start_server(defhost='localhost', defport=9999, standalone=True, description="A test server for the boots framework")
