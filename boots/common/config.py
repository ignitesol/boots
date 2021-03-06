'''
Created on 08-Jul-2011
'''

from __future__ import print_function
from boots import concurrency
from collections import OrderedDict
if concurrency == 'gevent':
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock
    
from configobj import ConfigObj, Section
import validate
import logging

# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())


class Config(ConfigObj):
    '''
    Config provides a transparent wrapper to a configuration management class. The objective is that configurations
    can be read from multiple sources and this object serves as an in-memory instance of configuration data. It can
    seamlessly read the configurations from files and write updated configurations to config files.
    
    As such, it is a wrapper to one of many available configuration parsers. The additional features implemented are
    - threadsafe behavior
    - callbacks on set
    - callbacks on del
    - (future) passing default values
    - (future) overriding values through command line
    
    The basic features (being leveraged from underlying config parsers) that need to be provided are
    - read config files 
    - write config files
    - allow get and set of attributes
    - allow del of attributes
    - reload config files
    
    In this version, we rely on the fact that configobj.ConfigObj inherits from configobj.Section which is the building
    block of all the elements stored in the config
    '''
    
    class Action:
        ''' 
        An enum for callbacks. This is passed as a parameter when invoking a callback
        Action.onset is passed when the callback is a result of the set action
        Action.ondel is passed when the callback is a result of the del action
        '''
        onset = 'onset'
        ondel = 'ondel'
    
    # instance variables. Initialized in __init__
    callbacks = None # maps a key to a list of callbacks to be invoked on set or del
    lock = None      # a re-entrant lock to provide thread-safe behavior

    def _find_parent_keys(self, complete=True):
        '''
        Specifically for ConfigObj. Returns a list of complete the parent keys (ordered as outermost first) to the current object.
        Relies on the implementation of Section where parent implies the parent Section object and main is the main (outermost) 
        ConfigObj object.
        @param complete: if complete is True, gives the whole chain. If complete is False, just provides immediate parent's key
        @type complete: bool
        '''
        
        with self.main.lock:
            try:
                # self.parent_items is a list of tuples [(key, value), (key, value)] of the items in the parent Section
                # we want to find the items whose value is the same as the current section (self). 
                # if no parent found (i.e. root level), an exception is thrown
                [(par_key, _)] = list(filter(lambda x: x[1] is self, self.parent.items()))  # note: 'is' is used instead of '=='
                return self.parent._find_parent_keys(complete=complete) + [par_key] if complete else [par_key]  # recursively call parent's find_parent_key
            except (ValueError, KeyError):
                return []
    
    def _new_getitem(self, attr, *args, **kargs):
        '''
        A wrapper to the getitem of configobj.Section. We use this to make attribute access thread safe.
        This unbound version of this method gets assigned to Section.__getitem__ and hence gets invoked
        whenever section_obj[attr] is used. 
        @param attr: The name of the attribute being accessed
        @type attr: str
        '''
        try:
            self.main.lock
        except AttributeError:          #Means we are not a Config.
            return self._orig_getitem(attr, *args, **kargs) # just invoke the original getitem
        else:
            with self.main.lock:
                try:
                    return self._orig_getitem(attr, *args, **kargs) # just invoke the original getitem
                except Exception as exception:
                    raise exception
    
    def _new_setitem(self, attr, val, *args, **kargs):
        '''
        A wrapper to the __setitem__ of configobj.Section. We use this to make attribute access thread safe
        and to introduce any callback invocation
        This unbound version of this method gets assigned to Section.__setitem__ and hence gets invoked
        whenever section_obj[attr] = val is used. 
        @param attr: The name of the attribute being accessed
        @type attr: str
        @param val: the value being assigned
        @param val: any
        '''
        #We are calling update_main here so that the .main of all sections in the hierarchy is set.
        depth = -1
        try:
            self.main.lock
        except AttributeError:          #Means we are not a Config.
            self._orig_setitem(attr, val, *args, **kargs)    # 1st set the new value
        else:
            self._update_main(val)
                
            with self.main.lock:
                self.main.recursive_depth += 1
                self._orig_setitem(attr, val, *args, **kargs)    # 1st set the new value 
                callbacks = self._get_callbacks(attr)
                self.main.pending_callbacks += callbacks
                self.main.recursive_depth -= 1
                depth = self.main.recursive_depth
                callbacks = self.main.pending_callbacks
                if depth == 0:
                    self.main.pending_callbacks = []  

        
        # calling callbacks outside the lock
        if self == self.main and depth == 0:
            self.process_callbacks(Config.Action.onset, depth, callbacks)
        
            # invoke the callbacks. Note callbacks are called after releasing the lock
