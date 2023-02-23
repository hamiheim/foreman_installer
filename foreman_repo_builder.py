#!/usr/bin/env python3

import os
import argparse
import platform
import subprocess
from sys import exit


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


arg = argparse.ArgumentParser(description="Foreman installer script",
                              formatter_class=argparse.ArgumentDefaultsHelpFormatter)

arg.add_argument("-c", "--online", action="store_true",
                 help="Setup repos on connected host")
arg.add_argument("-d", "--offline", action="store_true",
                 help="Setup repos on offline host")
arg.add_argument("-f", "--foreman", action="store",
                 help="Foreman version", default="")
arg.add_argument("-k", "--katello", action="store",
                 help="Katello version", default="")
flg = arg.parse_args()

con = flg.online
dcon = flg.offline
kver = flg.katello
fver = flg.foreman


def clear_screen():
    os.system('clear')


repodir = str("foreman-repos")
cwd = os.getcwd()


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


def install_repo(repo_name):
    subprocess.run(["sudo", "dnf", "install", "-y", repo_name])


def enable_repo(repo_name):
    subprocess.run(["sudo", "dnf", "repolist", "--enablerepo", repo_name])


def enable_module(module_name):
    subprocess.run(["sudo", "dnf", "module", "enable", "-y", module_name])


def switch_module(module_name):
    subprocess.run(["sudo", "dnf", "module", "switch-to", "-y", module_name])


def install_package(package_name):
    subprocess.run(["sudo", "dnf", "install", "-y", package_name])


def sync_repos(repo_name):
    subprocess.run(["reposync", "--delete", "--download-metadata", "-p",
                    repodir, "-n", "--repo", repo_name])


def create_repo():
    os.system("for dir in " + repodir + "; do echo processing $dir;" +
              "cd $dir; createrepo .; cd " + cwd + "; done")
# Unable to get subprocess to work properly
#   subprocess.run(["for", "dir", "in", repodir, ";",
#                   "do", "echo", "Processing $dir", ";", "cd", "$dir", ";",
#                   "createrepo", ".", ";", "done"])


def package_repos():
    os.system("cd " + repodir +
              "; pulpkey=$(grep -m 1 'GPG-RPM-KEY-pulpcore'" +
              " /etc/yum.repos.d/katello.repo|awk -F '=' '{print $2}')" +
              "; wget $pulpkey")
    os.system("sudo cp /etc/pki/rpm-gpg/* " + repodir + "/")
    os.system("tar cf " + repodir + ".tar " + repodir)
# Unable to get subprocess to work properly
#    subprocess.run(["tar", "cf", repodir, ".tar", repodir])


def unpackage_repos():
    os.system("sudo mv foreman-repos.tar /var/lib/")
    os.system("cd /var/lib; sudo tar --skip-old-files -xf foreman-repos.tar")
# Unable to get subprocess to work properly
#    subprocess.run(["cd", "/var/lib/", ";", "tar", "vxf", repodir,
#                    ".tar", "cd"])


def check_repos():
    subprocess.run(["dnf", "repolist"])


# Script init banner
banner = "# Foreman Repo Setup Script #"
print('')
print(f"{tcolor.gen}-" * len(banner))
print(f"{tcolor.gen}{banner}")
print(f"{tcolor.gen}-{tcolor.dflt}" * len(banner))
print('')

# Check platform ID to ensure it's EL8
platform_id()

# Ensure only one host type is selected
if con and dcon:
    print(f"{tcolor.flb}You cannot select both connected and" +
          " disconnected system types!")
    print(f"{tcolor.msg}See foreman_repo_builder.py -h for help")
    print(f"{tcolor.fl}Exiting!{tcolor.dflt}")
    exit()

# Define Foreman and Katello versions
if len(fver) == 0:
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

if len(kver) == 0:
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
if con:
    print(f"{tcolor.msg}Configuring online repositories...{tcolor.dflt}")
    print('')
    install_repo("https://yum.theforeman.org/releases/" +
                 str(fver) + "/el8/x86_64/foreman-release.rpm")
    install_repo("https://yum.theforeman.org/katello/" + str(kver) +
                 "/katello/el8/x86_64/katello-repos-latest.rpm")
    install_repo("https://yum.puppet.com/puppet7-release-el-8.noarch.rpm")
    enable_repo("appstream")
    enable_repo("baseos")
    print(f"{tcolor.ok}Repositories configured!{tcolor.dflt}")
    # Disable conflicting modules, and enable required modules
    # Errors may be encountered if modules are already enabled/disabled
    # These can be safely ignored. I will work on error handling later
    print(f"{tcolor.msg}Configuring DNF Modules...{tcolor.dflt}")
    switch_module("postgresql:12")
    switch_module("ruby:2.7")
    enable_module("katello:el8")
    enable_module("pulpcore:el8")
    print(f"{tcolor.ok}DNF Modules configured!{tcolor.dflt}")
    print('')
