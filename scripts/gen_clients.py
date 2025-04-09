#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import check_output, run
from time import sleep
from os import listdir, linesep, path
from utils import get_file_source, mess_window



def main(number_clients, cfg_folder):
    try:
        clc_clients = len(listdir(path.join(cfg_folder, "clients")))
        serv_pub_1 = get_file_source(path.join(cfg_folder,"server.pub"))
        serv_pub = str(check_output(["cat", path.join(cfg_folder,"server.pub")]))[2:-3]
        print(serv_pub_1 == serv_pub)
        ip = str(check_output(["curl", "https://checkip.amazonaws.com/"]))[2:-3]
        for numb in range(clc_clients, clc_clients + number_clients):
            print(f"Клиент № {numb-clc_clients+1} из {number_clients}")
            client_name = f"client_{numb}"
            client_folder = path.join(cfg_folder, "clients", client_name)
            run(["mkdir", client_folder])
            subnet = str(len(listdir(client_folder)) + 1)
            print("\n    Генерация ключей")
            run(f"wg genkey | tee {client_folder}/{client_name}.key | wg pubkey > {client_folder}/{client_name}.pub", shell=True)
            ppri = str(check_output(["cat", f"{client_folder}/{client_name}.key"]))[2:-3]
            ppub = str(check_output(["cat", f"{client_folder}/{client_name}.pub"]))[2:-3]

            print("\n")

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


                ipuse = ip
                peer.write("Endpoint = " + ipuse + ":" + port + "\n")
                peer.write("AllowedIPs = 0.0.0.0/0, ::/0\n")
                peer.write("PersistentkeepAlive = 20")

                run(f"wg genpsk > {client_folder}/{client_name}.psk", shell=True)
                psk = str(check_output(["cat", f"{client_folder}/{client_name}.psk"]))[2:-3]
                wg0.write("\nPresharedKey = " + psk + "\n")
                peer.write("\nPresharedKey = " + psk + "\n")

            """with open(f"{client_folder}/{client_name}.conf") as peer:
                lines = peer.read().splitlines()
                qr = qrcode.QRCode()
                qr.add_data(linesep.join(lines))
                img = qr.make_image(fill_color=(75, 0, 75), back_color=(190, 190, 255))
                img.save(f"{client_folder}/{client_name}.png")"""

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