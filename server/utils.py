# fastapi_guard/utils.py
import logging
import os
import pathlib
import re
from ipaddress import IPv4Address, ip_network
from typing import Any, Optional, Union
import subprocess
import math
import datetime

from fastapi import Request

from server.models import SecurityConfig
from server.handlers.ipinfo_handler import IPInfoManager
from server.handlers.sus_patterns import SusPatterns


async def setup_custom_logging(log_file: str) -> logging.Logger:
    """
    Setup custom logging
    for the application.
    """
    logger = logging.getLogger(__name__)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    return logger


async def log_request(request: Request, logger: logging.Logger) -> None:
    """
    Log the details of
    an incoming request.

    Args:
        request (Request):
            The FastAPI request object.
        logger (logging.Logger):
            The logger instance to use.
    """
    client_ip = "unknown"
    if request.client:
        client_ip = request.client.host

    method = request.method
    url = str(request.url)
    headers: dict[str, Any] = dict(request.headers)
    message = "Request from"
    details = f"{message} {client_ip}: {method} {url}"
    reason_message = f"Headers: {headers}"
    logger.info(f"{details} - {reason_message}")


async def log_suspicious_activity(request: Request, reason: str, logger: logging.Logger) -> None:
    """
    Log suspicious activity
    detected in a request.

    Args:
        request (Request):
            The FastAPI request object.
        reason (str):
            The reason for flagging
            the activity as suspicious.
        logger (logging.Logger):
            The logger instance to use.
    """
    client_ip = "unknown"
    if request.client:
        client_ip = request.client.host

    method = request.method
    url = str(request.url)
    headers = dict(request.headers)
    message = "Suspicious activity detected from "
    details = f"{message} {client_ip}: {method} {url}"
    reason_message = f"Reason: {reason} - Headers: {headers}"
    logger.warning(f"{details} - {reason_message}")


async def is_user_agent_allowed(user_agent: str, config: SecurityConfig) -> bool:
    """
    Check if the user agent is allowed
    based on the security configuration.

    Args:
        user_agent (str):
            The user agent string to check.
        config (SecurityConfig):
            The security configuration object.

    Returns:
        bool: True if the user agent
              is allowed, False otherwise.
    """
    for pattern in config.blocked_user_agents:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return False
    return True


async def check_ip_country(request: (Union[str, Request]), config: SecurityConfig, ipinfo_db: IPInfoManager) -> bool:
    """
    Check if IP is from a blocked country
    or in the whitelist.

    Args:
        request (Union[str, Request]):
            The FastAPI request object or IP string.
        config (SecurityConfig):
            The security configuration object.
        ipinfo_db (IPInfoManager):
            The IPInfo database handler.

    Returns:
        bool:
            True if the IP is from a blocked
            country or in the whitelist,
            False otherwise.
    """
    if not config.blocked_countries and not config.whitelist_countries:
        message = "No countries blocked or whitelisted"
        host = ""
        if isinstance(request, str):
            host = request
        elif request.client:
            host = request.client.host
        details = f"{host}"
        reason_message = "No countries blocked or whitelisted"
        logging.warning(f"{message} {details} - {reason_message}")
        return False

    if not ipinfo_db.reader:
        await ipinfo_db.initialize()

    ip = (
        request
        if isinstance(request, str)
        else (request.client.host if request.client else "unknown")
    )
    country = ipinfo_db.get_country(ip)

    if not country:
        message = "IP not geolocated"
        details = f"{ip}"
        reason_message = "IP geolocation failed"
        logging.warning(f"{message} {details} - {reason_message}")
        return False

    if config.whitelist_countries and country in config.whitelist_countries:
        message = "IP from whitelisted country"
        details = f"{ip} - {country}"
        reason_message = "IP from whitelisted country"
        logging.info(f"{message} {details} - {reason_message}")
        return False

    if config.blocked_countries and country in config.blocked_countries:
        message = "IP from blocked country"
        details = f"{ip} - {country}"
        reason_message = "IP from blocked country"
        logging.warning(f"{message} {details} - {reason_message}")
        return True

    message = "IP not from blocked or whitelisted country"
    details = f"{ip} - {country}"
    reason_message = "IP not from blocked or whitelisted country"
    logging.info(f"{message} {details} - {reason_message}")
    return False


async def is_ip_allowed(ip: str, config: SecurityConfig, ipinfo_db: Optional[IPInfoManager] = None) -> bool:
    """
    Check if the IP address is allowed
    based on the security configuration.

    Args:
        ip (str):
            The IP address to check.
        config (SecurityConfig):
            The security configuration object.
        ipinfo_db (Optional[IPInfoManager]):
            The IPInfo database handler.

    Returns:
        bool:
            True if the IP is allowed, False otherwise.
    """
    try:
        ip_addr = IPv4Address(ip)

        # Blacklist
        if config.blacklist:
            for blocked in config.blacklist:
                if "/" in blocked:  # CIDR
                    if ip_addr in ip_network(blocked, strict=False):
                        return False
                elif ip == blocked:  # Direct match
                    return False

        # Whitelist
        if config.whitelist:
            for allowed in config.whitelist:
                if "/" in allowed:  # CIDR
                    if ip_addr in ip_network(allowed, strict=False):
                        return True
                elif ip == allowed:  # Direct match
                    return True
            return False  # If whitelist exists but IP not in it

        # Blocked countries
        if config.blocked_countries and ipinfo_db:
            country = await check_ip_country(ip, config, ipinfo_db)
            if country:
                return False

        # Cloud providers
        if config.block_cloud_providers and cloud_handler.is_cloud_ip(
            ip, config.block_cloud_providers
        ):
            return False
        return True
    except ValueError:
        return False  # Invalid IP
    except Exception as e:
        logging.error(f"Error checking IP {ip}: {str(e)}")
        return True


