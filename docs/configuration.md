# Configuration

The public role interface consists of the `openhands_` variables declared in
`roles/agent_canvas/defaults/main.yml` and described by
`roles/agent_canvas/meta/argument_specs.yml`. The role
validates the complete interface before making managed-host changes.

This document explains relationships and operational consequences that do not
fit into one-line variable comments. `roles/agent_canvas/defaults/main.yml`
remains the source of truth for exact default values.

## Supported deployment

The initial supported deployment is deliberately narrow:

| Item | Supported value |
| --- | --- |
| Managed operating system | Ubuntu 26.04 |
| Managed architectures | native amd64 and arm64 |
| Minimum controller version | `ansible-core 2.20` |
| Service manager | systemd |
| Conversation runtime | Docker only |
| Agent Canvas mode | full frontend and backend |

Docker Engine must already be installed, running, and usable through the host's
configured Docker access group. This role does not install Docker, configure its
daemon, open firewall ports, manage DNS or TLS, or install a reverse proxy.

## Pinned application stack

The role defaults to explicit versions rather than following floating releases:

| Component | Default |
| --- | --- |
| Node.js | `24.11.1` |
| uv and uvx | `0.9.30` |
| OpenHands Agent Canvas | `1.43.0` |
| Conversation image | `ghcr.io/openhands/agent-server:rel-1.62.0-golang` |

Node.js and uv have optional architecture-specific SHA-256 checksum variables.
Agent Canvas has an optional SHA-512 checksum for its npm archive. All five
default to empty, so prerequisite downloads use their exact versioned URLs
without digest verification. A non-empty checksum enables verification for that
artifact and must use the expected lowercase hexadecimal format.

The role verifies the installed executable versions after installation, but a
version check is not a substitute for cryptographic content verification. Set
checksums when deployment policy requires downloaded content to be pinned.

### Obtaining prerequisite checksums

Checksums for a configured version are available from these upstream artifacts:

