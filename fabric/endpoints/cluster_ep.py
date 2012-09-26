from fabric import concurrency
from fabric.datastore.datamodule import DSWrapperObject
from fabric.endpoints.http_ep import BasePlugin
from functools import wraps
import bottle
import urllib2

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
  
    def __init__(self, datastore=None, ds='ds'):
        '''
        :param datastore: The datastore object 
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
        server = self.get_callback_obj(callback).server

        @wraps(callback)
        def wrapper(*args, **kargs): # assuming bottle always calls with keyword args (even if no default)
            server_adress = None
            exception = None
            stickyvalues = None
            ds_wrapper = DSWrapperObject(self.datastore, callback.im_self.uuid, callback.im_self.name)
            try:
                # Gets the stickykeys provided from  route/ endpoint /server in that order
                sticky_keys = kargs.get('stickykeys', None) or getattr(callback.im_self, 'stickykeys', None) or server.stickykeys
                if sticky_keys:
                    # we need to create in order to find if the stickiness already exists
                    stickyvalues = self._get_stickyvalues(server, sticky_keys, kargs)
                    try:
                        #reads the server to which this stickyvalues and endpoint combination belong to
                        ds_wrapper._read_by_stickyvalue(stickyvalues)
                        server_adress = ds_wrapper.server_address
                    except Exception:
                        with Atomic.lock: # Do we really need at this level
                            server_adress = server.get_least_loaded(server.servertype, server.server_adress)
                            ds_wrapper.server_address = server_adress
                        
                    if server_adress != server.server_adress: 
                        destination_url =   bottle.request.environ["wsgi.url_scheme"] + "://" + server_adress + \
                                                bottle.request.environ["PATH_INFO"] + "?" + bottle.request.environ["QUERY_STRING"]
                        print "proxying to destination server: ", destination_url
                        headers = bottle.request.headers.environ
                        cookies = bottle.request.COOKIES.dict
                        getparams = bottle.request.GET.dict
                        postparams = bottle.request.POST.dict
                        res = self._make_proxy_call(server_adress, headers, cookies, getparams, postparams)
                        return res
                        
                # If method-route expects the param then add the ds_wrapper with the param named defined in the plugin
                if self.ds in callback._signature[0]:
                    kargs[self.ds] = ds_wrapper
                result = callback(*args, **kargs)
            except Exception as e:
                exception = e
                print e
                result=None
            finally:
                if exception:
                    raise
            # Typically application needs to add the sticky key values to the "stickywrapper" object that gets passed to it 
            # Application needs to implement how load gets updated AND # Also need to determine how load is decremented
            with Atomic.lock: #Do we really need at this level
                if stickyvalues:
                    # We reach here when request is handled by this server ( there was NO redirect via stickiness or least-load)
                    ds_wrapper._update(stickyvalues, server.get_new_load())
            #Inside this method we check if autosave is true , dirty flag is true and then make save call 
            ds_wrapper._save()
            return result
        self.plugin_post_apply(callback, wrapper)
        return wrapper
    
    
    
    def  _get_stickyvalues(self, server, sticky_keys,  paramdict):
        '''
        This method creates the stickyvalues based on the paramaters provided
        :param dict paramdict: this is the dict of all the parameters provided for this route
        
        :rtype: returns the list of sticky values that needs to be updated to the 
        '''
        stickyvalues = [] # this is list of stickyvalues
        if type(sticky_keys) is str:
            try :
                stickyvalues += [ paramdict[sticky_keys] ]
            except KeyError:
                pass # If key not present no stickiness 
        elif type(sticky_keys) is tuple:
            value_tuple = self._extract_values_from_keys(sticky_keys, paramdict)
            stickyvalues += [ server.transform_stickyvalues(value_tuple) ]  if value_tuple else []
        elif type(sticky_keys) is list:
            for sticky_key in sticky_keys:
                #recursive call
                stickyvalues += self._get_stickyvalues(server, sticky_key, paramdict)
#                value_tuple = self._extract_values_from_keys(sticky_key, paramdict)
#                stickyvalues += [ server.transform_stickyvalues(value_tuple) ]  if value_tuple else []
        elif hasattr(sticky_keys, '__call__'):
            val = sticky_keys(paramdict)
            if val is not list:
                val = [val]
            stickyvalues +=val
        return stickyvalues

    
    
    def _extract_values_from_keys(self, key_tuple, paramdict):
        '''
        This is internal method that extracts the values for the keys provided in the tuple from the param dict
        :param tuple key_tuple: the tuple of keys which are used for the extracting the corresponding values
        :param dict paramdict: the dict of param which contains the values if they exist
        
        :rtype: return the tuple if all the values are present else return None
        '''
        try:
            return tuple([ paramdict[key] for key in key_tuple ])
        except KeyError:
            return None 
        
        
    def _update_stickyobj(self, *args, **kwargs):
        pass
    
    
    def _make_proxy_call(self, server_adress , headers, cookies, getparams, postparams):
        #server_adress = "localhost:8870"
        '''
        This method makes the proxy call to the destination serever
        '''
        
        destination_url =   bottle.request.environ["wsgi.url_scheme"] + "://" + server_adress + \
                                                    bottle.request.environ["PATH_INFO"] + "?" + bottle.request.environ["QUERY_STRING"]
        
        data = postparams if postparams else None
        req = urllib2.Request(destination_url, data, headers)
        res = urllib2.urlopen(req)
        return res.read()