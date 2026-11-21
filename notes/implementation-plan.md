# OpenHands Ansible Role — Implementation Plan and Current Design Contract

> **Status: living planning document, not a binding specification**
>
> This note records the current understanding, preferences, and decisions for
> implementing this repository. It is intentionally **not exempt from
> questioning or revision**. Future implementers should challenge any decision
> here when new upstream behavior, better evidence, operational experience, or
> changed requirements justify doing so. The goal is to preserve context, not
> to turn early decisions into permanent constraints.
>
> When changing an established decision, document the reason and update this
> note so that the repository continues to explain its current direction.

## Purpose

Build `nietaki/ansible-role-openhands` as a conventional standalone Ansible
role that deploys OpenHands Agent Canvas on a dedicated Ubuntu host.

The initial deployment shape is:

- Agent Canvas and its outer Agent Server run natively as a systemd service.
- Every conversation runs in a separate Docker container.
- Docker uses an official OpenHands Agent Server `-golang` image.
- Conversation workspaces and persistence are bind-mounted from the host.
- Docker itself is provisioned outside this role.

The role should be reusable outside the `kotik` repository, while working well
for the initial `underturn` deployment.

## Current repository and packaging contract

| Item | Current decision |
| --- | --- |
| GitHub repository | `nietaki/ansible-role-openhands` |
| Distribution model | Standalone Ansible role |
| Role name | `openhands` |
| Galaxy identifier | `nietaki.openhands` |
| Public variable prefix | `openhands_` |
| License | MIT |
| Initial managed OS | Ubuntu 26.04 |
| Initial architectures | `amd64` and `arm64` |
| Minimum Ansible version | `ansible-core 2.20` |

Ubuntu 26.04 uses Python 3.14. `ansible-core 2.20` is the earliest release in
its published support matrix that supports Python 3.14 on managed nodes. This
minimum should be revisited if the supported platform or upstream Ansible
support policy changes.

The role should not start as an Ansible collection. A collection can be
considered later if the project gains multiple roles, modules, or plugins that
benefit from being released together.

## Initial scope

### The role manages

- A dedicated `openhands` service user and group.
- Node.js 24 or later, at an explicitly selected version.
- npm, supplied with Node.js.
- `uv`, at an explicitly selected version.
- `@openhands/agent-canvas`, at an explicitly selected version.
- Persistent data and workspace directories.
- A restricted environment file.
- A systemd service for full Agent Canvas.
- Docker conversation-runtime configuration.
- Membership of the service user in a configurable Docker access group.
- Read-only preflight validation of the external Docker installation.
- Service enablement, startup, restart, and local health verification.

### Consumers must provide

- Ubuntu 26.04 on `amd64` or `arm64`.
- A Python interpreter supported by the declared Ansible version.
- A functioning Docker Engine and daemon.
- A Docker socket/group access model usable by the service account.
- Networking, firewall, VPN, tunnel, reverse-proxy, DNS, and TLS policy.
- Model-provider credentials and OpenHands application-level secrets not
  explicitly modeled by the role.

### Initial non-goals

- Installing or reconfiguring Docker.
- Building conversation images on managed hosts.
- Publishing a project-owned conversation image before one is needed.
- Supporting operating systems other than Ubuntu 26.04.
- Supporting architectures other than `amd64` and `arm64`.
- Supporting backend-only Canvas mode.
- Supporting local or per-conversation-selectable execution modes.
- Managing a reverse proxy, Cloudflare Tunnel, Tailscale, firewall, DNS, or
  TLS certificates.
- Claiming hardened hostile multi-tenancy.
- Automatically following floating dependency versions.

## Deployment decisions

### Full Canvas only

The initial stable service interface runs full Agent Canvas: frontend and
backend together. Backend-only and frontend-only modes should not be exposed as
role modes until a concrete use case justifies the additional service and test
paths.

### Docker-only conversations

