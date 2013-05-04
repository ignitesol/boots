=================
Starting Servers 
=================

Server's start_server is used to start a server.
Here, *standalone* indicates that this server is not being invoked from another WSGI container and that it should bind to the appropriate host and port. 
The default host is *127.0.0.1* and the default port is *8080*. 
::
	if __name__ == "__main__":
		server.start_server(standalone=True, description='A test server for the boots framework')

You can specify host and port accordingly.
::
	if __name__ == "__main__":
		server.start_server(standalone=True, description='A test server for the boots framework', defhost='localhost', defport=8888)