- Node.js publishes `SHASUMS256.txt` in each
  [release directory](https://nodejs.org/download/release/). Use the
  `linux-x64.tar.gz` value for `openhands_node_checksum_x86_64` and the
  `linux-arm64.tar.gz` value for `openhands_node_checksum_aarch64`.
- uv publishes a `.sha256` sidecar for every archive on its
  [GitHub release](https://github.com/astral-sh/uv/releases) page. The role uses
  the `x86_64-unknown-linux-gnu` and `aarch64-unknown-linux-gnu` archives.
- Agent Canvas publishes its versioned npm archive through the
  [npm registry](https://www.npmjs.com/package/@openhands/agent-canvas). Hash
  that exact archive with SHA-512 for `openhands_agent_canvas_checksum`.

The following copy-pasteable commands print the five checksum assignments in
role-variable format. Set the three versions first:

```sh
NODE_VERSION=24.11.1
UV_VERSION=0.9.30
AGENT_CANVAS_VERSION=1.43.0

NODE_SHASUMS="$(
  curl -fsSL \
    "https://nodejs.org/download/release/v${NODE_VERSION}/SHASUMS256.txt"
)"
printf '%s\n' "$NODE_SHASUMS" | awk \
  -v file="node-v${NODE_VERSION}-linux-x64.tar.gz" \
  '$2 == file { print "openhands_node_checksum_x86_64: " $1 }'
printf '%s\n' "$NODE_SHASUMS" | awk \
  -v file="node-v${NODE_VERSION}-linux-arm64.tar.gz" \
  '$2 == file { print "openhands_node_checksum_aarch64: " $1 }'

for arch in x86_64 aarch64; do
  printf 'openhands_uv_checksum_%s: ' "$arch"
  curl -fsSL \
    "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${arch}-unknown-linux-gnu.tar.gz.sha256" \
    | awk '{ print $1 }'
done

printf 'openhands_agent_canvas_checksum: '
curl -fsSL \
  "https://registry.npmjs.org/@openhands/agent-canvas/-/agent-canvas-${AGENT_CANVAS_VERSION}.tgz" \
  | python3 -c \
    'import hashlib, sys; print(hashlib.sha512(sys.stdin.buffer.read()).hexdigest())'
```

Review that all five commands produced non-empty hexadecimal values before
copying them into inventory, group variables, or another deployment-specific
configuration source. You may configure only the architectures you deploy;
an empty checksum skips verification on that architecture. The filenames and
algorithms must continue to match the download URLs in `roles/agent_canvas/vars/main.yml` and
`roles/agent_canvas/tasks/prerequisites.yml` if the installation layout changes.

The role installs managed prerequisites below `/opt/openhands` and exposes
stable internal paths:

```text
/opt/openhands/node
/opt/openhands/uv/uv
/opt/openhands/uv/uvx
/opt/openhands/agent-canvas
```

Versioned artifacts remain below the installation prefix. Stable paths are
updated to the configured release and relevant changes notify the OpenHands
service restart handler.

## Basic usage

A minimal private deployment is:

```yaml
---
- name: Deploy OpenHands Agent Canvas
  hosts: openhands_hosts
  become: true
  roles:
    - role: nietaki.openhands.agent_canvas
      vars:
        openhands_docker_group: docker
        openhands_public: false
```

This binds Agent Canvas to `127.0.0.1:8000`, creates the `openhands` service
identity, installs the pinned application stack, prepares the official
conversation image, and manages the systemd service.

## Installation and service switches

### `openhands_install_prerequisites`

When `true`, the role installs and verifies Node.js, uv, uvx, and Agent Canvas.
The managed target must be Linux on `x86_64` or `aarch64`.

Set it to `false` only when the configured executable paths already satisfy the
role's service contract or when running a deliberately non-production test.
The role does not provide variables for relocating the internal installation
prefix.

### `openhands_manage_service`

When `true`, the role:

- ensures the effective conversation image is locally available;
- validates that its architecture matches the managed host;
- writes the environment file and systemd unit;
- enables and starts `openhands.service`;
- verifies the Agent Canvas version and local HTTP health.

Setting it to `false` skips conversation-image preparation and all systemd
management. Persistence directories are still managed.

### `openhands_manage_service_identity`

When `true`, the role creates the service group and system user and adds the
user to `openhands_docker_group`. If disabled, the named user and group must
already exist and have the required permissions.

## Docker access and preflight

The relevant variables are:

```yaml
openhands_docker_executable: docker
openhands_docker_group: docker
openhands_docker_preflight_enabled: true
```

With preflight enabled, the role runs `docker --version` and `docker info`
before creating users, directories, or installing prerequisites. This catches a
missing executable or unreachable daemon early.

The initial preflight runs as the Ansible execution user. When service
management is enabled, conversation-image inspection and pulling run as the
OpenHands service user, which also verifies that the runtime identity can use
the daemon.

Membership in the Docker group is effectively host-root-equivalent access. It
must be treated as a privileged trust boundary, not as an ordinary application
permission. The role is intended for trusted single-user or trusted-team
infrastructure, not hostile multi-tenancy.

Disabling preflight is useful for safe contract tests but is not recommended for
normal deployments.

## Service identity and filesystem paths

Defaults:

```yaml
openhands_service_user: openhands
openhands_service_group: openhands
openhands_data_dir: /var/lib/openhands
openhands_workspace_dir: /srv/openhands/workspaces
```

The service account is a system user with `/usr/sbin/nologin`. The data and
workspace directories are owned by the service account and use mode `0750`.
Conversation workspaces are bind-mounted into Docker containers and can be
modified by agents and their tools.

Both configured paths must be absolute and cannot be `/`. Changing paths after
a deployment does not migrate existing data; plan and perform any filesystem
migration separately.

The role also manages:

```text
/etc/openhands/agent-canvas.env
/etc/systemd/system/openhands.service
```

The environment file is owned by `root:<service-group>` with mode `0640`. The
systemd unit is root-owned with mode `0644`.

## Listener and authentication

Private defaults:

```yaml
openhands_bind_host: "127.0.0.1"
openhands_port: 8000
openhands_public: false
openhands_backend_api_key: ""
```

With `openhands_public: false`, the bind host must be a loopback address. The
role does not expose the service through a firewall, reverse proxy, VPN, tunnel,
DNS record, or TLS endpoint.

A non-loopback bind requires `openhands_public: true`. Public mode also requires
an API key of at least 32 characters:

```yaml
openhands_bind_host: "0.0.0.0"
openhands_public: true
openhands_backend_api_key: "{{ vault_openhands_backend_api_key }}"
```

Length validation is not an entropy guarantee. Generate a random secret and
store it in Ansible Vault or another secret-management system. Do not commit it
to inventory or pass it as a command-line extra variable where process or shell
history could expose it.

Public mode is not a complete internet-exposure policy. Use an authenticated
reverse proxy, VPN, or equivalent external access-control layer and manage TLS
outside this role.

## Health checks

Defaults:

```yaml
openhands_health_retries: 12
openhands_health_delay: 5
```

After pending handlers are applied, the role requests the local Agent Canvas
root URL until it returns HTTP 200. The defaults allow roughly one minute for
startup. Increase them on slower hosts or after introducing slower startup-time
configuration.

For wildcard bind addresses such as `0.0.0.0` or `::`, the role probes the
corresponding loopback address rather than the wildcard address.

## Conversation image

Defaults:

```yaml
openhands_conversation_image: >-
  ghcr.io/openhands/agent-server:rel-1.62.0-golang
openhands_conversation_image_digest: ""
```

The role accepts exact official OpenHands Agent Server `-golang` tags and
rejects an image value that already contains `@...`. When a digest is supplied,
the effective reference is:

```text
<image-tag>@sha256:<digest>
```

For a deployment supporting both architectures, use the multi-architecture
manifest digest rather than a platform-specific child-manifest digest.

The role first inspects the exact effective reference as the service user. It
pulls only when that reference is absent, which supports idempotent runs and
preloaded or offline hosts. Afterward it verifies that Docker selected an image
matching the host architecture.

The unusual `rel-1.62.0-golang` default is intentional. Upstream's final
`1.62.0-golang` tag was built from its Python/Node base and does not contain Go.
The release-branch image uses the intended `golang:1.21-bookworm` base and is
validated on native amd64 and arm64 by this project's integration tests.

A registry tag can theoretically move. Set the optional digest when deployment
policy requires immutable image content. If overriding the image, supply a
digest belonging to that image or leave the digest empty.

## Conversation resource limits

Defaults:

```yaml
openhands_conversation_memory: 4g
openhands_conversation_cpus: "2.0"
openhands_conversation_pids_limit: 512
openhands_conversation_startup_timeout: 120
openhands_conversation_idle_ttl_seconds: 1200
```

These values are passed to Agent Canvas and apply to individual conversation
containers:

- memory uses a positive Docker-style unit such as `4g` or `4096m`;
- CPUs is a positive numeric string and may be fractional;
- PID limit must be positive;
- startup timeout must be positive;
- idle TTL may be zero if upstream semantics for disabling or immediate expiry
  are intentionally desired.

Choose limits based on the expected tools and workloads. Resource limits reduce
accidental host exhaustion but do not turn Docker daemon access into a safe
multi-tenant boundary.

## Extra environment variables

`openhands_extra_environment` is an escape hatch for Agent Canvas settings that
do not yet justify a dedicated public variable:

```yaml
openhands_extra_environment:
  LOG_LEVEL: INFO
```

Keys must be valid environment-variable names. The role rejects keys it manages
directly, including listener, authentication, runtime, image, resource, idle
TTL, secret-key, and workspace settings. This prevents the mapping from
silently overriding role policy.

Prefer dedicated variables for stable or security-sensitive settings. Values
are written to the restricted environment file, and the rendering task hides
its diff and output, but inventory and external logging still need appropriate
secret handling.

## Configuration validation

`roles/agent_canvas/meta/argument_specs.yml` validates variable types.
`roles/agent_canvas/tasks/main.yml` performs
cross-variable and format checks before managed-host mutation, including:

- semantic version formats and optional checksum syntax and lengths;
- Unix user and group names;
- listener and public-mode authentication relationships;
- absolute persistence paths;
- official conversation-image and digest syntax;
- positive resource and health-check values;
- valid and non-reserved extra environment names.

For a portable validation pass, use the contract tests described in
[`testing.md`](testing.md). The complete native deployment path is exercised by
the persistence scenario in CI.

## Upgrades

Application versions are configuration, not floating dependencies. Upgrade them
through a reviewed change and run native integration before deployment. If your
deployment configures checksums, update each checksum with its version or clear
it explicitly to use version-only installation.

The repository does not yet claim automated previous-release migration
coverage because no released and production-exercised baseline exists. The
future upgrade scenario will provision the previous released collection before
applying a candidate release. Until then, back up persistent data and review
release changes before changing pinned versions or deploying a newer collection.