The initial role sets the conversation runtime to Docker. It should not expose
local, worktree, or user-selectable runtime modes initially.

This produces one clear security and lifecycle model and ensures that normal
conversation commands run inside dedicated Agent Server containers rather than
directly under the host service account.

### Docker is deliberately external

Docker installation is a host-wide policy decision. It affects package
repositories, daemon configuration, networking, storage, containerd,
firewalls, and privileged group membership. The role therefore validates the
Docker executable, daemon reachability, and service-user access, but does not
install or reconfigure Docker.

The initial `underturn` host already provisions Docker separately in `kotik`.

## Conversation image policy

The default conversation image should be an official versioned OpenHands Agent
Server `-golang` image:

```text
ghcr.io/openhands/agent-server:<exact-version>-golang
```

Do not use `latest-golang` or `main-golang` as the role default.

The official image is preferred over maintaining a project-owned image. A
custom image pipeline should be introduced only after a concrete requirement
shows that the official image is insufficient, for example:

- Its Go version is too old for required work.
- A required toolchain cannot reasonably be installed at conversation time.
- Startup-time preparation is too slow.
- An upstream architecture or runtime capability is missing.
- A controlled extension is needed for repeatable project workflows.

At the time this plan was written, the upstream OpenHands build workflow used
`golang:1.21-bookworm` for the `golang` variant and published native `amd64`
and `arm64` images. Both details are upstream implementation facts and must be
reverified when selecting the initial pinned image.

### Optional digest

The current variable design preference is:

```yaml
openhands_conversation_image: >-
  ghcr.io/openhands/agent-server:<exact-version>-golang
openhands_conversation_image_digest: ""
```

With no digest, the effective reference is the versioned tag. With a digest,
the role appends it:

```text
ghcr.io/openhands/agent-server:1.2.3-golang@sha256:...
```

Validation should reject malformed combinations, including an image containing
`@...` when `openhands_conversation_image_digest` is also set.

For a deployment supporting both architectures, the documented digest should
normally be the multi-architecture manifest digest. A platform-specific image
digest will work only for its corresponding architecture.

## Dependency installation and maintenance

Node.js, `uv`, and Agent Canvas are role-managed application prerequisites,
not consumer prerequisites.

General policy:

- Select explicit versions.
- Do not track `latest` automatically.
- Verify downloaded artifacts where upstream checksums are available.
- Install or change a component only when the configured version differs.
- Support deliberate upgrades and downgrades to the configured version.
- Restart Agent Canvas only when a relevant runtime or configuration change
  requires it.
- Produce zero changes on a second identical Ansible run.

### Node.js

The current preference is to install an official versioned Node.js archive
rather than run the NodeSource setup script or depend on old apt package
versions remaining available.

Expected architecture mapping:

| Ansible architecture | Node.js artifact suffix |
| --- | --- |
| `x86_64` | `linux-x64` |
| `aarch64` | `linux-arm64` |

A likely layout is a versioned installation beneath `/opt/openhands`, with a
stable symlink used by the service. The exact paths and update mechanics should
be proven in CI before being treated as final.

### uv

The current preference is to download an official versioned `uv` archive and
verify its published checksum, without piping an installer directly into a
shell.

Expected architecture mapping:

| Ansible architecture | uv artifact |
| --- | --- |
| `x86_64` | `uv-x86_64-unknown-linux-gnu.tar.gz` |
| `aarch64` | `uv-aarch64-unknown-linux-gnu.tar.gz` |

Upstream currently classifies Linux aarch64 as a Tier 2 platform: official
binaries are built, but upstream's complete test suite may not run there. The
role's native arm64 integration job should compensate by exercising the actual
installation and service path.

### Agent Canvas

Install an exact `@openhands/agent-canvas` npm package version into a dedicated
role-owned prefix rather than relying on the operating system's global npm
prefix or an interactive user's shell configuration.

A likely path is:

```text
/opt/openhands/agent-canvas
```

