'''
Servers are the logical entity that provides services to 
the rest of the system. Servers contain :py:class:`EndPoint`
through which they communicate (receive and send). 

 
'''
from warnings import warn
import inspect
import sys
import os
import functools
from fabric.servers.helpers.serverconfig import ServerConfig
from logging.config import dictConfig
import logging

from fabric.common.utils import new_counter, generate_uuid

class Server(object):
    '''
    :py:class:`Server` is the base class for Server based functionality. Subclasses include :py:class:`HTTPServer`
    which adds functionality for HTTP based servers and :py:class:`ManagedServer` which offers additional capabilities
    for configuring and administering servers. Our intent is to add *ClusteredServer* and other subclasses.
    
    An actual server may (but need not) define a subclass of one or more of the Server subclasses. The actual server
    would (to achieve any work) need to instantiate one or more endpoints through which it receives requests.
    
    The Server class provides additional **experimental** capabilities to compose other servers (called sub_servers).
    
    Some of the capabilities provided by the Server include
    
    * command line parameter parsing
    * configuration through config .ini file processing
    * associating callbacks that are invokved when specific sections of the configuration are instantiated or modified
    '''
    _name_prefix = "Server_"
    _counter = new_counter()
    
    ## settings for configuration and callbacks. Override or add in subclasses
    #: config_callbacks is a class level attribute that provides a consistent method for the server (and all 
    #: subclasses) to setup up callback functions (as per ServerConfig class specifications)
    #: Subclasses can override specific callbacks or add additional callbacks.
    #: config_callbacks is initialized outside the class (see below) so as to allow reference to class instance methods 
    #: alternately, set up the instance methods within the constructor
    config_callbacks = { }
    
    #: config_overrides provide a means of overriding any specific config item directly through code. This allows
    #: config files to maintain structure but for the code to still control what values get finally setup 
    #: within the config
    #: The format of the config_overrides is a list of tuples, each tuple being of the form ( 'dot.separated.key', config-value)
    #: Each element of the dot.seperated.key forms a Section/Subsection of the config structure.
    #: For example ( 'Logging.formatters.detailed.format', '%(message)s' ) implies
    #: changing config['Logging']['formatters']['detailed']['format'] = '%(message)s'
    config_overrides = [ ('Logging.formatters.detailed.format', '%(levelname)s:%(asctime)s:[%(process)d:%(thread)d]:%(funcName)s: %(message)s'),
                        ] # override the logging format 
    
    def __init__(self, name=None, endpoints=None, parent_server=None, **kargs):
        '''
        :param name: A name for the server. This will be useful when handling health, stats and configuration.
            Defaults to a generic, autogenerated name
        :param endpoints: A list of :py:class:`EndPoint` (or subclass of EndPoint) that become the endpoints
            of this server (Note - additional endpoints may be automatically added by superclasses of the Server
        :param parent_server: A link back to the parent_server when this server is a composed sub_server.
        :param kargs: Additional parameters required for the server. 
        :param bool logger: An optional parameter to determine if logging needs to be configured for this server.
        '''
        self.name = name or self._name_prefix + str(Server._counter()) # _name_prefix will be from subclass if overridden
        self.endpoints = endpoints or []
        self.sub_servers = []
        self.parent_server = parent_server
        self.config = {} #: holds the parsed and processed config for this server (based on ini files and other updates)
        self.cmmd_line_args = None #: a dict holding the command line arguments for the server

        self._proj_dir = None
        logger = kargs.get('logger', False)
        if logger: self.__class__.config_callbacks['Logging'] = Server._logger_config_update # defined in this class
        self.uuid = generate_uuid()
        
    def add_endpoint(self, endpoint):
        '''
        Simply add to the list of endpoints if it does not already exist. assumes an activated endpoint is being added if the server has already been activated
        '''
        if endpoint.uuid not in [ e.uuid for e in self.endpoints ]:
            self.endpoints += [ endpoint ]
    
    def remove_endpoint(self, endpoint):
        '''
        Remove an endpoint from the list
        '''
        self.endpoints = list(filter(lambda e: endpoint.uuid != e.uuid, self.endpoints))
        
    def add_sub_server(self, server, mount_prefix=None):
        '''
        Add sub_servers to support a model of server composition. Allows servers to be independently developed
        but run as an integrated unit. **experimental**
        '''
        if mount_prefix is not None: server.mount_prefix = mount_prefix 
        self.sub_servers += [ server ]

    def start_server(self, parent_server=None, standalone=False, proj_dir=None, conf_subdir='conf', config_files=['common', '<auto>' ], description=None, **kargs):
        '''
        start_server does the initialization for the server. NOTE, while start_server would have
        access to the cmmd_line arguments, the configuration is not read when it is invoked.
        Rather, after all the start servers have been invoked, the configuration is read and 
        ideally callbacks of the configuration are called.
        Finally, the start_main_server is invoked.
        
        start_server is invoked by the master server with parent_server = None (default).  
        It activates all its endpoints, then starts all its sub-servers.
        
        :param parent_server: a reference to this server's parent server (None implies outermost i.e. the final subclass)
        :param proj_dir: an optional argument. If specified, this is taken to be the root of the project directory.
            If not specified, this is infered through introspection
        :param conf_subdir: the configuration subdirectory within the proj_dir where configuration files may be obtained
        :param list config_files: a list of filename stems (i.e without the .ini extension) that contain the configuration for this server.
            If mulitple files are given, the order is important and files on the right may overwrite config options specified in files on the left
            A special token *<auto>* is replaced with the name of the main file that was invoked to launch this app (determined through introspection)
            Defaults to [ 'common', '<auto'> ]
        :param description: for purposes of help messages on cmmd line
        :param bool standalone: A boolean that indicates whether this server is invoked from an environment (e.g. modwsgi)
            or is standalone. If standalone is True one of the subclasses should start a server. If standalone is False, implies no
            command line argument processing 
        '''

        self.standalone = standalone
        self.parent_server = parent_server or self.parent_server
        self.is_master = self.parent_server == None
        self.root_server = self if self.is_master else self.parent_server.root_server
        
        if self.is_master:
            self.cmmd_line_args = self.parse_cmmd_line(description, **kargs)
            
        if self.is_master:
            self.configure(proj_dir=proj_dir, conf_subdir=conf_subdir, config_files=config_files)
        
        self.pre_activate_hook()        
        self.activate_endpoints()
        self.start_all_sub_servers()
        
        if self.is_master:
            Server.main_server = self
            self.start_main_server()
        self.post_activate_hook() 
            
    # these can be overridden defined by the subclasses
    def activate_endpoints(self):
        '''
        Activate this server's endpoints. This is typically overridden in subclasses
        '''
        pass
    
    def pre_activate_hook(self):
        '''
        This is hook to do pre-start processing
        '''
        pass
    
    def post_activate_hook(self):
        '''
        This is hook to do post-start processing
        '''
        pass

    def start_all_sub_servers(self, **kargs):
        ''' starts all added sub_servers. This is **experimental** '''
        [ server.start_server(parent_server=self, **kargs) for server in self.sub_servers ]
            
    def start_main_server(self, **kargs):
        ''' Typically run after all endpoints of the master and sub_server are activated. This actually
            runs the main event loop (if any) for the servers. Typically overridden in subclasses '''
        pass
            
    @classmethod
    def _mro_classattribute_get(cls, attrname):
        '''
        walks through the mro and returns a list of attributes from the MRO classes with the name attrname
        attributes are returned in reverse MRO (i.e. supermost first)
        @param cls: classname from where to start the MRO walk
        @type cls: type
        @param attrname: Name of the attribute
        @type attrname: str
        '''
        classes = list(cls.__mro__)
        classes.reverse()
        attrvals = [getattr(c, attrname, None) if issubclass(c, Server) else None for c in classes]
        # make unique keeping order and keeping the 1st occurance
        attrvals = [ val for i, val in enumerate(attrvals) if val is not None and attrvals.index(val) == i ] 
        
        return attrvals
    
    def _get_proj_dir(self, subdir=None):
        '''
        return the project root dir (i.e. the parent of the src dir) by expecting 
        Note - this will not work if the current file is the __main__ since we cannot get the module name
        '''
        # assumption - this module (fabric.server.server) always hangs off the root src dir)
