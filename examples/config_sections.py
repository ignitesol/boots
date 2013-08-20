'''
This example simply prints sections from a configuration file.
'''
from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute


class EP(HTTPServerEndPoint):

    @methodroute(path="/<section>")
    def get_config_section(self, section):
        print self.server.config[section]
        return self.server.config[section]
        #return self.server.config["Logging"]["logs"]


    @methodroute()
    def get_config(self):
        return "CONFIG"  + '<br/>'.join("{}={}".format(k,v) for (k,v) in self.server.config.items())

   

my_server = HTTPServer(endpoints=[EP()])
if __name__ == "__main__":
    my_server.start_server(standalone=True, conf_subdir=".", \
                       config_files=["config_sections"], description="To read configuration", defhost="localhost", defport=8081)
    