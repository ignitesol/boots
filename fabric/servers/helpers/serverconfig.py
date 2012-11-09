if __name__ == "__main__":
    
    import sys
    import os

    try:
        import fabric
    except ImportError:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))) # Since fabric is not as yet installed into the site-packages



import warnings
import logging
from fabric.common.config import Config

from validate import Validator

# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())

class ServerConfig(Config):
    initialized = False

    def __init__(self, config_files, overrides = [], callbacks=None,
                 env_config=None):
        '''
        initialize the server configuration. Add the callbacks for the configuration and then load it. Validate it.

        @param configfile: a list of tuples [(filename, specfilename), ...]. Files later in the list override earlier configs 

        @param overrides: A list of tuples of the form [ ( 'X.Y.Z', val) where X.Y.Z resolves to config[X][Y][Z] = val. It allows
        the app to set or override config parameters
        @type overrides: list
        
        @param callbacks: A dict containing all the callbacks to be made.
        @type callbacks: dict
        
        @param env_config: a set of key-value pairs that will be added to the config spec before interpolation. Useful for adding _proj_dir
        @type env_config: dict
                
        @return: returns a instance of ServerConfig
        

        '''
        callbacks = callbacks or {}
        env_config = env_config or {}
        
        super(ServerConfig, self).__init__(interpolation='template')

        # Empty config initialized,Now we will add callbacks before reading the file.
        for key,values in callbacks.items():
            self.add_callback(list(key) if type(key) is tuple else [key], values) #Key can be string or tuple
        
        val = Validator()
        
        # initialize common config (empty if None)
        common_config = Config()
        common_configspec = Config(list_values=False, _inspec=True, interpolation=False)
        
        for configfile, specfile in config_files:
            spec_config = Config(configfile, interpolation=False)
            spec_configspec = Config(specfile, list_values=False, _inspec=True, interpolation=False)
            common_config.merge(spec_config)        #Merging configs
            common_configspec.merge(spec_configspec)        #Merging configspecs
        
        self.merged_configspec = common_configspec

        # add the default values for project dirs
        for k, v in env_config.iteritems():
            common_config[k] = v
             
        configuration = Config(common_config, configspec=common_configspec, interpolation='template')     # Making new object out of merged config and configspec
        
        configuration = self.handle_overrides(configuration, overrides)
        
        config_test = configuration.validate(val, preserve_errors=True)

        if config_test != True:
            warnings.warn('Configuration validation failed on %s and result is %s' % (config_files, config_test))

        self.merge(configuration) # callbacks will be invoked now
        
        if config_test != True:
            logging.getLogger().warning('Configuration validation not completely successful for %s and result is %s',
                                        configfile, config_test)

    def update_config(self, config, overrides=None): #TODO:Testing pending.
        '''
        Updates the current configuration is a safe manner
        @param config: the new (partial) configuration
        '''
        # 1st let us perform a safe validation
        config = config or {}
        overrides = overrides or []
        
        curr_config = Config(self.dict())
        configspec = self.merged_configspec
        val = Validator()
        
        configuration = Config(curr_config, configspec=configspec, interpolation='template')     # Making new object out of merged config and configspec
        curr_config.merge(config)
        configuration = self.handle_overrides(configuration, overrides)
        config_test = configuration.validate(val, preserve_errors=True)
        if config_test != True:
            logging.getLogger().warning('Update configuration validation not completely successful. Attempting to update with %s. Result is %s',
                                        config, config_test)
            return #TODO: Return a better error msg.
        else:
            self.merge(config) # selected callbacks should be called
            return None #TODO: return a success msg.

    def handle_overrides(self, conf, overrides):
        # adding overrides
        overrides = overrides or []
        for key, val in overrides:
            new_conf = conf
            key_list = key.split('.')
            for k in key_list[:-1]:
                new_conf.setdefault(k, {})  # if it does not exist, create an empty dict
                new_conf = new_conf[k]
            new_conf[key_list[-1]] = val
        return conf
    
    
if __name__ == "__main__":
    import argparse
    
    def logcallback(action, fullkey, val, c):
        print 'In logcallback', fullkey, val
    
    parser = argparse.ArgumentParser(description='Run unit tests on ServerConfig')
    parser.add_argument('files', metavar='file', type=str, nargs='+',
                   help='config files to be loaded')    
    args = parser.parse_args()
    
    files = zip(args.files, [ f.replace('.ini', '_configspec.ini') for f in args.files])

    callbacks = { 'Logging': logcallback }
    sconfig = ServerConfig(files, callbacks=callbacks, env_config={'_proj_dir': '.'})
    
    d = {}
    try:
        d['Logging'] = sconfig.get('Logging', {}).dict()
    except AttributeError:
        d['Logging'] = dict(sconfig.get('Logging', {}))
    print type(d), type(d['Logging']), type(d['Logging']['handlers']), type(d['Logging']['handlers']['console']), type(d['Logging']['handlers']['console']['level'])
    d['Logging']['handlers']['console']['level'] = 'ERROR'
    print ' ABout to update with ', d

    print "____MERGING___"
    sconfig.update_config(d)
    

    
    
    