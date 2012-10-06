'''
Created on 18-Oct-2011

@author: harsh
'''
    
from barrel.form import FormAuth
import re
from string import Template

class SparxAuth(FormAuth):
    '''
    Custom Web Form authentication middleware. This middleware forms a WSGI app that can sit in the request stack, intercept
    all requests and check if the requestor is authenticated. While largely built on capabilities of the barrel middleware, the 
    custom additions include a list of open_urls that are allowed to execute without being tested for authentication.
    
    SPARXAuth relies on a session management middleware(i.e.Beaker) upfront in the stack. 
    '''
    loginpage ='''
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
<META HTTP-EQUIV="CACHE-CONTROL" CONTENT="NO-CACHE">
    <link href="/css/styles.css" rel="stylesheet" type="text/css" />

    <title>SPARX Suite by Ignite Solutions</title>
    
</head>

<body>
    <div id="login-body" class="bw">
        <div class="black_overlay"></div>
        <div class="loginbg">
            <div class="login_content">
            <br>
                <center>
                <img src="/images/logo_splash_screen.png" width=50% alt="" />
                </center>
                <br><br>
                <form method="POST" style="boder: none" action="">
                <center>
                    <legend style="text-align: center; margin: 0px 0px 10px 0px">${message}:</legend>
                    <br>
                    <label for="username" style="margin: 2px;">Username:</label>
                    <input class="textbg" type="text" name="username" id=$user_field value=""
                        style="margin: 2px;"></input>
                    <br><br><label for="password" style="margin: 2px;">Password:</label>
                    <input class="textbg" type="password" name="password" id=$pass_field
                        style="margin: 2px 2px 2px 5px;"></input>
                    <br><br><button type="submit" name=$button id="barrel-form-button"
                            value="submit">Sign In</button> 
                    <br><br><legend
                            style="text-align: left; margin: 10px 0px 20px 0px">
                            If you forgot your username or password, please contact
                            administrator or <a href="http://www.ignitesol.com">Ignite
                                Solutions</a>
                        </legend>
                        </center>
                </form>
    
            </div>
            <img src="/images/popup_medium_with_cross.png" width="100%" border="0" usemap="#loginmap" style="position:absolute; top:0; left:0;"/>
            <map name="loginmap">
                <area shape="rect" coords="666,53,683,72" href="javascript: history.back();" alt="Close" />
            </map>
        </div>
    </div>
</body>
    ''' 
    def __init__(self, app, users=None, open_urls=None, session_key=None, template=None):
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
        '''
        self.unsecure_urls = open_urls or []
        self.unsecure_compiled_urls = [ re.compile(p) for p in self.unsecure_urls ]
        
        self.app = app
        super(SparxAuth, self).__init__(app, users)
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
        return super(SparxAuth, self).__call__(environ, start_response)