import json
import re
import subprocess
import math
import argparse
from datetime import datetime
from operator import attrgetter
from server.schemas import StatisticClient, ListStatisticClient
from server.ini_file_core import ServerConfig

wg0_file = '/etc/wireguard/wg0.conf'  # wireguard config file
wg_iface = 'wg0'  # wireguard interface
sg_to_timeout = 300  # seconds needed to pass for consider client is disconnected

def status():
    # read wg config return {"client1": pub_key}
    #clients = read_wg0(wg0_file)
    srv_cfg_file = ServerConfig(wg0_file)
    status_list = []
    stats = subprocess.run(['sudo', 'wg', 'show', wg_iface, 'dump'], stdout=subprocess.PIPE).stdout.decode('utf-8')

    stats = stats.split('\n')
    stats.pop(0)
    stats.pop(len(stats) - 1)

    for line in stats:
        row = line.split('\t')
        client_ = StatisticClient.model_validate({"pub_key": row[0],
                                   "shared_key": row[1],
                                   "endpoint": row[2],
                                   "allowed_ips": row[3],
                                   "latest_handshake": int(row[4]),
                                   "rx": int(row[5]),
                                   "tx": int(row[6]),
                                   "keepalive": int(row[7])}
                                  )
        for client in clients:
            if client_.pub_key == clients[client]:
                client_.name = client
        status_list.append(client_)

    # order client list based on last_handshake
    status_list.sort(key=attrgetter('latest_handshake'), reverse=False)
    return status_list