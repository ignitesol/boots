from barrel.form import FormAuth
import re
import logging
from boots.common.template import BootsTemplate
import collections
from test.test_support import temp_cwd

class SimpleAuth(FormAuth):
    '''
    Custom Web Form authentication middleware. This middleware forms a WSGI app that can sit in the request stack, intercept
    all requests and check if the requestor is authenticated. While largely built on capabilities of the barrel middleware, the 
    custom additions include a list of open_urls that are allowed to execute without being tested for authentication.
    
    SimpleAuth relies on a session management middleware(i.e.Beaker) upfront in the stack. 
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
                <legend style="text-align: center; margin: 0px 0px 10px 0px">{{args['message']}}:</legend>
                <br>
                <label for="username" style="margin: 2px;">Username:</label>
                <input type="text" name="username" id={{args['user_field']}} value="" style="margin: 2px;"></input>
                <br><br>
                <label for="password" style="margin: 2px;">Password:</label>
                <input type="password" name="password" id={{args['pass_field']}}  style="margin: 2px 2px 2px 5px;"></input>
                <br><br>
                <button type="submit" name={{args['button']}} id="barrel-form-button" value="submit">Sign In</button> 
                <br><br><legend style="text-align: left; margin: 10px 0px 20px 0px">
                            If you forgot your username or password, please contact the administrator</legend>
            </center>
        </form>
    </div>
</body>
</html>
    ''' 
    def __init__(self, app, logins=None, open_urls=None, session_key='barrel.session', template=None, template_args={}, domain_setter=None, remote_user_key='REMOTE_USER', **kargs):
        '''
        Take the app and template to wrap and optional settings.

        @param app: - The app instance to be used.
        @type app: WSGI middleware application.
        
        @param template: - The template containing a HTML page.
        @type template: string (using BootsTemplate syntax)
        
        @param users: - The list of authenticated users.
        @type users: List of Tuples
        
        @param open_urls: - regular expressionn patterns for url which are open.
        @type open_urls: List of Patterns
        
        @param session_key: - The key used to store the session in.
        @type session_key: str
        
        :param remote_user_key: optional. If specified, indicates the environ key in which the authenticated user information is stored. Defaults to REMOTE_USER 

        '''
        self.unsecure_urls = open_urls or []
        self.unsecure_compiled_urls = [ re.compile(p) for p in self.unsecure_urls ]
        self.domain_setter = domain_setter
        self.remote_user_key = remote_user_key
        
        self.app = app
        super(SimpleAuth, self).__init__(app, logins)
        self.session_key = session_key
        self.template = template or BootsTemplate(self.loginpage)
        self.template_args = collections.defaultdict(str)
        self.template_args.update(template_args)
        self.fallback_template = BootsTemplate(self.loginpage)
        
    def cache_username(self, environ, username):
        '''
        this wrapper to cache_username is used to allow multiple levels of auth. The BasicAuth object always sets REMOTE_USER
        We may not want REMOTE_USER to be set for secondary auths. So, if remote_user_key was specifed, we save the current value of REMOTE_USER
        and reset it after the call to super. We also 
        ''' 
        if self.remote_user_key is not 'REMOTE_USER': 
            remote_user = environ.pop('REMOTE_USER', None) # get the original REMOTE_USER and clear it
            
        # let super set REMOTE_USER
        retval = super(SimpleAuth, self).cache_username(environ, username)
        
        if self.remote_user_key is not 'REMOTE_USER':
            # save the set REMOTE_USER in self.remote_user_key
            environ[self.remote_user_key] = environ.pop('REMOTE_USER', None)
            # reset the orig REMOTE_USER
            if remote_user is not None: environ['REMOTE_USER'] = remote_user
            
        return retval
    
    @classmethod
    def root_level_domain(cls, full_domain):
        ''' 
        returns a tuple - the last 2 of the domain-name
        '''
        if full_domain == None:
            return ''
        domain = full_domain
        #If it seems like an ip address dont change the domain
        try:
            map(int, domain.split('.'))
            return domain
        except:
            if domain != '.'.join(domain.split('.')[-2:]):
                return '.'.join(domain.split('.')[-2:]).split(':')[0]
        
    def __call__(self, environ, start_response):
        '''
        If request is not from an authenticated user, check if the path is secured if yes then challenge.
        '''
        # obtain the beaker session and ensure that we set the session domain to just the domainname portion as opposed to the hostname
        # this is useful since we have shared authentication (using shared sessions) across multiple servers and hence the session
        # cookie will be passed to all those servers.Only doing this if format is x.y or x.y... 
        #Due to beaker cookie session problems in setting non dotted session domain. 

        if self.domain_setter:
            session = environ.get(self.session_key)
            session.domain, session.path = self.domain_setter(environ.get('SERVER_NAME'))
            session.path = '/'
        
        path =   environ.get('SCRIPT_NAME', '') + ("" if environ.get('SCRIPT_NAME', '')[-1:] == '/' else '/') + environ.get('PATH_INFO', '')
        
        #logging.getLogger().debug('Authenticator %s: checking open url %s against %s', type(self), path, self.unsecure_urls)
        
        # determine if the url is unsecure
        if list(filter(None, [ p.search(path) for p in self.unsecure_compiled_urls ])) != []:
            #logging.getLogger().debug('Authenticator %s: Skipping open url %s', type(self), path)
            return self.app(environ, start_response)
        
        # invoke barrel
        return super(SimpleAuth, self).__call__(environ, start_response)
    
    def not_authenticated(self, environ, start_response):
        '''
        Overridden so that Cache-Control can be added,
        Copied from barrel/form.py
        '''
        start_response('200 OK', [('Content-Type', 'text/html'), ('Cache-Control', 'no-cache')])
        username = environ.get(self.environ_user_key, '')
        if username:
            message = self.failed_message
        else:
            message = self.first_message
        
        # if self.template is callable, call it with the environ. It should return a BootsTemplate object on which we can call render
        try:
            template = (self.template(environ) if callable(self.template) else self.template) or self.fallback_template
        except Exception as e:
            logging.getLogger().exception('Failed template finder: %s', e)
            template = self.fallback_template
        
        template_args = collections.defaultdict(str)
        template_args.update(self.template_args) # make a copy
        template_args.update(environ) # update with environ
        return [ str(template.render(args=template_args)) ]
    
    

if __name__ == '__main__':
    import bottle
    import beaker.middleware as bkmw

    config_obj = dict(
        BootsAuth = dict(
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
    app = SimpleAuth(app, users=users, 
                    open_urls=config_obj['BootsAuth']['open_urls'], 
                    session_key=config_obj['BootsAuth']['key'])
    app = bkmw.SessionMiddleware(app, 
                                 config_obj['BootsAuth']['beaker'], 
                                 environ_key=config_obj['BootsAuth']['key'])


    @bottle.route(path='/', method='ANY')
    def index():
        return 'hello world <a href="/secure">secure route</a>';
    
    @bottle.route(method='ANY')
    def secure():
        return 'secure route <a href="/">home page</a>';
        
    bottle.debug(True)
    bottle.run(app=app, port=9999, reloader=False)
    