The systemd unit should use explicit executable paths and should not depend on
interactive shell startup files.

Exact Node.js, `uv`, Agent Canvas, and Agent Server image versions have not yet
been selected. They should be selected together with reproducible artifact
metadata and tested before becoming defaults.

## Service identity and filesystem layout

Current preferred defaults:

```yaml
openhands_service_user: openhands
openhands_service_group: openhands
openhands_docker_group: docker

openhands_data_dir: /var/lib/openhands
openhands_workspace_dir: /srv/openhands/workspaces
```

The service account should:

- Use `/var/lib/openhands` as its home/data area unless testing shows a better
  separation is required.
- Have no interactive login shell.
- Own only the paths needed by Agent Canvas.
- Receive no general sudo privileges.
- Be added to the configured Docker group when needed.

Docker group access is effectively host-privileged access. This must be stated
prominently in user documentation rather than presented as ordinary low-risk
group membership.

## Network and authentication defaults

Current preferred defaults:

```yaml
openhands_bind_host: "127.0.0.1"
openhands_port: 8000
openhands_public: false
openhands_backend_api_key: ""
```

Expected validation and behavior:

- Public mode requires a non-empty, high-entropy backend API key.
- Secret-bearing tasks use `no_log: true` and suppress diffs where needed.
- The environment file has restrictive ownership and permissions.
- The role never opens firewall ports.
- The role never assumes that a public listener is safe merely because
  conversation execution uses containers.
- Reverse proxies and tunnels may target the loopback listener but remain the
  consumer's responsibility.

The exact relationship between Agent Canvas's `--public` option, bind address,
authentication, and reverse-proxy behavior must be verified against the pinned
Canvas version in integration tests.

## Preliminary public variable interface

The exact interface is not final, but the current direction is a flat,
`openhands_`-prefixed API validated by `meta/argument_specs.yml`.

```yaml
# Versions and installation
openhands_node_version: "<exact-version>"
openhands_uv_version: "<exact-version>"
openhands_agent_canvas_version: "<exact-version>"

# Service identity
openhands_service_user: openhands
openhands_service_group: openhands
openhands_docker_group: docker

# Listener and authentication
openhands_bind_host: "127.0.0.1"
openhands_port: 8000
openhands_public: false
openhands_backend_api_key: ""

# Persistence
openhands_data_dir: /var/lib/openhands
openhands_workspace_dir: /srv/openhands/workspaces

# Docker conversation runtime
openhands_conversation_image: >-
  ghcr.io/openhands/agent-server:<exact-version>-golang
openhands_conversation_image_digest: ""
openhands_conversation_memory: 4g
openhands_conversation_cpus: "2.0"
openhands_conversation_pids_limit: 512
openhands_conversation_startup_timeout: 120
openhands_conversation_idle_ttl_seconds: 1200

# Escape hatch for documented settings not modeled yet
openhands_extra_environment: {}
```

Important settings should receive dedicated variables. The extra environment
mapping is an escape hatch, not a substitute for designing a stable interface.

Expected validation includes:

- Paths are absolute.
- Ports and numeric limits are positive and within sensible ranges.
- Public mode requires an API key.
- Docker runtime requires a conversation image.
- A supplied digest has valid `sha256:` syntax.
- The selected architecture is supported.
- User-supplied environment entries do not silently override role-managed
  security-critical settings without an explicit policy.

## CI-first implementation strategy

CI must exist and pass before the role performs meaningful changes to a target
machine.

GitHub Actions provides native `ubuntu-26.04` and `ubuntu-26.04-arm` runners,
so integration tests should run on real ephemeral VMs rather than emulate
systemd and Docker through nested privileged containers.

### Quality job

Run once, normally on amd64:

- `yamllint`.
- `ansible-lint`, preferably with the production profile.
- Role metadata and argument-spec validation.
- Example playbook syntax checks.
- Documentation checks added by the project.

Development and CI dependencies should be locked, currently expected through
`uv`, so local and CI commands use the same tool versions.

