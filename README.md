# Ansible Role for Nebula

Quickly and easily deploy the [Nebula Overlay VPN](https://github.com/slackhq/nebula) software onto all of your hosts.

# What Is Nebula

> Nebula is a scalable overlay networking tool with a focus on performance, simplicity and security. It lets you seamlessly connect computers anywhere in the world.

You can read more about Nebula [on the official repo](https://github.com/slackhq/nebula)

# Example Playbook
```
---
- name: Deploy Nebula (multi-lighthouse)
  hosts: all
  gather_facts: yes
  user: ansible
  become: yes
  vars:
    nebula_version: 1.8.0
    nebula_network_name: "My Company Nebula"
    nebula_network_cidr: 16

    # --- Multi-Lighthouse Configuration ---
    # The FIRST entry is the primary (hosts the CA key).
    # All additional entries are secondaries.
    nebula_lighthouses:
      - hostname: lighthouse1
        internal_ip: 10.43.0.1
        public_hostname: lh1.example.com
        public_port: 4242
        is_relay: true
      - hostname: lighthouse2
        internal_ip: 10.43.0.2
        public_hostname: lh2.example.com
        public_port: 4242
        is_relay: true

    nebula_firewall_block_action: reject
    nebula_inbound_rules:
      - { port: "any", proto: "icmp", host: "any" }
      - { port: 22, proto: "tcp", host: "any" }
    nebula_outbound_rules:
      - { port: "any", proto: "any", host: "any" }

  roles:
    - role: nebula


# =============================================================
# IMPORTANT: The hostname in the inventory must match the
# hostname field in nebula_lighthouses!
#
# lighthouse1.example.com → hostname: lighthouse1
# lighthouse2.example.com → hostname: lighthouse2
#
# The role looks up the matching entry using:
# selectattr('hostname', 'equalto', inventory_hostname)
#
# If you want to use FQDNs as the hostname field:
# - hostname: lighthouse1.example.com
#   ...
# and in the inventory as well:
# lighthouse1.example.com
# =============================================================
```

# Example Inventory
```
[nebula_lighthouse]
lighthouse1.example.com
lighthouse2.example.com

[servers]
web01.example.com nebula_internal_ip_addr=10.43.0.10
docker01.example.com nebula_internal_ip_addr=10.43.0.11
db01.example.com nebula_internal_ip_addr=10.43.0.12
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
