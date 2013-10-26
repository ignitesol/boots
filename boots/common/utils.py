'''
'''

from boots import concurrency
import random
if concurrency == 'gevent':
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
        
    def _internal_counter(seed):
        while 1:
            retval = seed
            seed += 1
            yield retval
            
    if major >= 3:
        nexter = _internal_counter(seed).__next__
    else:
        # python 2
        nexter = _internal_counter(seed).next
    
    class __dummy:
        @classmethod
        def _generator_wrapper(cls):
            with lock:  # guarantee atomicity
                return nexter()
        
    return __dummy._generator_wrapper
    
def generate_uuid(frames=3):
    return '-'.join(['%X'%random.Random().randint(0, pow(10,16)) for _ in range(0, frames)])