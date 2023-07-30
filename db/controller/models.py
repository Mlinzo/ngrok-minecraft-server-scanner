from sqlalchemy import ForeignKey, Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .engine import engine

Base = declarative_base()

class BaseDB():
    id = Column(Integer, primary_key=True, autoincrement=True)  

class StatusDB(BaseDB, Base):
    __tablename__ = 'statuses'

    name = Column(String, nullable=False, unique=True)
    details = Column(String)

class HostDB(BaseDB, Base):
    __tablename__ = 'hosts'

    name = Column(String, nullable=False, unique=True)

class SocketDB(BaseDB, Base):
    __tablename__ = 'sockets'

    hostId = Column(Integer, ForeignKey(HostDB.id), nullable=False)
    port = Column(Integer, nullable=False)
    statusId = Column(Integer, ForeignKey(StatusDB.id))

    host = relationship(HostDB)
    status = relationship(StatusDB)

    __table_args__ = (UniqueConstraint('hostId', 'port', name='_host_port_uc'), )

class MServerDB(BaseDB, Base):
    __tablename__ = 'mservers'
    
    socketId = Column(ForeignKey(SocketDB.id), nullable=False, unique=True)
    version = Column(String, nullable=False)
    description = Column(String, nullable=False)
    max_players = Column(Integer, nullable=False)

    socket = relationship(SocketDB)

def create_all():
    Base.metadata.create_all(engine)

def drop_all():
    Base.metadata.drop_all(engine)
