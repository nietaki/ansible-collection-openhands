# Pre-upgrade backups

## Status

Design agreed; not yet implemented.

This document records the intended first implementation of optional backups
created by the role before an OpenHands upgrade. It deliberately describes a
small rollback-checkpoint feature rather than a complete backup or disaster
recovery system.

## Purpose

An OpenHands upgrade can change persisted application state. If the new version
is broken or corrupts that state, the operator should have a checkpoint from
before the new application version first used the data.

The checkpoint is intended to protect against a bad deployment or data
migration on the same host. An archive stored on the same filesystem does not
protect against host loss, disk failure, ransomware, or deletion by a host
administrator. Operators that need disaster recovery should copy the archives
off-host or use a dedicated backup system.

## Agreed initial scope

The first implementation should:

- be optional and disabled by default;
- create a backup before an existing installation is upgraded;
- back up the complete `openhands_data_dir`;
- include `openhands_workspace_dir` by default, with one option to exclude it;
- stop Agent Canvas and explicitly quiesce its Docker conversation containers
  before reading either persistence root;
- create a private root-owned `tar.gz` archive in a configurable directory;
- write the archive through a temporary name and rename it only after success;
- create a SHA-256 sidecar using standard system tools;
- abort the upgrade when a required checkpoint cannot be created;
- document a manual, non-overlay restore procedure.

The initial implementation should not:

- install a custom create, list, verify, or restore command;
- restore data through an Ansible role variable;
- automatically restore after a failed deployment or health check;
- maintain a deployment-history database or post-deployment marker;
- automatically prune old archives;
- schedule backups or transfer them off-host;
- support arbitrary include and exclude patterns;
- make archive ownership configurable;
- back up reproducible installation files under `/opt/openhands`;
- migrate persistence between different configured paths;
- support restoring an archive into paths different from those it contains;
- provide storage-provider-specific snapshot integrations.

## Proposed role interface

The minimal public interface is expected to be similar to:

```yaml
openhands_backup_enabled: false
openhands_backup_dir: /var/backups/openhands
openhands_backup_include_workspaces: true
```

The exact variable names remain subject to implementation review, but the
interface should remain this small unless implementation uncovers a concrete
need for another control.

Enabling backups should not mean creating an archive on every idempotent role
run. It should enable automatic checkpoints when the role detects an upgrade of
an existing installation.

## Upgrade detection without deployment history

The role should inspect the existing installation before changing managed
application files. The primary signal is the result of running the currently
installed Agent Canvas binary with `--version` and comparing it with
`openhands_agent_canvas_version`.

The effective conversation image may also be compared with the configured image
and digest when the existing value can be obtained simply and without exposing
the environment file's secrets. An image-only change is worth checkpointing,
but parsing or persisting a complete deployment fingerprint is outside the
initial scope.

The detector should behave conservatively:

- no installed application and no pre-existing OpenHands state means a fresh
  installation and does not require a backup;
- a known installed version equal to the target version does not require a
  backup;
- a known installed version different from the target version requires a
  backup;
- an existing state directory combined with an installed version that cannot be
  determined should be treated as requiring a backup.

Some unnecessary checkpoints are acceptable when they keep the detector simple
and safe. A role release, configuration-only change, Node.js change, or uv
change does not by itself have to trigger a checkpoint in the first
implementation.

Changing `openhands_data_dir` or `openhands_workspace_dir` is not an ordinary
upgrade. The current role does not migrate data or rewrite paths embedded in
persisted records. The backup feature must not silently archive newly created
empty target directories and imply that migration occurred. Path changes should
remain an explicit, separately documented operator procedure.

## Backup contents

### Data directory

The complete configured `openhands_data_dir` should be archived. The role must
not select only `.openhands/` or a list of currently known files.

The data directory is the service's working directory and `HOME`. Its contents
include settings, secrets, encryption keys, conversation history, Automation's
SQLite database, Docker runtime state, extensions, skills, hooks, memory, and
other optional or version-dependent data. Selecting individual paths would
couple the role to upstream internal layouts and could produce an archive that
looks valid while omitting a newly introduced persistence file.

### Workspace directory

`openhands_workspace_dir` should be included by default so that conversation
records and the files they reference represent the same point in time.

Operators may disable workspace inclusion when workspaces are very large or are
already protected by another system. Such an archive is an application-state
checkpoint, not a complete OpenHands rollback point. Documentation and archive
naming or metadata should make that limitation visible.

### Excluded paths

The checkpoint does not need to contain:

