#!/usr/bin/env python3

# Script to install Foreman server. Work is in progress for both connected
# and disconnected installation.
# Specifically targeting EL8 for repo constraints
# Currently does not log to a file, so logging must be done manually from shell

import os
from sys import exit
from multiprocessing import cpu_count
import psutil
import platform
import argparse
import socket
import subprocess
try:
    import dns.resolver
except ModuleNotFoundError:
    subprocess.run(["pip3", "install", "--user", "dnspython", "dnspython"])
    import dns.resolver
import dns.reversename

# Define arguments for script
arg = argparse.ArgumentParser(description="Foreman installer script",
                              formatter_class=argparse.ArgumentDefaultsHelpFormatter)
arg.add_argument("-a", "--noprompt", action="store_true",
                 help="Do not prompt to continue/on non-critical errors")
arg.add_argument("-d", "--disconnected", action="store_true",
                 help="Disconnected mode")
arg.add_argument("-f", "--foreman", action="store",
                 help="Foreman version", default="")
arg.add_argument("-k", "--katello", action="store",
                 help="Katello version", default="")
arg.add_argument("-l", "--loc", action="store", help="Location",
                 default="Default_Location")
arg.add_argument("-o", "--org", action="store",
                 help="Organization", default="Default_Organization")
arg.add_argument("-t", "--tune", action="store",
                 help="Tuning profile. Acceptable options include:" +
                 " development, default, medium, large," +
                 " extra-large, extra-extra-large",
                 default="default")
arg.add_argument("-u", "--username", action="store",
                 help="Admin username", default="admin")

arg.add_argument("-c", "--compute-resource", dest="compute_resource",
                 action="store", default='', help="Compute Resource type; " +
                 "Acceptable options include: " +
                 "vmware, ec2, gce, openstack, ovirt, and libvirt ")

flg = arg.parse_args()

# Define required variables
disconnected = flg.disconnected
npmt = flg.noprompt
fver = flg.foreman
kver = flg.katello
tunp = flg.tune
org = flg.org
loc = flg.loc
badmun = flg.username
cr = flg.compute_resource


# Define terminal color output variables using ANSII codes
class tcolor:
    fl = '\033[0;31m'
    flb = '\033[1;31m'
    msg = '\033[0;36m'
    pmt = '\033[1;36m'
    wrn = '\033[0;33m'
    wrnb = '\033[1;33m'
    ok = '\033[0;32m'
    okb = '\033[1;32m'
    gen = '\033[0;35m'
    dflt = '\033[0m'


if len(cr) > 0:
    if str(cr) == str("vmware"):
        crpack = "--enable-foreman-compute-vmware"
    elif str(cr) == str("ec2"):
        crpack = "--enable-foreman-compute-ec2"
    elif str(cr) == str("libvirt"):
        crpack = "--enable-foreman-compute-libvirt"
    elif str(cr) == str("gce"):
        crpack = "--enable-foreman-compute-gce"
    elif str(cr) == str("openstack"):
        crpack = "--enable-foreman-compute-openstack"
    elif str(cr) == str("ovirt"):
        crpack = "--enable-foreman-compute-ovirt"
    else:
        print(f"{tcolor.wrnb}Compute resource invalid!")
        print(f"{tcolor.msg}Use foreman-installer.py -h for valid options")
        print(f"{tcolor.wrn}Exiting!{tcolor.dflt}")

# Define hostname and IP Address
hname = socket.gethostname()
ipaddr = socket.gethostbyname(socket.gethostname())


# Define required functions
def clear_screen():
    os.system('clear')


# Subprocess functions for running commands directly on the host shell
def enable_repo(repo_name):
    subprocess.run(["sudo", "dnf", "repolist", "--enablerepo", repo_name])


def install_package(package_name):
    subprocess.run(["sudo", "dnf", "install", "-y", package_name])


def update_package():
    subprocess.run(["sudo", "dnf", "update", "-y"])


def install_module(package_name):
    subprocess.run(["sudo", "dnf", "module", "install", "-y", package_name])


def enable_module(module_name):
    subprocess.run(["sudo", "dnf", "module", "enable", "-y", module_name])


def switch_module(module_name):
    subprocess.run(["sudo", "dnf", "module", "switch-to", "-y", module_name])


def enable_fw_svc(firewall_service):
    subprocess.run(["sudo", "firewall-cmd", "--add-service", firewall_service])


def fw_reload():
    subprocess.run(["sudo", "firewall-cmd", "--runtime-to-permanent"])


