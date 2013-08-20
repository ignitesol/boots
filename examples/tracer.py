from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute, Tracer
import logging
from cookielib import logger

def handler1():
    pass

class my_tracer(Tracer):
        def handler(self, before_or_after, request_context, callback, url, result=None, exception=None, **kargs):
            pass
            
class EP(HTTPServerEndPoint):
    
    @methodroute()
    def get_val(self):
        print "val "
        
        
my_server = HTTPServer(endpoints=[EP(plugins=[my_tracer(tracer_paths="", handler=handler1)])])
if __name__ == "__main__":
    my_server.start_server(standalone=True,  description="To read configuration", defhost="localhost", defport=8081, logger=True)
    
    
        

    
