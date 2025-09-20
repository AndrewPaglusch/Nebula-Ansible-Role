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

# SSH Debug Console

This role supports Nebula's built-in SSH debug console feature. To enable it, set:

```yaml
nebula_sshd_enabled: true
nebula_sshd_listen: "127.0.0.1:2222"  # Optional, defaults to 127.0.0.1:2222
nebula_sshd_authorized_users:
  - user: admin
    keys:
      - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... admin@host"
    key_files:
      - "/path/to/admin.pub"
  - user: developer
    key_files:
      - "~/.ssh/developer_key.pub"
```

You can specify SSH keys either:
- **Inline** using the `keys` field with the full public key string
- **From files** using the `key_files` field with paths to public key files
- **Both** in the same user entry

The role automatically generates an ED25519 SSH host key at `/opt/nebula/ssh_host_ed25519_key` when the SSH daemon is enabled.

# Running the Playbook
```
ansible-playbook -i inventory nebula.yml
```
