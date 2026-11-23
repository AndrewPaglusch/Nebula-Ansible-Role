# GitHub integration testing implementation plan

## Objective and scope

Introduce a small, upstream-ready integration testing framework for this Nebula
Ansible role. The first scenario must prove that the checked-out role can deploy
a real overlay connecting three isolated Ubuntu 24.04 systems:

| Inventory host | Purpose | Nebula address |
| --- | --- | --- |
| `lighthouse` | Lighthouse and disposable certificate authority | `10.43.0.1/24` |
| `node1` | Ordinary node and connectivity test source | `10.43.0.2/24` |
| `node2` | Ordinary node and connectivity test destination | `10.43.0.3/24` |

The desired complete test command is `molecule test`. A successful role run or
running service is not sufficient: node1 must reach node2's Nebula address using
the configured tunnel interface.

Use Molecule, LXD system containers, Ansible verification and GitHub Actions.
Keep deployment, verification and resource lifecycle responsibilities separate.
Provide an understandable foundation for future regression assertions without a
custom driver, runner or configuration language.

Initial scope excludes idempotency testing, certificate rotation, group changes,
separate CA hosts, multiple distributions, Windows, upgrades, NAT traversal,
roaming, performance and long-term reliability. Do not introduce placeholder
tests for these features.

## Status and evidence boundary

This document is an implementation plan, not a report of working tests. The
investigation below was performed while the session was read-only. No scenario,
containers, dependency environment or workflow was created during that
investigation. No overlay connectivity or negative-control result is established.

The user's subsequent request authorises creation of this plan file. Execution
of the implementation phases is separate from writing this document.

## 1. Preflight findings

Recheck mutable environment details before executing the plan.

| Area | Observed result | Remaining verification |
| --- | --- | --- |
| Controller OS | Ubuntu 26.04.1 LTS, x86-64, inside a container | None for basic identification |
| Privileges | Passwordless sudo available | Root access alone does not establish usable namespace or TUN operations |
| Local TUN | `/dev/net/tun` is a character device | Actual tunnel creation and permissions |
| LXD client | Direct Snap binary works with existing authenticated configuration | Ensure Ansible invokes the same authenticated client |
| Remote daemon | `mythie`, LXD 5.21.9, trusted TLS connection | Container launch and image retrieval |
| Remote project | `opencode-temp` exists and was empty | Recheck before provisioning |
| Remote profile | Inherited `default` profile has a root disk on `cypher` and NIC on `lxdbr0` | Storage capacity and actual guest connectivity |
| Remote bridge | `10.126.197.1/24`, distinct from proposed overlay | DHCP, DNS, forwarding and guest egress |
| Remote resources | Approximately 32 GiB RAM total, approximately 10 GiB unused at inspection | Recheck current availability and pool capacity |
| Local daemon | LXD 6.10.1 reachable, reports no configured storage pool | Local nested launch not established; remote is simpler for this session |
| Other runtimes | Docker launcher exists; Incus was not found | Docker daemon functionality was not established |
| Python | Python 3.14.4 exists | pip, Ansible and Molecule were absent from the current environment |
| Outbound HTTPS | GitHub and Canonical image server returned HTTP 200 | Controller package indexes and daemon/guest download paths |
| Git | Installed; tracked files clean at inspection | Preserve current and subsequent user changes |
| GitHub remote | `https://github.com/Hooloovoo/Nebula-Ansible-Role.git` | No authority to push or create PRs |
| GitHub CLI | Installed, but `gh auth status` reports no authentication | Remote Actions execution and inspection unavailable in this session |

Useful read-only checks already used or suitable to repeat:

```bash
uname -a
id
sudo -n -l
git status --short
git remote -v
gh auth status
ls -l /dev/net/tun
LXD_CONF="$HOME/snap/lxd/common/config" /snap/lxd/current/bin/lxc remote list
LXD_CONF="$HOME/snap/lxd/common/config" /snap/lxd/current/bin/lxc project list mythie:
LXD_CONF="$HOME/snap/lxd/common/config" /snap/lxd/current/bin/lxc list mythie: --project opencode-temp
LXD_CONF="$HOME/snap/lxd/common/config" /snap/lxd/current/bin/lxc profile show mythie:default --project opencode-temp
LXD_CONF="$HOME/snap/lxd/common/config" /snap/lxd/current/bin/lxc network list mythie: --project opencode-temp
```

The direct client configuration is an environment-specific validation detail,
not an upstream default. Document ordinary local LXD access first and remote
overrides separately.

