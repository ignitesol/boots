'''
Created on Mar 18, 2012

@author: AShah
'''

class EndPoint(object):
    ''' Endpoints represent an inbound or outbound port or interface for communication between servers or with clients. 
        These can represent unicast, multicast or peer-to-peer communications''' 
    pass

class EndPointException(Exception):
    '''
    A generic exception thrown by subclasses of :py:class:`EndPoint`
    '''
    pass

        
        