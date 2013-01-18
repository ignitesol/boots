from fabric import concurrency
from fabric.datastore.datawrapper import DSWrapperObject
from fabric.endpoints.http_ep import BasePlugin
from fabric.endpoints.httpclient_ep import HTTPClientEndPoint
from functools import wraps
import bottle
import logging

if concurrency == 'gevent':
    from gevent.coros import RLock
elif concurrency == 'threading':
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
  
    def __init__(self, datastore=None, ds='ds'):
        '''
        :param datastore: The datastore object that is used to communicate with datastore
        :param ds: parameter name of the data-wrapper-object thats passed to application. 
                    This object can be used by application to update the sticky value for this request
        '''
        self.datastore = datastore
        self.ds = ds # parameterr name of the data-wrapper-object thats passed to application
        
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
            
            headers = bottle.request.headers.environ
#            logging.getLogger().debug("Headers at he start of the plugin")
#            for hk,v in headers.items():
#                logging.getLogger().debug("%s=%s", hk, v)
            ep = self.get_callback_obj(callback)
            server = ep.server
            server_adress = None
            exception = None
            stickyvalues = None
            
            server.server_adress = ep.server_name
            server_id = server.create_data()
            ds_wrapper = DSWrapperObject(self.datastore, server.server_adress, server_id, ep.uuid, ep.name)
            try:
                # Gets the stickykeys provided from  route/ endpoint /server in that order
                sticky_keys = kargs.get('stickykeys', None) or getattr(ep, 'stickykeys', None) or server.stickykeys
                add_sticky = kargs.get('autoaddsticky', True)
                if sticky_keys:
                    # we need to create in order to find if the stickiness already exists
                    stickyvalues = server.get_stickyvalues(sticky_keys, kargs)
#                    logging.getLogger().debug("Sticky values formed are : %s ", stickyvalues)
                    try:
                        #reads the server to which this stickyvalues and endpoint combination belong to
                        server_adress = ds_wrapper._read_by_stickyvalue(stickyvalues, server.servertype)
                        #server_adress = ds_wrapper.server_address
                    except Exception as e:
                        logging.getLogger().exception("exception while _read_by_stickyvalue occured is : %s ", e)
                        raise Exception("All the server of type : %s are running at max-limit", server.servertype)
                    res = None    
                    #logging.getLogger().debug("server_adress retuned by _read_by_stickyvalue: %s ", server_adress)
                    if  server_adress and server_adress != server.server_adress: 
                        destination_url =   server_adress + self.get_callback_obj(callback).request.urlparts.path
                        headers = bottle.request.headers.environ
                        cookies = bottle.request.COOKIES.dict
                        #logging.getLogger().debug("Cookies : %s", headers)
                        cookie_headers = {}
                        hstr =""
                        for k, v  in cookies.items():
                            hstr += '{key}={value};'.format(key=k, value=v[0])
                        cookie_headers = {'Cookie' : hstr}
                        
                        fwd_h = {}
                        for k,v in headers.items():
                            if k == 'HTTP_X_FORWARDED_HOST':
#                                logging.getLogger().debug("The forwarded host : %s", v)
                                fwd_h['X_FORWARDED_HOST'] = v
                            #else:fwd_h[k] = v
                        cookie_headers.update(fwd_h)
                        #cookie_headers.update(headers)
                        getparams = bottle.request.GET.dict
                        
                        params = bottle.request.POST
                        d = {}
                        for k in params.keys():
                            d[k] = params.getall(k)
                            if len(d[k]) == 1:
                                d[k] = d[k][0] # drop the list of single valued params
                        postparams = d
                        res = self._make_proxy_call(destination_url, cookie_headers, getparams, postparams)
                    if res:return res # return if there is response 
                        
                # Add the ds object (Since the ds_wrapper object is singleton. We can get the oject directly )
                #kargs[self.ds] = ds_wrapper
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
            # Typically application needs to add the sticky key values to the "stickywrapper" object that gets passed to it 
            # Application needs to implement how load gets updated AND # Also need to determine how load is decremented
            with Atomic.lock: #Do we really need at this level
                if stickyvalues and add_sticky:
                    pass
            # We reach here when request is handled by this server ( there was NO redirect via stickiness or least-load)
            #Inside this method we check if autosave is true , dirty flag is true and then make save call 
            ds_wrapper._save()
            return result
        self.plugin_post_apply(callback, wrapper)
        return wrapper
    
    
    
    def _make_proxy_call(self, destination_url , headers, getparams, postparams):
        '''
        This method makes the proxy call to the destination serever
        :param server_adress: the server address to which we want to proxy the request
        :param headers: the server header from the request
        :param getparams : all the get parameters
        :param postparams : all the post params
        :returns: the response that is returned from the proxied server 
        '''
        ret_val = None
        http_client = HTTPClientEndPoint()
        try:
#            logging.getLogger().debug("Proxy call postparams : %s ", postparams)
            ret_val = http_client.request(destination_url, headers=headers, **postparams).data
        except Exception as e:
            logging.getLogger().debug("Exception occured in proxying the request: %s", e)
#            logging.getLogger().debug("Proxy call returned : %s ", ret_val)
        return ret_val
