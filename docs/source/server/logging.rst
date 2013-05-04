===============
Simple Logging 
===============

Boots let you log request and response in a simple manner.   

::

	main_server = HTTPServer(endpoints=[ep1], logger=True)
	

Refer :doc:`../server/config` to learn about config files and its sections.
Under *Logging* section of config file, set handlers. 	
::

	[[root]]
	level = NOTSET
	handlers = console,rotatingfile, 
		
		
Set an appropriate level.
Common levels that can be used for logging purpose are:

* WARNING		
* EXCEPTION
* ERROR
* DEBUG

The log file name must be mentioned under *filename*. 
This creates a log file when the config file is read.
*maxBytes* limits the memory to be used per log file. 
*backupCount* limits number of times a log file is created. 
For example, backupCount = 5 will create 5 log files, one for each run. On the next subsequent run it 
deletes the previous files before creating a new log file.
::

	[[handlers]]
	[[[console]]]
		class = logging.StreamHandler
		level = DEBUG
		formatter = detailed
		stream = ext://sys.stdout
	[[[file]]]
		class = logging.FileHandler
		filename = first.log # override in specific ini file
		level = DEBUG
		mode = a
		formatter = detailed
	[[[rotatingfile]]]
		class = logging.handlers.RotatingFileHandler
		filename = 	first.log # override in specific ini file
		level = DEBUG
		formatter = detailed
		maxBytes = 1024 			# 1K
		backupCount = 5
		


Finally, a small step to specify logging for a particular level:		
::

	self.server.logger.debug('hello called with %s', name)
	
The log file is created in the project's root folder.
	
	