async def detect_penetration_attempt(request: Request) -> bool:
    """
    Detect potential penetration
    attempts in the request.

    This function checks various
    parts of the request
    (query params, body, path, headers)
    against a list of suspicious
    patterns to identify potential security threats.

    Args:
        request (Request):
            The FastAPI request object to analyze.

    Returns:
        bool:
            True if a potential attack is
            detected, False otherwise.
    """

    suspicious_patterns = await SusPatterns().get_all_compiled_patterns()

    async def check_value(value: str) -> bool:
        try:
            import json

            data = json.loads(value)
            if isinstance(data, dict):
                return any(
                    pattern.search(str(v))
                    for v in data.values()
                    if isinstance(v, str)
                    for pattern in suspicious_patterns
                )
        except json.JSONDecodeError:
            return any(pattern.search(value) for pattern in suspicious_patterns)
        return False

    # Query params
    for value in request.query_params.values():
        if await check_value(value):
            message = "Potential attack detected from"
            client_ip = "unknown"
            if request.client:
                client_ip = request.client.host
            details = f"{client_ip}: {value}"
            reason_message = "Suspicious pattern: query param"
            logging.warning(f"{message} {details} - {reason_message}")
            return True

    # Path
    if await check_value(request.url.path):
        message = "Potential attack detected from"
        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host
        details = f"{client_ip}: {request.url.path}"
        reason_message = "Suspicious pattern: path"
        logging.warning(f"{message} {details} - {reason_message}")
        return True

    # Headers
    excluded_headers = {
        "host",
        "user-agent",
        "accept",
        "accept-encoding",
        "connection",
        "origin",
        "referer",
        "sec-fetch-site",
        "sec-fetch-mode",
        "sec-fetch-dest",
    }
    for key, value in request.headers.items():
        if key.lower() not in excluded_headers and await check_value(value):
            message = "Potential attack detected from"
            client_ip = "unknown"
            if request.client:
                client_ip = request.client.host
            details = f"{client_ip}: {key}={value}"
            reason_message = "Suspicious pattern: header"
            logging.warning(f"{message} {details} - {reason_message}")
            return True

    # Body
    try:
        body = (await request.body()).decode()
        if await check_value(body):
            message = "Potential attack detected from"
            client_ip = "unknown"
            if request.client:
                client_ip = request.client.host
            details = f"{client_ip}: {body}"
            reason_message = "Suspicious pattern: body"
            logging.warning(f"{message} {details} - {reason_message}")
            return True
    except Exception:
        pass

    return False

def mess_window(mess, type_mess="error"):
    print("\n\n")
    total_len = 100
    if type_mess == "error":
        head_mess = "О Ш И Б К А"
    elif type_mess == "warning":
        head_mess = "В Н И М А Н И Е"
    print("=" * 40 + head_mess + "=" * (total_len-40-len(head_mess)))
    print(f"{mess}")
    print("=" * 100)
    print("\n\n")

def get_file_source(file_name):
    source_txt = None
    with open(file_name, "r") as f:
        source_txt = f.read()
    return source_txt.strip()

def run_system_command(command: str) -> Optional[str]:
    """Выполняет системную команду и возвращает её вывод."""
    result = os.system(command)
    return result

def get_host_server_ip(file_name="/etc/wireguard/ip_host"):
    res = None
    if pathlib.Path(file_name).exists():
        res = get_file_source(file_name)
    if not res:
        res = str(subprocess.check_output(["curl", "https://checkip.amazonaws.com/"]))[2:-3]
    return res

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def since1(date):
    now = datetime.datetime.now()
    then = datetime.datetime.fromtimestamp(int(date))
    duration = now - then
    return duration

def get_ip_next_server_config(srv_cfg_file):
    #srv_cfg_file = ServerConfig(wg0_file)
    free_ip = None

    srv_ip = IPv4Address(srv_cfg_file.get_serv_ip())
    srv_network = srv_cfg_file.get_serv_network()
    list_srv_ip_network = list(srv_network.hosts())

    all_clients_ips = srv_cfg_file.get_all_clients_ips()
    all_excluded_ips = set(all_clients_ips)
    all_excluded_ips.add(srv_ip)

    for excl_ip in all_excluded_ips:
        try:
            list_srv_ip_network.remove(excl_ip)
        except Exception as ex:
            logging.exception(f"при попытке удалить {excl_ip}: \n")

    if len(list_srv_ip_network) == 0:
        raise Exception("no free IPs")
    else:
        free_ip = list_srv_ip_network[0]
    return free_ip

def remove_client(client, logger:logging.Logger, srv_cfg_file):
    logger.info(f"Удаляем конфиг клиента: \n{client}")
    pub_key = client.pub_key
    client_folder = os.path.join("/etc/wireguard/clients", client.name) if client.name else None
    if client_folder and os.path.exists(client_folder):
        # удаляем папку с конфигами клиента
        pth = pathlib.Path(client_folder)
        for sub in pth.iterdir():
            if sub.is_file():
                sub.unlink()
        pth.rmdir()

    srv_cfg_file.delete_peer(client)
    # удаляем динамически в wireguard
    #wg set wg0 peer "K30I8eIxuBL3OA43Xl34x0Tc60wqyDBx4msVm8VLkAE=" remove
    #ip -4 route delete 10.101.1.2/32 dev wg0
    run_system_command(f'wg set wg0 peer "{pub_key}" remove')
    run_system_command(f'ip -4 route delete {client.allowed_ips} dev wg0')


