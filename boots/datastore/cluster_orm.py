from sqlalchemy import Column, schema as saschema
from sqlalchemy.dialects.mysql.base import LONGTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.types import String, Integer, Float, DateTime

class ClusterORM(object):
    def __init__(self, Base):
        '''
        Constructor
        '''
        self.Base = Base
    
        class Server(Base):
            ''' mapping class for server table'''
            __tablename__ = 'server'
            server_id = Column(Integer, primary_key=True)
            server_type = Column(String(200))
            server_address = Column(String(200))
            server_state = Column(LONGTEXT)
            server_info = Column(LONGTEXT)
            creation_date = Column(DateTime)
            load =  Column(Float)
            
            __table_args__  = ( saschema.UniqueConstraint("server_address"), {'mysql_engine':'InnoDB'} ) 
            stickymapping = relationship("StickyMapping",
                        cascade="all, delete-orphan",
                        passive_deletes=True,
                        backref="server"
                        )
            
            def __init__(self, server_type, server_address, server_state, server_info, creation_date, load ):
                self.server_type = server_type
                self.server_address = server_address
                self.server_state = server_state
                self.server_info = server_info
                self.creation_date = creation_date
                self.load = load
                
            def __repr__(self):
                return "<Server (server_type, server_address, server_state, load)('%s', '%s', '%s', '%s')>" % \
                    (self.server_type, str(self.server_address), str(self.server_state), str(self.load))
                
        class StickyMapping(Base):
            ''' mapping class for stickypping table'''
            __tablename__ = 'stickymapping'
            
            mapping_id = Column(Integer, primary_key=True)
            server_id = Column(Integer, ForeignKey('server.server_id', ondelete='CASCADE'))
            endpoint_key = Column(String(100))
            endpoint_name = Column(String(100))
            sticky_value = Column(String(500))
            
        
            __table_args__  = ( saschema.UniqueConstraint("server_id", "sticky_value" ),
                                saschema.UniqueConstraint("endpoint_name", "sticky_value" ), {'mysql_engine':'InnoDB'} ) 
        
            
            @property
            def sticky_mapping_key(self):
                return (self.endpoint_key, self.sticky_value)
            
            def __init__(self, server_id, endpoint_key, endpoint_name, sticky_value):
                self.server_id = server_id
                self.endpoint_key = endpoint_key
                self.endpoint_name = endpoint_name
                self.sticky_value = sticky_value   
                
                
            def __repr__(self):
                return "<StickyMapping (server_id, endpoint_key, endpoint_name, sticky_value)('%s', '%s', '%s', '%s')>" % \
                    (self.server_id, str(self.endpoint_key), str(self.endpoint_name), str(self.sticky_value))

        self.Server = Server
        self.StickyMapping = StickyMapping
