'''
Created on Mar 21, 2012

@author: AShah
'''

from fabric import concurrency
if concurrency == 'gevent':
    from gevent import monkey; monkey.patch_all()
    from gevent.coros import RLock
elif concurrency == 'threading':
    from threading import RLock
 
import sys

major, _, _, _, _ = sys.version_info


##########################################################
## Atomic Counter ########################################
##########################################################
def new_counter(seed=0):
    '''
    creates a new counter and returns a function that, on every call, obtains the next counter value
    Takes an optional seed to seed the counter with (starts from that number). Defaults to zero
    Ensures thread safety
    example:
        countkeeper = new_counter(10)
        print countkeeper() # prints 10
        print countkeeper() # prints 11
    @param seed:
    @type seed:
    '''
    
    lock = RLock()
        
    def counter(seed):
        while 1:
            with lock:  # guarantee atomicity
                yield seed
                seed += 1

    if major >= 3:
        return counter(seed).__next__
    else:
        # python 2
        return counter(seed).next
    


