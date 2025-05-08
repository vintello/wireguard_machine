import json
import re
import subprocess
import math
import argparse
from datetime import datetime
from operator import attrgetter
from server.schemas import StatisticClient, ListStatisticClient
from server.ini_file_core import ServerConfig, clients_scan
import logging


def status(loger: logging.Logger, wg_iface: str, wg0_file: str) -> ListStatisticClient:
    loger.info("Получаем статус клиентов")
    clients_cfgs = clients_scan()
    status_list = []
    stats = subprocess.run(['sudo', 'wg', 'show', wg_iface, 'dump'], capture_output=True)
    if stats.returncode != 0:
        loger.error(f"Error running wg show: {stats.stderr.decode()}")
        return status_list
    stats = stats.stdout.decode()
    loger.info(stats)
    stats = stats.split('\n')

    # remove first line
    stats.pop(0)
    stats.pop(len(stats) - 1)
    client_list = ListStatisticClient()
    for line in stats:
        row = line.split('\t')
        curr_client = None
        for client in clients_cfgs.clients:
            if row[0] == client.pub_key:
                curr_client = client
                break
        client_ = StatisticClient.model_validate({"pub_key": row[0],
                                                  "shared_key": row[1],
                                                  "endpoint": row[2],
                                                  "allowed_ips": row[3],
                                                  "latest_handshake": int(row[4]),
                                                  "rx": int(row[5]),
                                                  "tx": int(row[6]),
                                                  "keepalive": int(row[7]) if row[7] != 'off' else 0,
                                                  "name": None if curr_client is None else curr_client.name,
                                                  "conf_created": None if curr_client is None else curr_client.conf_created,
                                                  "used": None if curr_client is None else curr_client.used,

                                                  }
                                                 )
        client_list.clients.append(client_)

    loger.info(f"Получено {len(client_list.clients)} клиентов")
    return client_list