def katello_install(loc, org, badmun, tunp):
    subprocess.run(["sudo", "foreman-installer", "--scenario", "katello",
                    "--tuning", tunp,
                    "--foreman-initial-location", loc,
                    "--foreman-initial-organization", org,
                    "--foreman-initial-admin-username", badmun])


def katello_install_w_compute(loc, org, badmun, tunp, crpack):
    subprocess.run(["sudo", "foreman-installer", "--scenario", "katello",
                    "--tuning", tunp,
                    "--foreman-initial-location", loc,
                    "--foreman-initial-organization", org,
                    "--foreman-initial-admin-username", badmun, crpack])


# Check platform ID
def platform_id():
    # Get host release info
    relid = platform.release()
    try:
        if relid.index("el8"):
            pass
    except ValueError:
        print(f"{tcolor.flb}EL8 platform not detected!")
        print(f"{tcolor.fl}Exiting!{tcolor.dflt}")
        exit()


def resource_check():
    global tunp

    # Define CPU core count and memory
    cpuc = int(cpu_count())
    memc = int(round(psutil.virtual_memory().total / 1024000000))

    # Validate physical resources meet default tuning spec
    if tunp == str("development") and memc < 6:
        print(f"{tcolor.flb}Host does not meet minimum resources spec" +
              f" for the development tuning profile {tcolor.wrn}" +
              "(1 core, 6 GB Memory)")
        print(f"{tcolor.fl}Exiting!{tcolor.dflt}")
        print('')
        exit()
    if cpuc < 4 and tunp != str("development") or memc < 20 and tunp != str("development"):
        print(f"{tcolor.wrnb}Host does not meet minimum resources spec" +
              f" for the default tuning profile {tcolor.wrn}" +
              "(4 core, 20 GB Memory)")
        print('')
        print(f"{tcolor.msg}For dev deployment, we'll set tuning to " +
              f"{tcolor.dflt}development")
        print('')
        if npmt:
            print(f"{tcolor.wrn}Assuming dev deployment...{tcolor.dflt}")
            if memc >= 6:
                tunp = "development"
                print('')
                print(f"{tcolor.okb}Proceeding with install!{tcolor.dflt}")
                print('')
            else:
                print('')
                print(f"{tcolor.flb}Host does not meet the minimum " +
                      "resources for the development tuning profile" +
                      f"{tcolor.fl} (1 core, 6 GB Memory)")
                print(f"{tcolor.fl}Exiting!{tcolor.dflt}")
                print('')
                exit()
            print('')
        else:
            print(f"{tcolor.pmt}Is this a development " +
                  f"deployment?{tcolor.dflt}")
            uans = str(input("(Y/n): "))
            if str.lower(uans) == str("y") or str.lower(uans) == ("yes"):
                if memc >= 6:
                    tunp = "development"
                    print('')
                    print(f"{tcolor.okb}Proceeding with install!{tcolor.dflt}")
                    print('')
                else:
                    print('')
                    print(f"{tcolor.flb}Host does not meet the minimum " +
                          "resources for the development tuning profile" +
                          f"{tcolor.fl} (1 core, 6 GB Memory)")
                    print(f"{tcolor.fl}Exiting!{tcolor.dflt}")
                    print('')
                    exit()
            elif str.lower(uans) == str("n") or str.lower(uans) == ("no"):
                print('')
                print(f"{tcolor.flb}Host does not meet resource spec!")
                print(f"{tcolor.fl}Exiting...{tcolor.dflt}")
                print('')
                exit()
            else:
                print('')
                print(f"{tcolor.fl}Invalid input. Assuming no...")
                print('')
                print(f"{tcolor.flb}Host does not meet resource spec!")
                print(f"{tcolor.fl}Exiting...{tcolor.dflt}")
                print('')
                exit()


def foreman_install():
    global log
    global loc
    global org
    global badmun
    global tunp
    global crpack
    print(f"{tcolor.okb}Proceeding with Foreman Installation!{tcolor.dflt}")
    print('')

    print(f"{tcolor.msg}Opening firewall for required services{tcolor.dflt}")
    enable_fw_svc("foreman")
    enable_fw_svc("foreman-proxy")
    fw_reload()
    print('')

    # Had to remove logic for successful installation since Foreman
    # doesn't send a clean exit code (0) after successful install.
    # Will revist once the exit code received for both successful
    # and failed installations have been identified.
    print(f"{tcolor.msg}Installing Foreman and Katello services{tcolor.dflt}")
    if cr:
        print('')
        katello_install_w_compute(loc, org, badmun, tunp, crpack)
    else:
        print('')
        katello_install(loc, org, badmun, tunp)
    print(f"{tcolor.okb}Foreman installation complete!{tcolor.dflt}")
    log = "/var/log/foreman-installer/katello.log"
    print(f"{tcolor.gen}See the following location for details:{tcolor.dflt}")
    print('')
    print("-" * len(log + str("|  |")))
    print(f"| {log} |")
    print("-" * len(log + str("|  |")))
    print('')


