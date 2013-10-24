'''
In this example, we change the config file to be used. 
'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute


class EP(HTTPServerEndPoint):

    @methodroute()
    def dev(self):
        return "CONFIG"  + '<br/>'.join("{}={}".format(k,v) for (k,v) in self.server.config.items())


    @methodroute()
    def admin(self):
#In order to change config files at route level:
        self.server.configure(skip_overrides=True, standalone=True, config_files=["config_admin"])
        return "CONFIG"  + '<br/>'.join("{}={}".format(k,v) for (k,v) in self.server.config.items())

 
 
#If a mountpoint is specified for an endpoint, then all routes start from it: /<mountpoint>/<route>
#Here, we need to call /conf/<route> instead of /<route>.
my_server = HTTPServer(endpoints=[EP(mountpoint="conf")])
if __name__ == "__main__":
#The config file defaults to common, <auto>. 
#<auto> specifies the config file with a name same as this file. 
    my_server.start_server(standalone=True, conf_subdir=".", \
                         description="To read configuration file", defhost="localhost", defport=8081)


