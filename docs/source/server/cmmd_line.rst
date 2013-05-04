=======================
Command Line Arguments
=======================
Boots lets you leverage command line tool with the help of Python's argparser.
Server's get_arg_parser returns an ArgumentParser which can be used to traverse/add command line arguments.  
::

	
    @classmethod
    def get_arg_parser(cls, description='', add_help=False, parents=[], conflict_handler='error', **kargs): 
        argparser = argparse.ArgumentParser(description=description, add_help=add_help, 
        parents=parents, conflict_handler=conflict_handler) 
        argparser.add_argument('-d', '--demo', dest='demo', default='hello', help='test:  (default: world)')
        argparser.add_argument('--intval-demo', default=0, type=int, help='test an int val:  (default: 0)')
       
Server's cmmd_line_args is a dict holding server's command line arguments. 
The following code uses this to display specified command line arguments.
::

    @methodroute(path="/demo", method="GET")
    def demo(self):
        format_str = '{key}: {value}' if not self.server.cmmd_line_args['verbose'] else 'The value of {key} is {value}'
        return '<br/>'.join([ format_str.format(key=k, value=self.server.cmmd_line_args[k]) for k in [ 'demo', 'intval_demo' ]])  
