import logging

import sqlalchemy.exc
import uvicorn
import bcrypt
import os
from sqlmodel import Field, Session, SQLModel, create_engine, select, column
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status, Request
from models import SecurityConfig
from handlers.midleware import SecurityMiddleware
from models import Type_IP_List, IPList
from schemas import IP_List_Response, IP_List_Query, IP_List_Update, List_IP_List_Update, List_IP_List_Update_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
loggersql = logging.getLogger('sqlalchemy.engine')
loggersql.setLevel(logging.DEBUG)

if not hasattr(bcrypt, '__about__'):
    bcrypt.__about__ = type('about', (object,), {'__version__': bcrypt.__version__})

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def get_ip_list(type_ip:Type_IP_List):
    ip_list = set()
    with Session(engine) as session:
        statement = select(IPList).where(IPList.type_rec == type_ip)
        results = session.exec(statement)
        for row in results.all():
            ip_list.add(row.ip_addr)
    return [ip for ip in ip_list]



SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI(
    title="Wireguard Manager",
    description="""
работа с конфигами клиентов для Wireguard сервера
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.state.whitelist_list = get_ip_list(Type_IP_List.whitelist)
print(app.state.whitelist_list)

config = SecurityConfig(
    # Whitelist/Blacklist
    whitelist=app.state.whitelist_list,#get_ip_list(Type_IP_List.whitelist),#["0.0.0.0", "0.0.0.0/0"],
    blacklist=[],#"192.168.0.1/32", "10.0.0.100/32"],
    # Rate Limiting
    rate_limit=30,
    rate_limit_window=60,
    # Auto-ban Configuration
    enable_ip_banning=True,
    enable_penetration_detection=True,
    auto_ban_threshold=30,
    auto_ban_duration=60,
    # Excluded Paths
    exclude_paths=[
        #"/docs",
        #"/redoc",
        #"/openapi.json",
        #"/openapi.yaml",
        "/favicon.ico",
        "/static",
    ],
    # User Agent settings
    blocked_user_agents=["badbot", "malicious-crawler"],
    # IPInfo integration
    ipinfo_token=str(os.getenv("IPINFO_TOKEN")),
    #blocked_countries=["CN", "RU"],
    # Redis integration
    # NOTE: enable_redis=True by default
    #redis_url="redis://localhost:6379",
    #redis_prefix="fastapi_guard",
)
app.add_middleware(SecurityMiddleware, config=config)



@app.get("/get-wire")
async def get_wire(request: Request):
    return [{"item_id": "Foo", "owner": "current_user.username"}]

@app.get("/whitelist", response_model=list[IP_List_Response], tags=["access"])
async def list_whitelist(params: IP_List_Query = Depends()):
    with Session(engine) as session:
        statement = select(IPList).where(IPList.type_rec == Type_IP_List.whitelist)
        if params.ip_addr:
            statement = statement.where(column("ip_addr").ilike(f"%{params.ip_addr}%"))
        if params.id:
            statement = statement.where(IPList.id == params.id)
        #print(statement.compile(compile_kwargs={"literal_binds": True}))
        heroes = session.exec(statement).all()
        return heroes

@app.post("/whitelist", response_model=List_IP_List_Update_response, tags=["access"])
def post_whitelist(params: List_IP_List_Update = Depends()):
    with Session(engine) as session:
        result = []
        for row in params.items:
            try:
                new_data = row.model_dump(exclude_unset=True)
                new_data["type_rec"] = Type_IP_List.whitelist
                rec = IPList(**new_data)
                session.add(rec)
                session.commit()
                session.flush(rec)
                fill_resp = IP_List_Response(**{"id": rec.id, "ip_addr": rec.ip_addr})
            except sqlalchemy.exc.IntegrityError as ex:
                session.rollback()
                fill_resp = IP_List_Response(**{"id": None, "ip_addr": rec.ip_addr})


            result.append(fill_resp)
        resp = List_IP_List_Update_response(items = result)
        for row in result:
            config.whitelist.append(row.ip_addr)
    return resp

@app.patch("/whitelist/{id}", response_model=IP_List_Update, tags=["access"])
def update_whitelist(id: int, while_ip: IP_List_Update):
    with Session(engine) as session:
        rec = session.get(IPList, id)
        if not rec:
            raise HTTPException(status_code=404, detail=f"Record {id} not found")
        new_data = while_ip.model_dump(exclude_unset=True)
        rec.sqlmodel_update(new_data)
        session.add(rec)
        session.commit()
        session.refresh(rec)

        config.whitelist.append(rec.ip_addr)
    return rec

@app.delete("/whitelist/{id}", tags=["access"])
def delete_from_whitelist(id: int):
    with Session(engine) as session:
        rec = session.get(IPList, id)
        if not rec:
            raise HTTPException(status_code=404, detail=f"Record {id} not found")
        session.delete(rec)
        session.commit()
        config.whitelist.remove(rec.ip_addr)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)#, ssl_keyfile="path/to/key.pem", ssl_certfile="path/to/cert.pem")