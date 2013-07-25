'''
Created on 27-Feb-2013

@author: ashish
'''
from boots.endpoints.dbendpoints.db_base import DBConnectionEndPoint
from boots.datastore.cluster_dal import ClusterDAL

class ClusterDatabaseEndPoint(DBConnectionEndPoint):
    '''
    Database connection endpoint for the cluster Database
    '''
    def __init__(self, *args, **kargs):
        '''
        Constructor
        '''
        super(ClusterDatabaseEndPoint, self).__init__(*args, **kargs)
        self.dal = ClusterDAL(self, self.Base)
    
    def activate(self, *args, **kargs):
        super(ClusterDatabaseEndPoint, self).activate(*args, **kargs)

if __name__ == "__main__":
    pass