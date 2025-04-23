from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional, List
from pydantic import BaseModel, SerializeAsAny, computed_field

class IP_List_Response(SQLModel):
    id: Optional[int]
    ip_addr: Optional[str]

class IP_List_Query(SQLModel):
    id: Optional[int] = None
    ip_addr: Optional[str] = Field(default=None)

class IP_List_Update(SQLModel):
    ip_addr: Optional[str]

class List_IP_List_Update(SQLModel):
    items: List[IP_List_Update]

class List_IP_List_Update_response(SQLModel):
    items: List[IP_List_Response]

class Client(BaseModel):
    name: str
    used: Optional[bool] = False
    cfg_file: Optional[str] = None

class ListClients(BaseModel):
    clients: Optional[List[Client]] = []

class ListClientsWithTotal(BaseModel):
    #clients: Optional[List[Client]] = []
    total: Optional[int] = 0
    used: Optional[int] = 0
    free: Optional[int] = 0

class StatisticClient(BaseModel):
    name: Optional[str]
    pub_key: str
    shared_key: str
    endpoint: str
    allowed_ips : str
    latest_handshake: int
    rx: int
    tx: int
    keepalive: int

    @computed_field
    @property
    def last_seen(self) -> str:
        return "gggg"

    @computed_field
    @property
    def is_online(self)-> bool:
        return False

class ListStatisticClient(BaseModel):
    clients: Optional[List[StatisticClient]] = []