### Ansible compatibility job

Test at least:

- The declared minimum `ansible-core` release.
- The current project-pinned supported release.

Parser and interface compatibility can initially run on amd64 if full runtime
coverage is handled by the architecture matrix. Before releases, running the
full Ansible-version by architecture cross-product may provide stronger
confidence.

### Native architecture integration matrix

The integration matrix should include:

| Runner | Architecture |
| --- | --- |
| `ubuntu-26.04` | amd64 |
| `ubuntu-26.04-arm` | arm64 |

The first, no-op role milestone should already use this shape so later work
extends an existing matrix instead of redesigning CI.

As implementation grows, both jobs should verify:

- Initial convergence.
- A second idempotent run.
- Correct architecture-specific artifact selection.
- Installed Node.js, npm, `uv`, and Agent Canvas versions.
- Service account, files, directories, owners, groups, and modes.
- systemd enablement and service health.
- Docker access from the service account.
- Pulling and running the selected native OpenHands `-golang` image.
- `go version` inside the conversation image.
- Agent Server startup and health.
- Eventually, one complete conversation-container lifecycle.

The CI should use the same effective image reference, including an optional
digest, that the role renders for production.

### GitHub Actions security

- Pin third-party actions by commit SHA.
- Grant the minimum workflow permissions.
- Do not grant package publication permissions while no project image is
  published.
- Avoid passing secrets as command-line arguments or Docker build arguments.

## Planned implementation milestones

Each milestone is treated like a conceptual pull request, even though the
current working preference is to commit directly to `master`. A milestone may
contain more than one commit when that produces clearer, independently useful
history. Every completed milestone should leave the branch passing its relevant
checks.

### Milestone 1 — Repository contract and CI

- Add the standalone role skeleton.
- Add locked development dependencies.
- Add lint and syntax configuration.
- Add a no-op Molecule/delegated integration scenario.
- Add native amd64 and arm64 CI jobs.
- Add an official-image contract smoke test.
- Add contribution and development documentation.

No meaningful managed-host changes should occur in this milestone.

### Milestone 2 — Public interface and read-only preflight

- Draft `defaults/main.yml`.
- Mirror public variables in `meta/argument_specs.yml`.
- Add cross-variable assertions.
- Check Docker executable and daemon availability without installing Docker.
- Add minimal example usage.
- Test valid and invalid configuration.

This milestone should still avoid meaningful target mutation.

### Milestone 3 — Service identity and persistence

- Create the service group and user.
- Create data and workspace directories.
- Configure Docker group membership.
- Verify ownership, permissions, convergence, and idempotence.

### Milestone 4 — Managed application prerequisites

- Install pinned Node.js for both architectures.
- Install pinned `uv` for both architectures.
- Install pinned Agent Canvas into its dedicated prefix.
- Verify checksums and installed versions.
- Exercise upgrades and downgrades where practical.

### Milestone 5 — Configuration and systemd service

- Render the restricted environment file.
- Render the systemd unit.
- Add daemon-reload and restart handlers.
- Enable and start full Agent Canvas.
- Verify local health and version output.
- Verify that unchanged runs do not restart the service.

### Milestone 6 — Docker conversation execution

- Configure Docker-only conversations.
- Use the pinned official `-golang` image.
- Verify Docker access as the service account.
- Exercise image pulling and native architecture selection.
- Start and health-check a conversation Agent Server container.
- Verify persistence and idle shutdown behavior.

### Milestone 7 — Release-quality coverage and documentation

- Complete failure-path tests for absent or inaccessible Docker.
- Add realistic upgrade coverage.
- Complete security, configuration, troubleshooting, and upgrade docs.
- State the exact supported OS, architectures, Ansible versions, and pinned
  application versions.
- Prepare the first `0.x` release and Galaxy publication only after the role
  has been exercised on `underturn`.

### Deferred milestone — Custom conversation images

