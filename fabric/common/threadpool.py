from fabric import concurrency
if concurrency == concurrency.GEVENT:
    from gevent.threadpool import ThreadPool as t
else:
    from multiprocessing.pool import ThreadPool as t
    
from fabric.common.singleton import Singleton
import threading
import Queue
import time
from fabric.common.utils import new_counter
import functools
from heapq import heappop, heappush
import logging

class ThreadPool(t):
    
    def __init__(self, processes=5):
        if concurrency == concurrency.GEVENT:
            super(ThreadPool, self).__init__(maxsize=processes)
        else:
            super(ThreadPool, self).__init__(processes=processes)

class InstancedThreadPool(Singleton, ThreadPool):
    
    def __init__(self, num_workers=10):
        super(InstancedThreadPool, self).__init__(processes=num_workers)

class InstancedScheduler(Singleton, threading.Thread):    
    
    def __init__(self, *args, **kargs):
        super(InstancedScheduler, self).__init__(*args, **kargs)
        self.daemon = True
        self._task_heap = []
        self._cancelled = {}
        self._q = Queue.Queue()
        self._counter = new_counter()
        self._lock = threading.RLock()
        self._stop = False
        self.start()
    
    def cancel(self, idn):
        with self._lock: self._cancelled[idn] = True
    
    def timer(self, delay, fn, *args, **kargs):
        idn = self._counter()
        self._q.put((time.time() + delay, functools.partial(fn, *args, **kargs), idn))
        return idn
    
    def shutdown(self):
        logging.getLogger().debug("Shutting Down scheduler")
        
        def _set_stop(): 
            with self._lock: self._stop = True
        
        self.timer(0, _set_stop)
        
    def run(self):
        timeout = None
        while True:
            try:
                event = self._q.get(True, timeout)
                # We received an event
                heappush(self._task_heap, event)
                
            except Queue.Empty: # timeout ran
                _, callback, idn = heappop(self._task_heap)
                if idn in self._cancelled:
                    logging.getLogger.debug("cancelled %s", idn)
                    self._cancelled.pop(idn)
                else:
                    try: callback()
                    except Exception as e:
                        logging.getLogger().exception("Exception running scheduled Timer: %s", e)
                
                if self._stop is True: break
            finally:
                try:
                    # new timeout
                    timeout_in_time , _, _ = self._task_heap[0]
                    timeout = max((timeout_in_time - time.time(), 0))
                except IndexError: timeout = None
                # logging.getLogger().debug("Timeout %s", timeout)
                
