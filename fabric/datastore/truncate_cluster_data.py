from fabric.datastore.datamodule import Server, MySQLBinding, StickyMapping
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
        db = MySQLBinding()
        session = db.get_session()
        ClearAllData.delete(session)
        print "All data cleaned"
    except Exception as e:
        print e
        print "Failed to clean data"