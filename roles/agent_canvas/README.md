# `nietaki.openhands.agent_canvas`

The `agent_canvas` role in the `nietaki.openhands` collection deploys OpenHands
Agent Canvas as a native systemd service with Dockerized conversation
containers on Ubuntu 26.04. Its fully qualified collection name (FQCN) is
`nietaki.openhands.agent_canvas`.

This page summarizes the role's behavior and the components it manages. See the
[collection README](../../README.md) for installation and an invocation example,
the [configuration guide](../../docs/configuration.md) for the full variable
reference, and the [backup guide](../../docs/backups.md) for checkpoint and
restore details.

## What the role does

The role installs and runs Agent Canvas directly on the managed host as a
native systemd service. Docker is used only for the per-conversation Agent
Server containers; Agent Canvas itself does not run in the conversation image.

The default `state: present` installs or configures the deployment. Set
`state: absent` to stop and disable the managed services, stop running
conversation containers carrying the `ai.openhands.runtime-owner` label, and
remove the role-managed software and service files. This preserves the data,
workspace, and backup directories, the service user and group, and Docker
images. Stopped containers are retained unless `openhands_remove_containers: true`
is set; that option removes all matching containers, including those already
stopped, and deletes their container writable layers. If Docker cleanup fails,
the role continues uninstalling its software and service files, then reports a
failure so container cleanup can be retried.

### Validate configuration

Before changing the managed host, the role validates its complete public
interface. This includes variable types, versions and optional checksums, Unix
account names, absolute filesystem paths, listener and public-mode settings,
conversation image references, resource limits, and extra environment variable
names. Artifact checksums and the conversation image digest remain optional, so
interface validation alone does not provide cryptographic content verification.

### Check Docker readiness (optional)

By default, the role runs `docker --version` and `docker info` on the target as
the Ansible execution user before making managed-host changes. The check is
controlled by `openhands_docker_preflight_enabled`, and
`openhands_docker_executable` selects the command or absolute path to use. Later
image operations run as the service user, which also verifies that the runtime
identity can access the daemon.

The role does not install Docker, configure its daemon, or create the Docker
access group. Docker Engine must already be installed, running, and usable on
the target host.

### Install the application toolchain (optional)

With `openhands_install_prerequisites` enabled, the role downloads, installs,
and verifies pinned releases of Node.js, uv, uvx, and Agent Canvas on the target
host. Their versions and optional architecture-specific checksums are
configurable. Stable paths are `/opt/openhands/node`,
`/opt/openhands/uv/uv`, `/opt/openhands/uv/uvx`, and
`/opt/openhands/agent-canvas`; downloaded and versioned artifacts also remain
below `/opt/openhands`.

These tools are installed on the host, not in the conversation image. The
installation prefix is not currently configurable. If prerequisite installation
is disabled while service management remains enabled, compatible executables
must already be present at the paths expected by the role.

### Manage the service identity and Docker access (optional)

With `openhands_manage_service_identity` enabled, the role idempotently creates
the system group and system user selected by `openhands_service_group` and
`openhands_service_user`. The user has `/usr/sbin/nologin`, uses the configured
data directory as its home path, and is appended to `openhands_docker_group`.
The systemd unit also grants that group through `SupplementaryGroups`.

The role creates the service group, but it does not create the configured
Docker access group. If identity management is disabled, the named service user
and group, their Docker access, and the necessary permissions must already be
set up. Membership in the Docker group is effectively host-root-equivalent
access.

### Prepare persistent data and workspaces

The role creates `openhands_data_dir` and `openhands_workspace_dir` on the
target host, defaulting to `/var/lib/openhands` and
`/srv/openhands/workspaces`. They are owned by the service identity with mode
`0750`. The data directory is also the service working directory and `HOME`;
conversation workspaces are kept on the host and bind-mounted into containers.

These directories are managed even when prerequisite installation or service
management is disabled. Changing either path does not migrate existing data;
plan and perform filesystem migration separately.

### Create pre-upgrade checkpoints

Pre-upgrade checkpoints are enabled by default. Before changing the Agent
Canvas version on an existing installation, the role stops the service and any
remaining active OpenHands conversation containers, then writes the complete
data directory to a root-only archive under `/var/backups/openhands`. Same-
version runs and fresh installations do not create archives. A failed required
checkpoint aborts before application changes.

Workspace contents are excluded by default to limit archive size. Set
`openhands_backup_include_workspaces: true` to include them. The archive stays
on the same host, and old archives are not automatically pruned; this is a
rollback checkpoint, not disaster recovery. Restore is a manual operation that
must pair the checkpoint with the previous software configuration.

```yaml
openhands_backup_enabled: true
openhands_backup_dir: /var/backups/openhands
openhands_backup_include_workspaces: false
```

See [`docs/backups.md`](docs/backups.md) for archive verification, security,
retention, and restore instructions.

### Prepare the conversation image (optional)

When `openhands_manage_service` is enabled, the role inspects the exact
configured image reference in the target host's Docker daemon as the service
user. It pulls the image only when that reference is absent, then verifies that
Docker selected an image matching the host architecture. The image tag is set
with `openhands_conversation_image`, and
`openhands_conversation_image_digest` can pin its manifest digest.

The role accepts any non-empty, whitespace-free Docker image reference; it
does not build, modify, or configure software inside the image. Because an
already-present tag is not pulled again, use a digest when deployment policy
requires immutable image content.

### Configure conversation containers (optional)

The role writes Docker conversation policy into the Agent Canvas environment.
Agent Canvas later creates containers on demand when conversations begin;
Ansible does not create a permanent conversation container during provisioning.
The runtime is fixed to Docker and runtime selection is disabled.

The main controls are the conversation image, per-container memory, CPU and PID
limits, startup timeout, idle-container TTL, and the host workspace directory.
These limits reduce accidental host exhaustion, but Docker daemon access is not
a safe boundary for hostile multi-tenancy.

### Run Agent Canvas under systemd (optional)

With `openhands_manage_service` enabled, the role renders the restricted
environment file at `/etc/openhands/agent-canvas.env` and the unit at
`/etc/systemd/system/openhands.service`. It validates the unit, enables and
starts the service, restarts it after relevant managed changes, verifies the
Agent Canvas version, and waits for the local HTTP endpoint to become healthy.
Startup polling is controlled by `openhands_health_retries` and
`openhands_health_delay`.

Set `openhands_capture_runtime_logs: true` to independently enable the
`openhands-runtime-logs.service`. The role installs its script in
`openhands_data_dir`; the service follows newly started conversation containers
with the OpenHands runtime-owner label and writes timestamped, container-ID-
prefixed lines to journald. View them with
`journalctl -u openhands-runtime-logs.service -f`. Capture is best-effort: logs
may be missed if a short-lived container disappears before Docker attaches the
log follower. The journal may contain sensitive conversation output.

`openhands_extra_environment` can add non-reserved Agent Canvas settings to the
environment file. Disabling `openhands_manage_service` skips Agent Canvas
service management and conversation-image preparation. Runtime log capture is
managed independently by `openhands_capture_runtime_logs`; persistent
directories are still created.

### Configure access to Agent Canvas (optional)

The private default listens on `127.0.0.1:8000`, controlled by
`openhands_bind_host` and `openhands_port`. A non-loopback bind address requires
`openhands_public: true`; public mode also requires an
`openhands_backend_api_key` of at least 32 characters.

The role configures the Agent Canvas listener and its backend API key, but it
does not manage firewall rules, TLS, DNS, reverse proxies, VPNs, tunnels, or
external access control. Public mode is therefore not, by itself, a complete
internet-exposure policy.
