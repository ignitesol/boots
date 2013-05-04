'''
This example demonstrates request parameter processing with the help of a plugin, RequestParams. 
'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute

class EP(HTTPServerEndPoint):
    
#We can specify request parameters and their data types in @methodroute
#val=bool evaluates to True for any non empty value and False otherwise.
#RequestParams is available implicitly with HTTPServer and it uses 'params' from @methodroute to get parameters.
    @methodroute(path="/params", params=dict(name=str, val=bool))
    def params(self, name, val):
        print name, val
 
#We are able to add two integer parameters without parsing and splitting the url to get parameter values
#Also, the data type is specified in @methodroute. 
    @methodroute(path="/add", params=dict(a=int, b=int))
    def add(self, a, b):
        print a+b
         
        
class MyServer(HTTPServer):
        
        def __init__(self, handle_exception=True, **kargs):
            super(MyServer, self).__init__(handle_exception, **kargs)
            
#To print the default plugins available:            
        def get_standard_plugins(self, plugins):
            par_plugins = super(MyServer, self).get_standard_plugins(plugins)
            print par_plugins
            return par_plugins
        
my_server = MyServer(endpoints=[EP()])

if __name__ == "__main__":
    my_server.start_server(standalone=True, conf_subdir=".", \
                        description="To read configuration", defhost="localhost", defport=8081)
    