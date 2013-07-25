=========
Session
=========

Based on session configuration in config file, a session can be instantiated while instantiating a server. 
To start a session, a *session.key* in config file is necessary. 
::

	[Session]
		session.key = session_key
		session.type = memory
		session.cookie_expires = True
		session.auto = True


The param, 'session' should be set to *True* while instantiating a server. 
::

	main_server = HTTPServer(endpoints=[ep1], session=True)
	

Arguments from a session can be retrieved in the following manner. 
EndPoint's *session* returns a session related to this request if one is configured.	
::

        self.session['name'] = name
        self.session['count'] = self.session.get('count', 0) + 1
        return 'hello %s - you have called me %d times' % (capitalize(name), self.session['count'])
	