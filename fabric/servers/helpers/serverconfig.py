from fabric import concurrency
import warnings
if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()

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
        
        super(ServerConfig, self).__init__()

        # Empty config initialized,Now we will add callbacks before reading the file.
        for key,values in callbacks.items():
            self.add_callback([key], values)
        
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

    def update_config(self, config, overrides=None):
        '''
        Updates the current configuration is a safe manner
        @param config: the new (partial) configuration
        '''
        # 1st let us perform a safe validation
        config = config or {}
        overrides = overrides or []
        
        curr_config = dict(self)
        curr_config.update(config)
        configspec = self.merged_configspec
        val = Validator()
        
        configuration = Config(curr_config, configspec=configspec, interpolation='template')     # Making new object out of merged config and configspec
        configuration = self.handle_overrides(configuration, overrides)
        config_test = configuration.validate(val, preserve_errors=True)
        
        if config_test != True:
            logging.getLogger().warning('Update configuration validation not completely successful. Attempting to update with %s. Result is %s',
                                        config, config_test)
            return # do nothing
        else:
            self.merge(config) # selected callbacks should be called
        
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
    