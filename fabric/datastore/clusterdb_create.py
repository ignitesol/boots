'''
Created on 26-Dec-2012

@author: ashish
'''
import sys
import os
try:
    import fabric
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../fabric'))) # Since fabric is not as yet installed into the site-packages


from fabric.datastore.mysql_datastore import Base
from sqlalchemy.exc import OperationalError
if __name__ == '__main__':
    try:
        Base.metadata.create_all(checkfirst=False)
    except OperationalError:
        Base.metadata.drop_all(checkfirst=True)
        Base.metadata.create_all(checkfirst=True)