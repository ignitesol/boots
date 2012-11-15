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
                if cls.instance is None:
                    cls.instance = super(SingletonType, cls).__call__(*args, **kw)
        return cls.instance

class Singleton(object):
    __metaclass__ = SingletonType
   
   

    
def run():
    m = MyClass()

if __name__ == '__main__':
    
    class MyClass(Singleton):
        def __init__(self):
            time.sleep(1)
            print 'Object id for', self.__class__.__name__, 'is', id(self)
    
    
    class MySubClass(MyClass):
        pass
    
    class Dummy(object):
        
        def __init__(self):
            print 'In Dummy __init__, obj id for ', self.__class__.__name__, 'is', id(self)
            
    class MultiSubClass(Dummy, Singleton):
        pass
    
#    x1 = MyClass()
#    x2 = MyClass()
    for i in range(2):
        t = threading.Thread(target=run)
        t.start()
    
#    y1 = MySubClass()
#    y2 = MySubClass()
#    
#    z1 = MultiSubClass()
#    z2 = MultiSubClass()
#    
#    print 'Are all objects of MyClass the same?', id(x1) == id(x2)
#    print 'Are all objects of MySubClass the same?', id(y1) == id(y2)
#    print 'Are all objects of MultiSubClass the same?', id(z1) == id(z2)
#    print 'Are objects of MyClass same as objects of MySubClass?', id(x1) == id(y1)
    