# Contributing

Contributions to `nietaki.openhands` are welcome. Please keep changes focused
on the role and its test coverage, and explain operational or security
trade-offs in the pull request.

## Before opening a pull request

Run the same checks used by CI:

```console
uv sync --locked
make check
```

The first milestone intentionally contains a no-op role. Later milestones will
add managed-host behavior; new behavior should be accompanied by Molecule
coverage and should preserve idempotence.

Please do not commit credentials, generated secrets, local virtual environments,
or unreviewed dependency lock-file changes.
