'''
Fabric is a framework for simplifying the development of high volume, highly scalable distributed systems. The framework is an extensible set of abstractions for
developing servers that serve, consume or participate in unicast or multicast network communications. Fabric makes it easy to create uniform ways to configure, adminster, 
debug and compose servers.
'''
import sys
import os

__version__ = '0.2'
__author__ = 'Ignite Solutions'

#concurrency = 'gevent'
concurrency = 'threading'
