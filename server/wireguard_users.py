import ipaddress
import os
from logging import Logger
from subprocess import check_output, run
from os import listdir, path
from server.utils import get_file_source, get_host_server_ip, get_ip_next_server_config
from server.ini_file_core import ServerConfig, ClientConfig, BaseModel
import pydantic
import server.utils
import pathlib
import uuid


def gen_users(number_clients, cfg_folder, logger: Logger):
    new_user_list = []
    try:
        # ставим блокировку на генерацию
        blk_file_path = "generated.lock"
        blk_file_path = pathlib.Path(blk_file_path)
        if blk_file_path.exists():
            blk_file_path.unlink(missing_ok=True)
        with open(blk_file_path, 'a'):
            os.utime(blk_file_path, None)

        pathlib.Path(path.join(cfg_folder, "clients")).mkdir(parents=True, exist_ok=True)

        # clc_clients = len(listdir(path.join(cfg_folder, "clients")))
        serv_pub = get_file_source(path.join(cfg_folder, "server.pub"))
        serv_cfg = ServerConfig(path.join(cfg_folder, "wg0.conf"))

        ip_serv = get_host_server_ip()
        logger.debug(f"IP сервера: {ip_serv}")
        interface = serv_cfg.get_section("Interface", 0)[0]
        serv_port = interface.ListenPort
        serv_dns = interface.DNS

        for numb in range(1, number_clients + 1):
            new_client_ip = get_ip_next_server_config(serv_cfg)
            new_client_network = ipaddress.ip_network(f"{new_client_ip}/32")
            numb_uuid = str(uuid.uuid4())
            logger.info(f"Клиент № {numb} из {number_clients}")
            logger.info(f"подобран IP {new_client_ip}")
            logger.info(f"Сгенерирован UUID {numb_uuid}")

            client_name = f"client_{numb_uuid}"
            client_folder = path.join(cfg_folder, "clients", client_name)
            run(["mkdir", client_folder])

            run(f"wg genkey | tee {client_folder}/client.key | wg pubkey > {client_folder}/client.pub", shell=True)

            client_conf_file_path = path.join(client_folder, "client.conf")
            client_pub_key = get_file_source(path.join(client_folder, "client.pub"))
            client_priv_key = get_file_source(path.join(client_folder, "client.key"))

            client_conf = ClientConfig(client_conf_file_path)
            # client config
            new_client_inter = pydantic.create_model("Interface", __base__=BaseModel)()

            new_client_inter.Address = new_client_network
            new_client_inter.DNS = serv_dns
            new_client_inter.PrivateKey = client_priv_key
            client_conf.append_section(new_client_inter)

            new_client_peer = pydantic.create_model("Peer", __base__=BaseModel)()
            new_client_peer.PublicKey = serv_pub
            new_client_peer.Endpoint = f"{ip_serv}:{serv_port}"
            new_client_peer.AllowedIPs = "0.0.0.0/0"
            new_client_peer.PersistentKeepalive = 10
            client_conf.append_section(new_client_peer)
            client_conf.write(client_conf_file_path)
            # server config
            new_server_peer = pydantic.create_model("Peer", __base__=BaseModel)()
            new_server_peer.PublicKey = client_pub_key
            new_server_peer.AllowedIPs = new_client_network

            serv_cfg.append_peer(new_server_peer)
            serv_cfg.write()

            # https://serverfault.com/questions/1101002/wireguard-client-addition-without-restart
            # wg set wg0 peer "K30I8eIxuBL3OA43Xl34x0Tc60wqyDBx4msVm8VLkAE=" allowed-ips 10.101.1.2/32
            # ip -4 route add 10.101.1.2/32 dev wg0
            # run(f'wg set wg0 peer "{client_pub_key}" allowed-ips {max_network_on_serv_conf}', shell=True)
            res = server.utils.run_system_command(
                f'wg set wg0 peer "{client_pub_key}" allowed-ips {new_client_network}')

            run(f'ip -4 route add {new_client_network} dev wg0', shell=True)

            # добавляем клиента в список
            new_user_list.append(client_conf.conf_file_name)
    except Exception as ex:
        logger.exception("Генерация клиентов закончилась с ошибкой")
        raise ex
    finally:
        blk_fl = pathlib.Path(blk_file_path)
        if blk_fl.exists():
            blk_fl.unlink(missing_ok=True)
    return new_user_list