- `/opt/openhands/`;
- `/etc/systemd/system/openhands.service`;
- `/etc/openhands/agent-canvas.env`;
- Docker images;
- Docker container writable layers.

The role and its pinned variables reproduce the installation files. The host
persistence roots contain the durable conversation and workspace data. The
operator must retain the inventory, variable files, Ansible Vault data, and any
external secret-manager records needed to reproduce the old deployment.

## Archive format and security

The default destination should be:

```text
/var/backups/openhands/
```

Recommended permissions are:

```text
/var/backups/openhands/           root:root 0700
/var/backups/openhands/*.tar.gz   root:root 0600
```

The service account must not own or have write access to the backup directory.
The archives can contain source code, transcripts, API credentials, encryption
keys, and authentication state. Giving the application account write access
would allow an application compromise to destroy its rollback points.

The configured destination must not be equal to or nested beneath either
persistence root. This prevents an archive from recursively including itself.
The role should manage only the configured backup directory and must not
recursively change ownership on an arbitrary parent or shared mount.

A filename should contain a UTC timestamp and enough version context to make its
purpose apparent, for example:

```text
openhands-1.43.0-before-1.44.0-20261124T153012Z.tar.gz
```

Archive members should use paths relative to `/` so that standard GNU tar can
restore them beneath the filesystem root without storing unsafe absolute member
names. Tar is preferred over ZIP because it preserves Unix ownership,
permissions, symbolic links, and Git metadata more naturally. GNU tar support
for ACLs and extended attributes may be used, but a complex portability layer
is not required for the role's supported Ubuntu target.

Creation should be transactional:

1. create a hidden or otherwise clearly temporary `.partial` archive;
2. run tar and compression to completion;
3. remove the temporary file on failure;
4. rename it to the final name only after success;
5. generate a standard SHA-256 sidecar.

No custom verification command is required. Operators can use `tar -tzf`,
`gzip -t`, and `sha256sum -c` directly.

## Service and conversation-container lifecycle

### Current role behavior

The role currently installs prerequisites and prepares the configured
conversation image before service management. Changes notify the
`Restart OpenHands service` handler, which is flushed before version and health
verification. The role does not explicitly stop conversation containers during
normal deployment.

The systemd unit uses:

```ini
KillSignal=SIGINT
TimeoutStopSec=30s
```

Stopping `openhands.service` therefore asks Agent Canvas to shut down cleanly,
but systemd itself does not own the Docker containers.

The persistence Molecule cleanup already treats remaining conversation
containers as possible: after stopping the service it lists containers whose
names begin with `agent-server-conversation-` and forcibly removes them.

### Upstream shutdown behavior

Agent Canvas 1.43.0 pins host Agent Server 1.63.1. This host-side server is
separate from the role's currently configured `rel-1.62.0-golang` conversation
image. For those upstream host-service versions:

- Agent Canvas handles `SIGINT`, `SIGTERM`, and `SIGHUP` by sending `SIGTERM` to
  its child service process groups;
- Agent Canvas waits three seconds and then sends `SIGKILL` to child processes
  that are still running;
- Agent Server's FastAPI lifespan calls the Docker conversation registry's
  `shutdown()` method;
- the registry concurrently calls `docker stop` for containers it currently
  owns;
- conversation containers have names beginning with
  `agent-server-conversation-` and the label
  `ai.openhands.runtime-owner`;
- a later Agent Server startup removes stale containers with its owner label.

Relevant upstream sources:

