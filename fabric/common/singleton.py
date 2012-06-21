'''
This implements a metaclass that implements the Singleton pattern. Taken from http://stackoverflow.com/questions/31875/is-there-a-simple-elegant-way-to-define-singletons-in-python
The Singleton applies to the subclass - so each subclass of Singleton forms a unique signleton (i.e the base class is not a shared singleton)
@author: anand
'''

class SingletonType(type):
    ''' introduces a Singleton type that is used as a metaclass in the Singleton class '''
    def __init__(cls, name, bases, d):
        super(SingletonType, cls).__init__(name, bases, d)
        cls.instance = None 

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(SingletonType, cls).__call__(*args, **kw)
        return cls.instance

class Singleton(object):
    __metaclass__ = SingletonType

if __name__ == '__main__':
    
    class MyClass(Singleton):
        def __init__(self):
            print 'Object id for', self.__class__.__name__, 'is', id(self)
    
    
    class MySubClass(MyClass):
        pass
    
    x1 = MyClass()
    x2 = MyClass()
    
    y1 = MySubClass()
    y2 = MySubClass()
    
    print 'Are all objects of MyClass the same?', id(x1) == id(x2)
    print 'Are all objects of MySubClass the same?', id(y1) == id(y2)
    print 'Are objects of MyClass same as objects of MySubClass?', id(x1) == id(y1)
    