#            map(lambda cb_func: cb_func(Config.Action.onset, full_key, val, self.main), callbacks)
    
    def _update_main(self, vals):
        '''
        Sets the .main of all sections in the hierarchy recursively.
        '''
        if isinstance(vals, Section):
            vals.main = self.main
            for _, val in vals.items():
                if isinstance(val, Section): 
                    self._update_main(val)
                    
    def _new_delitem(self, attr, *args, **kargs):
        '''
        A wrapper to the __delitem__ of configobj.Section. We use this to make attribute access thread safe
        and to introduce any callback invocation
        This unbound version of this method gets assigned to Section.__detitem__ and hence gets invoked
        whenever del section_obj[attr] is used. 
        @param attr: The name of the attribute being accessed
        @type attr: str
        @param val: the value being assigned
        @param val: any
        '''
        depth = -1
        try:
            self.main.lock
        except AttributeError:          #Means we are not a Config.
            self._orig_delitem(attr, *args, **kargs)    # 1st set the new valuee
        else:
            with self.main.lock:
                self._orig_delitem(attr, *args, **kargs)    # 1st set the new value 
                callbacks = self._get_callbacks(attr)
                self.main.pending_callbacks += callbacks
                depth = self.main.recursive_depth
                callbacks = self.main.pending_callbacks
                if depth == 0:
                    self.main.pending_callbacks = []  

        
        # calling callbacks outside the lock
        if self == self.main and depth == 0:
            self.process_callbacks(Config.Action.ondel, depth, callbacks)
                     
            # invoke the callbacks. Note callbacks are called after releasing the lock
#            map(lambda cb_func: cb_func(Config.Action.ondel, full_key, None, self.main), callbacks)

    def _get_callbacks(self, attr):
        '''
        returns a list of tuples - each tuple is the key starting from the outermost and the list of callbacks affected by a particular update associated with that key or its subkey 
        @param attr: the attribute of the current section object
        @type attr: str
        '''
        with self.main.lock:
            full_key = self._find_parent_keys() + [attr]     # obtain the full key from outermost section to current attr as a list
            callbacks = []
            for i in range(len(full_key),0,-1):
                key, callback = tuple(full_key[:i]), self.main.callbacks.get(tuple(full_key[:i]), [])
                callbacks += [ (key, callback) ] if callback != [] else []
