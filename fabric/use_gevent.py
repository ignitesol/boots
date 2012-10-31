'''
Created on 04-Oct-2012

@author: harsh
'''
import fabric 
fabric.concurrency.state = 'gevent'
from gevent import monkey; monkey.patch_all()

