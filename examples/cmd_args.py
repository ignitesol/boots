'''
This example demonstrates usage of command line arguments with the help of Python's argparser.
cmmd_line_args is a dict that stores command line arguments with its default values. 
'''

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute
import argparse


class EP(HTTPServerEndPoint):

    
    # @methodroute passes requests with path = "/demo" to be handled by the following method.
    # If path is not mentioned in @methodroute, it defaults to the name of the method.
    @methodroute(path="/demo", method="GET")
    def demo(self):
        format_str = '{key}: {value}' if not self.server.cmmd_line_args['verbose'] else 'The value of {key} is {value}'
        return '<br/>'.join([ format_str.format(key=k, value=self.server.cmmd_line_args[k]) for k in [ 'demo', 'intval_demo' ]])

    #This prints the command line arguments with its default values (if none specified).          
    @methodroute(path="/cmd", method="GET")
    def cmd(self):
        return self.server.cmmd_line_args
    
class MyServer(HTTPServer):
            
        
    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=[],
                        conflict_handler='error', **kargs): 
        argparser = argparse.ArgumentParser(description=description, add_help=add_help, parents=parents, conflict_handler=conflict_handler) 
        argparser.add_argument('-d', '--demo', dest='demo', default='hello', help='test:  (default: world)')
        #Command line argument for --intval-demo can be passed python cmd_args.py --intval-demo world
        argparser.add_argument('--intval-demo', default=0, type=int, help='test an int val:  (default: 0)')
        argparser.add_argument('--verbose', action='store_true', default=False, help='turns on verbose output')
        return argparser
    
    
my_server = MyServer(endpoints=[EP()])
if __name__ == "__main__":
    my_server.start_server(standalone=True, description="Using request params", defhost="localhost", defport=8081)
    
    
    
