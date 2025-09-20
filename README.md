# Ansible Role for Nebula

Quickly and easily deploy the [Nebula Overlay VPN](https://github.com/slackhq/nebula) software onto all of your hosts.

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
    nebula_version: 1.8.0
    nebula_network_name: "Company Nebula Mgmt Net"
    nebula_network_cidr: 16

    nebula_lighthouse_internal_ip_addr: 10.43.0.1
    nebula_lighthouse_public_hostname: lighthouse.company.com
    nebula_lighthouse_public_port: 4242

    nebula_firewall_drop_action: reject

    nebula_inbound_rules:
      - { port: "any", proto: "icmp", host: "any" }
      - { port: 22, proto: "tcp", host: "any" }
    nebula_outbound_rules:
      - { port: "any", proto: "any", host: "any" }

    # Example lighthouse remote_allow_list configuration
    # Controls IP ranges that this node will consider when handshaking
    nebula_lighthouse_remote_allow_list:
      '172.16.0.0/12': false  # Block this subnet
      '0.0.0.0/0': true       # Allow all other IPs
      '10.0.0.0/8': false     # Block private range
      '10.42.42.0/24': true   # Allow specific subnet

    # Example lighthouse local_allow_list configuration
    # Filters which local IP addresses are advertised to the lighthouses
    nebula_lighthouse_local_allow_list:
      interfaces:
        tun0: false           # Block tun0 interface
        'docker.*': false     # Block all docker interfaces
      '10.0.0.0/8': true      # Only advertise this subnet

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

**Note:** More variables can be found in the [role defaults.](defaults/main.yml)

# Running the Playbook
```
ansible-playbook -i inventory nebula.yml
```
