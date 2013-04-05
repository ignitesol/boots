root_module = __file__
    
import sys
import os

FILE = os.path.abspath(__file__) if not hasattr(sys, 'frozen') else os.path.abspath(sys.executable)
root_module = FILE
DIR = os.path.dirname(FILE)
PROJ_DIR = os.path.abspath(DIR + os.sep + '../../')  # assumes we are 1 level deeper than the project root
sys.path.append(PROJ_DIR)  if not hasattr(sys, 'frozen') else sys.path.append(DIR)

try:
    import boots
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../boots'))) # Since boots is not as yet installed into the site-packages

from boots.servers.server import Server 
from boots.datastore.cluster_db_endpoint import ClusterDatabaseEndPoint

class ClearAllData:

    @classmethod
    def delete(cls, ep):
        '''
        This method clears all the data from DB.
        '''
        #clears up the data
        session = ep.session
        session.query(ep.dal.Server).delete(synchronize_session='fetch')
        session.query(ep.dal.StickyMapping).delete(synchronize_session='fetch')
        session.commit()
    
        
if __name__ == '__main__':
    try:
        ep = ClusterDatabaseEndPoint(dbtype='mysql', db_url='mysql://cluster:cluster@localhost:3306/cluster', name="cluster_db_ep")
        server = Server(name="ClusterFakeServer", endpoints=[ep])
        server.root_module = root_module
        server.start_server(standalone=True)
        ep.create_tables(clean=True)
        
        ClearAllData.delete(ep)
        print "All data cleaned"
    except Exception as e:
        print e
        print "Failed to clean data"