#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import check_output, run
from time import sleep
from os.path import exists
from os import listdir, linesep
try:

    if not "root" in str(check_output("whoami")):
        print("This script needs to be run as root to work, please prefix with 'sudo'.")
        exit()

    try:
        from qrcode import QRCode
    except ModuleNotFoundError:
        print("Installing required qrcode module")
        sleep(2)
        run(["apt", "install", "python3-qrcode"])

    if exists("/etc/wireguard") and not exists("/etc/wireguard/run-script-to-add-more-clients") and not exists("/etc/wireguard/run-script-to-configure"):
        print("It seems that WireGuard has already been installed")
        print("This will delete your existing configuration and your clients will not work anymore")
        print("It is being assumed that WireGuard was working before")
        print("If this is not the case, please press ^C and run 'sudo rm -rf /etc/wireguard'")
        input("Press enter to continue...")
        run(["rm", "-r", "/etc/wireguard/"])
        run(["mkdir", "/etc/wireguard/"])
        run(["touch", "/etc/wireguard/run-script-to-configure"])

    if not exists("/etc/wireguard"):

        print("\nUpdating\n")
        sleep(2)
        run(["apt", "update"])
        run(["apt", "upgrade"])

        print("\nInstalling dependencies\n")
        sleep(2)
        run(["apt", "install", "raspberrypi-kernel-headers", "libelf-dev", "pkg-config", "build-essential", "git", "dirmngr"])

        print("\nDownloading WireGuard and WireGuard tools\n")
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
        sleep(2)

        run("perl -pi -e 's/#{1,}?net.ipv4.ip_forward ?= ?(0|1)/net.ipv4.ip_forward = 1/g' /etc/sysctl.conf", shell=True)
        if 'y' in ipv6.lower():
            run("perl -pi -e 's/#{1,}?net.ipv6.conf.all.forwarding ?= ?(0|1)/net.ipv6.conf.all.forwarding = 1/g' /etc/sysctl.conf", shell=True)

        run(["touch", "/etc/wireguard/run-script-to-configure"])

        print("\nWireGuard has been installed")
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

        print("\nServer configuration complete.  Run the script again to add clients")
        print("Please forward port " + port + " on your router.")
        print("For instructions, visit https://portforward.com/router.htm")

        input("\nPress enter to reboot...")
        run("reboot")
    else:
        name = input("What should this client be named? ")
        run(["mkdir", "/etc/wireguard/clients/" + name])
        subnet = str(len(listdir("/etc/wireguard/clients")) + 1)
        print("\nGenerating keys")
        sleep(2)
        run("wg genkey | tee /etc/wireguard/clients/" + name + "/" + name + ".key | wg pubkey > /etc/wireguard/clients/" + name + "/" + name + ".pub", shell=True)
        ppri = str(check_output(["cat", "/etc/wireguard/clients/" + name + "/" + name + ".key"]))[2:-3]
        ppub = str(check_output(["cat", "/etc/wireguard/clients/" + name + "/" + name + ".pub"]))[2:-3]
        spub = str(check_output(["cat", "/etc/wireguard/server.pub"]))[2:-3]

        print("\nWriting to file")
        sleep(2)

        with open("/etc/wireguard/wg0.conf", "a+") as wg0, open("/etc/wireguard/clients/" + name + "/" + name + ".conf", "w") as peer:
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
            ipuse = input("What would you like to use to connect to this VPN (e.g. Public IP, DDNS) (Default: " + ip + ") ")
            if ipuse == '':
                ipuse = ip
            peer.write("Endpoint = " + ipuse + ":" + port + "\n")
            peer.write("AllowedIPs = 0.0.0.0/0, ::/0\n")
            pka = input("Will this device be behind a NAT? [N/y]: ")
            if 'y' in pka:
                peer.write("PersistentkeepAlive = 60")
            psk = input("Would you like to use a pre-shared key? (Recommended) [Y/n]: ")
            if not 'n' in psk:
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
                qr = QRCode()
                qr.add_data(linesep.join(lines))
                qr.print_ascii()

        input("Press enter to reboot...")
        run("reboot")

except KeyboardInterrupt or EOFError:
    print('')
    exit()