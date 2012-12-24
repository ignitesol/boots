import sys
import os
try:
    import fabric
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../fabric'))) # Since fabric is not as yet installed into the site-packages

from fabric.datastore.mysql_datastore import Server, MySQLBinding, StickyMapping
from fabric.datastore.dbengine import DBConfig

INI_FILE = '../conf/clustertestserver.ini'

class ClearAllData:

    @classmethod
    def delete(cls, session):
        '''
        This method clears all the data from DB.
        '''
        #clears up the data
        session.query(Server).delete(synchronize_session='fetch')
        session.query(StickyMapping).delete(synchronize_session='fetch')
        session.commit()
    
        
if __name__ == '__main__':
    try:
        dbtype = "mysql"
        db_url = "mysql://cluster:cluster@localhost:3306/cluster"
        pool_size = 100
        max_overflow = 0
        connection_timeout = 30
        dbconfig = DBConfig(dbtype, db_url, pool_size, max_overflow, connection_timeout)
            
        
        db = MySQLBinding(dbconfig)
        session = db.get_session()
        ClearAllData.delete(session)
        print "All data cleaned"
    except Exception as e:
        print e
        print "Failed to clean data"