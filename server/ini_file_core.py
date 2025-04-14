import pydantic
import re
import ipaddress

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
            respond +="\n"
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
            lines= []
        except Exception as ex:
            raise ex
        self.file_source = file_name

        curr_model = pydantic.create_model("Default", __base__=BaseModel)()
        counter = 0
        for row in lines:
            group = self.reg_name_sect.search(row)
            if group:
                counter +=1
                self.cfg.append(curr_model)
                name_sect = group.group(1).strip()
                curr_model = pydantic.create_model(name_sect, __base__=BaseModel)()
                setattr(curr_model, "_sequence", counter)
            else:
                value_re = self.value_sect.search(row)
                if value_re:
                    name_value = value_re.group(1).strip()
                    _value = value_re.group(2).strip()
                    setattr(curr_model,name_value,_value)

        self.cfg.append(curr_model)

    def append_section(self, section):
        self.cfg.append(section)

    def get_len(self):
        return len(self.cfg)

    def write(self, file_name):
        rows = sorted(self.cfg, key=lambda x: x._sequence)
        res = ""
        for row in rows:
            res+= row.model_to_str()
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
            if row.__class__.__name__== "Peer" and getattr(row,"AllowedIPs"):

                if self.max_AllowedIPs:
                    self.max_AllowedIPs = max(ipaddress.ip_network(getattr(row, "AllowedIPs")), self.max_AllowedIPs)
                else:
                    self.max_AllowedIPs = ipaddress.ip_network(getattr(row,"AllowedIPs"))

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


class ClientConfig:
    def __init__(self, conf_file_name=None):
        self.conf_file_name = conf_file_name
        self.conf_file = CfgFile()
        self.conf_file.read_from_file(conf_file_name)

    def append_section(self, section):
        if not section._sequence:
            section._sequence = self.conf_file.get_len()
        self.conf_file.append_section(section)

    def write(self, file_name):
        self.conf_file.write(file_name)
