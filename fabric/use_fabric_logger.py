'''
Created on 26-Oct-2012

@author: harsh
'''
import fabric 
fabric.use_logging = 'fabric'
print "use_fabric_logger called"
from fabric_logging import FabricLogging

FabricLogging.enable()
