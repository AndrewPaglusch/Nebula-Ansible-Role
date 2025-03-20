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
## Traditional Method (Manual IP Assignment)
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

## Automatic IP Assignment
With automatic IP assignment, you can organize hosts into groups without having to specify IPs:

```
[nebula_lighthouse]
lighthouse01.company.com

[webservers]
web01.company.com
web02.company.com
web03.company.com

[databases]
db01.company.com
db02.company.com

[app_servers]
app01.company.com
app02.company.com
```

IPs will be automatically assigned based on the group mapping defined in `nebula_ip_map`. 
By default, the following mapping is used:

```yaml
nebula_ip_map:
  nebula_lighthouse: {prefix: "10.43.0", start: 1}  # 10.43.0.1, 10.43.0.2, etc.
  webservers: {prefix: "10.43.1", start: 10}        # 10.43.1.10, 10.43.1.11, etc.
  databases: {prefix: "10.43.2", start: 10}         # 10.43.2.10, 10.43.2.11, etc.
  app_servers: {prefix: "10.43.3", start: 10}       # 10.43.3.10, 10.43.3.11, etc.
  monitoring: {prefix: "10.43.4", start: 10}        # 10.43.4.10, 10.43.4.11, etc.
  backups: {prefix: "10.43.5", start: 10}           # 10.43.5.10, 10.43.5.11, etc.
```

You can customize this mapping in your playbook variables. If a host isn't in a mapped group, it will use a fallback hash-based IP in the 10.43.254.x range.

**Note:** More variables can be found in the [role defaults.](defaults/main.yml)

# Cloudflare DNS Integration

This role can automatically create DNS records in Cloudflare for your Nebula nodes:

1. Enable the integration in your inventory:
```yaml
nebula_cloudflare_integration: true
nebula_cloudflare_zone: "example.com"
```

2. Store your Cloudflare API token securely in your vault file:
```yaml
nebula_cloudflare_api_token: "your-cloudflare-api-token"
```

3. Customize DNS naming convention:
```yaml
# Default: hostname-neb.example.com (nh-web01-neb.example.com)
nebula_dns_affix: "neb"
nebula_dns_affix_position: "suffix"  # Options: "suffix" or "prefix"
nebula_dns_affix_separator: "-"

# For prefix style: neb-hostname.example.com (neb-nh-web01.example.com)
nebula_dns_affix: "neb"
nebula_dns_affix_position: "prefix"
nebula_dns_affix_separator: "-"
```

4. Additional DNS settings:
```yaml
nebula_cloudflare_ttl: 120
nebula_cloudflare_proxied: false
```

The role creates A records for each Nebula host using your chosen naming convention, pointing to the host's Nebula internal IP. This makes it easy to address Nebula hosts by DNS name from anywhere with access to your DNS.

# Running the Playbook
```
ansible-playbook -i inventory nebula.yml
```

# DNS-only Update
To update only DNS records without modifying the Nebula installation:
```
ansible-playbook -i inventory nebula.yml --tags nebula_dns
```