Many untracked files and directories already exist, including `testing/`,
`rotation-tests/` and several PKI investigation directories. Preserve them.
There is no tracked `tests/`, Molecule scenario or GitHub workflow in the
inspected revision. Do not adopt or overwrite untracked artifacts accidentally.

## 2. Existing role behavior to exercise

The inspected checkout is the source of truth:

- `meta/main.yml` declares `role_name: nebula`, no role dependencies and
  `min_ansible_version: 2.4`.
- `defaults/main.yml` defaults to Nebula 1.8.0 and `/opt/nebula`.
- `nebula_lighthouse` is the lighthouse inventory group.
- `nebula_ca_host` defaults to `groups['nebula_lighthouse'][0]`.
- `tasks/lighthouse.yml` generates the CA and lighthouse leaf material on the
  CA host. Use this normal path to generate disposable certificates.
- Ordinary nodes use `nebula_internal_ip_addr`; the lighthouse uses
  `nebula_lighthouse_internal_ip_addr`.
- `nebula_lighthouse_public_hostname` and
  `nebula_lighthouse_public_port` supply the bootstrap underlay endpoint.
- `tasks/nebula.yml` downloads and extracts the actual release binaries.
- Node certificates are signed through delegated tasks in `tasks/sign.yml` and
  transferred to their recipients through the role's normal PKI tasks.
- Repeat certificate inspection uses `json_query`. Declare the collection and
  Python `jmespath` dependency needed to resolve that filter.
- Node installation normally schedules a cron check. Ensure cron is available
  in preparation rather than changing the role's normal behavior to avoid it.
- Linux service names differ: lighthouse uses `lighthouse`; nodes use `nebula`.
- Both configuration templates currently set `tun.dev: neb0`. Verification must
  extract the interface from the installed configuration rather than hard-code
  it or introduce a production variable solely for testing.
- Template validation already runs the installed Nebula configuration checker.
- The role has Windows tasks and a Windows handler. Determine whether their
  collection must be installed for parsing even though the scenario is Linux.

Keep the default linear strategy and deploy all three systems in one play batch
so the lighthouse's signing binary is installed before delegated signing begins.
No separate CA machine is required.

## 3. Architecture and decision log

### Container technology: LXD system containers

LXD supplies systemd, network namespaces, guest package management and TUN access
without an SSH daemon in each guest. Use Ubuntu 24.04 initially. The existing
authenticated remote permits realistic local validation without initialising a
nested daemon in the controller container.

Use unprivileged guests. If explicit TUN access is necessary, configure an LXD
`unix-char` device for `/dev/net/tun`. Do not enable broad privileged-container
settings as a shortcut.

### Molecule driver: built-in default/delegated

Use Molecule's built-in `default` driver with Ansible lifecycle playbooks and
the `community.general.lxd` connection plugin.

Investigation found:

- `ansible-community/molecule-lxd` is archived; its last push was in 2022.
- The current `molecule-plugins` README lists no LXD driver.
- A maintained compatible third-party driver was not established.

The built-in approach avoids another Python plugin compatibility layer. Its
small create/destroy playbooks are visible Ansible code and work locally and in
Actions. Do not write a custom driver.

Prefer `community.general.lxd_container` for lifecycle operations. Verify its
endpoint, project and certificate parameters against the selected collection
version. Its API authentication settings are distinct from the `lxc` CLI's
remote configuration. If using the authenticated CLI from Ansible command tasks
is materially simpler for local and remote support, document that choice and
keep lifecycle logic explicit and small. Do not accidentally introduce `pylxd`
or another undeclared dependency merely by assuming the module needs it.

### Dependency compatibility

Select a released Molecule version and compatible `ansible-core`, collection and
Python versions after checking their published requirements. Pin the tested
direct dependencies or use narrow bounds with an intentional compatibility
policy. Avoid an unbounded latest-version setup.

Prefer a modern controller stack compatible with Ubuntu 24.04's Python 3.12.
The workshop controller's Python 3.14 may require a separate supported Python
interpreter for validation. Resolve this explicitly rather than silently testing
a different dependency set from CI.

Modern Molecule cannot exercise Ansible 2.4. Explain that the integration harness
has a higher controller requirement than the role metadata; do not raise the
production minimum as part of this testing PR. Inspect included collections for
additional compatibility requirements.

### Resource isolation and ownership

