# Integration testing

One smoke test deploys **this checkout** to three unprivileged Ubuntu 24.04 LXD
containers: `lighthouse` (also the disposable CA), `node1` and `node2`. It verifies
node1 can ping node2's Nebula address, bound to the interface read from the
installed configuration. Ansible manages guests through LXD, independently of
Nebula, without SSH. Overlay addresses are `10.43.0.1`, `.2` and `.3` with a `/24`
prefix; change them together in `default/molecule.yml` if they conflict locally.
This initial scenario excludes idempotency, version matrices, certificate changes,
group/firewall-policy tests, separate CA hosts, other distributions and Windows.

## Prerequisites and installation

Use a Linux LXD host with systemd-capable containers, working `/dev/net/tun`,
outbound Ubuntu/GitHub access and roughly 1.5 GiB guest RAM plus image storage.
Preparation checks actual TUN creation using a narrow `unix-char` device.

On a **new** Ubuntu host:

```bash
sudo snap install lxd --channel=5.21/stable
sudo lxd init --auto
sudo usermod -aG lxd "$USER"
# Log out and back in to activate group membership, then run: lxc list local:
```

Reuse existing LXD configurations: the project's default profile must supply a
root disk and a working bridge NIC. LXD membership grants host administrative
access; Molecule itself need not run as root.

From the repository root, use Python 3.12–3.14 (`python3-venv` on Ubuntu):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r molecule/requirements.txt
ansible-galaxy collection install -r molecule/requirements.yml
molecule test
```

The pinned harness uses Ansible 2.20, not the role's historical 2.4 minimum.
Molecule also installs the declared collections. `jmespath` supports certificate
inspection; `ansible.windows` resolves the role's Windows handlers on Linux.

## Iteration and remote access

```bash
molecule create       # Creates guests and prepares prerequisites
molecule converge     # Apply the role; repeat after editing it
molecule verify       # Rerun assertions without redeploying
molecule side-effect  # Print provisioning, service, journal and network diagnostics
molecule destroy      # Remove owned guests, including partially prepared ones
```

Optionally select an existing remote/project; defaults are `local` and `default`:

```bash
export NEBULA_TEST_REMOTE=my-remote NEBULA_TEST_PROJECT=my-test-project
molecule test
```

Keep these settings throughout a run. Both lifecycle and connection-plugin
operations use `lxc` on PATH and its authenticated configuration (`LXD_CONF` when
needed). The scenario never deletes projects, networks or profiles. Names contain
a checkout-path hash, and ownership markers prevent deletion of colliding,
unowned instances. Use one run per physical checkout and remote/project at a time.

## Debugging and cleanup

`molecule test --destroy=never` retains guests, skipping both initial and final
destruction. Run `molecule destroy` first for a fresh retained environment.
Inspect with `molecule side-effect`, then reapply/verify or explicitly destroy.
Normal failed tests collect diagnostics before destruction through Molecule
26.11's automatic failure cleanup, independently of `test_sequence`. Verification
also preserves the original failing task/error. Private keys are not printed.
CI retains guests for diagnostics and always attempts explicit cleanup.

To inspect guests directly, calculate their prefix from the repository root:

```bash
export NEBULA_TEST_REMOTE="${NEBULA_TEST_REMOTE:-local}"
export NEBULA_TEST_PROJECT="${NEBULA_TEST_PROJECT:-default}"
PREFIX=$(python -c 'import hashlib,pathlib; print("nebula-smoke-" + hashlib.sha1(str(pathlib.Path.cwd().resolve()).encode()).hexdigest()[:10])')
lxc list "$NEBULA_TEST_REMOTE:" --project "$NEBULA_TEST_PROJECT"
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node1" --project "$NEBULA_TEST_PROJECT" -- journalctl -u nebula --no-pager -n 100
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node1" --project "$NEBULA_TEST_PROJECT" -- bash
```

The lighthouse service is named `lighthouse`, rather than `nebula`. Preparation
uses bounded IPv4 package downloads; failures include package-manager logs.
For bridge/Docker forwarding issues, see [Canonical's firewall guidance](https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/).
Do not flush host firewall rules. Explicit `molecule destroy` may be needed after
an interrupted process; it also removes disposable certificates and keys.

### Development-time negative control

After create/converge, use the prefix and remote/project variables above:

```bash
molecule verify  # Must pass
# Stop cron too: the role's watchdog can otherwise restart a stopped Nebula.
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node2" --project "$NEBULA_TEST_PROJECT" -- systemctl stop cron nebula
molecule verify  # Must fail with a non-zero exit and failed overlay ping
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node2" --project "$NEBULA_TEST_PROJECT" -- systemctl start nebula cron
molecule verify  # Must pass again
molecule destroy
```

Restore both services even after unexpected results. This exercises the same
verifier as CI and is not an additional automated test.

## Adding regression tests

Add an assertion in `default/verify.yml` and confirm it fails against the unfixed
role. Implement the fix, rerun `molecule converge` and `molecule verify`, then run
the complete `molecule test` suite. As checks grow, include ordinary task files
under `default/checks/`; reuse provisioning and inventory without changing CI.

The built-in default/delegated driver avoids the archived `molecule-lxd` plugin;
`molecule-plugins` does not include LXD. Lifecycle uses the standard CLI, and the
role is included by absolute checkout path. CI's alpha LXD setup action is pinned
to a reviewed SHA and a stable LXD channel.
