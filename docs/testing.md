# Testing

This project uses several complementary testing mechanisms. No single check can
cover an Ansible role that downloads architecture-specific artifacts, creates a
system account, manages systemd, talks to Docker, and starts real OpenHands
conversation containers.

The test suite is therefore layered from fast, portable checks to privileged
native integration tests.

## Quick start

Install the locked development environment and run the workstation-safe suite:

```console
uv sync --locked
make check
```

`make check` builds and installs the collection artifact locally, then runs
linting, contract tests, and the default Molecule scenario. This verifies the
role through its collection FQCN and packaged files. It is designed to be safe
on developer workstations, including macOS. It does not install OpenHands,
create a service account, manage systemd, or require Docker.

The full persistence scenario is separate and has explicit checksum modes:

```console
make molecule-persistence-version-only
make molecule-persistence-verified
```

`make molecule-persistence` remains a convenience alias for the version-only
mode, matching the role defaults.

The scenario is intended for a disposable Ubuntu 26.04 host with passwordless
privilege escalation, systemd, and a working Docker installation. It should
not be run on a normal workstation without first reviewing the scenario and
its cleanup playbook.

## Test layers

| Layer | Main command | Purpose | Typical environment |
| --- | --- | --- | --- |
| Collection packaging | `make collection-install` | Build and install the local collection artifact | Any development host |
| YAML lint | `make lint-yaml` | YAML syntax and formatting | Any development host |
| Ansible lint | `make lint` | Ansible correctness and production-profile conventions | Any development host |
| Contract tests | `make test` | Public interface, validation, templates, and failure paths | Any development host |
| Default Molecule scenario | `make molecule` | Safe role loading, convergence, and idempotence | Any development host |
| Ansible compatibility | CI only | Syntax and safe convergence across supported Ansible versions | Ubuntu amd64 |
| Version-only persistence | `make molecule-persistence-version-only` | Real installation without download checksums | Disposable Ubuntu host |
| Verified persistence | `make molecule-persistence-verified` | Real installation with download checksums | Disposable Ubuntu host |
| Native architecture matrix | CI only | Both checksum modes on native amd64 and arm64 | GitHub-hosted Ubuntu runners |

## Linting and static checks

The repository uses:

- `yamllint` for YAML formatting and syntax;
- `ansible-lint` with the production profile for Ansible-specific checks;
- `ansible-playbook --syntax-check` for the example collection role invocation;
- collection build and installation from the repository artifact.

The relevant files are:

- `.yamllint.yml` — YAML rules;
- `.ansible-lint` — Ansible lint configuration;
- `tests/fixtures/syntax.yml` — syntax-check entry point;
- `Makefile` — local command definitions;
- `pyproject.toml` and `uv.lock` — locked development toolchain.

Run both linters with:

```console
make lint
```

## Contract tests

Contract tests are Python `unittest` tests under `tests/contract/`. They launch
small Ansible fixtures or validate repository-level policies. The pre-upgrade
checkpoint transaction test needs passwordless root escalation and is skipped
on workstations that cannot provide it.

### Public interface tests

`tests/contract/test_interface.py` executes playbooks from `tests/fixtures/` and
checks that:

- valid role configuration is accepted;
- invalid public-mode and health-check configuration is rejected;
- floating conversation-image tags are rejected by the role interface;
- a missing Docker executable fails before managed-host mutation;
- an executable with an inaccessible Docker daemon fails before mutation;
- the rendered systemd unit preserves directive boundaries.

The Docker failure fixtures deliberately use an impossible executable path or a
small fake executable. They test the role's failure behavior without talking to
the developer's real Docker daemon.

### Pre-upgrade checkpoint tests

`tests/contract/test_backup.py` creates temporary persistence roots and a small
fake Agent Canvas executable that reports a selected version. It exercises the
production backup task file with a fake Docker executable that reports no
running containers. The scenarios verify that fresh and same-version runs do
not checkpoint, while a version mismatch or an unknown/missing installed
version with existing data does. For created archives, the fixture checks data
members, default workspace exclusion and opt-in inclusion, the SHA-256
sidecar, root ownership and private modes, and the version context in the
archive filename.

The archive tests use the real system `tar` and `sha256sum`. They run with
passwordless `sudo` where available; otherwise they are skipped so `make check`
remains usable on developer workstations. CI's Ubuntu runner executes them with
privilege escalation. The Docker client is stubbed, and these tests do not
exercise service shutdown or running-container quiescence.

### Conversation-image policy tests

`tests/contract/test_official_image.py` verifies the repository's policy for
official OpenHands Agent Server images. It accepts pinned official `-golang`
references, including the validated `rel-1.62.0-golang` release-branch image,
and rejects floating or non-official references.

Run all contract tests with:

```console
make test
```

When adding a public variable, validation rule, template invariant, or portable
failure path, prefer adding a contract fixture before relying only on native
integration.

## Default Molecule scenario

The default scenario lives in `molecule/default/`:

