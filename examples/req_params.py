'''
*****************************
Processing request parameters
*****************************
`bottle <http://bottlepy.org>`_ 

boots makes it easy to accept (and to validate) request parameters. Most of this functionality is based on bottle_.

This example shows a few of the ways to accept and validate parameters.

Here's a simple way to extract a named parameter and check it's type::

    @methodroute(path='/hello', params=dict(name=str))
    def hello(self, name):
        return "hello %s" % name

+-------------------+---------------------------------------------+
| Run this with url | and your output should be                   |
+===================+=============================================+
| /hello?name=henry | *hello henry*                               |
+-------------------+---------------------------------------------+
| /hello            | *400 code* with a *Missing parameter: name* |
+-------------------+---------------------------------------------+

We can supply default arguments::

    @methodroute()
    def hello2(self, name='buddy'):
        return "hello %s" % name

+-----------------------+------------------------------------+------------------------------------+
| Run this with url     | and your output should be          | Notes                              |
+=======================+====================================+====================================+
| /hello2?name=henry    | *hello henry*                      |                                    |
+-----------------------+------------------------------------+------------------------------------+
| /hello2/henry         | *hello henry*                      | ReSTful parameters (refer bottle_) |
+-----------------------+------------------------------------+------------------------------------+
| /hello2 *helly buddy* | default parameters (refer bottle_) |                                    |
+-----------------------+------------------------------------+------------------------------------+

Default arguments and type validation::

    @methodroute(params=dict(num=int))
    def hello3(self, num=20):
        return "hello %s is %s" % (num, 'an int' if type(num) == int else 'not an int')

+-------------------+---------------------------------------------------+------------------+
| Run this with url | and your output should be                         | Notes            |
+===================+===================================================+==================+
| /hello3           | *hello 20 is an int*                              | default argument |
+-------------------+---------------------------------------------------+------------------+
| /hello3/10        | *hello 10 is an int*                              |                  |
+-------------------+---------------------------------------------------+------------------+
| /hello3?num=15    | *hello 15 is an int*                              |                  |
+-------------------+---------------------------------------------------+------------------+
| /hello3/abc       | *400 code* with *Wrong parameter format for: num* |                  |
+-------------------+---------------------------------------------------+------------------+
| /hello3/?num=abc  | *400 code* with *Wrong parameter format for: num* |                  |
+-------------------+---------------------------------------------------+------------------+

Multiple arguments and different types::

    # val=bool evaluates to True for input value 'True', False otherwise.
    @methodroute(path='/echo', params=dict(name=str, val=bool))
    def echo(self, name, val):
        return dict(name=name, val=val)

    @methodroute(path='/add', params=dict(a=int, b=int))
    def add(self, a, b):
        return dict(a=a, b=b, sum=a+b)

Validators are really converters. They validate and convert the arguments to specific types and formats. In this case, 
the parameter name is converted to capitalized::
    
    @methodroute(path='/pretty', params=dict(name=lambda x: x.capitalize()))
    def pretty(self, name):
        return 'received %s' % name

Multi-value parameters have a slightly different syntax::

    @methodroute(path='/ages', params=dict(names=[str], ages=[int]))
    def ages(self, names, ages):
        return dict(zip(names, ages))

+----------------------------------------------------------------+----------------------------------------+
| Run this with url                                              | and your output should be              |
+================================================================+========================================+
| /ages?names=joe&ages=25                                        | *{"joe": 25}*                          |
+----------------------------------------------------------------+----------------------------------------+
| /ages?names=joe&ages=25&names=mary&names=henry&ages=24&ages=32 | *{"henry": 32, "joe": 25, "mary": 24}* |
+----------------------------------------------------------------+----------------------------------------+


'''

from boots.servers.httpserver import HTTPServer
from boots.endpoints.http_ep import HTTPServerEndPoint, methodroute

class EP(HTTPServerEndPoint):
    
    # one parameter expected. name is name, type is str
    # if parameter is not supplied, an 400 code return value is returned to the caller
    @methodroute(path='/hello', params=dict(name=str))
    def hello(self, name):
        return "hello %s" % name

    # This shows how default values are supplied (using bottle's magic) 
    # can be invoked as /hello2/newton or /hello2?name=newton
    @methodroute()
    def hello2(self, name='buddy'):
        return "hello %s" % name

    # This shows how default values are supplied (using bottle's magic) 
    # can be invoked as /hello2/newton or /hello2?name=newton
    @methodroute(params=dict(num=int))
    def hello3(self, num=20):
        return "hello %s is %s" % (num, 'an int' if type(num) == int else 'not an int')

    # val=bool evaluates to True for input value 'True', False otherwise.
    @methodroute(path='/echo', params=dict(name=str, val=bool))
    def echo(self, name, val):
        return dict(name=name, val=val)
 
    # We are able to add two integer parameters without parsing and splitting the url to get parameter values
    # Also, the data type is specified in @methodroute. 
    @methodroute(path='/add', params=dict(a=int, b=int))
    def add(self, a, b):
        return dict(a=a, b=b, sum=a+b)

    # custom validators. 
    @methodroute(params=dict(check=lambda x: x == 'check'))
    def checker(self, check=False):
        return 'validated %s' % check
    
    @methodroute(path='/pretty', params=dict(name=lambda x: x.capitalize()))
    def pretty(self, name):
        return 'received %s' % name
    
    @methodroute(path='/ages', params=dict(names=[str], ages=[int]))
    def ages(self, names, ages):
        return dict(zip(names, ages))
        
class MyServer(HTTPServer):
    pass
        
application = MyServer(endpoints=[EP()])

if __name__ == "__main__":
    application.start_server(standalone=True, description="Parameter type checking", defhost="localhost", defport=9999)
    