- [Agent Canvas launcher v1.43.0](https://github.com/OpenHands/OpenHands/blob/v1.43.0/scripts/dev-with-automation.mjs)
- [Agent Canvas v1.43.0 version defaults](https://github.com/OpenHands/OpenHands/blob/v1.43.0/config/defaults.json)
- [Agent Server Docker registry v1.63.1](https://github.com/OpenHands/software-agent-sdk/blob/v1.63.1/openhands-agent-server/openhands/agent_server/docker_runtime/registry.py)
- [Docker conversation-runtime documentation](https://docs.openhands.dev/openhands/usage/agent-canvas/backend-setup/docker-execution)

The graceful path intends to stop conversation containers, but it is not a
sufficient backup consistency guarantee. A Docker stop can outlast Agent
Canvas's three-second child-process grace period, leaving a container running
after the host service has stopped.

For an ordinary deployment this is less serious because the next Agent Server
startup removes stale owned containers. During archive creation, however, a
remaining container can continue writing conversation events, runtime
persistence, worktrees, or the main workspace while tar is reading them.

### Required backup quiescence

The backup transaction should therefore:

1. stop `openhands.service` so that no new conversation container can be
   created;
2. list matching conversation containers using the OpenHands label and name
   prefix;
3. stop any remaining matches;
4. poll until no matching container is running;
5. fail rather than create the checkpoint if quiescence cannot be established.

This explicit container handling can initially remain local to the backup path.
It does not need to become general conversation-container management for every
service restart.

## Intended task sequence

A minimal implementation can use the following sequence without first
refactoring the whole installation into staged preparation and atomic
activation phases:

1. validate the role interface and target platform;
2. inspect the currently installed Agent Canvas version before mutating
   prerequisites;
3. decide whether the run is a fresh install, a same-version run, or an upgrade;
4. when an upgrade checkpoint is required:
   1. create and validate the root-owned backup directory;
   2. stop `openhands.service` if it is running;
   3. stop and verify the absence of active conversation containers;
   4. archive the configured persistence roots to a temporary file;
   5. finalize the archive and checksum;
5. continue through the existing prerequisite, image, configuration, and
   service tasks;
6. start the service and perform the existing version and health checks.

This simplified ordering can keep OpenHands unavailable while downloads and
installation complete. It also means an installation failure may leave the
service stopped. Splitting prerequisites into prepare and activate phases, and
installing Agent Canvas into versioned directories behind a stable symlink,
would reduce downtime and improve software rollback. Those improvements are
valuable but are not prerequisites for the initial checkpoint feature.

If checkpoint creation itself fails before application mutation, the role
should attempt to restart the previously running service and then fail. Once
application activation has begun, the role should not automatically restore the
archive; it should report the archive path and leave rollback as an explicit
operator decision.

## Manual restore contract

The initial feature should document restoration rather than automate it. A
restore must replace the archived roots rather than overlay them on newer state,
because files introduced by the newer version could otherwise survive the
rollback.

The documented procedure should require the operator to:

1. verify or inspect the selected archive;
2. stop `openhands.service`;
3. stop any remaining OpenHands conversation containers;
4. rename the current data and workspace roots to timestamped recovery names;
5. extract the archive beneath `/`;
6. restore the old role variables, especially the Agent Canvas and conversation
   image versions associated with the checkpoint;
7. run the role to reinstall and start the old deployment;
8. inspect service status and logs, then verify settings, conversations,
   automations, and representative workspace files;
9. retain the moved-aside directories until the restoration has been confirmed.

Changing role variables alone does not migrate persistence, and restoring old
data before immediately starting the still-installed newer application can
reapply the problematic migration. The old software configuration and the old
data checkpoint belong together.

## Retention

The first implementation should not automatically delete archives. Backups are
expected only on detected upgrades, so they should be much less frequent than a
scheduled backup stream. The documentation should still warn that archives,
especially those containing workspaces, can consume substantial disk space and
that operators are responsible for monitoring and retention.

Automatic count-based retention can be added later without changing the archive
format. Any future pruning must only touch files created by this feature and
must not delete old checkpoints until a new archive and the associated
deployment have completed successfully.

## Validation and testing considerations

Implementation should add contract coverage for:

- defaults and argument specifications for the backup variables;
- absolute, non-root backup paths;
- rejection of a backup directory inside either persistence root;
- the workspace-inclusion boolean;
- fresh-install and same-version runs not creating an archive;
- version mismatch causing a checkpoint;
- conservative behavior when existing state is present but the installed
  version cannot be determined.

Native or Molecule coverage should verify, where practical:

- backup directory and archive ownership and modes;
- inclusion of the complete data directory;
- optional inclusion and exclusion of the workspace directory;
- a running conversation container is stopped before archiving;
- data written before quiescence is present in the archive;
- temporary archives are not left with final names after failure;
- backup failure prevents application activation;
- the ordinary idempotent run does not create another archive.

A restore test can follow the documented commands even though no restore utility
is installed: create representative data, create a checkpoint, replace or
remove the live data, extract the archive, and verify ownership, symlinks,
conversation state, and workspace files.

## Deferred improvements

Possible follow-up work includes:

- staging all downloads and image pulls before downtime;
- versioned Agent Canvas installations with atomic symlink activation;
- a standalone backup and restore utility;
- automatic retention after successful deployment;
- richer archive metadata and deployment fingerprints;
- explicit handling of image-only or configuration-only upgrades;
- filesystem or storage-provider snapshot hooks;
- off-host transfer integrations;
- supported persistence-path migration;
- automatic rollback of both software and data after a failed deployment.
