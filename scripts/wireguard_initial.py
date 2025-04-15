#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import check_output, run
from time import sleep
from os.path import exists


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

    if not exists("/etc/wireguard"):

        print("\nОбновление системы\n")
        sleep(2)
        run(["apt", "update"])
        #run(["apt", "upgrade"])

        print("\nУстановка зависимостей\n")
        sleep(2)
        app_list = ["curl", "libelf-dev", "pkg-config", "build-essential", "git", "dirmngr", "wireguard", "openresolv", "resolvconf"]
        for app in app_list:
            print(f"   -----  {app} -----")
            run(f"apt install {app}", shell=True)

        run("perl -pi -e 's/#{1,}?net.ipv4.ip_forward ?= ?(0|1)/net.ipv4.ip_forward = 1/g' /etc/sysctl.conf", shell=True)
        #if 'y' in ipv6.lower():
        #    run("perl -pi -e 's/#{1,}?net.ipv6.conf.all.forwarding ?= ?(0|1)/net.ipv6.conf.all.forwarding = 1/g' /etc/sysctl.conf", shell=True)

        print("\nWireGuard был установлен")

        run("umask 077 /etc/wireguard/", shell=True)

        print("\nGenerating keys")
        sleep(2)

        run("wg genkey | tee /etc/wireguard/server.key | wg pubkey > /etc/wireguard/server.pub", shell=True)

        spri = str(check_output(["cat", "/etc/wireguard/server.key"]))[2:-3]

        print("\nWriting to file")
        print("This will create a 10.9.0.* subnet\n")

        with open("/etc/wireguard/wg0.conf", "w") as wg0:
            wg0.write("[Interface]\n")
            wg0.write("Address = 10.9.0.1/24"+ "\n")

            port = "51820"
            wg0.write("ListenPort = " + port + "\n")

            dns = ""
            if dns == '':
                dns = '1.1.1.1'
            wg0.write("DNS = " + dns + "\n")

            wg0.write("PrivateKey = " + spri + "\n")


            interface = "eth0"

            wg0.write("\nPostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o " + interface + " -j MASQUERADE")
            wg0.write("\nPostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o " + interface + " -j MASQUERADE")

        run(["systemctl", "enable", "wg-quick@wg0"])
        run(["chown", "-R", "root:root", "/etc/wireguard"])
        run(["chmod", "-R", "og-rwx", "/etc/wireguard"])
        run(["wg-quick", "up", "wg0"])

        #run(["rm", "/etc/wireguard/run-script-to-configure"])
        run(["mkdir", "/etc/wireguard/clients"])
        #run(["touch", "/etc/wireguard/run-script-to-add-more-clients"])

        print("\nКонфигурация сервера завершена")

        input("\nPress enter to reboot...")
        run("reboot")
    else:
        print("запусти скрипт sudo python3 gen_clients.py")

except KeyboardInterrupt or EOFError:
    print('')
    exit()