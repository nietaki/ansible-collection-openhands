# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add optional best-effort journald capture for OpenHands conversation
  container logs.

### Changed

- Skip the full test and lint suite in release preparation; releases still
  require a clean, up-to-date `master` checkout.
- Clarify that platform-specific paths skipped by local validation need testing
  under CI-equivalent conditions.

### Fixed

- Skip runtime log systemd management unless log capture is enabled.

## [0.3.3] - 2026-11-25

### Fixed

- Route CI test and integration validation through the same Make targets used
  locally, preventing workflow commands from retaining stale test references.

## [0.3.2] - 2026-11-25

### Changed

- Accept custom and Python-tagged conversation image references instead of
  restricting deployments to official `-golang` tags.

- Upgrade GitHub Actions checkout and artifact upload actions to Node.js
  24-compatible releases.

## [0.3.1] - 2026-11-24

### Added

- Add role-specific Galaxy documentation and link it from the collection README.

## [0.3.0] - 2026-11-24

### Added

- Run the CI suite on pushes to every branch, in addition to pull requests.
- Document a 60-second minimum interval between CI status polls while a run
  is active.
- Publish the collection to Ansible Galaxy from matching SemVer tags after all
  CI validation jobs pass, using the `galaxy-publish` environment secret.

### Changed

- **Breaking:** Packaged the Agent Canvas role as the `nietaki.openhands`
  collection; its role FQCN is now `nietaki.openhands.agent_canvas`.

## [0.2.0] - 2026-11-24

### Added

- Backup and restore documentation covering persistent state locations,
  expected directory structure, SQLite consistency, encryption keys, and
  workspace data.
- Optional root-only pre-upgrade persistence checkpoints with SHA-256 sidecars,
  explicit conversation-container quiescence, and manual rollback instructions.
- Automated pre-upgrade detection and archive-content tests for upgrade decisions,
  checksums, permissions, and workspace inclusion.
- A pre-upgrade backup feature design documenting the agreed reduced scope,
  consistency requirements, container shutdown behavior, manual restore
  contract, and deferred improvements.

### Changed

- Enabled pre-upgrade checkpoints by default and excluded workspaces by default;
  operators can disable checkpoints or opt in to workspace inclusion.

## [0.1.0] - 2026-11-23

### Added

- Initial `nietaki.openhands` Ansible role for deploying OpenHands Agent Canvas
  as a native systemd service with Dockerized conversation environments.
- Strict validation for the role's public variables, cross-variable constraints,
  filesystem paths, Unix identities, listener configuration, image references,
  resource limits, checksums, and extra environment variable names.
- Optional Docker executable and daemon-access preflight checks before managed
  host changes begin.
- Optional installation of pinned Node.js, uv, uvx, and Agent Canvas releases,
  including architecture selection and optional SHA-256 or SHA-512 verification.
- Optional management of the OpenHands service user and group, including access
  to the configured Docker group.
- Managed persistent data and host workspace directories with restricted
  ownership and permissions.
- Conversation image inspection, conditional pulling, architecture validation,
  and optional manifest-digest pinning.
- Configurable Docker conversation policy, including memory, CPU, PID, startup
  timeout, idle-container TTL, and workspace controls.
- Restricted Agent Canvas environment and systemd unit management with service
  enablement, restart handling, version verification, and health polling.
- Safe private-listener defaults and explicit safeguards for non-loopback public
  mode, including a required backend API key.
- Configuration, deployment, upgrade, security, testing, and development
  documentation with an example playbook.
- Portable contract tests, delegated Molecule convergence and idempotence tests,
  and native persistence scenarios for version-only and checksum-verified modes.
- CI coverage for supported Ansible versions and native amd64 and arm64 Ubuntu
  deployments, including secret-safe failure diagnostics.
- Guarded semantic-version release targets that run the full project checks and
  atomically push the release commit and lightweight tag.
- Repository agent guidance for changelog maintenance and operator-only release
  ownership.
