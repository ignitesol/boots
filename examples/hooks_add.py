'''
Hooks let us implement filters.
'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, Hook


val = 1
class my_hook(Hook):
    
    def handler(self, before_or_after, request_context, callback, url, **kargs):
        print before_or_after, url
        if before_or_after == "before":
            global val
            val = val-1
            print "Before request processing: " + str(val)
        if before_or_after == "after":
            global val
            val = val+1
            print "After request processing: " + str(val)
            
class EP(HTTPServerEndPoint):
    
    @methodroute()
    def get_val(self):
        global val
        print "val is : " + str(val)
        
my_server = HTTPServer(endpoints=[EP(plugins=[my_hook()])])
if __name__ == "__main__":
    my_server.start_server(standalone=True,  description="To read configuration", defhost="localhost", defport=8081)
    
    
        

    
