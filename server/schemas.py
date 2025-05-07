from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional, List
from pydantic import BaseModel, SerializeAsAny, computed_field
from server.utils import since1
import datetime


class IP_List_Response(SQLModel):
    id: Optional[int]
    ip_addr: Optional[str]

class AccessListResponse(BaseModel):
    #draw: int
    #current_page: int
    #per_page: int
    #recordsTotal: int
    #recordsFiltered: int
    data: Optional[List[IP_List_Response]] = []


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
    path_to_cfg: Optional[str] = None
    pub_key: Optional[str] = None


class ListClients(BaseModel):
    clients: Optional[List[Client]] = []


class ListClientsWithTotal(BaseModel):
    # clients: Optional[List[Client]] = []
    total: Optional[int] = 0
    used: Optional[int] = 0
    free: Optional[int] = 0


class StatisticClient(BaseModel):
    name: Optional[str]
    pub_key: str
    shared_key: str
    endpoint: str
    allowed_ips: str
    latest_handshake: int
    rx: int
    tx: int
    keepalive: int

    @computed_field
    @property
    def last_seen(self) -> str:
        if self.latest_handshake == 0:
            return "never"

        return since1(self.latest_handshake)

    @computed_field
    @property
    def is_online(self) -> bool:
        result = False
        dt_object = datetime.datetime.fromtimestamp(self.latest_handshake, datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - dt_object
        if diff.total_seconds() < 300:
            result = True
        return result

    @computed_field
    @property
    def latest_handshake_dt(self) -> str:
        result = ""
        if self.latest_handshake != 0:
            dt_object = datetime.datetime.fromtimestamp(self.latest_handshake, datetime.timezone.utc)
            result = dt_object.strftime("%d.%m.%Y %H:%M:%S")
        return result


class ListStatisticClient(BaseModel):
    clients: Optional[List[StatisticClient]] = []

