'''
Created on 19-Jun-2012

@author: anand
'''
from threading import RLock, Thread
import threading
import zmq
from zmq.eventloop import ioloop
import time, random

tdata = threading.local()

def get_threadlocal():
    global tdata
    return tdata

# first, start a background ioloop thread and start ioloop
def iolooper():
    data = get_threadlocal()
    data.sockhash = {}
    loop = ioloop.IOLoop.instance() # get the singleton
    print threading.current_thread()
    loop.start()

t = Thread(target=iolooper)
t.daemon = True

def foo():
    print 'Hello'

ioloop.IOLoop.instance().add_callback(foo)
t.start()
ioloop.IOLoop.instance().add_callback(foo)

class ZMQEP(object):
    '''
    classdocs
    '''

    lock = RLock()
    class_id_count = 0
    
    def __init__(self, socket_type, address, bind=False):                                                                                                                  1,1           Top    def __init__(self, socket_type, address, bind=False):
        '''
        Constructor
        '''
        self.bind = bind
        self.address = address
        self.socket_type = socket_type
        self.ioloop = ioloop.IOLoop.instance()
        self.id # initialize the property

    @property
    def id(self):
        try:
            return self._id
        except AttributeError:
            with self.lock:
                self.__class__.class_id_count += 1
                self._id = self.__class__.class_id_count
            return self._id

    def setup(self):
        def _create():
            ''' this closure code will execute in the ioloop thread but have access to self '''
            print threading.current_thread()
            context = zmq.Context.instance()
            get_threadlocal().sockhash[self.id] = context.socket(self.socket_type)
            print 'created'

        self.ioloop.add_callback(_create)

    def start(self):
        def _start():
            ''' this closure code will execute in the ioloop thread but have access to self '''
            print threading.current_thread()
            sock = get_threadlocal().sockhash[self.id]
            if self.bind: sock.bind(self.address)
            else: sock.connect(self.address)

        self.ioloop.add_callback(_start)
        
if __name__ == '__main__':
    z = ZMQEP(zmq.PUB, 'tcp://*:9876')
    z.setup()
    z.start()
    n, i = 1000000, 0
    start_time = time.time()
    for i in range(0,n):
        try:
#            time.sleep(0.05)
#            z.send("%d Time: %d %d"%(random.Random().randint(1, 100), time.time()*1000, 1))
            z.send('msg')
        except KeyboardInterrupt:
            break
    end_time = time.time()
    print 'Total time for %s packets = %s' %(n, end_time-start_time)
    print 'Avg time per packet = %s' %((end_time-start_time)/n)
    time.sleep(2)
    zmq.Context.instance().term()
                                                      