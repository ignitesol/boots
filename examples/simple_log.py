'''
*******************************
Configuration through ini files
*******************************

Now that we understand endpoints and parameter passing, let us take a look at configuring servers. 
Boots uses a slightly modified version of configobj_ to provide configurations. The modifications 
are primarily to introduce *callbacks* when any configuration item changes - allowing runtime updates to configuration to be managed and propagated throughout the server.

.. _configobj: http://www.voidspace.org.uk/python/configobj.html

*******
Logging
*******

This example demonstrates basic logging with a config file. The config file used in this case is the 
*conf/common.ini* file:: 

	percent = %
	[Logging]
		version = 1
		[[root]]
			level = INFO
			handlers = console,		
		[[handlers]]
			[[[console]]]
				class = logging.StreamHandler
				level = INFO
				formatter = detailed
				stream = ext://sys.stdout
		[[filters]]
		[[formatters]]
			[[[detailed]]]
				format = ${percent}(levelname)s:${percent}(asctime)s: ${percent}(message)s

Here the **percent = %** and the use of **${percent}** demonstrates interpolation as defined by configobj_. A standard interpolation variable introduced by boots is **_proj_dir** which represents the project root. This is typically determined automatically by boots and boots expects a *conf* subdir within the project root to hold the config files. These can be overridden by parameters to *start_server*::

	main_server.start_server(proj_dir='.', conf_subdir='conf', defhost='localhost', defport=9999, standalone=True, description="Simple logging setup")

By default, boots looks for an ini file in the *conf* folder with the same name as the python file invoked (in this example's case *simple_log.ini*). Moreover, it also looks for *common.ini* and meregs common.ini with <filename>.ini such that <filename.ini> overrides any configurations in common.ini. This behavior, too, can be controlled by parameters.

Certain aspects of the configurations are understood by boots (but can be overridden). These are
* logging
* session
* caching

In this example, we will see how logging is turned on or off. The relevant section of the ini file is displayed above. When the server object is created, we can control whether logging should be on by passing a boolean to the *logger* argument::

	main_server = HTTPServer(endpoints=[EP()], logger=True)

logging is prevalent in boots and logger objects are created for the server and every endpoint (More on this later). You can use the logger directly in an endpoint as self.logger::

    @methodroute()
    def hello(self, name=None):
        name = name or 'world'  # the name is passed as an argument
        self.logger.info('hello called with %s', name)
        return 'hello %s' % name
 
'''
import boots

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute    
    
class EP(HTTPServerEndPoint):

    @methodroute()
    def hello(self, name=None):
        name = name or 'world'  # the name is passed as an argument
        self.logger.info('hello called with %s', name)
        return 'hello %s' % name
    
main_server = HTTPServer(endpoints=[EP()], logger=True)

if __name__ == '__main__':
    main_server.start_server(defhost='localhost', proj_dir='.', conf_dir='conf', defport=9999, standalone=True, description="Simple logging setup")
