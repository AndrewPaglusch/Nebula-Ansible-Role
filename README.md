# Nebula Overlay VPN Installer with Ansible

Quickly and easily deploy the [Nebula Overlay VPN](https://github.com/slackhq/nebula) software onto all of your hosts. Just add your servers to the `inventory` file and then edit `nebula_vars.yml`.

This playbook is meant to get you up and running with Nebula quickly with sane defaults.

# What Is Nebula

> Nebula is a scalable overlay networking tool with a focus on performance, simplicity and security. It lets you seamlessly connect computers anywhere in the world.

You can read more about Nebula [on the official repo](https://github.com/slackhq/nebula)

# How To Run

```
ansible-playbook -i inventory main.yml
```
