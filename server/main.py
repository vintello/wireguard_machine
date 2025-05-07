import logging
import pathlib
from contextlib import asynccontextmanager

import sqlalchemy.exc
import uvicorn
import bcrypt
import os
import csv
import io
from typing import Optional
from sqlmodel import Session, SQLModel, create_engine, select, column
from typing import List
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Request, UploadFile
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, Response
from fastapi_utils.tasks import repeat_every
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from server.models import SecurityConfig
from server.models import Type_IP_List, IPListAccess
from server.schemas import IP_List_Response, IP_List_Query, IP_List_Update, List_IP_List_Update, \
    List_IP_List_Update_response
from server.schemas import ListClients, Client, ListClientsWithTotal, AccessListResponse
from server.handlers.midleware import SecurityMiddleware
from server.wireguard_users import gen_users
from server.utils import get_file_source, run_system_command, get_ip_next_server_config
from server.utils import remove_client
from server.user_statistics import status
from server.ini_file_core import clients_scan, ServerConfig, ClientConfig
import ipaddress
import datetime
from sqlalchemy import func

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')

f_handler = logging.handlers.TimedRotatingFileHandler("server.log", when="D", interval=1, backupCount=5)
f_handler.setFormatter(formatter)
logger.addHandler(f_handler)
middleware_log = logging.getLogger("server.handlers.midleware")
middleware_log.addHandler(f_handler)
# loggersql = logging.getLogger('sqlalchemy.engine')
# loggersql.setLevel(logging.INFO)

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


def get_ip_list(type_ip: Type_IP_List):
    ip_list = set()
    with Session(engine) as session:
        statement = select(IPListAccess).where(IPListAccess.type_rec == type_ip)
        results = session.exec(statement)
        for row in results.all():
            try:
                if ipaddress.ip_address(row.ip_addr):
                    ip_list.add(row.ip_addr)
            except Exception as ex:
                logger.warning(f"ошибка преобразования в IP - id:'{row.id}' IP:'{row.ip_addr}'")
    return [ip for ip in ip_list]


@repeat_every(seconds=60)
async def remove_expired_tokens_task():
    '''
    Удаляем токены которые не использовались более 10 минут
    :return:'''
    wg0_file = '/etc/wireguard/wg0.conf'
    wg_iface = 'wg0'  # wireguard interface
    status_list = status(logger, wg_iface, wg0_file)
    srv_cfg_file = ServerConfig(wg0_file)

    for client in status_list.clients:
        if not client.is_online:
            pub_key = client.pub_key
            client_folder = os.path.join("/etc/wireguard/clients", client.name) if client.name else None
            if client_folder and os.path.exists(client_folder):
                lock_file = None
                for file in os.listdir(client_folder):
                    if file.endswith(".lock"):
                        lock_file = os.path.join(client_folder, file)

                if lock_file:
                    logger.info(f"АВТОЧИСТКА. Файл блокировки {lock_file} существует. Конфиг {client.name} не удален")
                    continue
                else:
                    remove_client(client, logger=logger, srv_cfg_file=srv_cfg_file)
                    logger.info(f"АВТОЧИСТКА. Конфиг {client.name} удален")
            else:
                logger.info(f"АВТОЧИСТКА. Конфиг для {pub_key} не найден")
                remove_client(client, logger=logger, srv_cfg_file=srv_cfg_file)
                logger.info(f"АВТОЧИСТКА. {pub_key} с сервера удален")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create remove task by scheduller
    await remove_expired_tokens_task()
    yield
    # do any on finish


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
    lifespan=lifespan
    # swagger_favicon_url="/favicon.ico"
)
app.state.whitelist_list = get_ip_list(Type_IP_List.whitelist)
app.mount("/static", StaticFiles(directory="server/static"), name="static")
templates = Jinja2Templates(directory="server/templates")

config = SecurityConfig(
    # Whitelist/Blacklist
    whitelist=app.state.whitelist_list,  # get_ip_list(Type_IP_List.whitelist),#["0.0.0.0", "0.0.0.0/0"],
    blacklist=[],  # "192.168.0.1/32", "10.0.0.100/32"],
    # Rate Limiting
    rate_limit=1000,
    rate_limit_window=1000,
    # Auto-ban Configuration
    enable_ip_banning=True,
    enable_penetration_detection=False,
    auto_ban_threshold=1000,
    auto_ban_duration=1000,
    # Excluded Paths
    exclude_paths=[
        "/ping",
        "/favicon.ico",
        "/static",
    ],
    # User Agent settings
    blocked_user_agents=["badbot", "malicious-crawler"],
    # IPInfo integration
    ipinfo_token=str(os.getenv("IPINFO_TOKEN")),
)

