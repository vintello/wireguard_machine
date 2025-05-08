import pydantic
import re
import os
import ipaddress
import datetime
from server.schemas import Client, ListClients
from server.utils import get_file_source

from sqlalchemy.util import counter


class BaseModel(pydantic.BaseModel, extra="allow"):
    _sequence: int = 0

    def model_to_str(self, exclude=["_sequence"]):
        respond = ""
        if len([val for val in self]) > len(exclude):
            respond += f"[{self.__class__.__name__}]\n"
            for name, value in self:
                if name not in exclude:
                    respond += f"{name} = {value}\n"
            respond += "\n"
        return respond


class CfgFile:
    def __init__(self):
        self.cfg = []
        self.reg_name_sect = re.compile(r"\[(.*?)\]")
        self.value_sect = re.compile(r"(.*?)=(.*?)$")
        self.max_AllowedIPs = None
        self.file_source = None

    def __iter__(self):
        for x in self.cfg:
            yield x

    def read_from_file(self, file_name):
        try:
            with open(file_name) as f:
                lines = [line.rstrip() for line in f]
        except FileNotFoundError as ex:
            lines = []
        except Exception as ex:
            raise ex
        self.file_source = file_name

        curr_model = pydantic.create_model("Default", __base__=BaseModel)()
        counter = 0
        for row in lines:
            group = self.reg_name_sect.search(row)
            if group:
                counter += 1
                self.cfg.append(curr_model)
                name_sect = group.group(1).strip()
                curr_model = pydantic.create_model(name_sect, __base__=BaseModel)()
                setattr(curr_model, "_sequence", counter)
            else:
                value_re = self.value_sect.search(row)
                if value_re:
                    name_value = value_re.group(1).strip()
                    _value = value_re.group(2).strip()
                    setattr(curr_model, name_value, _value)

        self.cfg.append(curr_model)

    def append_section(self, section):
        self.cfg.append(section)

    def get_len(self):
        return len(self.cfg)

    def write(self, file_name):
        rows = sorted(self.cfg, key=lambda x: x._sequence)
        res = ""
        for row in rows:
            res += row.model_to_str()
        with open(file_name, "w") as f:
            f.write(res)


class ServerConfig:
    def __init__(self, serv_conf=None):
        self.serv_conf = serv_conf
        self.conf_file = CfgFile()
        self.conf_file.read_from_file(serv_conf)
        self.max_AllowedIPs = None
        self.file_source = None

    def get_max_peer_network(self):
        for row in self.conf_file.cfg:
            if row.__class__.__name__ == "Peer" and getattr(row, "AllowedIPs"):
                if self.max_AllowedIPs:
                    self.max_AllowedIPs = max(ipaddress.ip_network(getattr(row, "AllowedIPs")), self.max_AllowedIPs)
                else:
                    self.max_AllowedIPs = ipaddress.ip_network(getattr(row, "AllowedIPs"))
        return self.max_AllowedIPs

    def get_next_free_ip(self):
        next_ip = None
        serv_ip = self.get_serv_ip()
        max_ip = self.get_max_peer_network()
        if not max_ip:
            next_ip = ipaddress.ip_address(serv_ip) + 1
        else:
            pass

    def delete_peer(self, peer):
        for row in self.conf_file:
            if row.__class__.__name__ == "Peer":
                if row.PublicKey == peer.pub_key:
                    self.conf_file.cfg.remove(row)
                    break
        # else:
        #    raise Exception("Такой Peer не найден в конфиге")
        self.conf_file.write(self.serv_conf)

    def append_peer(self, peer):
        for row in self.conf_file:
            if row.__class__.__name__ == "Peer":
                if row.PublicKey == peer.PublicKey:
                    raise Exception("Такой Peer уже существует в конфиге")
        if not peer._sequence:
            peer._sequence = self.conf_file.get_len()
        self.conf_file.append_section(peer)

    def write(self, file_name=None):

        if not file_name:
            file_name = self.serv_conf
        self.conf_file.write(file_name)

    def get_section(self, name, numb=None):
        res = []
        count = 0
        for section in self.conf_file:
            if section.__class__.__name__ == name:
                if count == numb:
                    res.append(section)
                count += 1
        return res

    def get_serv_ip(self) -> ipaddress.ip_address:
        '''
        Получаем IP адрес сервера
        :return: IP адрес сервера
        '''
        ip_adress = None
        for row in self.conf_file:
            if row.__class__.__name__ == "Interface":
                if getattr(row, "Address"):
                    network_adress = getattr(row, "Address")
                    ip_adress = network_adress.split("/")[0]
        return ip_adress

    def get_serv_network(self) -> ipaddress.ip_network:
        '''
        Получаем сетевой адрес сервера
        :return: сетевой адрес сервера
        '''
        network_adress = None
        for row in self.conf_file:
            if row.__class__.__name__ == "Interface":
                if getattr(row, "Address"):
                    network_adress = ipaddress.ip_network(getattr(row, "Address"), strict=False)

        return network_adress

    def get_all_clients_ips(self):
        '''
        Получаем список всех IP адресов клиентов
        :return: список IP адресов клиентов
        '''
        ip_list = []
        for row in self.conf_file:
            if row.__class__.__name__ == "Peer":
                if getattr(row, "AllowedIPs"):
                    ip_addr = ipaddress.ip_network(getattr(row, "AllowedIPs")).hosts()[0]
                    ip_list.append(ipaddress.ip_address(ip_addr))
        return ip_list


class ClientConfig:
    def __init__(self, conf_file_name=None):
        self.conf_file_name = conf_file_name
        self.conf_file = CfgFile()
        self.conf_file.read_from_file(conf_file_name)

    def append_section(self, section):
        if not section._sequence:
            section._sequence = self.conf_file.get_len()
        self.conf_file.append_section(section)

    def get_section(self, name, numb=None):
        res = []
        count = 0
        for section in self.conf_file:
            if section.__class__.__name__ == name:
                if count == numb:
                    res.append(section)
                count += 1
        return res

    def write(self, file_name):
        self.conf_file.write(file_name)


class Clients:
    def __init__(self):
        clients = []

    def get_all_clients(self):
        pass


def clients_scan(directory="/etc/wireguard/clients"):
    list_clients = ListClients()
    tree = list(os.walk(directory))
    for row in tree:
        if row[0] == directory:
            pass
        else:
            subdirname = row[0].split("/")[-1]
            created_dt = os.stat(row[0]).st_ctime
            client = Client(name=subdirname,
                            conf_created = datetime.datetime.fromtimestamp(created_dt),
                            )
            files_list = [os.path.splitext(file_) for file_ in row[2]]
            for file_ in files_list:
                if ".conf" in file_[1]:
                    client.cfg_file = os.path.join(row[0], file_[0] + file_[1])
                    client.path_to_cfg = row[0]
                if ".lock" in file_[1]:
                    client.used = True
                if ".pub" in file_[1]:
                    client.pub_key = get_file_source(os.path.join(row[0], file_[0] + file_[1]))
            list_clients.clients.append(client)
    return list_clients
