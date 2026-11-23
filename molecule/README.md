# Integration testing

The default Molecule scenario creates three unprivileged Ubuntu 24.04 LXD system
containers: `lighthouse`, `node1` and `node2`. It applies **this checkout** of the
role, generates a disposable CA on the lighthouse, and verifies that node1 can
ping node2's Nebula address through the tunnel interface read from the installed
configuration. Overlay addresses are `10.43.0.1`, `.2` and `.3`, with a `/24`
prefix; change them together in `default/molecule.yml` if they conflict locally.
Ansible uses LXD, independently of the overlay, without SSH servers in the guests.

## Prerequisites and installation

Use a Linux LXD host with working system containers, systemd, outbound access to
Ubuntu repositories and GitHub releases, and functional `/dev/net/tun` access.
The scenario gives each container a narrow `unix-char` TUN device, not privileged
mode. Preparation actually creates and removes a temporary tunnel to test access.
Allow roughly 1.5 GiB guest RAM plus host/image storage overhead.

On a **new** Ubuntu host, install and initialise LXD, then grant your user access:

```bash
sudo snap install lxd --channel=5.21/stable
sudo lxd init --auto
sudo usermod -aG lxd "$USER"
# Log out and back in to activate group membership before continuing.
lxc list local:
```

For an existing installation, reuse its configuration. The selected project's
default profile must supply a root disk and a network interface on a working
bridge. LXD access grants administrative control of its host; you do not need to
run Molecule itself as root.

From the repository root, use Python 3.12–3.14 with venv support (on Ubuntu,
install `python3-venv` if needed):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r molecule/requirements.txt
ansible-galaxy collection install -r molecule/requirements.yml
molecule test
```

Molecule also installs the declared collections during its dependency phase.
The pinned harness uses Ansible 2.20 and requires a modern controller; it does
not test the role's historical Ansible 2.4 metadata minimum. `jmespath` and
`community.general` support the role's certificate inspection on repeat runs;
`ansible.windows` resolves its existing Windows handlers even in this Linux test.

Optional existing remote/project selection:

```bash
export NEBULA_TEST_REMOTE=my-remote
export NEBULA_TEST_PROJECT=my-test-project
lxc list "$NEBULA_TEST_REMOTE:" --project "$NEBULA_TEST_PROJECT"
molecule test
```

Defaults are `local` and `default`; the scenario does not create or delete
projects, networks or profiles. Both lifecycle commands and Ansible's connection
plugin use `lxc` on PATH, so it must use your authenticated client configuration
(set `LXD_CONF` when necessary). Preserve these environment settings across all
commands for a given environment.

## Iteration and inspection

```bash
molecule create       # Creates guests and runs prerequisite preparation
molecule converge     # Applies the role; repeat after editing it
molecule verify       # Only reruns assertions; does not redeploy
molecule side-effect  # Prints provisioning, service, journal and network diagnostics
molecule destroy      # Explicit cleanup, also safe after partial preparation
```

Instance names have a checkout-path hash to distinguish independent checkouts.
Calculate the prefix and inspect the guests using the same remote/project:

```bash
export NEBULA_TEST_REMOTE="${NEBULA_TEST_REMOTE:-local}"
export NEBULA_TEST_PROJECT="${NEBULA_TEST_PROJECT:-default}"
PREFIX=$(python -c 'import hashlib,pathlib; print("nebula-smoke-" + hashlib.sha1(str(pathlib.Path.cwd().resolve()).encode()).hexdigest()[:10])')
lxc list "$NEBULA_TEST_REMOTE:" --project "$NEBULA_TEST_PROJECT"
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node1" --project "$NEBULA_TEST_PROJECT" -- bash
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node1" --project "$NEBULA_TEST_PROJECT" -- journalctl -u nebula --no-pager -n 100
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-lighthouse" --project "$NEBULA_TEST_PROJECT" -- journalctl -u lighthouse --no-pager -n 100
```

Use the physical checkout path (not a symlink) consistently. Only run one scenario
at a time per checkout and remote/project. Ownership metadata protects colliding
names: create/destroy refuse to touch an instance without this checkout's marker.
Do not remove or forge markers to get past that check. Cleanup removes only the
three owned instances, including their disposable certificate/key material.

## Failures and retained environments

```bash
molecule test --destroy=never
# Inspect or edit, then:
molecule side-effect
molecule converge
molecule verify
molecule destroy
```

In the pinned Molecule version, `--destroy=never` skips **both** the initial and
final destroy, and retains resources on failure. Start with `molecule destroy`
first if you want a fresh retained run. Normal `molecule test` starts clean and
destroys resources at completion; on failure its cleanup hook prints diagnostics
before destruction. Connectivity failures also print diagnostics inside verify.
Diagnostics never print private key contents, and a failed test remains failed.
CI retains instances for failure diagnostics and always runs explicit cleanup.

Preparation bounds package-manager waits and uses IPv4 repository access. If
guests cannot reach repositories, inspect DNS, bridge addressing and host
forwarding rules. Docker can block LXD forwarding; see [Canonical's targeted
firewall guidance](https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/).
The pinned CI setup action installs those bridge-scoped rules. Do not flush the
host firewall. A killed runner/process may require explicit `molecule destroy`;
no runner can guarantee cleanup after host loss.

### Development-time negative control

After `molecule create` and `molecule converge`, calculate `PREFIX` and export the
remote/project variables as above, then run:

```bash
molecule verify  # Must pass
# Stop cron too: the role's watchdog can otherwise restart a stopped Nebula.
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node2" --project "$NEBULA_TEST_PROJECT" -- systemctl stop cron nebula
molecule verify  # Must fail with a non-zero exit and failed overlay ping
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node2" --project "$NEBULA_TEST_PROJECT" -- systemctl start nebula cron
molecule verify  # Must pass again
molecule destroy
```

Restore both services even if an intermediate command surprises you. This manual
control validates the same assertion used in CI; it is not an additional CI test.

## Adding regression tests

1. Add an Ansible assertion in `default/verify.yml` that reproduces the bug.
2. Confirm it fails against the unfixed role using `molecule verify`.
3. Fix the role, then rerun `molecule converge` and `molecule verify`.
4. Confirm the new assertion passes and run the full `molecule test` suite.

Reuse the existing inventory and guests. When several assertions justify it,
include task files under `default/checks/` from verification; provisioning and CI
should not need changes. Use a separate scenario only for genuinely different
topology requirements. The initial smoke test deliberately excludes idempotency,
rotation, upgrades, other distributions and Windows.

### Why the built-in driver?

The original `ansible-community/molecule-lxd` driver is archived, and the
maintained `molecule-plugins` package does not include LXD. Molecule's built-in
default/delegated driver needs only small Ansible lifecycle playbooks. Those use
the standard `lxc` CLI so lifecycle and connection-plugin operations share local
or remote authentication without duplicating API certificate configuration.
The checked-out role is included by absolute path, avoiding Galaxy downloads or
directory-name-dependent role resolution. The CI setup action is alpha, so its
reviewed revision is SHA-pinned and its LXD channel is explicitly stable.
