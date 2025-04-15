import ipaddress
import os
from subprocess import check_output, run
from os import listdir, path
from server.utils import get_file_source
from server.ini_file_core import ServerConfig, ClientConfig, BaseModel
import pydantic
import pathlib

def gen_users(number_clients, cfg_folder, logger):
    try:
        pathlib.Path(path.join(cfg_folder, "clients")).mkdir(parents=True, exist_ok=True)
        clc_clients = len(listdir(path.join(cfg_folder, "clients")))
        serv_pub = get_file_source(path.join(cfg_folder,"server.pub"))
        serv_cfg = ServerConfig(path.join(cfg_folder, "wg0.conf"))
        ip = str(check_output(["curl", "https://checkip.amazonaws.com/"]))[2:-3]
        interface = serv_cfg.get_section("Interface", 0)[0]
        if interface:
            serv_addr = interface.Address.split(",")[0].strip()
            serv_dns = interface.DNS
            serv_ip_addr = [ip for ip in ipaddress.ip_network(serv_addr, False).hosts()][0]
            serv_port = interface.ListenPort
        else:
            raise Exception("please fill Interface in server config")

        for numb in range(clc_clients, clc_clients + number_clients):
            logger.info(f"Клиент № {numb-clc_clients+1} из {number_clients}")

            client_name = f"client_{numb}"
            client_folder = path.join(cfg_folder, "clients", client_name)
            run(["mkdir", client_folder])

            run(f"wg genkey | tee {client_folder}/{client_name}.key | wg pubkey > {client_folder}/{client_name}.pub", shell=True)

            client_conf_file_path = path.join(client_folder,f"{client_name}.conf")
            client_pub_key = get_file_source(path.join(client_folder,f"{client_name}.pub"))
            client_priv_key = get_file_source(path.join(client_folder,f"{client_name}.key"))

            client_conf = ClientConfig(client_conf_file_path)
            # client config
            new_client_inter = pydantic.create_model("Interface", __base__=BaseModel)()
            max_network_on_serv_conf = serv_cfg.get_max_peer_network()
            if not max_network_on_serv_conf:
                serv_ip_addr_next = serv_ip_addr + 1
                max_network_on_serv_conf = str(ipaddress.ip_network(f"{serv_ip_addr_next}/32"))

            new_client_inter.Address = max_network_on_serv_conf
            new_client_inter.DNS = serv_dns
            new_client_inter.PrivateKey = client_priv_key
            client_conf.append_section(new_client_inter)

            new_client_peer = pydantic.create_model("Peer", __base__=BaseModel)()
            new_client_peer.PublicKey = serv_pub
            new_client_peer.Endpoint = f"{ip}:{serv_port}"
            new_client_peer.AllowedIPs = "0.0.0.0/0"
            new_client_peer.PersistentKeepalive = 20
            client_conf.append_section(new_client_peer)
            client_conf.write(client_conf_file_path)
            # server config
            new_server_peer = pydantic.create_model("Peer", __base__=BaseModel)()
            new_server_peer.PublicKey = client_pub_key
            new_server_peer.AllowedIPs = max_network_on_serv_conf
            serv_cfg.append_peer(new_server_peer)
            serv_cfg.write()

    except KeyboardInterrupt or EOFError:
        print('')
        exit()
