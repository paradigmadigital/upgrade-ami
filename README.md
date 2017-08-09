# Upgrade AMIs

Python playbook to upgrade all the AMIs matching the next tag:

* `Upgrade`: 'YES'

Te reason of using python instead of a regular ansible playbook is that at the time of writing this, there's a bug that makes imposible the normal use of `include_role` with loops. More information [here](https://github.com/ansible/ansible/issues/21285). To learn how to program a playbook in Python, read the source code and read [this article](https://serversforhackers.com/running-ansible-2-programmatically) and the Ansible's page dedicated to the [Python API](http://docs.ansible.com/ansible/dev_guide/developing_api.html#python-api-2-0).

# Requirements

First of all, you may want to install the playbook's dependencies. You can do this executing the next line on the terminal:

```bash
ansible-galaxy -p roles/ -r requirements.yml install
```

Then you may install the PyYaml library, pretty useful:

```bash
sudo pip2 install PyYaml
```

This is all. But this playbook asumes that the AMI's name are following this convention:

```text
<ENVIROMENT>-<LOGIC_COMPONENT>-<RESOURCE_TYPE>-<COMPONENT>-<LOGIC_COMPONENT_VERSION>-<DATE>
```

An example would be:

```text
PRE-PORTAL-INS-2.2-20170202T100528
```

Anyway, it's important to add a date and that date _must_ be the last part of the name, since it's the part that this playbook will edit.

## Playbook Variables

They're all passed as parameters:

```bash
usage: upgrade-ami.py [-h] [-u user] [-r region] [-z zone] [-s security_group]
                      [-v vpc_subnet] [-k keypair] [-e keyfile] [-d keyfile]
                      [-p ssh_pass] [-i verbosity]

Upgrade mis

optional arguments:
  -h, --help            show this help message and exit
  -u user, --user user
  -r region, --region region
  -z zone, --zone zone
  -s security_group, --security-group security_group
  -v vpc_subnet, --vpc-subnet vpc_subnet
  -k keypair, --keypair keypair
  -e keyfile, --keyfile keyfile
  -d keyfile, --sudo-pass keyfile
  -p ssh_pass, --ssh-pass ssh_pass
  -i verbosity, --verbosity verbosity
```

## Execute playbook

```bash
python2 upgrade-ami.py
```

## License

GPLv3

## Author

alexperez@paradigmadigital.com
