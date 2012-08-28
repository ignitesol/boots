from bottle import redirect
from fabric.endpoints.http_ep import BasePlugin
from functools import wraps
import bottle

from fabric import concurrency
if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock
    
class Atomic(object):
    lock = RLock()

class ClusteredPlugin(BasePlugin):
    '''
    A ClusteredPlugin is a  plugin to execute check if request is handled by this server 
    If not find out the correct server and redirects to that server
    '''
  
    def __init__(self, default_handler=None):
        '''
        @param default_handler:       
        '''
        self.default_handler = default_handler
               
    def setup(self, app):
        for other in app.plugins:
            if isinstance(other, ClusteredPlugin):
                raise bottle.PluginError("Found another ClusteredPlugin plugin")
            
            
    def apply(self, callback, context):
        '''
        Create the sticky value for the server.
        Gets the server handling this sticky value
        If there is no such server , gets the server of that type with least load %
        Redirects to destination server if current server is NOT destination server .
        If current server is destination server DO NOTHING . Request will be handled by this server
        '''
        server = self.get_callback_obj(callback).server
        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            server_adress = None
            exception = None
            try:
                stickyvalue = server.create_sticky_value(kargs)
                #TODO : check first if server is of the required type ( adapter|mpeg OR adapter|CODF etc)
                server_adress = server.get_by_stickyvalue(stickyvalue)
                if not server_adress:
                    with Atomic.lock:
                        server_adress = server.get_least_loaded(server.servertype)

                if server_adress != server.server_adress: 
                    urlpath = bottle.request.environ["PATH_INFO"] + "?" + bottle.request.environ["QUERY_STRING"]
                    print "Redirecting to : ", server_adress + urlpath
                    redirect("http://" + server_adress + urlpath, 301)
                result = callback(*args, **kargs)
            except Exception as e:
                exception = e
                result=None
            finally:
                if exception:
                    raise
            # Application needs to implement how load gets updated 
            # Also need to determine how load is decremented
            with Atomic.lock:
                server.update_data(server_adress, load=server.get_current_load(), stickyvalue=stickyvalue)    
            return result
        self.plugin_post_apply(callback, wrapper)
        return wrapper