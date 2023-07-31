from pydantic import BaseModel
from .controller.models import StatusDB, SocketDB, HostDB, MServerDB
from typing import Generic, TypeVar
from typing import TYPE_CHECKING
from copy import deepcopy
if TYPE_CHECKING:
    from db.controller import DBBaseController
from sqlalchemy import inspect
import json

DBT = TypeVar('DBT')

class Base(BaseModel, Generic[DBT]):
    id: int = 0
   
    def to_db(self) -> DBT:
        if not hasattr(self, '_DB_entity'):
            raise NotImplementedError(f'No db entity mapping for {self.__class__.__name__} class!')
        if self.id == 0: 
            self.id = None #type: ignore
        final_attributes = deepcopy(self.dict()) 
        for attribute in self.__dict__:
            value = self.__dict__[attribute]
            if isinstance(value, Base):
                final_attributes.pop(attribute)
                final_attributes[attribute+'Id'] = value.to_db().id
        return self._DB_entity(**final_attributes) #type: ignore
    
    def update_db(self, db: 'DBBaseController', commit=True):
        if not hasattr(self, '_DB_entity'):
            raise NotImplementedError('No db entity mapping!')
        if self.id == 0: 
            raise Exception('Can\'t update entity without id')
        final_attributes = deepcopy(self.dict()) 
        for attribute in self.__dict__:
            value = self.__dict__[attribute]
            if isinstance(value, Base):
                final_attributes.pop(attribute)
                final_attributes[attribute+'Id'] = value.to_db().id
        db_entry: DBT = db.get(self._DB_entity, self.id) #type: ignore
        for attr in inspect(type(db_entry)).columns.keys():
            setattr(db_entry, attr, final_attributes[attr])
        if commit:
            db._conn.commit()

    class Config:
        orm_mode=True

class Status(Base[StatusDB]):
    name: str
    details: str | None = None
    _DB_entity = StatusDB

class Host(Base[HostDB]):
    name: str
    _DB_entity = HostDB

class Socket(Base[SocketDB]):
    host: Host
    port: int
    status: Status | None = None
    _DB_entity = SocketDB

class MServer(Base[MServerDB]):
    socket: Socket
    version: str
    description: str
    max_players: int
    _DB_entity = MServerDB

    @property
    def printable(self):
        p = {**self.__dict__}
        p['socket'] = f'{self.socket.host.name}:{self.socket.port}'
        return json.dumps(p)
