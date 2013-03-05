'''
Created on 18-Oct-2011

@author: harsh
'''
    
from barrel.form import FormAuth
import re
from string import Template

class FabricSimpleAuth(FormAuth):
    '''
    Custom Web Form authentication middleware. This middleware forms a WSGI app that can sit in the request stack, intercept
    all requests and check if the requestor is authenticated. While largely built on capabilities of the barrel middleware, the 
    custom additions include a list of open_urls that are allowed to execute without being tested for authentication.
    
    FabricSimpleAuth relies on a session management middleware(i.e.Beaker) upfront in the stack. 
    '''
    loginpage ='''
   <!DOCTYPE html>
<html>
<head>
<META HTTP-EQUIV="CACHE-CONTROL" CONTENT="NO-CACHE">
    <title>Login</title>
</head>

<body>
    <div>
        <br><br><br>
        <form method="POST" style="border: none" action="">
            <center>
                <legend style="text-align: center; margin: 0px 0px 10px 0px">${message}:</legend>
                <br>
                <label for="username" style="margin: 2px;">Username:</label>
                <input type="text" name="username" id=$user_field value="" style="margin: 2px;"></input>
                <br><br>
                <label for="password" style="margin: 2px;">Password:</label>
                <input type="password" name="password" id=$pass_field  style="margin: 2px 2px 2px 5px;"></input>
                <br><br>
                <button type="submit" name=$button id="barrel-form-button" value="submit">Sign In</button> 
                <br><br><legend style="text-align: left; margin: 10px 0px 20px 0px">
                            If you forgot your username or password, please contact the administrator</legend>
            </center>
        </form>
    </div>
</body>
</html>
    ''' 
    def __init__(self, app, logins=None, open_urls=None, session_key='barrel.session', template=None, **kargs):
        '''
        Take the app and template to wrap and optional settings.

        @param app: - The app instance to be used.
        @type app: WSGI middleware application.
        
        @param template: - The template containing a HTML page.
        @type template: String.Template
        
        @param users: - The list of authenticated users.
        @type users: List of Tuples
        
        @param open_urls: - regular expressionn patterns for url which are open.
        @type open_urls: List of Patterns
        
        @param session_key: - The key used to store the session in.
        @type session_key: str
        
        @param oauth_callback_urls: A list of paths (optional) that are special since these obtain the response
        from the social network callbacks and will put the REMOTE_USER into the environment. 
        If this parameter is not specified, the OAuthMixin does not do anything and the basic FormAuth processing takes place
        '''
        self.unsecure_urls = open_urls or []
        self.unsecure_compiled_urls = [ re.compile(p) for p in self.unsecure_urls ]
        
        self.app = app
        super(FabricSimpleAuth, self).__init__(app, logins)
        self.session_key = session_key
        self.template = template or Template(self.loginpage)

        
    def __call__(self, environ, start_response):
        '''
        If request is not from an authenticated user, check if the path is secured if yes then challenge.
        '''
        # obtain the beaker session and ensure that we set the session domain to just the domainname portion as opposed to the hostname
        # this is useful since we have shared authentication (using shared sessions) across multiple servers and hence the session
        # cookie will be passed to all those servers.Only doing this if format is x.y or x.y... 
        #Due to beaker cookie session problems in setting non dotted session domain. 

        session = environ.get(self.session_key)
        domain = environ.get('SERVER_NAME')
        session.path = '/'
#        logging.getLogger().debug('Domain: %s', domain)
        #If it seems like an ip address dont change the domain
        try:
            map(int, domain.split('.'))
            session.domain = domain
        except:
            if domain != '.'.join(domain.split('.')[-2:]):
                session.domain = '.'.join(domain.split('.')[-2:]).split(':')[0]
        
        path = environ.get('SCRIPT_NAME', '') + '/' + environ.get('PATH_INFO', '')
        
        # determine if the url is unsecure
        if list(filter(None, [ p.search(path) for p in self.unsecure_compiled_urls ])) != []:
            return self.app(environ, start_response)
        
        # invoke barrel
        return super(FabricSimpleAuth, self).__call__(environ, start_response)
    

    
if __name__ == '__main__':
    import bottle
    import beaker.middleware as bkmw

    config_obj = dict(
        FabricAuth = dict(
            open_urls = ['/$'],
            key = 'barrel.session',
            auth_key = 'auth',
            # cookie based
            beaker = {
                'session.type' : 'cookie',
                'session.validate_key' : 100,
                'session.encrypt_key' : 200,
                'session.auto' : True,
                'session.cookie_expires' : False,
                'session.key' : 'auth'
            }
        )
    )
    
    users = [('demo', 'demo')]
    app = bottle.default_app()
    app = FabricSimpleAuth(app, users=users, 
                    open_urls=config_obj['FabricAuth']['open_urls'], 
                    session_key=config_obj['FabricAuth']['key'])
    app = bkmw.SessionMiddleware(app, 
                                 config_obj['FabricAuth']['beaker'], 
                                 environ_key=config_obj['FabricAuth']['key'])


    @bottle.route(path='/', method='ANY')
    def index():
        return 'hello world <a href="/secure">secure route</a>';
    
    @bottle.route(method='ANY')
    def secure():
        return 'secure route <a href="/">home page</a>';
        
    bottle.debug(True)
    bottle.run(app=app, port=9999, reloader=False)
    