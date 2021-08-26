# Ansible Role for Nebula

Quickly and easily deploy the [Nebula Overlay VPN](https://github.com/slackhq/nebula) software onto all of your hosts. Just add your servers to the `inventory` file and then edit `nebula_vars.yml`.

This playbook is meant to get you up and running with Nebula quickly with sane defaults.

# What Is Nebula

> Nebula is a scalable overlay networking tool with a focus on performance, simplicity and security. It lets you seamlessly connect computers anywhere in the world.

You can read more about Nebula [on the official repo](https://github.com/slackhq/nebula)

# Example Playbook
```
---
- name: Deploy Nebula
  hosts: all
  gather_facts: yes
  user: ansible
  become: yes
  vars:
    nebula_version: 1.4.0
    nebula_network_name: "Company Nebula Mgmt Net"
    nebula_network_cidr: 16

    nebula_lighthouse_hostname: lighthouse
    nebula_lighthouse_internal_ip_addr: 10.43.0.1
    nebula_lighthouse_public_hostname: lighthouse.company.com
    nebula_lighthouse_public_port: 4242

    nebula_default_inbound_rules:
      - { port: 22, proto: "tcp", host: "any" }
      - { port: "any", proto: "icmp", host: "any" }
    nebula_default_outbound_rules:
      - { port: 22, proto: "tcp", host: "any" }
      - { port: "any", proto: "icmp", host: "any" }
      - { port: 4505, proto: "tcp", host: "10.43.0.1/32" }
      - { port: 4506, proto: "tcp", host: "10.43.0.1/32" }
  roles:
    - role: nebula
```

# Example Inventory
```
[nebula_lighthouse]
lighthouse01.company.com

[servers]
web01.company.com nebula_internal_ip_addr=10.43.0.2
docker01.company.com nebula_internal_ip_addr=10.43.0.3
zabbix01.company.com nebula_internal_ip_addr=10.43.0.4
backup01.company.com nebula_internal_ip_addr=10.43.0.5
pbx01.company.com nebula_internal_ip_addr=10.43.0.6
```

# Running the Playbook
```
ansible-playbook -i inventory nebula.yml
```
