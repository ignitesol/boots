'''
This implements a metaclass that implements the Singleton pattern. Taken from http://stackoverflow.com/questions/31875/is-there-a-simple-elegant-way-to-define-singletons-in-python
The Singleton applies to the subclass - so each subclass of Singleton forms a unique signleton (i.e the base class is not a shared singleton)
@author: anand
'''
import threading
import time

class Atomic(object):
    lock = threading.RLock() 

class SingletonType(type):
    ''' introduces a Singleton type that is used as a metaclass in the Singleton class '''
    def __init__(cls, name, bases, d):
        super(SingletonType, cls).__init__(name, bases, d)
        cls.instance = None 

    def __call__(cls, *args, **kw): #@NoSelf
        if cls.instance is None:
            with Atomic.lock:
                # we do this check again incase it was created between 
                # creating the lock and the previous sanity check
                if cls.instance is None:
                    cls.instance = super(SingletonType, cls).__call__(*args, **kw)
        return cls.instance

class NamespaceSingletonType(SingletonType):
    ''' Introduces namespaces to the Singleton class '''
    
    def __init__(cls, name, bases, d): #@NoSelf
        cls.__registry = {} # init this here, not on the class level
        super(SingletonType, cls).__init__(name, bases, d)
        
    def __call__(cls, *args, **kargs): #@NoSelf
        ns = kargs.pop('_ns', "")
        with Atomic.lock:
            cls.instance = cls.__registry.get(ns)
            cls.__registry[ns] = super(NamespaceSingletonType, cls).__call__(*args, **kargs)
        return cls.__registry[ns]
            

class Singleton(object):
    __metaclass__ = SingletonType

class NamespaceSingleton(object):
    __metaclass__ = NamespaceSingletonType
   
   
def run():
    MyClass()

if __name__ == '__main__':
    
    class MyClass(NamespaceSingleton):
        def __init__(self):
            time.sleep(1)
            print 'Object id for', self.__class__.__name__, 'is', id(self)
    
    
    class MySubClass(MyClass):
        pass
    
    class Dummy(object):
        
        def __init__(self):
            print 'In Dummy __init__, obj id for ', self.__class__.__name__, 'is', id(self)
            
    class MultiSubClass(Dummy, NamespaceSingleton):
        pass
    
    x1 = MyClass(_ns="1")
    x2 = MyClass()
    for i in range(2):
        t = threading.Thread(target=run)
        t.start()
    
    y1 = MySubClass(_ns="1")
    y2 = MySubClass(_ns="1")
    
    z1 = MultiSubClass(_ns="1")
    z2 = MultiSubClass(_ns="2")
    
    print 'Are all objects of MyClass the same?', id(x1) == id(x2)
    print 'Are all objects of MySubClass the same?', id(y1) == id(y2)
    print 'Are all objects of MultiSubClass the same?', id(z1) == id(z2)
    print 'Are objects of MyClass same as objects of MySubClass?', id(x1) == id(y1)
    