from models import IPList
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional

class IP_List_Response(SQLModel):
    id: int | None
    ip_addr: str | None

class IP_List_Query(SQLModel):
    id: Optional[int] = None
    ip_addr: Optional[str] = Field(default=None)

class IP_List_Update(SQLModel):
    ip_addr: Optional[str]

class List_IP_List_Update(SQLModel):
    items: list[IP_List_Update]

class List_IP_List_Update_response(SQLModel):
    items: list[IP_List_Response]