Prefer three uniquely scoped instance names plus an ownership marker if that
is simpler than creating a project. Inventory aliases can remain `lighthouse`,
`node1` and `node2` while `ansible_host` targets prefixed LXD instance names.

Before create or destroy acts on an existing name, confirm ownership. An
unrelated instance with the same name must cause a clear failure, not adoption
or deletion. Set ownership metadata at creation so partial provisioning can be
cleaned safely. Use an identifier stable across separate Molecule commands and
distinct across independent checkouts or concurrent runs.

Support an explicit remote/project selection without changing the user's active
LXD remote globally. Reuse the existing bridge/profile and never delete them.
If a project is created by the scenario instead, record ownership and only
remove that project once its owned resources are gone. Do not recursively delete
an arbitrary existing project.

### CI setup action

Canonical's `setup-lxd` action is labelled alpha. Pin a reviewed commit and an
explicit stable LXD channel, initially `5.21/stable` if still supported at
implementation time.

The inspected revision was
`25c036d6aa7fd68c4d980887ad2c0fb122234cd0`. Review `action.yml` at that exact
revision before using it; inspection of a moving `main` reference is not enough
to establish what a pin executes.

The inspected action implements Canonical's documented bridge-scoped
`DOCKER-USER` egress and established-return rules. This addresses a common
GitHub-runner Docker/LXD forwarding conflict without flushing firewall rules.
Verify the pinned action retains that behavior.

## 4. Phase A: prove the basic topology

Complete this before building elaborate framework code.

1. Recheck workspace status, LXD project contents, profile, storage capacity and
   available host resources.
2. Establish a supported isolated Python environment and install the proposed
   direct test dependencies.
3. Ensure the controller's `lxc` on PATH uses the authenticated configuration
   during workshop testing. Do not modify container configuration.
4. Create three task-owned Ubuntu 24.04 containers with bounded resource limits
   where practical.
5. Verify guest systemd startup with bounded polling. Distinguish degraded boot
   from a completely unusable init system and report relevant failed units.
6. Install only test/role prerequisites: Python, ping, iproute2, cron, CA trust
   and extraction tools as required by the image and role.
7. Verify DNS, package retrieval and access to Nebula release downloads from the
   guests. Controller HTTPS access is not proof of guest egress.
8. Verify `/dev/net/tun` and actual temporary TUN creation/deletion in each
   guest. A device node alone does not establish permission to use it.
9. Verify Ansible facts, file transfer and lighthouse delegation through the LXD
   connection. All management must remain independent of Nebula.
10. Gather the lighthouse's underlay address from guest facts or LXD state.
    Pass it as `nebula_lighthouse_public_hostname`; never use `10.43.0.1` as
    the bootstrap endpoint.
11. Apply the checked-out role to all three hosts, retaining role defaults where
    possible and providing only the required topology/firewall values.
12. Confirm node1 reaches node2 through the installed tunnel interface.

If launch or networking fails, inspect specific LXD errors and host forwarding
rules. Use documented targeted fixes. Time-box investigation of one
infrastructure blocker to approximately 30 minutes before reassessing.

Switching to Docker requires explicit discussion of the LXD blocker, documented
solutions and systemd/TUN behavior. Do not silently change technology.

## 5. Phase B: implement the Molecule scenario

Proposed deliverables:

```text
molecule/
  README.md
  requirements.txt
  requirements.yml
  default/
    molecule.yml
    create.yml
    prepare.yml
    converge.yml
    verify.yml
    diagnostics.yml
    destroy.yml
.github/
  workflows/
    integration.yml
```

Add only files actually required. Also add a short testing link to `README.md`
and narrowly scoped ignore entries for the virtual environment and generated
Molecule/Ansible caches. Preserve the existing broad `ansible_*` ignore rule and
check that new files are not inadvertently hidden by it.

### `molecule/requirements.txt`

Declare the tested Molecule, ansible-core and jmespath dependencies. Avoid adding
Testinfra, pytest, a custom Python runner or another verification framework for
this single ping assertion.

### `molecule/requirements.yml`

Declare the collections needed for the LXD connection/lifecycle, the role's
`json_query` use and any Windows plugin resolution needed at parse time. Use
versions compatible with the selected controller stack. Ensure both dependency
installation instructions and Molecule's dependency phase use this same file.

### `molecule/default/molecule.yml`

