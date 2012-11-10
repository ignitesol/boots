'''
Created on 26-Oct-2012

@author: harsh
'''

import logging
import re

class FabricFilter(logging.Filter):
    """
    FabricFilter is a more powerful version of the logging.Filter class.
    
    Filter instances are used to perform arbitrary filtering of LogRecords.

    Loggers and Handlers can optionally use Filter instances to filter
    records as desired. The base filter class only allows events which are
    below a certain point in the logger hierarchy. For example, a filter
    initialized with "A.B" will allow events logged by loggers "A.B",
    "A.B.C", "A.B.C.D", "A.B.D" etc. but not "A.BB", "B.A.B" etc. If
    initialized with the empty string, all events are passed.
    """
    def __init__(self, kargs):
        """
        Initialize a filter.

        Initialize with the logger which, together with its
        children, will have its events allowed through the filter.
        """
        self.update(kargs)
    
    def update(self, name=None, regex=None, args=[], level=None, lineno=None, funcName=None):
        self.name = name
        self.nlen = None
        if self.name:
            self.nlen = len(self.name)        
        self.regex = regex
        self.compiled_regex = re.compile(self.regex)
        self.args = args        
        self.re_args = [re.compile(arg) for arg in self.args]
        self.level = level
        self.lineno = lineno
        self.funcName = funcName

    def filter(self, record):
        """
        Determine if the specified record is to be logged.

        Is the specified record to be logged? Returns 0 for no, nonzero for
        yes. If deemed appropriate, the record may be modified in-place.
        """
        
        if self.funcName == record.funcName:
            return 1
        if self.lineno == record.lineno:
            return 1
        if self.level == record.level:
            return 1
        for arg in self.re_args:        #TODO potentially optimise
            for in_arg in record.args:
                if arg.search(in_arg):
                    return 1
        if self.regex:
            return 1 
        return 0
    def post_format_filter(self, msg):
        """
        Determine if the specified record is to be logged.

        Is the specified record to be logged? Returns 0 for no, nonzero for
        yes. If deemed appropriate, the record may be modified in-place.
        """
        if not self.regex:
            return 1
        return 1 if self.compiled_regex.search(msg) else 0

def getLoggerDict(self):
    '''
    Creates a dictionary of loggers and their information.
    '''
    d = {}
    for k in self.loggerDict.keys():
        d[k] = logging.getLogger(k).getInfo()
    return d

def getInfo(self):
    '''
    Gives the information for the logger as a dictionary.
    '''
    handlers = ["file"*isinstance(handler, logging.FileHandler) or "root"*isinstance(handler, logging.RootLogger) for handler in self.handlers]
    return dict(level=self.level,propagate=self.propagate,handlers=handlers,disabled=self.disabled)

def fabric_format(self, record):
    """
    Format the specified record.

    Run the post_filter on the formatted msg.
    """
    msg = self._orig_format(record)
    return msg if self.post_filter(msg) == 1 else ""

def post_filter(self, msg):
    """
    Determine if a record is logable by consulting all the post filters.

    The default is to allow the record to be logged; any filter can veto
    this and the record is then dropped. Returns a zero value if a record
    is to be dropped, else non-zero.
    """
    rv = 1
    for f in self.filters:
        if callable(getattr(f,"post_format_filter", None)):
            if not f.post_format_filter(msg):
                rv = 0
                break
    return rv

class FabricLogging:
    
    @classmethod
    def enable(cls):
        '''
        Patching python logging.
        '''
        logging.Logger.getInfo = getInfo
        logging.Handler._orig_format = logging.Handler.format
        logging.Handler.format = fabric_format
        logging.Filterer.post_filter = post_filter
        logging.Logger.manager.__class__.getLoggerDict = getLoggerDict