- `molecule.yml` defines the local delegated target and test sequence;
- `converge.yml` invokes the role with service identity, prerequisites, Docker
  preflight, and systemd management disabled;
- `verify.yml` checks the temporary persistence directories;
- `cleanup.yml` removes `/tmp/openhands-molecule`.

The scenario proves that the complete role can be loaded, validates its
arguments, converges safely, and produces zero changes on a second run. It does
not claim to test the production deployment path.

Run it with:

```console
make molecule
```

## Persistence and lifecycle scenario

The privileged scenario lives in `molecule/persistence/` and exercises the
actual deployment path. Its sequence is syntax, convergence, idempotence,
verification, and cleanup.

At a high level it verifies:

1. creation of the dedicated service identity and persistence directories;
2. installation of the pinned Node.js, uv, and Agent Canvas releases, either
   with checksum verification or using versioned URLs only;
3. rendering and validation of the environment file and systemd unit;
4. service enablement, startup, version output, and HTTP health;
5. Docker access through the service account;
6. presence and native architecture of the configured conversation image;
7. `go version` through the image's normal `PATH`;
8. creation of a real Docker-backed conversation through Agent Canvas;
9. conversation-container release and reprovisioning;
10. persistence of a bind-mounted workspace across container replacement;
11. conversation deletion and cleanup;
12. idempotence of an unchanged second convergence.

`OPENHANDS_CHECKSUM_MODE` selects `version-only` or `verified`. The Makefile
targets set it explicitly, and the scenario rejects any other value. Portable
interface tests separately assert that the public checksum defaults are empty
and malformed non-empty values are rejected.

`molecule/persistence/verify.yml` contains the assertions and lifecycle API
calls. `molecule/persistence/cleanup.yml` captures diagnostics before removing
the service, containers, files, prerequisites, and service identity.

The cleanup intentionally retains the pulled conversation image. This avoids
unnecessary registry access during repeated native runs and reflects the role's
inspect-before-pull behavior.

## Ansible-version compatibility

The `ansible-compatibility` job in `.github/workflows/ci.yml` checks:

- the declared minimum, `ansible-core 2.20.0`;
- the latest Ansible Core available from PyPI;
- `ansible-core 2.22.0`, currently used by the primary `kotik` consumer.

Each matrix entry uses an isolated `uv` environment. This prevents the locked
local Ansible version from accidentally masking incompatibilities. The job runs
the syntax fixture and default Molecule scenario, not the privileged lifecycle
scenario.

## Native architecture CI

The `native-integration` job runs four entries on GitHub-hosted native runners:

| Runner | Architecture | Checksum mode |
| --- | --- | --- |
| `ubuntu-26.04` | amd64 | version-only |
| `ubuntu-26.04` | amd64 | verified |
| `ubuntu-26.04-arm` | arm64 | version-only |
| `ubuntu-26.04-arm` | arm64 | verified |

Every entry runs the complete persistence scenario. The lightweight default
scenario runs only in the version-only entries, preserving one native run per
architecture without duplicating it for checksum mode. Native runners are
important because the role installs different Node.js and uv artifacts and
Docker resolves different conversation-image manifests for each architecture.

The workflow is defined in `.github/workflows/ci.yml`. Third-party actions are
pinned by commit SHA and workflow permissions are read-only.

## Diagnostics

The persistence cleanup playbook writes a secret-safe diagnostic bundle to:

```text
/tmp/openhands-ci-diagnostics/
```

CI uploads one artifact per architecture and checksum mode for seven days, even
when the scenario fails. The bundle includes systemd status and selected
properties, the service journal, listening ports, process information, service
identity, Docker access,
conversation-container state, installed stack information, and relevant path
metadata.

The bundle deliberately excludes `/etc/openhands/agent-canvas.env`, systemd
environment values, API keys, and arbitrary extra environment values.

## Upgrade coverage

A true role-upgrade test should provision a host with the previous released role
and then apply the candidate release. That can detect migrations involving old
paths, templates, variables, systemd state, and files that a same-version
reconvergence cannot exercise.

The project does not yet have a released and production-exercised baseline, so
it does not invent an artificial upgrade fixture. Previous-release-to-candidate
coverage is deferred until the first real role upgrade. Clean installation and
idempotence remain covered on both supported architectures in the meantime.

A consumer-specific rehearsal for `kotik` or `underturn` is complementary: it
should validate inventory, networking, Docker policy, and credentials outside
this standalone role's CI.

## Choosing where to add a test

Use the narrowest layer that can detect the regression:

- formatting or Ansible idiom: lint configuration;
- public-variable validation or portable failure behavior: contract fixture;
- role loading or local idempotence: default Molecule scenario;
- systemd, permissions, downloads, Docker, or real service behavior:
  persistence scenario;
- architecture-specific behavior: native matrix;
- compatibility with a different Ansible release: compatibility matrix;
- migration from an older published role: future upgrade scenario.

Changes to managed-host behavior should normally include both a focused
contract or template test where practical and integration coverage for the real
runtime behavior.
