=======
Server
=======

.. automodule:: boots.servers.server

Starting Servers
=================

Creating a Server object is not adequate to start it. The Server object's start_server is used to start a server. In this example, *standalone* indicates that this server is not being invoked from another WSGI container and that it should bind to the appropriate host and port.
.. `bottle <http://bottlepy.org>`_
The default host is *127.0.0.1* and the default port is *9000* (refer bottle_).::

	if __name__ == "__main__":
		server.start_server(standalone=True, description='A test server for the boots framework')

You can specify host and port accordingly.
::

	if __name__ == "__main__":
		server.start_server(standalone=True, description='A test server for the boots framework', defhost='localhost', defport=8888)

Configuring Servers
===================

Boots provides a standard way of configuring servers through configuraiton files. Boots utilizes config files as specified by ConfigObj_

.. _ConfigObj: http://www.voidspace.org.uk/python/configobj.html

A typical challenge in complex projects is determining where the configuration files will be present. Boots provides a standard way for any of the python modules to determine the location (and oftentimes the name) of the configuration file to be used.

Location of config files
--------------------------
Boots expects configuration files (ini files) and their validation specs (_configspec.ini files) to be always available in a standard location. By default, the standard location is relative to the project root directory.

The project root is (typically) determined implicitly by boots by introspecting the call stack. One can override this behavior by explicitly passing the project root dir when starting a server.

Config files are searched in project's root directory in a subdir specified by conf_subdir (defaults to *conf*)::

	my_server.start_server(standalone=True, proj_dir=".", conf_subdir="myconf", \
                           description="Config File Test Server")


Which config files are loaded
-------------------------------
Boots can load multiple config files and merge them. This allows common config for the project to be maintained in separate files and then have more specific config files for individual servers. The list of config files for a particular server are specified as the *config_files* argument to *start_server*.

This argument takes only the stem name of the files (e.g. myconf.ini should be specified as config_files=['myconf']). A special keyword *<auto>* in the config_files list is replaced with the stem of the main python file followed by ini. For example, if your
main program is my_server.py, then specifying *config_files=['shared_config', '<auto>' ] will result in boots loading *shared_config.ini*, merging to it (and hence overriding with values from) *my_server.ini* and creating a final config.

If files with the name *<stemname>_configspec.ini* are present, they are used to validate the configs for types and assign default values (refer configobj_)

The default value for *config_files* is *[ 'common', '<auto>']*.

You can provide multiple configuration files. For overlapping sections in between files, the rightmost one overwrites the similar sections present in earlier files.
Boots doesn't complain if no config files are specified or loaded.


Which config files are loaded
-------------------------------
Boots can load multiple config files and merge them.

Special keyword auto: boots replaces the keyword '<auto>' with the stem of the main python file followed by ini. For example, if your
main program is my_server.py, then specifying <auto> in the config files will inform boots to load my_server.ini

By default, the configuration files associated are common.ini and <auto>.
You can provide multiple configuration files. For overlapping sections in between files, the rightmost one takes precedence. Boots doesn't complain if no config files are specified or loaded.

Format of config files
----------------------
Config files adhere to the structure specified in configobj_ with template based interpolation.

A special interpolation variable ${_proj_dir} is prepopulated by boots to be the project directory, allowing config information to specify paths relative to the project's root directory. Some typical uses of this are for having fixed places to output log files.

Accessing config
---------------------------
After *start_server* is called, the server's config is accessible from an object attribute *config*. The config is stored as a dict (refer configobj_) These can be accessed from the server as

::

	self.config

or from an endpoint as

::

	self.server.config

Handling configuration through callbacks
-----------------------------------------
Boots has added a callback mechanism to configobj_. The callback mechanism is to invoke a method associated with any section of the config if any part of the information in that config changes at runtime. The registered callback is, thus, called when the server initializes (and the config is read for the 1st time) and also at any time when the information in that config section changes. This allows management of servers through updates to the config. Consider a management console that can read the config from a server through a standard method, show the config using a user interface and push any changes made from the console back to the config in the server. Changes to the config will result in a callback being invoked, which in-turn will change server behavior. A simple (SNMP-ish) behavior can now be implemented (and is done by :py:class:`ManagedServer`).

A callback is registered through addition of the callback to a dict *config_callbacks* in the server object. The key of the dict should be the Section (or subsection) of the config file, changes to which will result in the callback being invoked.

In the following example, every time 'Database' section of config file is updated (or initially created), it's registered callback, *self.setup_conn_pool* is called. ::

    def __init__(self, *args, **kargs):
        self.config_callbacks['Database'] = self.setup_conn_pool
        super(MyServer, self).__init__(*args, **kargs)


Enabling Logging
=================

Boots understands a few config sections automatically. For instance, to enable logging, when creating the server object, just passing *logger=True* will instruct boots to look for a **Logging** section in the config and use that to instantiate loggers (refer to examples/simple_log.py)::

	main_server = HTTPServer(endpoints=[EP()], logger=True)

Parsing and Using Command Line Arguments
========================================

Boots lets you leverage command line tool with the help of Python's argparser.
Server's get_arg_parser returns an ArgumentParser which can be used to traverse/add command line arguments::

    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=[], conflict_handler='error', **kargs):
        argparser = argparse.ArgumentParser(description=description, add_help=add_help,
        parents=parents, conflict_handler=conflict_handler)
        argparser.add_argument('-d', '--demo', dest='demo', default='hello', help='test:  (default: world)')
        argparser.add_argument('--intval-demo', default=0, type=int, help='test an int val:  (default: 0)')

Server's cmmd_line_args is a dict holding server's command line arguments.
The following code uses this to display specified command line arguments.::

    @methodroute(path="/demo", method="GET")
    def demo(self):
        format_str = '{key}: {value}' if not self.server.cmmd_line_args['verbose'] else 'The value of {key} is {value}'
        return '<br/>'.join([ format_str.format(key=k, value=self.server.cmmd_line_args[k]) for k in [ 'demo', 'intval_demo' ]])

Adding Endpoints
================
.. note:: Needs improvement

EndPoints are a gateway to the Server. In a simple HTTPServer, they offer flexibility of adding routes (urls where HTTP can be served from), providing parameter processing and validation capabilities.

An endpoint may be added to the server before/after start_server.

Adding before start of server
------------------------------

Endpoints can be added while instantiating a server as shown below.
This enables the endpoint to receive requests at start of the server itself::

	class EP(HTTPServerEndPoint):
		pass

	ep1 = EP()
	main_server = HTTPServer(endpoints=[ep1])

We can specify a mountpoint while adding endpoints.
If a mountpoint is specified for an endpoint, then all routes start from it: /<mountpoint>/<route>
Here, we need to call /admin/<route> instead of /<route>.
::

	my_server = HTTPServer(endpoints=[EP(mountpoint="/admin")])


Adding after start of server
----------------------------------

If added after start_server, it is assumed to be activated.
This way multiple endpoints may be added to the server.
::

	db_ep = EP()
	self.add_endpoint(db_ep)
