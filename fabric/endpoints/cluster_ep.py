from bottle import redirect
from fabric.endpoints.http_ep import BasePlugin
from fabric.servers.helpers.clusterenum import ClusterDictKeyEnum
from functools import wraps
import bottle
class ClusteredPlugin(BasePlugin):
    '''
    A ClusteredPlugin is a  plugin to execute check if reuest is handled by this server 
    If not find out the correct server abd redirects to that server
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
            # Check if this request is handled by me is_local()
            # If not find the right server if already handled by somebody
            #        If handled : Redirect to corresponding server
            #        else : Find a new/existing (depending on adapter type)
        '''
        server = self.get_callback_obj(callback).server
        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            serverdata = None
            exception = None
            try:
                try:
                    channel = kargs['channel']
                    if not server.is_local(channel):
                        serverdata = server.get_by_channel(channel)
                except KeyError:
                    pass
                if serverdata:
                    print serverdata[ClusterDictKeyEnum.SERVER]
                    if serverdata[ClusterDictKeyEnum.SERVER] != server.my_end_point:
                        urlpath = bottle.request.environ["PATH_INFO"] + "?" + bottle.request.environ["QUERY_STRING"]
                        print "Redirecting to : ", serverdata[ClusterDictKeyEnum.SERVER] + urlpath
                        redirect("http://" + serverdata[ClusterDictKeyEnum.SERVER] + urlpath, 301)
                else:
                    #find by key if key is given (if this is re-usable adapter)
                    try:
                        key = kargs['key']
                    except KeyError:
                        key = None
                    new_server_for_client = server.get_existing_or_free(key, server.servertype)
                    #If current server, do not redirect
                    print "DataStore Endpoint : ", new_server_for_client[ClusterDictKeyEnum.SERVER]
                    print "Server endpoint ",  server.my_end_point
#                    if new_server_for_client[ClusterDictKeyEnum.SERVER] != server.my_end_point:
#                        redirect(new_server_for_client[ClusterDictKeyEnum.SERVER], 303)
                
                result = callback(*args, **kargs)
            except Exception as e:
                exception = e
                result=None
            finally:
                if exception:
                    raise
            return result
        
        self.plugin_post_apply(callback, wrapper)
        return wrapper       

