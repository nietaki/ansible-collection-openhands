# Development

This repository is a standalone Ansible role. Its role name is `openhands`, its
Galaxy identifier is `nietaki.openhands`, and all public variables use the
`openhands_` prefix.

## Development environment

Development dependencies are declared in `pyproject.toml` and resolved in
`uv.lock`. Install the locked environment with:

```console
uv sync --locked
```

Use the Makefile as the local command interface:

```console
make lint                   # yamllint and ansible-lint
make test                   # portable Python contract tests
make molecule               # safe local Molecule scenario
make check                  # lint, contract tests, and local Molecule
make molecule-persistence   # privileged native integration scenario
```

See [`testing.md`](testing.md) for the purpose, prerequisites, and related files
for every test layer. In particular, review that document before running the
persistence scenario outside CI.

## Repository layout

Important paths include:

| Path | Purpose |
| --- | --- |
| `defaults/main.yml` | Public defaults and pinned application versions |
| `meta/argument_specs.yml` | Public variable types and short descriptions |
| `tasks/` | Validation, prerequisites, image preparation, and service management |
| `templates/` | Restricted environment file and systemd unit |
| `handlers/main.yml` | systemd reload and service restart handlers |
| `molecule/default/` | Safe delegated convergence and idempotence |
| `molecule/persistence/` | Privileged native lifecycle integration |
| `tests/contract/` | Portable interface and policy tests |
| `tests/fixtures/` | Small Ansible playbooks used by tests and CI |
| `.github/workflows/ci.yml` | Quality, compatibility, and native CI jobs |
| `docs/` | Detailed operator and developer documentation |
| `notes/implementation-plan.md` | Living design history and deferred work |

## Making changes

Keep changes focused and update the narrowest useful test layer. Managed-host
behavior should preserve idempotence and normally have native integration
coverage where it depends on systemd, Docker, permissions, downloads, or real
service behavior.

When adding or changing a public variable:

1. update `defaults/main.yml`;
2. update `meta/argument_specs.yml`;
3. add cross-variable validation in `tasks/main.yml` when types are
   insufficient;
4. update [`configuration.md`](configuration.md);
5. add or update contract fixtures;
6. update native integration assertions when runtime behavior changes.

Do not commit credentials, generated secrets, local virtual environments,
diagnostic bundles, or unreviewed lock-file changes.

## Dependency updates

Node.js, uv, Agent Canvas, and the Agent Server image are intentionally pinned.
A dependency update should include:

- the exact new version or image tag;
- architecture-specific checksums where applicable;
- evidence that the selected image contains the required runtime tools;
- updated documentation;
- successful portable checks and native amd64/arm64 integration.

Do not assume that an upstream image suffix proves its contents. The current
Agent Server default uses `rel-1.62.0-golang` because upstream's final
`1.62.0-golang` tag was built from the wrong base image.

## CI and diagnostics

CI checks the declared minimum Ansible version, the latest available Ansible
Core, and the version used by the primary `kotik` consumer. Native integration
runs on both amd64 and arm64 Ubuntu 26.04 runners.

The persistence cleanup captures a secret-safe bundle in
`/tmp/openhands-ci-diagnostics/`, and CI uploads it even after failures. Never
add the rendered environment file, systemd environment values, API keys, or
arbitrary extra environment values to diagnostics.