#                print("###", 'key', tuple(full_key[:i]), 'callbacks', self.main.callbacks.get(tuple(full_key[:i]), []))
        return callbacks
    
    def merge(self, indict):
        depth = -1
        try:
            self.main.lock
        except AttributeError:          #Means we are not a Config.
            super(Config, self).merge(indict)
        else:
            self._update_main(indict)
            with self.main.lock:
                self.main.recursive_depth += 1
                
                super(Config, self).merge(indict)
                
                self.main.recursive_depth -= 1
                depth = self.main.recursive_depth
                callbacks = self.main.pending_callbacks
                if depth == 0:
                    self.main.pending_callbacks = []  
        
        # calling callbacks outside the lock
        if self == self.main and depth == 0:
            self.process_callbacks(Config.Action.onset, depth, callbacks)

    def process_callbacks(self, action, depth, callbacks):
        called = {}
        if depth == 0: # we only call when depth is 0
            for key, callback_list in callbacks:
                called.setdefault(key, [])
                val = self.main
                for k in key:
                    if val and isinstance(val, dict):
                        val = val.get(k)
                    
                for f in callback_list:
                    if f not in called[key]:
                        f(action, key, val, self.main)
                called[key] += callback_list

            
        
        
        

    # this is class-level code (i.e. gets executed on import). This code does the magic that allows us
    # to intercept and mediate calls to get, set, del
    # what we are doing is to save the original Section.__setitem__ (and others) and override them with
    # our version which in-turn invokes the original version
    try:
        # in case of multiple imports, we want to do run our code only the 1st time
        # this checks to see if Section._orig_getitem already exists, in which case we don't do anything
        getattr(Section, '_orig_getitem')
    except AttributeError:
        # save original __getitem__ etc into a Section class level member
        # since we do this at a class level, all configobjs (in our code or in other code) will get affected.
        # we may need to modify to only affect our code
        Section._orig_getitem, Section._orig_setitem, Section._orig_delitem = Section.__getitem__, Section.__setitem__, Section.__delitem__
        Section.__getitem__, Section.__setitem__, Section.__delitem__ = _new_getitem, _new_setitem, _new_delitem
        Section._find_parent_keys, Section._get_callbacks, Section._update_main = _find_parent_keys, _get_callbacks, _update_main
    
    def __init__(self, *args, **kargs):
        self.callbacks = {}   # initialize the callback hash
        self.lock = RLock()   # create a reentrant lock that is per Config object.
        self.recursive_depth = 0 # when calling merge or set items this determines the current recursive depth. Callbacks are called at top-depth (i.e. 0)  
        self.pending_callbacks = []
        super(Config, self).__init__(*args, **kargs) # invoke the ConfigObj __init__
        
    def add_callback(self, key, callback_func):
        '''
        Register a callback that will be invoked whenever config[key] is set or deleted
        @param key: a list of attributes that represent an ordered list of sections and subsections and finally the key
        @type key: list of strings
        @param callback_func: a callback function or bound method that is invoked when the attribute represented by key is set or deleted. 
        The callback_func should take 4 parameters callback(action, full_key, new_value, config_obj)
        is passed the key, the new value that was set, a reference to the config object and an 
            @param for callback -- action: action indicates whether callback is regarding a value being set on the attribute or a delete of the attribute. 
            Action is of type Config.Action (indicates onset or ondel)
            @param for callback -- full_key: the same as key
            @param for callback -- new_value: The value that was just set or in case action == ondel, None
            @param for callback -- config_obj: a reference to the config_obj on which this callback was registered 
            @
        @type callback_func: function
        '''
        key = tuple(key)
        cb_list = self.main.callbacks.setdefault(key, [])
        if callback_func not in cb_list:
            cb_list += [callback_func] 
            
    def del_callback(self, key, callback_func):
        '''
        Delete a previously registed callback. See @see add_callback. Parameters are same as add_callback
        '''
        key = tuple(key)
        cb_list = self.main.callbacks.setdefault(key, [])
        try:
            cb_list.remove(callback_func)
        except ValueError:
            pass
        
    def dict(self):
        """
        Return a deepcopy of self as a dictionary.
        
        All members that are ``Section`` instances are recursively turned to
        ordinary dictionaries - by calling their ``dict`` method.
        
        >>> n = a.dict()
        >>> n == a
        1
        >>> n is a
        0
        """
        newdict = OrderedDict()
        for entry in self:
            this_entry = self[entry]
            if isinstance(this_entry, Section):
                this_entry = this_entry.dict()
            elif isinstance(this_entry, list):
                # create a copy rather than a reference
                this_entry = list(this_entry)
            elif isinstance(this_entry, tuple):
                # create a copy rather than a reference
                this_entry = tuple(this_entry)
            newdict[entry] = this_entry
        return newdict
        
class ConfigSingleton(Config):
    '''
    This implements a singleton class - only one instance of it will ever exist. 
    If you inherit from this class, only one instance of that type will exist. However, note that multiple 
    different inherited class types can exist (one per type). 
    '''
    
    get = None

    def __init__(self, *args, **kargs):
        if self.__class__.get is None:
            self.__class__.get = self
            super(ConfigSingleton, self).__init__(*args, **kargs)
    
    def __getattr__(self, attr):
        if id(self) == id(self.__class__.get):
            return super(ConfigSingleton, self).__getattr__(attr)
        return getattr(self.__class__.get, attr)
    
    def __setattr__(self, attr, value):
        if id(self) == id(self.__class__.get):
            return super(ConfigSingleton, self).__setattr__(attr, value)
        return setattr(self.__class__.get, attr, value)
        
        
