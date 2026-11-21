# Development

This repository is a standalone Ansible role. The role name is `openhands` and
its Galaxy identifier will be `nietaki.openhands`.

## Tooling

Development dependencies are declared in `pyproject.toml` and resolved in
`uv.lock`. Use the locked environment for local work:

```console
uv sync --locked
```

The main checks are available through the Makefile:

```console
make lint       # yamllint and ansible-lint
make test       # contract tests
make molecule   # delegated no-op Molecule scenario
make check      # all of the above
```

The delegated scenario runs against the local machine and must not install or
change host software. It is a smoke test for role loading and CI wiring until
managed-host behavior is introduced.

The preliminary role interface is demonstrated in
[`examples/main.yml`](../examples/main.yml). The role performs configuration
validation and, by default, a read-only Docker executable and daemon preflight.
Docker installation and daemon configuration remain outside the role.

The CI compatibility job checks three Ansible versions: the declared minimum
(`2.20.0`), the latest version available from PyPI, and the version currently
used by the primary `kotik` consumer (`2.22.0`). These checks use isolated uv
environments so the locked development environment cannot accidentally mask a
compatibility problem.

## Milestones

Implementation follows `notes/implementation-plan.md`. Keep milestone commits
coherent, avoid mixing unrelated work, and update the plan when a decision
changes. The initial CI matrix deliberately uses native `amd64` and `arm64`
GitHub-hosted Ubuntu runners so architecture-specific installation behavior can
be tested without nested virtualization.
