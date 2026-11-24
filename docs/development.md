# Development

This repository contains the `nietaki.openhands` Ansible collection. Its
`agent_canvas` role is invoked as `nietaki.openhands.agent_canvas`, and all
public variables use the `openhands_` prefix.

## Development environment

Development dependencies are declared in `pyproject.toml` and resolved in
`uv.lock`. Install the locked environment with:

```console
uv sync --locked
```

Use the Makefile as the local command interface. `make check`, `make test`,
and Molecule targets build and install the collection artifact locally before
running role-based checks:

```console
make collection-install                  # build and install the local collection artifact
make lint                                # yamllint and ansible-lint
make test                                # portable Python contract tests
make molecule                            # safe local Molecule scenario
make check                               # lint, contract tests, and local Molecule
make molecule-persistence                # version-only persistence alias
make molecule-persistence-version-only   # persistence without download checksums
make molecule-persistence-verified       # persistence with download checksums
```

See [`testing.md`](testing.md) for the purpose, prerequisites, and related files
for every test layer. In particular, review that document before running the
persistence scenario outside CI.

## Repository layout

Important paths include:

| Path | Purpose |
| --- | --- |
| `galaxy.yml` | Collection metadata and sole source of its version |
| `roles/agent_canvas/defaults/main.yml` | Public defaults and pinned application versions |
| `roles/agent_canvas/meta/argument_specs.yml` | Public variable types and short descriptions |
| `roles/agent_canvas/tasks/` | Validation, prerequisites, image preparation, and service management |
| `roles/agent_canvas/templates/` | Restricted environment file and systemd unit |
| `roles/agent_canvas/handlers/main.yml` | systemd reload and service restart handlers |
| `molecule/default/` | Safe delegated convergence and idempotence |
| `molecule/persistence/` | Privileged native lifecycle integration |
| `tests/contract/` | Portable interface and policy tests |
| `tests/fixtures/` | Small Ansible playbooks used by tests and CI |
| `.github/workflows/ci.yml` | Quality, compatibility, and native CI jobs |
| `AGENTS.md` | Changelog guidance and operator-only release ownership |
| `CHANGELOG.md` | Notable changes following Keep a Changelog |
| `scripts/release.sh` | Guarded collection release script used by Make |
| `docs/` | Detailed operator and developer documentation |
| `notes/implementation-plan.md` | Living design history and deferred work |

## Making changes

Keep changes focused and update the narrowest useful test layer. Managed-host
behavior should preserve idempotence and normally have native integration
coverage where it depends on systemd, Docker, permissions, downloads, or real
service behavior.

When adding or changing a public variable:

1. update `roles/agent_canvas/defaults/main.yml`;
2. update `roles/agent_canvas/meta/argument_specs.yml`;
3. add cross-variable validation in
   `roles/agent_canvas/tasks/main.yml` when types are insufficient;
4. update [`configuration.md`](configuration.md);
5. add or update contract fixtures;
6. update native integration assertions when runtime behavior changes.

Do not commit credentials, generated secrets, local virtual environments,
diagnostic bundles, or unreviewed lock-file changes.

## Dependency updates

Node.js, uv, Agent Canvas, and the Agent Server image are intentionally pinned.
A dependency update should include:

- the exact new version or image tag;
- confirmation that the documented optional-checksum commands still match the
  upstream artifacts;
- evidence that the selected image contains the required runtime tools;
- updated documentation;
- successful portable checks and native amd64/arm64 integration.

Do not assume that an upstream image suffix proves its contents. The current
Agent Server default uses `rel-1.62.0-golang` because upstream's final
`1.62.0-golang` tag was built from the wrong base image.

## Releases

Releases are performed only by the repository operator, not by agents.
`galaxy.yml` contains the collection version and is the sole version source.
From a clean local `master` that matches `origin/master`, select the appropriate
semantic version bump:

```console
make release-patch
make release-minor
make release-major
```

Record notable work under `## [Unreleased]` in `CHANGELOG.md`. The release
script runs `make check`, displays the proposed version and local release date,
and asks for confirmation. Enter `y` to update the version in `galaxy.yml`,
place the Unreleased changelog entries under `## [X.Y.Z] - YYYY-MM-DD`, create a
commit named `Release X.Y.Z`, create the lightweight `X.Y.Z` tag, and atomically
push the commit and tag to `origin`. The release aborts if the target tag already
exists locally or on the remote; existing tags are never moved. Pushing the
release tag triggers CI for that tagged commit. After all validation jobs pass,
CI publishes the collection to Ansible Galaxy only when the plain `X.Y.Z` tag
matches `galaxy.yml` and its commit is reachable from `master`. The publishing
job reads `ANSIBLE_GALAXY_API_KEY` from the GitHub Actions `galaxy-publish`
environment; it is not exposed to validation jobs. Tags that are not plain
`X.Y.Z` versions are treated as non-release tags and skip publication. A strict
version tag that disagrees with `galaxy.yml` or is not on `master` fails release
eligibility.

Galaxy versions are immutable after publication. Review collection contents,
changelog entries, and the version/tag match before creating the tag. CI builds
the artifact from the tagged commit; a failed validation job prevents publishing.

## CI and diagnostics

CI runs on pull requests, pushes to every branch, and version-shaped tag pushes.
It checks the declared minimum Ansible version, the latest available Ansible
Core, and the version used by the primary `kotik` consumer. Native integration
runs on both amd64 and arm64 Ubuntu 26.04 runners. Galaxy publishing remains
limited to eligible version tags after all validation jobs pass.

The persistence cleanup captures a secret-safe bundle in
`/tmp/openhands-ci-diagnostics/`, and CI uploads it even after failures. Never
add the rendered environment file, systemd environment values, API keys, or
arbitrary extra environment values to diagnostics.
