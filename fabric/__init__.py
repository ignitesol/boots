'''
Fabric is a framework for simplifying the development of high volume, highly scalable distributed systems. The framework is an extensible set of abstractions for
developing servers that serve, consume or participate in unicast or multicast network communications. Fabric makes it easy to create uniform ways to configure, adminster, 
debug and compose servers.
'''
import sys
import os
import time
__version__ = '0.2'
__author__ = 'Ignite Solutions'

class state_meta(type):
    '''
    Created a meta class to override how we interact with the object of concurrency class.
    '''
    def __eq__(self, new_state):
        '''
        Overridding so that directly set an internal variable of the class rather that the change the object.
        '''
        return self.state == new_state
    
    def __repr__(self):
        '''
        Overridding so that we can directly print the internal variable by printing the class.
        '''
        return self.state
    
class concurrency(object):
    __metaclass__ = state_meta
    GEVENT, THREADING = "gevent", "threading"
    state = THREADING

class use_logging(object):
    __metaclass__ = state_meta
    state = 'logging'
