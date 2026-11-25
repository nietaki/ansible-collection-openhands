# nietaki.openhands

An Ansible collection containing the `agent_canvas` role.

Deploy OpenHands Agent Canvas as a native systemd service with Dockerized
conversations on Ubuntu 26.04.

## Supported deployment

| Item | Supported value |
| --- | --- |
| Managed operating system | Ubuntu 26.04 |
| Managed architectures | amd64 and arm64 |
| Minimum Ansible version | `ansible-core 2.20` |
| Service | Full OpenHands Agent Canvas under systemd |
| Conversation runtime | Docker |

Docker must already be installed and configured. The role validates Docker
availability and access but does not install Docker, configure its daemon, or
manage host networking, firewalls, DNS, TLS, tunnels, or reverse proxies.

Docker group membership is effectively host-root-equivalent access. This role
is intended for trusted single-user or trusted-team infrastructure, not hostile
multi-tenancy.

## Default application stack

The role uses reviewed, explicit versions:

| Component | Default |
| --- | --- |
| Node.js | `24.11.1` |
| uv | `0.9.30` |
| Agent Canvas | `1.43.0` |
| Agent Server image | `rel-1.62.0-golang` |

Prerequisite downloads use exact versioned URLs by default. Optional SHA-256
and SHA-512 variables enable checksum verification when deployment policy
requires content pinning. The conversation image is verified on both native
supported architectures.

## Install

After the collection is published, install it from Ansible Galaxy:

```console
ansible-galaxy collection install nietaki.openhands
```

The role's fully qualified collection name (FQCN) is
`nietaki.openhands.agent_canvas`. For development from a checkout, run
`make collection-install` to build and install the local collection artifact.

## Example

```yaml
---
- name: Deploy OpenHands Agent Canvas
  hosts: openhands_hosts
  become: true
  roles:
    - role: nietaki.openhands.agent_canvas
      vars:
        # Docker Engine and this access group must already exist.
        openhands_docker_group: docker
        openhands_public: false
```

The private default listens on `127.0.0.1:8000`. Public mode requires an
explicit non-loopback bind address and a backend API key of at least 32
characters; external access control and TLS remain the consumer's
responsibility.

See [`examples/main.yml`](examples/main.yml) for the repository example.

## Documentation

- [`roles/agent_canvas/README.md`](roles/agent_canvas/README.md) — role behavior
  and the components it manages.
- [`docs/configuration.md`](docs/configuration.md) — supported deployment,
  variables, security implications, paths, images, resources, and upgrades.
- [`docs/backups.md`](docs/backups.md) — persistent data layout, backup scope,
  consistency, and restore considerations.
- [`docs/testing.md`](docs/testing.md) — test layers, commands, CI jobs,
  scenarios, diagnostics, and guidance for adding coverage.
- [`docs/development.md`](docs/development.md) — development environment and
  repository workflow.

## Development

Install the locked development environment and run the workstation-safe checks:

```console
uv sync --locked
make check
```

The privileged persistence and Docker lifecycle scenario is intentionally not
part of `make check`. See [`docs/testing.md`](docs/testing.md) before running it
on a disposable Ubuntu host.

## License

MIT. See [`LICENSE`](LICENSE).
