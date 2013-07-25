'''
This example demonstrates how to override config section values.
'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute



class EP(HTTPServerEndPoint):

    @methodroute()
    def config_override(self):
        a = self.server.config
        return "AFTER OVERRIDE"  + '<br/>'.join("{!s}={!r}".format(k,v) for (k,v) in a.items())

class MyServer(HTTPServer):
    #Overridding config section value.
    config_overrides = [('Datastore.datastore', 'datamart')]
    
    
my_server = MyServer(endpoints=[EP()])
if __name__ == "__main__":
    my_server.start_server(standalone=True, conf_subdir=".", \
                       config_files=["config_override"], description="To read configuration", defhost="localhost", defport=8081)

