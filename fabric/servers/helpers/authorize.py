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
    def __init__(self, app, users=None, open_urls=None, session_key=None, template=None, oauth_callback_urls=None):
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
        super(FabricSimpleAuth, self).__init__(app, users)
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
        
        path = environ.get('PATH_INFO', '')
        
        # determine if the url is unsecure
        if list(filter(None, [ p.match(path) for p in self.unsecure_compiled_urls ])) != []:
            return self.app(environ, start_response)
        
        # invoke barrel
        return super(FabricSimpleAuth, self).__call__(environ, start_response)
    
class SocialAuth(FabricSimpleAuth):
    
    _mixin_loginpage = '''
<!DOCTYPE html>
<html>
<head>
    <META HTTP-EQUIV="CACHE-CONTROL" CONTENT="NO-CACHE">
    <script src="/lib/dojo.minified/dojo.min.js" type="text/javascript" djConfig="parseOnLoad:true"></script>
    <script src="/oauth.js"></script>
    <title>Login with your social network</title>
    <style>
        btn {
            border-color: #c5c5c5;
            display: inline-block;
            padding: 4px 12px;
            line-height: 20px;
            color: #333333;
            text-align:center;
            vertical-align: middle;
            cursor: pointer;
            text-shadow: 0 1px 1px rgba(255, 255, 255, 0.75);
            background-color: #f5f5f5;
            background-image: -webkit-linear-gradient(top, #ffffff, %e6e6e6);
            border: 1px solid #bbbbbb;
        }
    </style>
</head>

<body>
    <div>
    <br>
        <center>
        <br><br>
        <button class="btn" onclick="SPARXOAuth.authorize(SPARXOAuth.Providers.Twitter, function(resp) { window.open(resp.popup_url); });">Login with Twitter</button>
        <br>
        <button class="btn" onclick="SPARXOAuth.authorize(SPARXOAuth.Providers.Facebook, function(resp) { window.open(resp.popup_url); });">Login with Facebook</button>
        <br>
        <button class="btn" onclick="javascript: history.back();">Cancel</button>
        </center>
    </div>
</body>
</html>
    '''
    
    def __init__(self, app, users=None, open_urls=None, session_key=None, template=None, oauth_callback_urls=None):
        self.oauth_callback_urls = oauth_callback_urls or []
        template = template or Template(self._mixin_loginpage)
        super(SocialAuth, self).__init__(app, users=users, open_urls=open_urls, session_key=session_key, template=template)
        
    def authenticate(self, environ):
        """Is this request from an authenicated user? (True or False)"""
        
#        logging.getLogger().debug('Session key %s, session = %s, session_user_key %s, session[session_user_key] = %s', self.session_key, environ.get(self.session_key), self.session_user_key, environ.get(self.session_key).get(self.session_user_key))
        username = self.get_cached_username(environ)
        if username is not None:
            environ[self.environ_user_key] = username
            self.cache_username(environ, username)
            return True
            
        return False
       
    def __call__(self, environ, start_response):

        # if this request is not authenticated and this path is a callback path
        # set up a method to update the user in the cookie
        # this has to be called before the return starts being processed so that the cookie
        # headers can be sent before the body 
        path_info = environ.get('PATH_INFO', '')
        if path_info in self.oauth_callback_urls and not self.authenticate(environ):
            environ['_IGN_SETUSER'] = lambda username: self.cache_username(environ, username)
        
        ret = super(SocialAuth, self).__call__(environ, start_response)
        return ret
        

    
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
    