app.add_middleware(SecurityMiddleware, config=config)


@app.get("/", include_in_schema=False)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="statistic.html",
    )
    #return RedirectResponse("/docs")


#@app.get("/ping", tags=["work"])
def ping_pong():
    return "pong"

@app.get("/access", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="access_list.html",
    )


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("server/static/favicon.ico")


@app.get("/get-wire", response_class=PlainTextResponse,
         tags=["work"],
         description="""Возвращает свободный конфиг и маркирует его как выданный. при следующем запросе выдаст новый

         пример получения :

             $ wget -O client.conf http://<domain>/get-wire 

         """,
         name="Получить свободный конфиг"
         )
async def get_wire(response: Response):
    new_user_cfg = gen_wireguard_users(number_clients=1)
    file_cnt = None
    # print(new_user_cfg)
    if new_user_cfg:
        cfg_file_ = new_user_cfg[0]
        # print(cfg_file_)
        file_cnt = get_file_source(cfg_file_)
    if file_cnt:
        return file_cnt
    else:
        response.status_code = 400
        return {"message": "no_serts_available"}


async def get_wire_old(response: Response):
    file_ = None
    data = clients_scan()
    for row in data.clients:
        if not row.used:
            file_ = row.cfg_file
            break
    if file_:
        folder_ = os.path.dirname(file_)
        file_path = os.path.join(folder_, "used.lock")
        with open(file_path, 'a'):
            os.utime(file_path, None)
        file_cnt = get_file_source(file_)
        return file_cnt
    else:
        response.status_code = 400
        return {"message": "no_serts_available"}


@app.get("/whitelist",
         response_model=AccessListResponse,
         tags=["access"],
         description="Полный список всех разрешенных IP для доступа к сервису.",
         name="Получить список IP адресов и их Id"
         )
async def list_whitelist(request: Request, params: IP_List_Query = Depends()):

    draw = request.query_params.get('draw', 1)
    search = request.query_params.get("search[value]", False)
    length_ = int(request.query_params.get('length', 300))
    start = int(request.query_params.get('start', 0))
    page = int((length_ + start) / length_)
    with Session(engine) as session:
        statement = select(IPListAccess).where(IPListAccess.type_rec == Type_IP_List.whitelist)
        if params.ip_addr:
            statement = statement.where(column("ip_addr").ilike(f"%{params.ip_addr}%"))
        if params.id:
            statement = statement.where(IPListAccess.id == params.id)
        heroes = session.exec(statement).all()
    resp = AccessListResponse(
        data=heroes
    )
    return resp

@app.post("/whitelist_file",
          tags=["access"],
          description="на вход можно загрузить список IP адресов для добавления CSV формате.",
          name="Добавление IP адресов"
          )
def whitelist_upload_file(file: UploadFile):
    result = []
    tt= file.file.read().decode('utf-8')
    reader_obj = csv.reader(io.StringIO(tt), delimiter=",")
    with Session(engine) as session:
        for row in reader_obj:
            print(row[0])
            new_data= dict()
            new_data["ip_addr"] = row[0]
            new_data["type_rec"] = Type_IP_List.whitelist
            rec = IPListAccess(**new_data)
            session.add(rec)
            session.commit()
            session.flush(rec)
            fill_resp = IP_List_Response(**{"id": rec.id, "ip_addr": rec.ip_addr})
            result.append(fill_resp)
    resp = List_IP_List_Update_response(items=result)
    return resp

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
                rec = IPListAccess(**new_data)
                session.add(rec)
                session.commit()
                session.flush(rec)
                fill_resp = IP_List_Response(**{"id": rec.id, "ip_addr": rec.ip_addr})
            except sqlalchemy.exc.IntegrityError as ex:
                session.rollback()
                fill_resp = IP_List_Response(**{"id": None, "ip_addr": rec.ip_addr})

            result.append(fill_resp)
        resp = List_IP_List_Update_response(items=result)
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
        rec = session.get(IPListAccess, id)
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
        rec = session.get(IPListAccess, id)
        if not rec:
            raise HTTPException(status_code=404, detail=f"Record {id} not found")
        session.delete(rec)
        session.commit()
        try:
            config.whitelist.remove(rec.ip_addr)
        except Exception as ex:
            logger.exception(f"при удалении из списка доступа {rec.ip_addr}")
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
            # selected_clients.clients.append(row)
            free_ += 1
        else:
            used_ += 1
    selected_clients.used = used_
    selected_clients.free = free_
    return selected_clients


