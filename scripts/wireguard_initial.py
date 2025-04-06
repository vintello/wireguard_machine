#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import check_output, run
from time import sleep
from os.path import exists
from os import listdir, linesep
import sqlite3

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
try:
    # проверяем наличие базы данных
    if not exists("../database.db"):
        mess_window("Не найдена база данных. Необходимо в первую очередь запустить проект", )
        exit()
    if not "root" in str(check_output("whoami")):
        mess_window("Этот скрипт нужно запускать от имени администратора (root), используй 'sudo'.")
        exit()

    try:
        from qrcode import QRCode
    except ModuleNotFoundError:
        print("Инсталируем qrcode module")
        sleep(2)
        run(["apt", "install", "python3-qrcode"])

    if exists("/etc/wireguard") and not exists("/etc/wireguard/run-script-to-add-more-clients") and not exists("/etc/wireguard/run-script-to-configure"):
        mess = '''
        Похоже WireGuard уже установлен
        Это приведет к удалению вашей текущей конфигурации, и ваши клиенты больше не будут работать.
        Предполагается, что WireGuard работал и раньше.
        Если это так, нажмите ^C чтобы остановить работу.
        Если не так, то нажмите Enter чтобы удалить конфигурации в автоматическом режиме
        '''
        mess_window(mess, "warning")
        input("Нажмите Enter, чтобы продолжить...")
        run(["rm", "-r", "/etc/wireguard/"])
        run(["mkdir", "/etc/wireguard/"])
        run(["touch", "/etc/wireguard/run-script-to-configure"])

    if not exists("/etc/wireguard"):

        print("\nОбновление системы\n")
        sleep(2)
        run(["apt", "update"])
        run(["apt", "upgrade"])

        print("\nУстановка зависимостей\n")
        sleep(2)
        run(["apt", "install", "curl", "libelf-dev", "pkg-config", "build-essential", "git", "dirmngr", "wireguard", "openresolv"])

        """print("\nDownloading WireGuard and WireGuard tools\n")
        sleep(2)
        run(["git", "clone", "https://git.zx2c4.com/wireguard-linux-compat"])
        run(["git", "clone", "https://git.zx2c4.com/wireguard-tools"])

        print("\nCompiling WireGuard\n")
        sleep(2)
        run(["make -C wireguard-linux-compat/src -j$(nproc)"], shell=True)
        run(["sudo", "make", "-C", "wireguard-linux-compat/src", "install"])

        print("\nCompiling WireGuard tools\n")
        sleep(2)
        run(["make -C wireguard-tools/src -j$(nproc)"], shell=True)
        run(["make", "-C", "wireguard-tools/src", "install"])

        print("\nRemoving WireGuard source code")
        sleep(2)
        run(["rm", "-r", "wireguard-tools", "wireguard-linux-compat"])

        ipv6 = input("\nWould you like to use IPv6? (If you don't know what this is, say no) [N/y]: ")

        print("\nEnabling IP forwarding\n")
        sleep(2)"""

        run("perl -pi -e 's/#{1,}?net.ipv4.ip_forward ?= ?(0|1)/net.ipv4.ip_forward = 1/g' /etc/sysctl.conf", shell=True)
        #if 'y' in ipv6.lower():
        #    run("perl -pi -e 's/#{1,}?net.ipv6.conf.all.forwarding ?= ?(0|1)/net.ipv6.conf.all.forwarding = 1/g' /etc/sysctl.conf", shell=True)

        run(["touch", "/etc/wireguard/run-script-to-configure"])

        print("\nWireGuard был установлен")
        print("THIS SCRIPT WILL NEED TO BE RUN AGAIN TO FINISH CONFIGURING WIREGUARD")

        input("\nPress enter to reboot...")
        run("reboot")

    elif exists("/etc/wireguard/run-script-to-configure"):
        run("umask 077 /etc/wireguard/", shell=True)

        print("\nGenerating keys")
        sleep(2)

        run("wg genkey | tee /etc/wireguard/server.key | wg pubkey > /etc/wireguard/server.pub", shell=True)

        spri = str(check_output(["cat", "/etc/wireguard/server.key"]))[2:-3]

        print("\nWriting to file")
        print("This will create a 10.9.0.* subnet\n")
        sleep(2)

        with open("/etc/wireguard/wg0.conf", "w") as wg0:
            wg0.write("[Interface]\n")
            wg0.write("Address = 10.9.0.1/24, fd08:4711::1/64\n")

            port = input("Which port would you like to use? (Type nothing for the default, 51820) ")
            if port == '':
                port = "51820"
            wg0.write("ListenPort = " + port + "\n")

            print("\nWhich DNS Server would you like to use? (Default: Cloudflare, 1.1.1.1) ")
            print("If the device you are using currently is the DNS Server (like if you are using Pi-Hole or Unbound), use it's 'External' IP address, (i.e., 192.168.*.*)")
            dns = input("See https://docs.pi-hole.net/guides/upstream-dns-providers/ for a good list: ")
            if dns == '':
                dns = '1.1.1.1'
            wg0.write("DNS = " + dns + "\n")

            wg0.write("PrivateKey = " + spri + "\n")

            interface = input("\nWhich interface are you using to connect to the internet? (eth0 for ethernet (default), wlan0 for Wi-Fi, etc.) ")
            if interface == '':
                interface = "eth0"

            wg0.write("\nPostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o " + interface + " -j MASQUERADE\n")
            wg0.write("PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o " + interface + " -j MASQUERADE\n")

        run(["systemctl", "enable", "wg-quick@wg0"])
        run(["chown", "-R", "root:root", "/etc/wireguard"])
        run(["chmod", "-R", "og-rwx", "/etc/wireguard"])
        run(["wg-quick", "up", "wg0"])

        run(["rm", "/etc/wireguard/run-script-to-configure"])
        run(["mkdir", "/etc/wireguard/clients"])
        run(["touch", "/etc/wireguard/run-script-to-add-more-clients"])

        print("\nКонфигурация сервера завершена")

        input("\nPress enter to reboot...")
        run("reboot")
    else:
        print("запусти скрипт sudo python3 gen_clients.py")

except KeyboardInterrupt or EOFError:
    print('')
    exit()