def connected_install():
    global kver
    global fver
    global badmun
    global loc
    global org
    # Define Foreman and Katello versions
    if len(fver) == 0 and npmt:
        print(f"{tcolor.flb}Unable to get Foreman verison interactively!")
        print(f"{tcolor.fl}Define foreman argument, or allow prompting")
        print(f"{tcolor.msg}Use -h or --help for assistance{tcolor.dflt}")
        print('')
        exit()
    elif len(fver) == 0:
        print(f"{tcolor.pmt}What version of Foreman" +
              " are you targeting?")
        print('')
        print(f"{tcolor.msg}For a list of supported" +
              f" versions, browse to:{tcolor.dflt}")
        print("https://docs.theforeman.org")
        print('')
        while True:
            try:
                fver = float(input(tcolor.pmt + "Foreman: " + tcolor.dflt))
                break
            except ValueError:
                print(f"{tcolor.fl}Invalid input!{tcolor.dflt}")

    if len(kver) == 0 and npmt:
        print(f"{tcolor.flb}Unable to get Katello verison interactively!")
        print(f"{tcolor.fl}Define Katello argument, or allow prompting")
        print(f"{tcolor.msg}Use -h or --help for assistance{tcolor.dflt}")
        print('')
        exit()
    elif len(kver) == 0:
        print(f"{tcolor.pmt}What version of Katello are you targeting?")
        print('')
        print(f"{tcolor.msg}For a list of supported" +
              f" versions, browse to:{tcolor.dflt}")
        print("https://docs.theforeman.org")
        print('')
        while True:
            try:
                kver = float(input(tcolor.pmt + "Katello: " + tcolor.dflt))
                break
            except ValueError:
                print(f"{tcolor.fl}Invalid input!{tcolor.dflt}")

    # Setup/install repositories required for installation
    print('')
    print(f"{tcolor.msg}Configuring repositories...{tcolor.dflt}")
    print('')
    install_package("https://yum.theforeman.org/releases/" +
                    str(fver) + "/el8/x86_64/foreman-release.rpm")
    install_package("https://yum.theforeman.org/katello/" + str(kver) +
                    "/katello/el8/x86_64/katello-repos-latest.rpm")
    install_package("https://yum.puppet.com/puppet7-release-el-8.noarch.rpm")
    enable_repo("appstream")
    enable_repo("baseos")
    print(f"{tcolor.ok}Repositories configured!{tcolor.dflt}")
    print('')

    # Disabled conflicting modules, and enabled required modules for installation
    # Errors may be encountered if modules are already enabled/disabled
    # These can be safely ignored. I will work on error handling later
    print(f"{tcolor.msg}Configuring DNF Modules...{tcolor.dflt}")
    switch_module("postgresql:12")
    switch_module("ruby:2.7")
    enable_module("katello:el8")
    enable_module("pulpcore:el8")
    print(f"{tcolor.ok}DNF Modules configured!{tcolor.dflt}")
    print('')

    # Install required packages
    print(f"{tcolor.msg}Installing packages...{tcolor.dflt}")
    update_package()
    install_package("foreman-installer-katello")
    print(f"{tcolor.ok}Package installation complete!{tcolor.dflt}")
    print('')

    # Part of package installation is to do a full system update
    # User should reboot host if kernel was updated
    print(f"{tcolor.msg}Run {tcolor.dflt}rpm -qa kernel --last{tcolor.msg}" +
          f" to see if a reboot is needed.{tcolor.dflt}")

    # Define paramaters for Foreman installation
    print('')
    if len(org) == 0:
        org = input(tcolor.pmt + "Organization: " + tcolor.dflt)
    if len(loc) == 0:
        loc = input(tcolor.pmt + "Location: " + tcolor.dflt)
    if len(badmun) == 0:
        badmun = input(tcolor.pmt + "Admin username: " + tcolor.dflt)
    print('')

    # Prompt user to continue with install
    print(f"{tcolor.msg}Host is ready for Foreman Installation.")
    if npmt:
        foreman_install()
    else:
        print(f"{tcolor.pmt}Would you like to proceed?{tcolor.dflt}")
        uans = str(input("(Y/n): "))
        if str.lower(uans) == str("y") or str.lower(uans) == ("yes"):
            print('')
            foreman_install()
        elif str.lower(uans) == str("n") or str.lower(uans) == ("no"):
            print('')
            print(f"{tcolor.wrn}Host is setup for Foreman installation" +
                  f" but foreman has {tcolor.fl}NOT{tcolor.wrn} been installed.")
            print('')
            if len(cr) > 0:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f"{crpack}")
                print(f'{tcolor.dflt}')
            else:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f'{tcolor.dflt}')
        else:
            print('')
            print(f"{tcolor.fl}Invalid input. Assuming no...")
            print(f"{tcolor.wrn}Host is setup for Foreman installation" +
                  f" but foreman has {tcolor.fl}NOT{tcolor.wrn} been installed.")
            print('')
            print(f"{tcolor.msg}Execute the following to complete installation:")
            if len(cr) > 0:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f"{crpack}")
                print(f'{tcolor.dflt}')
            else:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f'{tcolor.dflt}')