# оставляю на всякий случай
# @app.get("/gen_clients/",
#         # response_model=ListClientsWithTotal,
#         tags=["wireguard"],
#         description="Генерируем необходимое количество клиентов. Если клиенты ранее существовали то будет добавлено указанное количество",
#         name="Генерация клиентов",
#         include_in_schema=False
#         )
def gen_wireguard_users(number_clients: int = 300):
    # number_clients = 300
    cfg_folder = "/etc/wireguard"
    blk_file_path = "generated.lock"
    fname = pathlib.Path(blk_file_path)
    new_user_list = []
    if fname.exists():
        mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime, tz=datetime.timezone.utc)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        how_long = now - mtime
        if datetime.timedelta(minutes=10) < how_long:
            new_user_list = gen_users(number_clients, cfg_folder, logger)
        else:
            raise HTTPException(status_code=400,
                                detail=f"В текущий момент идет генерация. Повторите попозже (запущено {how_long} назад)")
    else:
        new_user_list = gen_users(number_clients, cfg_folder, logger)
    return new_user_list


@app.get("/wireguard_user_status",
         tags=["wireguard"],
         description="Возвращает статус всех клиентов Wireguard. аналогично wg show",
         name="Получить статус всех клиентов Wireguard", )
def wireguard_user_status():
    wg0_file = '/etc/wireguard/wg0.conf'  # wireguard config file
    wg_iface = 'wg0'  # wireguard interface
    status_list = status(logger, wg_iface, wg0_file)
    return status_list

@app.get("/wireguard_user_status_blank")
def templ_user_status():
    data = {
      "clients": [
        {
          "name": "client_1d7dc416-2db9-4b3d-b36b-2466eea1ea39",
          "pub_key": "fobvYFJQWEF5D3aiFxjv77Q5jgdCAVcT5bFpqSbKO10=",
          "shared_key": "(none)",
          "endpoint": "(none)",
          "allowed_ips": "10.9.0.2/32",
          "latest_handshake": 0,
          "rx": 0,
          "tx": 0,
          "keepalive": 0,
          "last_seen": "never",
          "is_online": False,
          "latest_handshake_dt": ""
        }
      ]
    }
    return data

@app.delete("/del_all_cfg",
            tags=["wireguard"],
            description="""Удаляет все конфигурационные файлы клиентов, которые не используются в данный момент, 
         и также чистит wg0.cfg сервера. 
         Если в папке есть файл .lock то такой конфиг не удаяется в автоматическом режиме. зайдите на сервер с правами администратора и удалите файл .lock""",
            name="Удаление ВСЕХ конфигов клиентов и пользователей в Wireguard", )
def del_all_cfg():
    wg0_file = '/etc/wireguard/wg0.conf'
    wg_iface = 'wg0'  # wireguard interface
    logger.info("Удаляем все конфиги клиентов")
    status_list = status(logger, wg_iface, wg0_file)
    client_removed_list = []
    srv_cfg_file = ServerConfig(wg0_file)

    for row in status_list.clients:
        pub_key = row.pub_key
        client_folder = os.path.join("/etc/wireguard/clients", row.name) if row.name else None
        if client_folder and os.path.exists(client_folder):
            lock_file = None
            for file in os.listdir(client_folder):
                if file.endswith(".lock"):
                    lock_file = os.path.join(client_folder, file)

            if lock_file:
                logger.info(f"Файл блокировки {lock_file} существует. Конфиг {row.name} не удален")
                client_removed_list.append({"name": row.name, "pub_key": pub_key, "status": "lock_file"})
                continue
            else:
                remove_client(row, logger=logger, srv_cfg_file=srv_cfg_file)
                client_removed_list.append({"name": row.name, "pub_key": pub_key, "status": "deleted"})
                logger.info(f"Конфиг {row.name} удален")
        else:
            logger.info(f"Конфиг для {pub_key} не найден")
            remove_client(row, logger=logger, srv_cfg_file=srv_cfg_file)
            client_removed_list.append({"name": row.name, "pub_key": pub_key, "status": "deleted"})
            logger.info(f"{pub_key} с сервера удален")

    srv_cfg_file.write()

    return client_removed_list


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)