'''
Created on 07-Mar-2012

@author: harsh
'''
import time

class ZMQSPARXMessage(list):
    
    __placements__ = dict(filters=0)
    
    def __init__(self, *args, **kargs):
        index_hash = kargs.get('index_hash', None)
        super(ZMQSPARXMessage, self).__init__(*args)
        if not index_hash: index_hash = self.__class__.__placements__
        self._named_items = dict(index_hash)
        for _ in range(max(index_hash.values()) - len(self)): self.append('')
    
    def __setitem__(self, k, v): 
        if type(k) is not int:
            return self.set_named_item(k, v)
        else: key = k
        return super(ZMQSPARXMessage, self).__setitem__(key, v)
    
    def __getitem__(self, k):
        if type(k) is not int:
            return self.get_named_item(k)
        else: key = k
        return super(ZMQSPARXMessage, self).__getitem__(key)
                                                        
    def __repr__(self, *args, **kargs):
        return super(ZMQSPARXMessage, self).__repr__(*args, **kargs)
    
    def get_named_item(self, name):
        return self.__getitem__(self._named_items[name])
    
    def set_named_item(self, name, value):
        try:
            i = self._named_items[name]
            self.__setitem__(i, value)
        except KeyError:
            self.append(value)
            self._named_items[name] = len(self) - 1
    
    def get_name_index(self, name):
        return self._named_items[name]
    
    def get_item_width(self, name):
        indices = self._named_items.values()
        indices.sort()
        try: width = indices[indices.index(self._named_items[name]) + 1] - indices[indices.index(self._named_items[name])]
        except IndexError: width = 1
        return width
             

class SparxMessage(dict):
    
    @classmethod
    def create(cls, status, dictionary):
        return SparxMessage(status, **dictionary)
    
    def __init__(self, status, reason="" , *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self['status'] = status
        self['reason'] = reason
        self.setdefault('tracelog', TraceLog(''))
        self.setdefault('profiler', Profiler())
        
    
    def __repr__(self, *args, **kwargs):
        return dict.__repr__(self, *args, **kwargs)
    
    def touch(self):
        pass
    
class MessageStatus:
    """

    """
    Success = "Success" 
    ReadError = 'Read Error'
    AppDoesnotExist = 'Read Error'
    UnknownConfigError = 'Read Error'
    UserConfigError = 'Read Error'
    ConfigReadError = 'Read Error'
    UserRepoError = 'Read Error'
    AppError = 'Read Error'
    UnknownAppError = 'Read Error'
    
    AppInstalled = 'Read Error'
        
    Disconnect = 'Read Error'

class Profiler(list):
    
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
    
    def touch(self, info):
        self.append([time.time(), info])

class TraceLog(list):
    def __init__(self, pattern):
        self.pattern = pattern
    
    def add(self, pattern=None, *args, **kwargs):
        mess = pattern or self.pattern
        self.append(mess.format(*args, **kwargs))
    
if __name__ == '__main__':
    l = ZMQSPARXMessage(index_hash=dict(filters=0, message=1, error=3))
    l['filters'] = 'abc/cbd'
    l['message'] = 'message'
    print l['filters']
    print l.get_index('error')
    print l