=====================
Configuration Files 
=====================
Configuration files are used for server process settings. Boots utilizes config files as specified by ConfigObj_
Config files are searched in project's root directory. 
${_proj_dir} can be used in config files to specify a relative path from project's root directory. 

.. _ConfigObj: http://www.voidspace.org.uk/python/configobj.html
 

Location of config files
--------------------------
Boots searches for config files in 'conf' folder of the project's root folder. 
In order to change it's search path, change the conf_subdir and proj_dir accordingly when invoking start_server

::

	    my_server.start_server(standalone=True, conf_subdir=".", \
                         description="To read configuration file", defhost="localhost", defport=8081)
	  
	  
Which config files are loaded
-------------------------------
Boots can load multiple config files and merge them.

Special keyword auto: boots replaces the keyword '<auto>' with the stem of the main python file followed by ini. For example, if your 
main program is my_server.py, then specifying <auto> in the config files will inform boots to load my_server.ini  

By default, the configuration files associated are common.ini and <auto>.  
You can provide multiple configuration files. For overlapping sections in between files, the rightmost one takes precedence. 
Boots doesn't complain if no config files are specified or loaded.

Accessing config
---------------------------
config is stored in server object as a dict. These can be accessed from the server as

::  

	self.config

or from an endpoint as 

::

	self.server.config
	


Handling configuration through callbacks
-----------------------------------------
A callback is registered on the config_obj and every read/update event on config file results in this callback to be called.
Here, every time 'Database' section of config file is read, it's registered callback, 'self.setup_conn_pool' is called. ::

    def __init__(self, *args, **kargs):
        self.config_callbacks['Database'] = self.setup_conn_pool
        super(MyServer, self).__init__(*args, **kargs)
        

Special config Sections 
------------------------
Logging
^^^^^^^^
Boots uses Python's Logging_ facility to enable logging. 
The following shows logging section of a common config file. 
Common levels that can be used for logging purpose are 

.. _Logging: http://docs.python.org/2/library/logging.config.html

* WARNING
* EXCEPTION
* ERROR
* DEBUG

::

	[Logging]
	version = 1
	#disable_existing_loggers  = True
	[[root]]
		level = NOTSET
		handlers = console,		
	[[handlers]]
		[[[console]]]
			class = logging.StreamHandler
			level = DEBUG
			formatter = detailed
			stream = ext://sys.stdout
		[[[file]]]
			class = logging.FileHandler
			filename = output.log # override in specific ini file
			level = DEBUG
			mode = a
			formatter = detailed
		[[[rotatingfile]]]
			class = logging.handlers.RotatingFileHandler
			filename = 	output.log # override in specific ini file
			level = DEBUG
			formatter = detailed
			maxBytes = 1024 			
			backupCount = 5
	[[formatters]]
		[[[detailed]]]
			format = 
	[[loggers]]
		[[[SPARX]]]
			propagate = True
			level = DEBUG
			#handlers = file,	

Session
^^^^^^^^
Boots uses Beaker_ to enable sessions.
To start a session, it is mandatory to provide a session key in the config file. 
A simple session section of a config file is shown below.
To learn more on Boots sessions, refer :doc:`../http_server/session`.

.. _Beaker: https://pypi.python.org/pypi/Beaker

::

	[Session]
	session.key = session_key
	session.type = memory
	session.cookie_expires = True
	session.auto = True
	
	
Caching
^^^^^^^^
Boots uses Beaker_ to enable caching.
Refer :doc:`../http_server/cache` for more information.

.. _Beaker: http://beaker.readthedocs.org/en/latest/caching.html

::

	[Caching]
	cache.enabled = True
	cache.regions = datastore
	cache.datastore.type = ext:memcached
	cache.datastore.url = 127.0.0.1:11211
	cache.datastore.expire = 7200
	cache.datastore.lock_dir = /home/cache
