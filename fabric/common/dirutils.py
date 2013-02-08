'''
Created on 08-Feb-2013

@author: anand

A set of methods to assist with folders and validation of folders
'''
import logging
import os

# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())

class DirUtils(object):
    
    def is_updated(self, file_path, timestamp):
        '''
        Checks if file_path's modified time is newer than timestamp
        :param str file_path: str containing the file_path (absolute or relative to current working dir) 
        :type float timestamp: str or float containing the timestamp against which the file is to be checked
        :returns: boolean. TypeError if timestamp cannot be converted to float. OSError if file does not exist 
        '''
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        return os.path.getmtime(file_path) > timestamp

if __name__ == '__main__':
    pass