def disconnected_install():
    global kver
    global fver
    global badmun
    global loc
    global org

    # Install required packages
    print(f"{tcolor.msg}Installing packages...{tcolor.dflt}")
    update_package()
    switch_module("postgresql:12")
    switch_module("ruby:2.7")
    enable_module("katello:el8")
    enable_module("pulpcore:el8")
    install_package("foreman-installer-katello")
    print(f"{tcolor.ok}Package installation complete!{tcolor.dflt}")
    print('')

    # Part of package installation is to do a full system update
    # User should reboot host if kernel was updated
    print(f"{tcolor.msg}Run {tcolor.dflt}rpm -qa kernel --last{tcolor.msg}" +
          f" to see if a reboot is needed.{tcolor.dflt}")

    # Define paramaters for Foreman installation
    print('')
    if len(org) == 0:
        org = input(tcolor.pmt + "Organization: " + tcolor.dflt)
    if len(loc) == 0:
        loc = input(tcolor.pmt + "Location: " + tcolor.dflt)
    if len(badmun) == 0:
        badmun = input(tcolor.pmt + "Admin username: " + tcolor.dflt)
    print('')

    # Prompt user to continue with install
    print(f"{tcolor.msg}Host is ready for Foreman Installation.")
    if npmt:
        foreman_install()
    else:
        print(f"{tcolor.pmt}Would you like to proceed?{tcolor.dflt}")
        uans = str(input("(Y/n): "))
        if str.lower(uans) == str("y") or str.lower(uans) == ("yes"):
            print('')
            foreman_install()
        elif str.lower(uans) == str("n") or str.lower(uans) == ("no"):
            print('')
            print(f"{tcolor.wrn}Host is setup for Foreman installation" +
                  f" but foreman has {tcolor.fl}NOT{tcolor.wrn} been installed.")
            print('')
            if len(cr) > 0:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f"{crpack}")
                print(f'{tcolor.dflt}')
            else:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f'{tcolor.dflt}')
        else:
            print('')
            print(f"{tcolor.fl}Invalid input. Assuming no...")
            print(f"{tcolor.wrn}Host is setup for Foreman installation" +
                  f" but foreman has {tcolor.fl}NOT{tcolor.wrn} been installed.")
            print('')
            print(f"{tcolor.msg}Execute the following to complete installation:")
            if len(cr) > 0:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f"{crpack}")
                print(f'{tcolor.dflt}')
            else:
                print(f"{tcolor.msg}Execute the following to " +
                      "complete installation:")
                print(f"{tcolor.dflt}firewall-cmd " +
                      "--add-service={foreman,foreman-proxy}")
                print("firewall-cmd --runtime-to-permanent")
                print("foreman-installer --scenario katello \\")
                print(f" --foreman-initial-location={org} \\")
                print(f" --foreman-initial-organization={loc} \\")
                print(f" --foreman-initial-admin-username={badmun}")
                print(f'{tcolor.dflt}')


clear_screen()

# def environment_check():
# Script init banner
banner = "# Foreman Installation Script #"
print('')
print(f"{tcolor.gen}-" * len(banner))
print(f"{tcolor.gen}{banner}")
print(f"{tcolor.gen}-{tcolor.dflt}" * len(banner))
print('')

# Check platform ID to ensure it's EL8
platform_id()

# Check host resources
resource_check()