Only add a custom-image pipeline after documenting a demonstrated gap in the
official image. If added later, custom images should extend a pinned official
Agent Server image, retain its entrypoint and runtime contract, run as the
expected non-root user, and be built and published only in CI.

## Development workflow

The current operator preference is:

- Work directly on `master`.
- Represent each conceptual PR with one or more coherent commits.
- Keep commits testable and suitable for `git bisect` where practical.
- Inspect the diff, status, untracked files, and staged content before each
  commit.
- Do not mix unrelated milestone work into the same commit.

Commit subjects are expected to follow a simple conventional style, for
example:

```text
ci: establish role quality gates
feat: define the role configuration contract
feat: provision the OpenHands service account
feat: install Agent Canvas prerequisites
feat: manage the Agent Canvas systemd service
feat: enable Docker conversation runtimes
test: add end-to-end conversation coverage
```

## Security assumptions

> This is trusted single-user or trusted-team infrastructure, not a hardened
> hostile multi-tenant platform.

- Docker daemon access is effectively host-root access.
- The Agent Canvas host process is trusted infrastructure.
- Conversation containers improve isolation but do not make arbitrary host
  mounts or Docker access safe.
- Writable bind-mounted workspaces can be modified by agents and tools.
- Model credentials and backend API keys must not appear in role defaults,
  images, logs, diffs, or source control.
- A remotely reachable Canvas deployment requires authentication plus an
  external access-control layer such as a VPN or authenticated reverse proxy.
- The role must not silently expose ports or weaken host firewall policy.
- Image tags without digests can theoretically be moved by the publisher; the
  optional digest exists for users requiring stronger immutability.

## Important open questions

These should be answered with current evidence when their milestone begins,
not guessed permanently now:

- Which exact Node.js 24 release should be the first default?
- Which exact `uv` release should be the first default?
- Which exact Agent Canvas release should be the first default?
- Which exact official Agent Server `-golang` tag should be paired with it?
- Should CI lock the current Ansible release alongside the declared 2.20
  minimum, and when should that lock be updated?
- What exact command-line flags and environment variables are required by the
  pinned Agent Canvas release for full Canvas, Docker-only conversations,
  loopback binding, and authenticated public mode?
- Should Node.js use official archives as currently preferred, or does a
  manually configured and pinned apt source provide a better maintenance
  trade-off on Ubuntu 26.04?
- Which systemd hardening directives are compatible with Docker access,
  workspace writes, npm-installed Canvas assets, and `uv` execution?
- What health endpoint and readiness criteria are stable for the pinned Canvas
  and Agent Server versions?
- How should generated variable documentation be kept synchronized with
  `meta/argument_specs.yml`?
- When should the complete Ansible-version by architecture test matrix run:
  every pull request/commit, scheduled, or only before releases?

## Upstream references

These links describe upstream behavior but should be rechecked because OpenHands
and its dependencies evolve quickly:

- OpenHands per-conversation Docker execution:
  <https://docs.openhands.dev/openhands/usage/agent-canvas/backend-setup/docker-execution>
- OpenHands VM/self-hosted Agent Canvas installation:
  <https://docs.openhands.dev/openhands/usage/agent-canvas/backend-setup/vm>
- OpenHands Agent Server image workflow:
  <https://github.com/OpenHands/software-agent-sdk/blob/main/.github/workflows/server.yml>
- OpenHands custom sandbox image guidance:
  <https://docs.openhands.dev/enterprise/custom-sandbox-images/building-custom-images>
- Ansible release and Python support matrix:
  <https://docs.ansible.com/projects/ansible-core/devel/reference_appendices/release_and_maintenance.html>
- GitHub-hosted runner reference:
  <https://docs.github.com/en/actions/reference/runners/github-hosted-runners>
- Node.js release downloads:
  <https://nodejs.org/download/release/>
- uv platform support:
  <https://docs.astral.sh/uv/reference/policies/platforms/>