elif dcon:
    print(f"{tcolor.msg}Configuring offline repositories...{tcolor.dflt}")
    print('')
    unpackage_repos()
    os.system("pip3 install --user -r /var/lib/" + repodir +
              "/requirements.txt --no-index --find-links /var/lib/"
              + repodir + "/")
    os.system("sudo find /etc/yum.repos.d/ -type f" +
              " -name '*.repo' -exec mv {} {}.old \;")
    file = open("alma.repo", "a")
    file.write("[baseos]\n")
    file.write("name=AlmaLinux 8 - BaseOS\n")
    file.write("baseurl=file:///var/lib/foreman-repos/baseos\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/RPM-GPG-KEY-AlmaLinux\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=1\n")
    file.write("\n[appstream]\n")
    file.write("name=AlmaLinux 8 - AppStream\n")
    file.write("baseurl=file:///var/lib/foreman-repos/appstream\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/RPM-GPG-KEY-AlmaLinux\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=1")
    file.close()
    file = open("foreman.repo", "a")
    file.write("[foreman]\n")
    file.write("name=Foreman " + fver + "\n")
    file.write("baseurl=file:///var/lib/foreman-repos/foreman\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=1\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/RPM-GPG-KEY-foreman")
    file.close()
    file = open("foreman-plugins.repo", "a")
    file.write("[foreman-plugins]\n")
    file.write("name=Foreman plugins " + fver + "\n")
    file.write("baseurl=file:///var/lib/foreman-repos/foreman-plugins\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=0\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/RPM-GPG-KEY-foreman")
    file.close()
    file = open("katello.repo", "a")
    file.write("[katello]\n")
    file.write("name=Katello " + kver + "\n")
    file.write("baseurl=file:///var/lib/foreman-repos/katello\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=1\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/RPM-GPG-KEY-foreman\n")
    file.write("\n[katello-candlepin]\n")
    file.write("name=Candlepin: an open source entitlement" +
               " management system\n")
    file.write("baseurl=file:///var/lib/foreman-repos/katello-candlepin\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/RPM-GPG-KEY-foreman\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=1\n")
    file.write("\n[pulpcore]\n")
    file.write("name=pulpcore: Fetch, Upload, Organize, and Dist SW Packs\n")
    file.write("baseurl=file:///var/lib/foreman-repos/pulpcore\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/GPG-RPM-KEY-pulpcore\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=1")
    file.close()
    file = open("puppet.repo", "a")
    file.write("[puppet7]\n")
    file.write("name=Puppet 7 Repository el 8 x86_64\n")
    file.write("baseurl=file:///var/lib/foreman-repos/puppet7\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/" +
               "RPM-GPG-KEY-puppet7-release\n")
    file.write("gpgkey=file:///var/lib/foreman-repos/" +
               "RPM-GPG-KEY-2025-04-06-puppet7-release\n")
    file.write("enabled=1\n")
    file.write("gpgcheck=1")
    file.close()
    os.system("sudo mv *.repo /etc/yum.repos.d/")
    os.system("sudo restorecon /etc/yum.repos.d/*;" +
              " sudo chown root: /etc/yum.repos.d/*")
else:
    print('')
    print(f"{tcolor.flb}System type not defined!")
    print(f"{tcolor.wrn}You must define connected or disconnected")
    print(f"{tcolor.msg}Use -h or --help for assistance")
    print(f"{tcolor.fl}Exiting!{tcolor.dflt}")
    exit()

# Sync repos
if con:
    print(f"{tcolor.msg}Syncing repos...{tcolor.dflt}")
    install_package("yum-utils")
    install_package("createrepo")
    sync_repos("appstream")
    sync_repos("baseos")
    sync_repos("foreman-plugins")
    sync_repos("foreman")
    sync_repos("katello")
    sync_repos("katello-candlepin")
    sync_repos("pulpcore")
    sync_repos("puppet7")
    create_repo()
    print('')
    print(f"{tcolor.msg}Syncing dnspython packages...{tcolor.dflt}")
    file = open(repodir + "/requirements.txt", "w")
    file.write("dnspython==1.15.0")
    file.close()
    os.system("pip3 download -r " + repodir + "/requirements.txt -d" + repodir)
    print(f"{tcolor.ok}Repo sync complete!{tcolor.dflt}")
    print('')
    print(f"{tcolor.msg}Packaging offline repos...{tcolor.dflt}")
    package_repos()
    print(f"{tcolor.ok}Repos packaged!{tcolor.dflt}")
    print(f"{tcolor.msg}Tarball located at {repodir}.tar")
    print(f"{tcolor.pmt}Bring tarball and this script over to the" +
          "diconnected host and run foreman_repo_builder.py -d to install" +
          f" or update foreman{tcolor.dflt}")
elif dcon:
    print('')
    print(f"{tcolor.msg}Checking repos...{tcolor.dflt}")
    check_repos()
    print(f"{tcolor.ok}Repos check complete!{tcolor.dflt}")
    print(f"{tcolor.msg}Repos are setup, run the foreman_installer.py script" +
          f" to complete setup{tcolor.dflt}")

print(f"{tcolor.okb}Offline repo setup complete{tcolor.dflt}")
