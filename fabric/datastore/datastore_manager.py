'''
This module is used to get relevant datastore , given a string.
When a new data store module is plugged in we need to have an entry in the following list
'''
from fabric.datastore.dbengine import DBConfig
from fabric.datastore.mysql_datastore import MySQLBinding
datastore_list = ['mysql', ]

def get_datastore(datastore_type, config_obj):
    if not datastore_type or datastore_type not in datastore_list:
        return None
    if datastore_type ==  'mysql':
        clusterdb = config_obj['MySQLConfig']
        dbtype = clusterdb['dbtype']
        db_url = dbtype + '://'+ clusterdb['dbuser']+ ':' + clusterdb['dbpassword'] + '@' + clusterdb['dbhost'] + ':' + str(clusterdb['dbport']) + '/' + clusterdb['dbschema']
        dbconfig =  DBConfig(dbtype, db_url, clusterdb['pool_size'], clusterdb['max_overflow'], clusterdb['connection_timeout']) 
        return MySQLBinding(dbconfig)


    