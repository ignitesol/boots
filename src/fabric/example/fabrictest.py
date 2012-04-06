'''
this is an example of the basic usage of the server and http endpoint components of the fabric framework
* Servers are entities that provide specific functionality and capability
* Servers consist of endpoints (source or destinations of communication) and optionally subservers
* this way, the main server is an arbitrary nesting of servers. Each server consist of one or more endpoints

In this example, we demonstrate a set of servers composed to form a main server each with one or more endpoints

MainServer is our class that represents the main server. 
    ManagementServer is a subserver that provides interfaces for management of the mainserver
    ManagementServer has one endpoint that has two http routes (/admin and /health)
    ManagementServer is mounted at /mgmt. So, /mgmt/admin and /mgmt/health are the actual routes 
    The MainServer has 2 endpoint instances (for this concept, both of them are the same class). These server
    the /index and /second/index routes

Created on Mar 18, 2012

@author: AShah
'''
from fabric import concurrency

if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
elif concurrency == 'threading':
    pass

from fabric.servers.httpserver import HTTPServer
import argparse
from fabric.endpoints.http_ep import HTTPServerEndPoint, methodroute,\
    RequestParams, WrapException
    
from fabric.common.utils import new_counter


import time

class EP(HTTPServerEndPoint):
    
    def __init__(self, name=None, mountpoint='/', plugins=None):
        super(EP, self).__init__(name=name, mountpoint=mountpoint, plugins=plugins)
        self.count = new_counter()
    
    @methodroute(params=dict(b=int, c=[str]))
    def index(self, a, b=None, c=''):
        b = b or 0
        if b:
            yield 'Waiting %s seconds<br/>' % (b,)   # to test gevent
            time.sleep(b)  # to test gevent
        yield 'Call # %d to this endpoint. a = %s, b = %s, c = %s' % (self.count(), a, b, c) # this count is end-point count

ep1 = EP(plugins=[ RequestParams() ] )
ep2 = EP(mountpoint='/second', plugins=[ RequestParams() ])

class MainServer(HTTPServer):
    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=None, 
                        conflict_handler='error', **kargs):
        _argparser = argparse.ArgumentParser(description=description, add_help=add_help, parents=parents, conflict_handler=conflict_handler)
        # adding an argument over and above those in HTTPServer 
        _argparser.add_argument('-x', '--xhost', dest='xhost', default=kargs.get('defhost', 'localhost'),
                                 help='hostname or ip address. (default: {})'.format(kargs.get('defhost', 'localhost')))
        
        # overriding an argument from http server
        _argparser.add_argument('-p', '--port', dest='port', type=int, default=kargs.get('defport', '7777'),
                                 help='port number. (default: {})'.format(kargs.get('defport', '7777'))),
                                 
        # adding an argument                                 
        _argparser.add_argument('--trial', action="store_true", help='start bottle server in debug mode')
        return _argparser

class EP2(HTTPServerEndPoint):
    @methodroute()
    def health(self):
        return 'Healthy. Total Calls to ManagementServer %d' % (self.server.count(),) # this is ManagemntServer's count
    
    @methodroute()
    def admin(self):
        return 'Admin called. Total Calls to ManagementServer %d' % (self.server.count(),) # this is ManagemntServer's count

class ManagementServer(HTTPServer):
    
    count = new_counter()
    
main_server = MainServer(endpoints=[ep1, ep2], session=True, cache=True, auth=True, logger=True)
# we can add sub-servers during (i.e. by passing in __init__ or after creation of main server
mgmt_server = ManagementServer(endpoints=[EP2()])
main_server.add_sub_server(mgmt_server, '/mgmt')


if __name__ == "__main__":
    main_server.start_server(description="A test server for the fabric framework")