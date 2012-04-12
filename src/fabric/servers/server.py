'''
Created on Mar 21, 2012

@author: AShah
'''
from fabric import concurrency

if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
elif concurrency == 'threading':
    pass

from warnings import warn
import inspect
import sys
import os
import functools
from fabric.servers.helpers.serverconfig import ServerConfig
from logging.config import dictConfig

from fabric.common.utils import new_counter

class Server(object):
    _name_prefix = "Server_"
    counter = new_counter()
    
    ## settings for configuration and callbacks. Override or add in subclasses
    # config_callbacks is initialized outside the class (see below) so as to allow reference to class instance methods 
    # alternately, set up the instance methods within the constructor
    config_callbacks = { }
    config_overrides = [ ('Logging.formatters.detailed.format', '%(levelname)s:%(asctime)s:[%(process)d:%(thread)d]:%(funcName)s: %(message)s'),
                        ] # override the logging format 
    
    def __init__(self, name=None, endpoints=None, parent_server=None, **kargs):
        '''
        optional argument: logger (bool) controls logging
        '''
        self.name = name or self._name_prefix + str(Server.counter()) # _name_prefix will be from subclass if overridden
        self.endpoints = endpoints or []
        self.sub_servers = []
        self.parent_server = parent_server
        self.config = {}
        self._proj_dir = None
        logger = kargs.get('logger', False)
        if logger: self.__class__.config_callbacks['Logging'] = Server.logger_config_update # defined in this class
        
    def add_sub_server(self, server, mount_prefix=None):
        if mount_prefix is not None: server.mount_prefix = mount_prefix 
        self.sub_servers += [ server ]

    def start_server(self, parent_server=None, proj_dir=None, conf_subdir='conf', config_files=['common', '<auto>' ], description=None, **kargs):
        '''
        start_server does the initialization for the server. NOTE, while start_server would have
        access to the cmmd_line arguments, the configuration is not read when it is invoked.
        Rather, after all the start servers have been invoked, the configuration is read and 
        ideally callbacks of the configuration are called.
        Finally, the start_main_server is invoked.
        
        self.root_server.cmmd_line_args is a dict holding the command line arguments for all servers (main or sub)
        
        start_server is invoked by the master server with parent_server = None (default).  
        It activates all its endpoints, then starts all its sub-servers.
        @param parent_server: a reference to this server's parent server (None implies outermost i.e. the final subclass)
        @type parent_server: subclass of Server
        @param description: for purposes of help messages on cmmd line
        @type description: str
        @param file: the __file__ of the mainserver. Used only by the main server. None implies no configuration read
        @type file: str
        '''

        self.parent_server = parent_server or self.parent_server
        self.is_master = self.parent_server == None
        self.root_server = self if self.is_master else self.parent_server.root_server
        
        if self.is_master:
            self.cmmd_line_args = self.parse_cmmd_line(description, **kargs)
                
        if self.is_master:
            self.configure(proj_dir=proj_dir, conf_subdir=conf_subdir, config_files=config_files)
        
        self.activate_endpoints()
        self.start_all_sub_servers()
        
        if self.is_master:
            self.start_main_server()
            
    # these can be overridden defined by the subclasses
    def activate_endpoints(self):
        '''
        Activate this server's endpoints
        '''
        pass

    def start_all_sub_servers(self):
        [ server.start_server(parent_server=self) for server in self.sub_servers ]
            
    def start_main_server(self):
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
    
    def get_proj_dir(self, subdir=None):
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
        root_module = inspect.stack()[-1][1]
        path_subset = [ s for s in sys.path if root_module.startswith(s) and os.path.exists(os.path.join(s, '..', subdir)) ]
        try:
            return os.path.abspath(os.path.join(path_subset[0], '..'))
        except IndexError:
            warn('Cannot determine project directory automatically. Defaulting to curr dir %s' % (os.getcwd()))
            return '.'
        
    def _get_config_files(self, conf_dir, config_file='<auto>'):
        if config_file == '<auto>':
            root_module = inspect.stack()[-1][1]
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
                
    def configure(self, skip_overrides=False, proj_dir=None, conf_subdir='conf', config_files=None, **kargs):
        '''
        runs the configuration processes. If config is None, will read the default config files which are common and the stem of the file
        @param file: the main server filename or None. If None, no file processing is done 
        @type file: str
        @param skip_overrides: should we skip any override processing?
        @type skip_overrides: bool
        '''
        self._proj_dir = proj_dir or self.get_proj_dir(conf_subdir) or '.'
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
                                   env_config=dict(_proj_dir=self.get_proj_dir()))
        
        
    def stats(self):
        return {}
    
    def health(self):
        return {}
            
    def parse_cmmd_line(self, description='', **kargs):
        '''
        A generic method to parse command line arguments. returns a dict of { name: value }
        pairs. Each subclass could optionally define a classmethod called get_arg_parser which returns
        an ArgumentParser defined by argparse. an example of get_arg_parser and its signature can be found in
        in this class and in HTTPServer
        ** Overlapping arguments defined by a class may be overridden in a subclass.
        ** Distinct arguments in subclasses are added to the list of arguments
        ** A help message combines all the arguments (super and subclasses)
        **
        This method should be called by start_main_server with the appropriate arguments. 
        @param description: A description for the entire server (will be printed in help)
        @type description: str
        @return: A dict with name, value pairs (name is the explicit or implicit destination of argparse)
        '''
        
        classes = self._mro_classattribute_get('get_arg_parser')
        classes.reverse() # first is subclass
        if classes in [ None, [] ]:
            return None
        
        super_parsers = [ _get_arg_parser(**kargs) for _get_arg_parser in classes[1:] ]
        _get_arg_parser = classes[0]
        submost_parser = _get_arg_parser(description=description, add_help=True, parents=super_parsers, conflict_handler='resolve',
                                    **kargs);
        
        return vars(submost_parser.parse_args())

    def logger_config_update(self, action, full_key, new_val, config_obj):
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