- Select the built-in default driver and Ansible verifier.
- Define three platforms and the `nebula_lighthouse` inventory group.
- Keep the overlay addresses and connection settings easy to find.
- Avoid duplicating topology definitions across multiple inventory files.
- Configure bounded lifecycle timeouts and readable Ansible output.
- Set role resolution so convergence uses the checkout regardless of directory
  name; verify Molecule's prerun behavior and role naming requirements.
- Configure the test sequence explicitly, without idempotence:

  ```yaml
  scenario:
    test_sequence:
      - dependency
      - destroy
      - create
      - prepare
      - converge
      - verify
      - destroy
  ```

- Verify the selected release's create/converge sequences include preparation
  as needed for ordinary iterative commands.

### `create.yml`

Provision only scenario-owned instances and any truly necessary owned
infrastructure. Reuse the configured default profile and bridge. Include safe
ownership checks, Ubuntu 24.04 image selection, explicit TUN device configuration
if needed and bounded waiting for startup/address allocation.

Populate the instance configuration/inventory data required by the chosen
Molecule release and LXD connection. Do not blindly use an SSH-oriented
instance-config example for a non-SSH connection.

### `prepare.yml`

Bootstrap Python with raw commands if the chosen image lacks it. Install ping,
iproute2, cron and necessary download/extraction prerequisites. Verify functional
systemd and TUN access. Use bounded retries for apt locks, DHCP and boot readiness
rather than fixed long sleeps.

Do not install Nebula, generate Nebula configuration or sign certificates here.

### `converge.yml`

Gather facts on all three guests, resolve the lighthouse's reachable underlay
address and apply the real role using normal public variables. Keep the
lighthouse as CA. Use the default role release initially so the first smoke test
exercises the default deployment rather than an unrelated Nebula upgrade.

Use the role's default firewall rules or a minimal public ICMP allow rule as
appropriate. No test-only production changes may bypass installation, signing,
configuration validation or service management.

### `verify.yml`

Run one functional assertion on node1:

1. Read the installed Nebula configuration from `nebula_config_dir`.
2. Parse YAML and retrieve `tun.dev`.
3. Obtain node2's overlay address from the shared inventory definition.
4. Execute the equivalent of:

   ```text
   ping -I <configured-tunnel-interface> -n -c 1 -W 2 <node2-overlay-address>
   ```

5. Retry a bounded number of times with short delays to allow startup and peer
   discovery; target approximately one minute or less of total waiting.
6. Mark observation tasks unchanged. A non-zero ping result after retries must
   fail verification clearly.

The assertion must not substitute underlay addresses or accept service status as
success. Bind the traffic to the tunnel even if a route happens to exist.

### `diagnostics.yml`

Keep diagnostics simple and usable from verification failure handling and CI.
Collect from the lighthouse and both nodes over LXD:

- status of `lighthouse` or `nebula`, as appropriate;
- the last 100 journal lines for that service;
- `ip addr` and `ip route`;
- configuration-check output or configuration existence where useful;
- scoped LXD instance information for provisioning/connection failures.

Do not print or upload certificate private keys, slurped key contents or complete
ephemeral inventories containing credentials. Prefer command results in the
Actions/Ansible log over a custom artifact framework.

Diagnostic commands are best-effort so one unavailable guest does not hide
information from the others. Their error handling must never turn the original
test failure into success.

### `destroy.yml`

Remove only the exact owned instances. Handle missing instances and partially
completed creation. Check ownership before deletion. Reset Molecule instance
state as required by the selected release. Do not delete shared bridges,
profiles, storage pools, unrelated instances or existing projects.

## 6. Phase C: correctness and negative-control validation

Record actual command lines, dependency versions, exit statuses and meaningful
results. Do not label implemented behavior as verified until it has run.

### Positive and iterative paths

Run:

```bash
molecule create
molecule converge
molecule verify
molecule converge
molecule verify
```

The second convergence checks that the documented iteration path works without
manually recreating certificates or guests. It is not a new idempotency test and
does not require a zero changed count.

Confirm the installed certificates, tunnel addresses and services exist as
supporting observations; the ping is the functional pass/fail assertion.

### Required negative control

Use the same retained environment and the same verifier:

```bash
molecule verify
# Stop node2's nebula service through the configured LXD remote/project.
molecule verify
# Start node2's nebula service through the configured LXD remote/project.
molecule verify
```

The expected results are pass, non-zero failure, pass. Replace the comments in
the final guide/report with the exact tested `lxc exec ... systemctl stop/start
nebula` commands and actual instance names.