#        nested_depth = len(__name__.split('.')) # note this will include the module
#        return  os.path.abspath(os.path.join(os.path.dirname(__file__), os.sep.join(['..'] * nested_depth)))

        if self._proj_dir is not None:
            return self._proj_dir

        subdir = subdir or 'conf'        
        root_module = getattr(self, "root_module", None)
        if not root_module:
            root_module = inspect.stack()[-1][1]
            warn('Did not find Server.root_module. Using %s' % (root_module,))
        root_module = os.path.abspath(root_module)
        path_subset = [ os.path.abspath(s) for s in sys.path if root_module.startswith(os.path.abspath(s)) and os.path.exists(os.path.join(os.path.abspath(s), '..', subdir)) ]
        try:
            return os.path.abspath(os.path.join(path_subset[0], '..'))
        except IndexError:
            warn('Cannot determine project directory automatically. Defaulting to curr dir %s' % (os.getcwd()))
            return '.'
        
    def _get_config_files(self, conf_dir, config_file='<auto>'):
        if config_file == '<auto>':
            root_module = getattr(self, "root_module", None)
            if not root_module:
                root_module = inspect.stack()[-1][1]
                warn('Did not find Server.root_module. Using %s' % (root_module,))
            stem = os.path.splitext(os.path.basename(root_module))[0]
            config_file_stem = stem.replace('meta_', '')
            ext = '.ini'
        else:
            config_file_stem, ext = os.path.splitext(config_file)
            if ext == '': ext = '.ini'
        return (os.path.join(conf_dir, config_file_stem + ext), 
                os.path.join(conf_dir, config_file_stem + '_configspec' + ext))
        
    def _bind_callbacks(self, callbacks):
        '''
        convert unbound instance methods to bound using partial only if subclasses of Server. 
        classmethods will already be bound to the class
        @param callbacks:
        @type callbacks:
        '''
        new_callbacks = {}
        for k, v in callbacks.iteritems():
            assert(callable(v)) # v has to be a callable
            try:
                v.im_self
            except AttributeError: # it is not a method of a class or object
                pass
            else: # only for classmethods or instance methods 
                if not v.im_self and issubclass(v.im_class, Server): # unbound instance method
                    v = functools.partial(v, self)
            new_callbacks[k] = v
        return new_callbacks
                
    def configure(self, skip_overrides=False, proj_dir=None, conf_subdir='conf', config_files=None, standalone=False, **kargs):
        '''
        runs the configuration processes. If config is None, will read the default config files which are common and the stem of the file
        
        :param proj_dir: an optional argument. If specified, this is taken to be the root of the project directory.
            If not specified, this is infered through introspection
        :param conf_subdir: the configuration subdirectory within the proj_dir where configuration files may be obtained
        :param list config_files: a list of filename stems (i.e without the .ini extension) that contain the configuration for this server.
            If mulitple files are given, the order is important and files on the right may overwrite config options specified in files on the left
            A special token *<auto>* is replaced with the name of the main file that was invoked to launch this app (determined through introspection)
            Defaults to [ 'common', '<auto'> ]
        :param bool skip_overrides: controls if override processing should be skipped
        '''
        self._proj_dir = proj_dir or self._get_proj_dir(conf_subdir) or '.'
        conf_dir = os.path.join(self._proj_dir, 'conf') if self._proj_dir is not '.' else self._proj_dir
        
        config_files = [] if config_files is None else [config_files] if type(config_files) not in [list, tuple] else config_files
        
        config_callbacks = {}
        [ config_callbacks.update(c) for c in self._mro_classattribute_get('config_callbacks') ]

        config_callbacks = self._bind_callbacks(config_callbacks)
        
        config_overrides = []
        if not skip_overrides:
            config_overrides = list(reduce(lambda x,y: x+y, self._mro_classattribute_get('config_overrides'), []))
        
        config_files = [ self._get_config_files(conf_dir, f) for f in config_files ]
        
        self.config = ServerConfig(config_files=config_files, 
                                   overrides=config_overrides, callbacks=config_callbacks,
                                   env_config=dict(_proj_dir=self._get_proj_dir()))
        
        
    def stats(self):
        ''' default handlers for stats. Does nothing and returns an empty dict. Typically overridden by 
        ManagedServer
        
        :rtype: dict
        '''
        return {}
    
    def health(self):
        ''' default handlers for health. Does nothing and returns an empty dict which implies that server
        is healthy (since it could respond).
        
        :rtype: dict
        ''' 
        return {}
            
    def parse_cmmd_line(self, description='', **kargs):
        '''
        A generic method to parse command line arguments. returns a dict of { name: value }
        pairs. Each subclass could optionally define a classmethod called get_arg_parser which returns
        an ArgumentParser defined by argparse. an example of get_arg_parser and its signature can be found in
        in :py:class:`HTTPServer` 
        
        * Overlapping arguments defined by a class may be overridden in a subclass.
        * Distinct arguments in subclasses are added to the list of arguments
        * A help message combines all the arguments (super and subclasses)

        This method should be called by start_main_server with the appropriate arguments. 

        :param description: A description for the entire server (will be printed in help)
        :returns: A dict with name, value pairs (name is the explicit or implicit destination of argparse)
        '''
        
        classes = self._mro_classattribute_get('get_arg_parser')
        classes.reverse() # first is subclass
        if classes in [ None, [] ]:
            return None
        
        super_parsers = [ get_arg_parser(**kargs) for get_arg_parser in classes[1:] ]
        get_arg_parser = classes[0]
        submost_parser = get_arg_parser(description=description, add_help=True, parents=super_parsers, conflict_handler='resolve',
                                    **kargs);
        
        return vars(submost_parser.parse_args())

    def _logger_config_update(self, action, full_key, new_val, config_obj):
        '''
        Called by Config to update the logging Configuration.
        '''
        try:
            d=config_obj.dict()
            dictConfig(d.get('Logging', {}))
        except KeyError as e:
            warn('Cannot instantiate logging: %s' % (e,))
        except ValueError as e:
            warn('Incomplete logging configuration: %s' % (e,))
        self.logger = logging.getLogger()


