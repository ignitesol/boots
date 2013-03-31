from fabric.datastore.dbengine import DBConfig
from fabric.datastore.mysql_datastore import MySQLBinding, Server, StickyMapping
from fabric.endpoints.httpclient_ep import HTTPClientEndPoint
import unittest


class TestClusterFunctionality(unittest.TestCase):
    '''
    To run this test you must do following
    1) add host entries 
    127.0.0.1     testserver1.ignitelabs.local     testserver2.ignitelabs.local
    
    2)start following servers
    cd ~workspace/fabric/examples;     python clustertestserver.py -i testserver1.ignitelabs.local -p 4001
    cd ~workspace/fabric/examples;     python clustertestserver.py -i testserver2.ignitelabs.local -p 4002
    
    '''

    def cleanup(self):
        dbtype = "mysql"
        db_url = "mysql://cluster:cluster@localhost:3306/cluster"

        dbconfig = DBConfig(dbtype, db_url)
        db = MySQLBinding(dbconfig)
        session = db.get_session()
        session.query(Server).delete(synchronize_session='fetch')
        session.query(StickyMapping).delete(synchronize_session='fetch')
        session.commit()

    def setUp(self):
        
        self.cleanup()

    def tearDown(self):
        self.cleanup()

    def test_basic_sticky(self):
        # make sure the request returned is same in both case. The response contains the server name from where
        #the response is coming back
        data1 = HTTPClientEndPoint().request('http://testserver1.ignitelabs.local:4001/register?channel=c').data
        data2 = HTTPClientEndPoint().request('http://testserver2.ignitelabs.local:4002/register?channel=c').data
        self.assertEqual(data1, data2)

if __name__ == '__main__':
    unittest.main()