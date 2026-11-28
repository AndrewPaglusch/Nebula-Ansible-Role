# Integration testing

Each scenario installs this checkout on three fresh Ubuntu 26.04 LXD containers:
`lighthouse` (also the disposable CA), `node1` and `node2`. Verification checks the
installed Nebula version on all three guests, then pings node2's overlay address
from node1, bound to the configured Nebula interface.
Ansible manages the guests through LXD, independently of Nebula and without SSH.

## Prerequisites and installation

Use a Linux LXD host with systemd-capable containers, working `/dev/net/tun`,
outbound Ubuntu/GitHub access and roughly 1.5 GiB guest RAM per scenario plus
image storage. The controller needs Python 3.12–3.14 with venv support
(`python3-venv` on Ubuntu).

On a **new** Ubuntu host:

```bash
sudo snap install lxd --channel=5.21/stable
sudo lxd init --auto
sudo usermod -aG lxd "$USER"
# Log out and back in to activate group membership, then run: lxc list local:
```

For an existing installation, reuse its configuration. The selected project's
default profile must supply a root disk and a working bridge NIC. Run Molecule
as a user with LXD access; it does not need sudo.

Install dependencies from the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r molecule/requirements.txt
ansible-galaxy collection install -r molecule/requirements.yml
```

## Running tests

```bash
molecule test --all                # Both versions, each with fresh containers
molecule test                      # Role's default Nebula version
molecule test -s nebula-1-12        # 1.12.0 only
```

The `default` scenario inherits `nebula_version` from the role's `defaults/main.yml`;
`nebula-1-12` selects 1.12.0. To override a version, use
`molecule test -- -e "nebula_version=1.12.0"`. The suite tests fresh installations
and connectivity, not upgrades between versions.

For iterative development:

```bash
molecule create       # Creates guests and prepares prerequisites
molecule converge     # Apply the role; repeat after editing it
molecule verify       # Rerun assertions without redeploying
molecule side-effect  # Print provisioning, service, journal and network diagnostics
molecule destroy      # Remove owned guests, including partially prepared ones
```

Bare commands select `default`; append `-s nebula-1-12` for the other scenario.

## Remote access

Optionally select an existing remote/project; defaults are `local` and `default`:

```bash
export NEBULA_TEST_REMOTE=my-remote NEBULA_TEST_PROJECT=my-test-project
molecule test --all
```

The `lxc` on PATH must use your authenticated configuration (`LXD_CONF` when
needed). **Developers sharing an LXD remote must use different LXD projects**:
identical checkout paths can produce identical guest names. Use one run per
checkout and scenario at a time. Keep the checkout path, remote and project the
same until cleanup finishes.

## Debugging and cleanup

`molecule test --all --destroy=never` retains both environments (six guests),
skipping initial and final destruction. Run `molecule destroy --all` first for a
fresh retained run. Inspect with `molecule side-effect --all`, then reapply/verify
one scenario or explicitly clean up with `molecule destroy --all`.
Normal failed tests print diagnostics before destroying their guests. After an
interrupted process, run `molecule destroy --all` explicitly. Cleanup removes only
owned test guests and their disposable certificates; it refuses unowned name
collisions and does not delete projects, networks or profiles.

To inspect guests directly, select a scenario and calculate its prefix:

```bash
export NEBULA_TEST_REMOTE="${NEBULA_TEST_REMOTE:-local}"
export NEBULA_TEST_PROJECT="${NEBULA_TEST_PROJECT:-default}"
SCENARIO=default  # Or nebula-1-12
CHECKOUT_HASH=$(python -c 'import hashlib, pathlib; print(hashlib.sha256(str(pathlib.Path.cwd()).encode()).hexdigest()[:16])')
PREFIX="nb-$CHECKOUT_HASH-$SCENARIO"
lxc list "$NEBULA_TEST_REMOTE:" --project "$NEBULA_TEST_PROJECT"
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node1" --project "$NEBULA_TEST_PROJECT" -- journalctl -u nebula --no-pager -n 100
lxc exec "$NEBULA_TEST_REMOTE:$PREFIX-node1" --project "$NEBULA_TEST_PROJECT" -- bash
```

The lighthouse service is named `lighthouse`, rather than `nebula`.
Diagnostics include package-manager logs when prerequisite installation fails.
For bridge/Docker forwarding issues, see [Canonical's firewall guidance](https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/).

## Adding regression tests

Add an assertion in `molecule/default/verify.yml` and confirm it fails against
the unfixed role. Implement the fix, rerun `molecule converge` and
`molecule verify`, then run the complete `molecule test --all` suite. As checks
grow, include task files under `molecule/default/checks/`; reuse provisioning
and inventory without changing CI.

Shared inventory and lifecycle configuration live in `.config/molecule/config.yml`;
playbooks are shared in `molecule/default/`. Overlay addresses are `10.43.0.1`,
`.2` and `.3` with a `/24` prefix; change them together in the shared configuration
if they conflict locally. To add a version, copy `molecule/nebula-1-12/molecule.yml`
to a new scenario directory and change `nebula_version`; `--all` includes it
automatically.

CI selects scenarios explicitly in `.github/workflows/integration.yml`; add new
scenarios to its matrix list to run them on pull requests.
