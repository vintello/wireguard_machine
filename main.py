import logging

import sqlalchemy.exc
import uvicorn
import bcrypt
import os
from sqlmodel import Field, Session, SQLModel, create_engine, select, column
from typing import Annotated
import configparser

from fastapi import Depends, FastAPI, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse, Response
from models import SecurityConfig
from handlers.midleware import SecurityMiddleware
from models import Type_IP_List, IPList
from schemas import IP_List_Response, IP_List_Query, IP_List_Update, List_IP_List_Update, List_IP_List_Update_response
from schemas import ListClients, Client, ListClientsWithTotal
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
description = """
работа с конфигами клиентов для Wireguard сервера. 🚀

## work

сервисные точки 

## access

Управление настройками доступа к серверу.

`Внимание` если ни один IP не прописан то доступ разрешен всем

###### При потере доступа к сервису необходимо зайти в папку проекта найти файл database.db, -это sqlite база данных и туда внести в ручном режиме необходимый IP с типом whitelist 


## wireguard

работа с конфигами wireguard
"""

app = FastAPI(
    title="Wireguard Manager",
    description=description,
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
    rate_limit=1000,
    rate_limit_window=1000,
    # Auto-ban Configuration
    enable_ip_banning=True,
    enable_penetration_detection=True,
    auto_ban_threshold=1000,
    auto_ban_duration=1000,
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


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/docs")

@app.get("/get-wire",
         tags=["work"],
         description="""Возвращает свободный конфиг и маркирует его как выданный. при следующем запросе выдаст новый
         
         пример получения :
         
             $ wget -O client.conf http://<domain>/get-wire 
         
         """,
         name="Получить свободный конфиг"
         )
async def get_wire(response: Response):
    file_ = None
    data = clients_scan()
    for row in data.clients:
        if not row.used:
            file_ = row.cfg_file
            break
    if file_:
        folder_ = os.path.dirname(file_)
        file_path = os.path.join(folder_, "blocked.lock")
        with open(file_path, 'a'):
            os.utime(file_path, None)
        return FileResponse(path=file_, filename='config.conf')#, media_type='multipart/form-data')
    else:
        response.status_code = 400
        return {"message": "no_serts_available"}

@app.get("/whitelist",
         response_model=list[IP_List_Response],
         tags=["access"],
         description="Полный список всех разрешенных IP для доступа к сервису.",
         name="Получить список IP адресов и их Id"
         )
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

@app.post("/whitelist",
          response_model=List_IP_List_Update_response,
          tags=["access"],
          description="на вход можно загрузить список IP адресов для добавления.",
          name="Добавление IP адресов"
)
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

@app.patch("/whitelist/{id}",
           response_model=IP_List_Update,
           tags=["access"],
           description="на вход нужно подать id, который можно взять в пункте /whitelist.",
           name="Обновление IP"

           )
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

@app.delete("/whitelist/{id}",
            tags=["access"],
            description="на вход нужно подать id, который можно взять в пункте /whitelist",
            name="Удаление разрешения на доступ для IP"
            )
def delete_from_whitelist(id: int):
    with Session(engine) as session:
        rec = session.get(IPList, id)
        if not rec:
            raise HTTPException(status_code=404, detail=f"Record {id} not found")
        session.delete(rec)
        session.commit()
        config.whitelist.remove(rec.ip_addr)
    return {"status": "success"}

@app.get("/list_cfg/",
         response_model=ListClients,
         tags=["wireguard"],
         description="Отображает все конфигурационные файлы, которые зарегистрированы на сервере а также их статус",
         name="Просмотр конфигов на сервере"
         )
def scan_wireguard_user_configs(background_tasks: BackgroundTasks):
    data = clients_scan()
    return data

@app.get("/statistic/",
         response_model=ListClientsWithTotal,
         tags=["wireguard"],
         description="Отображает сводку по занятым и свободным конфигам в количественном выражении",
         name="Просмотр краткой сводки по конфигам"
)
def free_for_use_wireguard_user_configs(background_tasks: BackgroundTasks):
    selected_clients = ListClientsWithTotal()
    data = clients_scan()
    selected_clients.total = len(data.clients)
    used_ = 0
    free_ = 0
    for row in data.clients:
        if not row.used:
            #selected_clients.clients.append(row)
            free_ +=1
        else:
            used_+=1
    selected_clients.used = used_
    selected_clients.free = free_
    return selected_clients

def clients_scan(directory = "/etc/wireguard/clients"):
    list_clients = ListClients()
    tree = list(os.walk(directory))
    for row in tree:
        if row[0] == directory:
            pass
        else:
            subdirname = row[0].split("/")[-1]
            client = Client(name=subdirname)
            files_list = [os.path.splitext(file_) for file_ in row[2]]
            for file_ in files_list:
                if ".conf" in file_[1]:
                    client.cfg_file = os.path.join(row[0], file_[0]+file_[1])
                if ".lock" in file_[1]:
                    client.used = True
            list_clients.clients.append(client)


    return list_clients

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)#, ssl_keyfile="path/to/key.pem", ssl_certfile="path/to/cert.pem")