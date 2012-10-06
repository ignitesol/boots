'''
Created on 04-Oct-2012

@author: harsh
'''
import fabric
print fabric.concurrency 
fabric.concurrency.state = 'gevent'
print "use_gevent",fabric.concurrency
from gevent import monkey; monkey.patch_all()
print "patching done" 