Stop only the task-created node2 service. Check the role's scheduled cron helper
does not unexpectedly restart it during the bounded negative control. If
necessary, temporarily mask the service for the development-time control and
unmask/start it afterward, recording the exact procedure.

Inspect the failed verifier's diagnostics and ensure the failure is ping
connectivity, not a different assertion that merely observes service state.

### Lifecycle and failure behavior

1. Run `molecule destroy`, then the complete `molecule test` lifecycle.
2. Verify all three test instances are removed after success.
3. Exercise a deliberate connectivity failure and confirm a non-zero result,
   diagnostics before destruction and cleanup of owned resources.
4. Verify `molecule test --destroy=never` against the selected version. Establish
   its behavior for initial cleanup, success and failure before documenting it.
5. Confirm partial provisioning can be cleaned and an unrelated name collision
   is refused safely.
6. Confirm independent `molecule verify` does not recreate or reconverge guests.

## 7. Phase D: GitHub Actions

Add one workflow using an ordinary `pull_request` event, a standard
`ubuntu-24.04` runner, minimal `contents: read` permissions and a reasonable job
timeout. Do not use `pull_request_target`, repository secrets or real PKI.

Workflow responsibilities:

1. Check out the PR revision with a pinned action and avoid unnecessary retained
   Git credentials.
2. Set up a supported Python version with a pinned action if needed.
3. Initialise LXD using the reviewed SHA-pinned Canonical action and explicit
   stable channel.
4. Install dependencies from the same declarations used locally.
5. Run the Molecule scenario, retaining resources long enough to collect
   diagnostics when a required phase fails.
6. On failure, run the scenario's diagnostics before destroying resources.
7. Run `molecule destroy` with `if: always()` after diagnostics.

Preferred CI strategy, subject to verified CLI behavior:

- Execute `molecule test --destroy=never`.
- Collect diagnostics in a failure step, including convergence failures.
- Always perform explicit destruction afterward.

Verification should also collect connectivity diagnostics itself so local users
receive useful output from `molecule test`. Reuse diagnostics rather than
duplicating their implementation in workflow shell commands.

Do not use `continue-on-error` on the test step or otherwise erase its failure.
Molecule's exit code must determine job failure. A cleanup failure should also be
visible rather than silently declaring a clean run.

Review the chosen release's actual `--destroy=never` behavior before relying on
it. If necessary, use a documented sequence of ordinary Molecule commands that
provides the same diagnostics-before-cleanup guarantee without a custom wrapper.

Validate YAML, Molecule configuration and Ansible syntax locally. Use an
available workflow validator if practical, without adding a large permanent
dependency merely for validation.

No branch push, workflow trigger or PR creation is authorised. Without subsequent
explicit permission and suitable authentication, report GitHub-hosted execution
as unverified even if all local tests pass.

## 8. Phase E: documentation and developer experience

Write `molecule/README.md` and link it from the main README. Keep it short enough
to be useful to a first-time contributor or coding agent.

Cover:

- What the three-node test proves and the underlay/overlay distinction.
- Linux host capabilities, systemd guests, TUN support and LXD access.
- Installing and initialising LXD on a fresh developer host; do not instruct
  users to reinitialise an existing daemon blindly.
- Supported controller Python/Ansible/Molecule versions and collection install
  commands.
- A normal local setup and optional existing remote/project selection.
- The complete command `molecule test`.
- Iteration with `molecule create`, `molecule converge`, `molecule verify` and
  `molecule destroy`.
- The actual tested retention command and explicit cleanup command.
- Exact scoped `lxc exec` commands to inspect each guest, service and journal.
- The negative-control commands and expected exit results.
- Where disposable CA material lives and how destruction removes it.
- Links to Canonical's Docker/LXD forwarding guidance for network failures.

