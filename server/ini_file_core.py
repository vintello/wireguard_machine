import pydantic
import re


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
        with open(file_name) as f:
            lines = [line.rstrip() for line in f]
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