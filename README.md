# Foreman Installation automation scripts

Contains scripts to automated setup of foreman repos for disconnected systems
as well as automate installation of foreman for both connected and disconnected systems.

## Manifest

| File | Required |
|-|-|
| foreman_repo_setup.py | no |
| foreman_installer.py | yes |

## Overview

Foreman (https://docs.theforeman.org) is an infrastructure management service
to help automate installation and maintenance of Linux platforms.

The automation in this repo will provide the ability to completely deploy foreman
in both connected and disconnected environments by simply running these scripts.

Future plans will consolidate into a single script that will call the repo setup as a 
python module for setup of repos.

The instructions and scripts will not go into detail regarding Foreman versions and
resource requirements. See the documentation in the above link for that info.

## Instructions

### Connected systems

1. Deploy a host (physical or virtual) that has the minimum resources required for your deployment size.

2. Push the `foreman_installer.py` script to the host and verify that it has both internet connectivity and can resolve both forward and reverse DNS records for the host. 
If a DNS server is not available on the network, setup the `/etc/hosts` file with the proper entry for local DNS resolution.

> The script will not check that the `/etc/hosts` file is setup properly if DNS the DNS resolution check fails
but will simply trust the admin has done so.

3. Enable execution of the script by changing the mode (`chmod 750` or `chmod +x`)

4. Run the script to complete installation

> The script has logic to use arguments to make the installation mostly unattended aside from sudo prompts. Available arguments and default values can be seen using `foreman_installer.py -h`

5. After successful script execution, ensure that you can login to Foreman via https://<host fqdn>

### Disconnected systems

1. Deploy a host that has connectivity to the internet; this can be a permanent or temporary host.

2. Push the `foreman_repo_setup.py` script to the host on a partition that has at least 20GiB free for storing the repo content.

3. Enable execution of the script by changing the mode (`chmod 750` or `chmod +x`)

4. Run the script, passing the `-c` flag for a connect host.

> The script has logic to use arguments to make the installation mostly unattended aside from sudo prompts. Available arguments and default values can be seen using `foreman_installer.py -h`

5. After successful script execution, pull the `foreman-repos.tar` tarball of the connected host, and push both the `foreman_repo_setup.py` script and `foreman-repo.tar` files to the target disconnected host.

6. Enable execution of the script by changing the mode (`chmod 750` or `chmod +x`)

7. Run the script, passing the -d flag for a disconnected host.

8. After successful script execution, ensure that you can login to Foreman via https://<host fqdn>