if __name__ == '__main__':
    # to test the functionality
    # 1st create a temp config file
    
    
    def callback(action, full_key, value, main):
        print('action =', action, 'key =', full_key, 'value =', value)
        
    temp = Config()
    temp.filename = 'config.test.ini'
    temp['toplevel 1'] = 'one'
    temp['toplevel 2'] = 'two'
    temp['Section1'] = {}
    temp['Section1']['sec1_var_1'] = 'ten'
    temp['Section1']['sec1_var_2'] = 'twenty'
    temp['Section1']['SubSection1.1'] = {}
    temp['Section1']['SubSection1.1']['subsec1.1_var1'] = 'hello world'
    temp['Section1']['SubSection1.1']['subsec1.1_var2'] = 'hello world'
    temp['Section1']['SubSection1.2'] = {}
    temp['Section1']['SubSection1.2']['subsec1.2_var1'] = 'how are you?'
    temp['Section2'] = {}
    temp['Section2']['sec2_var1'] = 30
    temp['Section2']['sec2_var2'] = 40
    temp['Section3'] = {}
    temp['Section3']['sec3_var1'] = 300
    temp['Section3']['sec3_var2'] = 400
    temp['Section3']['sec3_var3'] = 401
    temp.write()
    
    cfg = Config()
    cfg.add_callback([ 'Section1', 'sec1_var_1' ], callback)
    cfg.add_callback([ 'Section1' ], callback)
    cfg.add_callback([ 'Section2' ], callback)
    cfg.add_callback([ 'toplevel 1' ], callback)
    cfg.add_callback([ 'Section2', 'sec2_var2'], callback)
    cfg2 = Config('config.test.ini')
#    validator = validate.Validator()
#    result = cfg2.validate(validator)
#    if not result:
#        print('validate failed')

    cfg3 = {}
    cfg3['Section1'] = temp['Section1']
    cfg3['Section1']['SubSection1.1']['subsec1.1_var1'] = 'new hello world'
    cfg3['Section1']['SubSection1.2']['subsec1.2_var1'] = {}
    cfg3['Section1']['SubSection1.2']['subsec1.2_var1']['subsec1.2.1'] = 'sub sub sec'
    cfg3 = Config(cfg3)
    
    cfg4 = cfg3.dict()
    cfg4['Section1']['SubSection1.1']['subsec1.1_var2'] = 'new new hello world'
    cfg4 = Config(cfg4)


    print ("-----------------READY TO MERGE------------------------")
    cfg.merge(cfg2)
    print ("-----------------DONE MERGE------------------------")
    
    print ("-----------------READY TO MERGE CFG3------------------------")
    cfg.merge(cfg3)
    print ("-----------------DONE MERGE CfG3------------------------")
    
    print ("-----------------READY TO MERGE CFG4------------------------")
    cfg.merge(cfg4)
    print ("-----------------DONE MERGE CfG4------------------------")
    
    cfg['Section1']['sec1_var_1'] = 10
    
    cfg['Section2'].merge({ 'sec2_var1' : 'new_30', 'sec2_var2': 'new_40' })
    
    cfg['Section2']['sec2_var2'] = '1000'
    print('[Section2][sec2_var1]', cfg['Section2']['sec2_var1'])
#    cfg.filename = 'config.test2.ini'
#    cfg.write()
#    
#    print('[Section3][sec3_var1]', cfg['Section3']['sec3_var1'], type(cfg['Section3']['sec3_var1']))
#    print('[Section3][sec3_var2]', cfg['Section3']['sec3_var2'], type(cfg['Section3']['sec3_var2']))
#    print('[Section3][sec3_var3]', cfg['Section3']['sec3_var3'], type(cfg['Section3']['sec3_var3']))
