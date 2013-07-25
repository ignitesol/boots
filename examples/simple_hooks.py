'''
This example demonstrates how to use hooks as filters, pre and post to request processing. 
'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, Hook

class Hook(Hook):
    
    def handler(self, before_or_after, request_context, callback, url, **kargs):
        print before_or_after, url
        if before_or_after == "before":
            print "This is before request processing"
        if before_or_after == "after":
            print "After request processing"
            
class EP(HTTPServerEndPoint):
    
    @methodroute()
    def hello(self):
        print "hello"


#All endpoints associated with a server are activated before a server is started. 
my_server = HTTPServer(endpoints=[EP(plugins=[Hook()])])
if __name__ == "__main__":
#While starting a server, we can mention config files, host, port, etc. There are no mandatory parameters as such 
    my_server.start_server(standalone=True,  description="To read configuration", defhost="localhost", defport=8081)
    