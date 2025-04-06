#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import check_output, run
from time import sleep
from os.path import exists
from os import listdir, linesep, path
import sqlite3
import qrcode

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

def main(number_clients, cfg_folder):
    try:
        clc_clients = len(listdir(path.join(cfg_folder, "clients"))) +1
        spub = str(check_output(["cat", path.join(cfg_folder,"server.pub")]))[2:-3]
        for numb in range(clc_clients, clc_clients + number_clients +1):
            print(f"Клиент № {numb-clc_clients+1} из {number_clients}")
            client_name = f"client_{numb}"
            client_folder = path.join(cfg_folder, "clients", client_name)
            run(["mkdir", client_folder])#"f"/etc/wireguard/clients/{numb}"])
            subnet = str(len(listdir(client_folder)) + 1)
            print("\n    Генерация ключей")
            sleep(2)
            run(f"wg genkey | tee {client_folder}/{client_name}.key | wg pubkey > {client_folder}/{client_name}.pub", shell=True)
            ppri = str(check_output(["cat", f"{client_folder}/{client_name}.key"]))[2:-3]
            ppub = str(check_output(["cat", f"{client_folder}/{client_name}.pub"]))[2:-3]

            print("\nWriting to file")
            sleep(2)

            with open(path.join(cfg_folder,"wg0.conf"), "a+") as wg0, open(path.join(client_folder,f"{client_name}.conf"), "w") as peer:
                wg0.write("\n[Peer]\n")
                wg0.write("PublicKey = " + ppub + "\n")
                wg0.write("AllowedIPs = 10.9.0." + subnet + "/32\n")
                wg0.seek(0)
                for i, line in enumerate(wg0):
                    if i == 2:
                        port = line[13:]
                    elif i == 3:
                        dns = line[6:]
                    elif i > 3:
                        break

                peer.write("[Interface]\n")
                peer.write("Address = 10.9.0." + subnet + "/32, fd08:4711::" + subnet + "/128\n")
                peer.write("DNS = " + dns + "\n")
                peer.write("PrivateKey = " + ppri + "\n")
                peer.write("\n[Peer]\n")
                peer.write("PublicKey = " + spub + "\n")

                ip = str(check_output(["curl", "https://checkip.amazonaws.com/"]))[2:-3]
                #ipuse = input("What would you like to use to connect to this VPN (e.g. Public IP, DDNS) (Default: " + ip + ") ")
                #if ipuse == '':
                ipuse = ip
                peer.write("Endpoint = " + ipuse + ":" + port + "\n")
                peer.write("AllowedIPs = 0.0.0.0/0, ::/0\n")
                peer.write("PersistentkeepAlive = 20")

                run("wg genpsk > /etc/wireguard/clients/" + name + "/" + name + ".psk", shell=True)
                psk = str(check_output(["cat", "/etc/wireguard/clients/" + name + "/" + name + ".psk"]))[2:-3]
                wg0.write("PresharedKey = " + psk + "\n")
                peer.write("PresharedKey = " + psk + "\n")

            print("Peer has been configured.")
            print("To see how to install the VPN on devices, please see the guide at https://www.wireguard.com/install")
            useqr = input("Would you like to generate a QR code to scan? [Y/n]: ")
            if not 'n' in useqr.lower():
                with open("/etc/wireguard/clients/" + name + "/" + name + ".conf") as peer:
                    lines = peer.read().splitlines()
                    qr = qrcode.QRCode()
                    qr.add_data(linesep.join(lines))
                    qr.print_ascii()

        input("Press enter to reboot...")
        run("reboot")
    except KeyboardInterrupt or EOFError:
        print('')
        exit()

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("-n", "--client_numbers",
                        dest="n", default=300, type=int,
                        help="количество клиентов для генерации")
    parser.add_argument("-cf", "--config_folder",
                        dest="cf", default="/etc/wireguard",
                        help="папка с конфигурациями. отсылка к файлу wg0.conf Клиентские конфиги в папке /clients/*")

    args = parser.parse_args()
    main(args.n, args.cf)
    print(args)