# Check if session is "screen"ed or "tmux"ed
# If not, prompt user to continue at own risk
ptyv = os.environ['TERM']
if str(ptyv) != str("screen"):
    print(f"{tcolor.wrnb}Session does not appear to be running in" +
          " asynchronous method (i.e screen or tmux)")
    print(f"{tcolor.msg}Foreman installation can be time consuming")
    print("It may not finish before remote session reaches idle timeout.")
    print('')
    if npmt:
        print(f"{tcolor.wrn}Proceeding without screen/tmux{tcolor.dflt}")
        print('')
    else:
        print(f"{tcolor.pmt}Do you wish to proceed?{tcolor.dflt}")
        uans = str(input("(Y/n): "))
        if str.lower(uans) == str("y") or str.lower(uans) == ("yes"):
            print('')
            print(f"{tcolor.wrn}Proceeding without screen/tmux{tcolor.dflt}")
        elif str.lower(uans) == str("n") or str.lower(uans) == ("no"):
            print('')
            print(f"{tcolor.flb}Exiting...{tcolor.dflt}")
            exit()
        else:
            print('')
            print(f"{tcolor.fl}Invalid input. Assuming no...")
            print(f"{tcolor.flb}Exiting...{tcolor.dflt}")
            exit()

# Validate DNS records for host (required for install)
try:
    dns.resolver.query(hname, 'A')
except dns.resolver.NXDOMAIN:
    print('')
    print(f"{tcolor.flb}DNS lookup failed!{tcolor.dflt}")
    print(f"{tcolor.msg}Ensure hosts file has" +
          f" the following entry or install will fail:{tcolor.dflt}")
    print('')
    print("-" * len(hname + str('    ') + str('|  |') + ipaddr))
    print(f"| {ipaddr}    {hname} |")
    print("-" * len(ipaddr + str('    ') + str('|  |') + hname))
    print('')
    if npmt:
        print(f"{tcolor.wrn}Proceeding with install!{tcolor.dflt}")
    else:
        print(f"{tcolor.pmt}Do you wish to continue{tcolor.dflt}")
        uans = str(input("(Y/n): "))
        if str.lower(uans) == str("y") or str.lower(uans) == ("yes"):
            print('')
            print(f"{tcolor.wrn}Proceeding with install!{tcolor.dflt}")
            print('')
        elif str.lower(uans) == str("n") or str.lower(uans) == ("no"):
            print('')
            print(f"{tcolor.wrn}Submit A record in DNS" +
                  " server or configure hosts file with above entry")
            print('')
            print(f"{tcolor.fl}Exiting...{tcolor.dflt}")
            print('')
            exit()
        else:
            print('')
            print(f"{tcolor.fl}Invalid input. Assuming no...")
            print(f"{tcolor.wrn}Submit A record in DNS" +
                  " server or configure hosts file with above entry")
            print('')
            print(f"{tcolor.fl}Exiting...{tcolor.dflt}")
            print('')
            exit()
try:
    dns.resolver.query(dns.reversename.from_address(ipaddr), 'PTR')
except dns.resolver.NXDOMAIN:
    print('')
    print(f"{tcolor.flb}Reverse DNS lookup failed!{tcolor.dflt}")
    print(f"{tcolor.msg}Ensure hosts file has" +
          f" the following entry or install will fail:{tcolor.dflt}")
    print('')
    print("-" * len(hname + str('    ') + str('|  |') + ipaddr))
    print(f"| {ipaddr}    {hname} |")
    print("-" * len(ipaddr + str('    ') + str('|  |') + hname))
    print('')
    if npmt:
        print(f"{tcolor.wrn}Proceeding with install!{tcolor.dflt}")
    else:
        print(f"{tcolor.pmt}Do you wish to continue{tcolor.dflt}")
        uans = str(input("(Y/n): "))
        if str.lower(uans) == str("y") or str.lower(uans) == ("yes"):
            print('')
            print(f"{tcolor.wrn}Proceeding with install!{tcolor.dflt}")
            print('')
        elif str.lower(uans) == str("n") or str.lower(uans) == ("no"):
            print('')
            print(f"{tcolor.wrn}Submit PTR record in DNS" +
                  " server or configure hosts file with above entry")
            print('')
            print(f"{tcolor.fl}Exiting...{tcolor.dflt}")
            print('')
            exit()
        else:
            print('')
            print(f"{tcolor.fl}Invalid input. Assuming no...")
            print(f"{tcolor.wrn}Submit PTR record in DNS" +
                  " server or configure hosts file with above entry")
            print('')
            print(f"{tcolor.fl}Exiting...{tcolor.dflt}")
            print('')
            exit()

if disconnected:
    print(f"{tcolor.msg}Starting disconnected install of Foreman...{tcolor.dflt}")
    disconnected_install()
else:
    print(f"{tcolor.msg}Starting connected install of Foreman...{tcolor.dflt}")
    connected_install()

# Future plans
# - Add ability to specify additional plugins to enable
# - Option for setup disconnected installation media only
# - Disconnected installation