Dependency installation examples should ultimately have this shape, with exact
supported interpreter/version choices filled in after testing:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r molecule/requirements.txt
ansible-galaxy collection install -r molecule/requirements.yml
molecule test
```

Document the regression workflow literally:

1. Add an assertion that reproduces the bug.
2. Confirm it fails against the unfixed role.
3. Implement the fix.
4. Confirm the new assertion passes.
5. Run the complete suite.

Put simple new assertions in `verify.yml`. Once several checks justify it,
include ordinary task files under `checks/` without changing provisioning,
inventory or CI. Do not create empty future check files in the initial PR.

## 9. Existing role bugs and scope decisions

No existing production bug has been demonstrated by this investigation.

If execution exposes a role issue:

1. Reproduce it independently of lifecycle or connection mistakes.
2. Record the failing task, inputs and reproduction command.
3. Prefer a minimal necessary fix and retain the smoke test as evidence.
4. List production changes separately in the final report.
5. Discuss substantial role behavior changes before implementing them.

Do not refactor the role to make the scenario easier. Default-deployment upgrade,
migration and failure-path checks become relevant only if production behavior is
changed; obey the repository's applicable compatibility instructions then.

Significant deviations requiring explicit discussion include replacing LXD,
adding a custom framework, adding substantial dependencies, changing unrelated
CI, changing production behavior substantially, or pushing/creating a PR.

## 10. Final review and acceptance evidence

Before finishing, inspect the complete diff and repository status. Remove
temporary scaffolding and ensure generated PKI, caches and virtual environments
are not included. Preserve pre-existing untracked work.

### Functional acceptance

- [ ] Three isolated Ubuntu 24.04 systems were actually provisioned.
- [ ] Ansible managed them independently of Nebula, including delegated signing.
- [ ] The checked-out role generated disposable PKI and configured all nodes.
- [ ] The correct services and tunnel interfaces started.
- [ ] Node1 reached node2's Nebula address through the configured tunnel.
- [ ] The identical verifier failed with node2's overlay stopped.
- [ ] The identical verifier passed after restoring node2.

### Lifecycle and developer acceptance

- [ ] `molecule test` completed successfully.
- [ ] Convergence and verification can be rerun independently.
- [ ] Failure diagnostics precede destruction and preserve the failed exit code.
- [ ] Retention and cleanup commands were actually exercised.
- [ ] Partial creation cleanup and collision ownership checks were exercised.
- [ ] Cleanup left unrelated LXD resources intact.
- [ ] Documentation contains exact tested commands and a regression workflow.

### CI and maintenance acceptance

- [ ] Workflow syntax/configuration checked locally.
- [ ] Workflow uses the same scenario, minimal permissions and pinned actions.
- [ ] Stable LXD channel and Docker forwarding handling reviewed.
- [ ] Dependencies are declared and compatible with the selected controller.
- [ ] Test sequence is explicit and excludes idempotence.
- [ ] Main README links to the guide.
- [ ] No unrelated production or CI changes exist.
- [ ] Real GitHub Actions execution verified, or explicitly reported unverified.

### Required final implementation report

Separate implemented functionality from demonstrated execution. Include:

1. Files added/modified and the overlay assertion they implement.
2. Driver/container decisions and any significant deviations.
3. Exact commands and outcomes: successful runs, failures and causes, unexecuted
   checks and their environmental/permission blockers.
4. Explicit pass/fail/pass negative-control evidence, or a precise explanation
   why it could not be run.
5. Existing role bugs and production changes, separately from test infrastructure
   issues.
6. Known limitations, especially unverified GitHub-hosted execution.
7. Copy-and-paste dependency, full-run, iteration, diagnostics and cleanup commands.
8. A proposed upstream title and description; do not create the PR without
   explicit authorisation.

Suggested PR title:

> Add a three-node Nebula integration smoke test with Molecule and LXD

Suggested description outline:

> Add one Ubuntu 24.04 Molecule scenario that provisions a lighthouse and two
> nodes, applies the checked-out role with disposable certificates, and verifies
> node-to-node connectivity through the configured Nebula tunnel. Add diagnostics,
> scoped cleanup, a pull-request workflow and a short local testing guide.
>
> Run with `molecule test` after installing the documented LXD and Python/Ansible
> dependencies. Contributors can reproduce bugs through additional Ansible
> verification assertions without duplicating provisioning or changing CI.
>
> Include the actual local and negative-control results here. Identify hosted CI
> execution as unverified unless a real authorised run was inspected. This first
> scenario deliberately excludes idempotency, rotation, upgrades and additional
> platforms.

## References reviewed during investigation

- Molecule configuration and lifecycle documentation:
  <https://docs.ansible.com/projects/molecule/configuration/>
- Archived original LXD driver:
  <https://github.com/ansible-community/molecule-lxd>
- Maintained Molecule plugin list:
  <https://github.com/ansible-community/molecule-plugins>
- Ansible LXD lifecycle module:
  <https://docs.ansible.com/ansible/latest/collections/community/general/lxd_container_module.html>
- Canonical setup action and alpha/pinning guidance:
  <https://github.com/canonical/setup-lxd>
- Canonical firewall and Docker forwarding guidance:
  <https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/>
