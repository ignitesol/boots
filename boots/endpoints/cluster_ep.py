from boots.datastore.datawrapper import DSWrapperObject
from boots.endpoints.http_ep import BasePlugin
from boots.endpoints.httpclient_ep import HTTPClientEndPoint, Header
from functools import wraps
import bottle
import logging
from threading import RLock
    
class Atomic(object):
    lock = RLock()

class ClusteredPlugin(BasePlugin):
    '''
    A ClusteredPlugin is a  plugin to execute check if request can be handled by this server.
    The stickiness by a virtue of sticky-keys in the request , determines whether the request can be handled by 
    this server. If there are no sticky keys we find the server with minimum load and proxy it to the corresponding server, which 
    will handle this request. At the end of request the stickiness is injected into the system by cluster module for subsequent request
    '''
  
    def __init__(self, datastore=None):
        '''
        :param datastore: The datastore object that is used to communicate with datastore
        '''
        self.datastore = datastore
        
    def setup(self, app):
        for other in app.plugins:
            if isinstance(other, ClusteredPlugin):
                raise bottle.PluginError("Found another ClusteredPlugin plugin")
            
    def apply(self, callback, context):
        '''
        Create the sticky value for the server/endpoint/route.
        Gets the server handling this sticky value
        If there is no such server , gets the server of that type with least load %. This is the DESTINATION SERVER
        If current server is one of the least loaded server, assigns this new request to current server. Current server is the DESTINATION SERVER
        Redirects to destination server if current server is NOT destination server .
        If current server is destination server DO NOTHING . Request will be handled by this server
        '''
        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            
            ep = self.get_callback_obj(callback)
            server = ep.server
            server_address = None
            exception = None
            stickyvalues = None
            
            server.server_address = ep.http_host
#            logging.getLogger().debug("The server name is : %s", ep.server_name)
            server_id = server.get_data()
            ds_wrapper = DSWrapperObject(self.datastore, server.server_address, server_id, ep.uuid, ep.name)
#            logging.getLogger().debug("DSWrapperObject id in apply %s. Server address : %s", id(ds_wrapper), ds_wrapper.server_address)
            try:
                # Gets the stickykeys provided from  route/ endpoint /server in that order
                sticky_keys = kargs.get('stickykeys', None) or getattr(ep, 'stickykeys', None) or server.stickykeys
                add_sticky = kargs.get('autoaddsticky', True)
                if sticky_keys:
                    # we need to create in order to find if the stickiness already exists
                    stickyvalues = server.get_stickyvalues(sticky_keys, kargs)
                    #logging.getLogger().debug("Sticky values formed are : %s on server : %s ", stickyvalues, server.server_address)
                    try:
                        #reads the server to which this stickyvalues and endpoint combination belong to
                        server_address = ds_wrapper._read_by_stickyvalue(stickyvalues, server.servertype)
                        #server_address = ds_wrapper.server_address
                    except Exception as e:
                        logging.getLogger().exception("exception while _read_by_stickyvalue occured is : %s ", e)
                        raise Exception("All the server of type : %s are running at max-limit", server.servertype)
                    res = None    
                    #logging.getLogger().debug("server_address retuned by _read_by_stickyvalue: %s ", server_address)
                    if  server_address and server_address != server.server_address: 
                        destination_url =   server_address + self.get_callback_obj(callback).request.urlparts.path
                        headers = ep.headers
                        fwd_h = Header(headers)
                        [ fwd_h.pop(x, None) for x in [ 'Content-Length', 'Via', 'X-Forwarded-For', 'Connection', 'Host', 'Content-Type', 'User-Agent']]
                        postparams = ep.request_params_as_dict
                        res = self._make_proxy_call(destination_url, fwd_h, postparams)
                    if res:
                        ep.headers = {'Content-Type': res.info().gettype()}
                        # removing headers that caused problems before forwarding the rest
                        [ res.headers.pop(x, None) for x in [ 'Content-Length', 'Transfer-Encoding']]
                        ep.headers = res.headers
#                        for hk, hv in res.headers.items():
#                            logging.getLogger().debug("%s = %s", hk, hv)
                        return res.data # return if there is response 
                # ds_wrapper object is singleton. We can get the object directly )
                if add_sticky:
                    ds_wrapper.add_sticky_value(stickyvalues)
                ds_wrapper._save_stickyvalues()
                result = callback(*args, **kargs)
            except Exception as e:
                exception = e
                result=None
            finally:
                if exception:
                    raise
            # We reach here when request is handled by this server ( there was NO redirect via stickiness or least-load)
            #Inside this method we check if autosave is true , dirty flag is true and then make save call 
            ds_wrapper._save()
            return result
        self.plugin_post_apply(callback, wrapper)
        return wrapper
    
    def _make_proxy_call(self, destination_url , headers, postparams):
        '''
        This method makes the proxy call to the destination serever
        :param server_address: the server address to which we want to proxy the request
        :param headers: the server header from the request
        :param getparams : all the get parameters
        :param postparams : all the post params
        :returns: the response that is returned from the proxied server 
        '''
        ret_val = None
        http_client = HTTPClientEndPoint()
        try:
            #logging.getLogger().debug("Proxy call url %s, postparams : %s, headers %s", destination_url, postparams, headers)
            ret_val = http_client.request(destination_url, headers=headers, **postparams)
        except Exception as e:
            logging.getLogger().debug("Exception occured in proxying the request:%s %s", type(e), e)
            raise
        #logging.getLogger().debug("Proxy call returned : %s ", ret_val.data)
        return ret_val

class ManagedPlugin(BasePlugin):
    '''
    ManagedPlugin is used to create entry of the server on first request
    '''
  
    def __init__(self, datastore=None):
        '''
        :param datastore: The datastore object that is used to communicate with datastore
        '''
        self.datastore = datastore
        
    def setup(self, app):
        for other in app.plugins:
            if isinstance(other, ManagedPlugin):
                raise bottle.PluginError("Found another ManagedPlugin plugin")
            
    def apply(self, callback, context):
        '''
        This plugin only creates entry in the server table.
        '''
        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            ep = self.get_callback_obj(callback)
            server = ep.server
            server.server_address = ep.http_host
            _server_id = server.create_data()
            return callback(*args, **kargs)
        self.plugin_post_apply(callback, wrapper)
        return wrapper
