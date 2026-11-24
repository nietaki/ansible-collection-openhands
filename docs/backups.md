# Backups

OpenHands state in this deployment is split across the configured data directory
and workspace directory. Back up both locations to preserve application
configuration, conversation history, automation data, and the files modified by
agents.

The role defaults are:

```yaml
openhands_data_dir: /var/lib/openhands
openhands_workspace_dir: /srv/openhands/workspaces
```

The recommended backup scope is therefore:

```text
/var/lib/openhands/
/srv/openhands/workspaces/
```

Backing up the complete configured directories is safer than selecting only
individual files. Agent Canvas and Agent Server may add persistence files as
the pinned application versions change.

## Persistence roots

The systemd service uses `openhands_data_dir` as its working directory and
`HOME`. Agent Canvas derives its default persistence root from `HOME`:

```text
<openhands_data_dir>/.openhands/
```

With the role defaults, this is:

```text
/var/lib/openhands/.openhands/
```

Changing `openhands_data_dir` changes this effective path. The role does not
migrate existing data when either persistence path changes.

The configured `openhands_workspace_dir` is separate. It contains repositories,
worktrees, generated files, and other content exposed to conversation
containers. Conversation records can survive without these files, but resumed
conversations may then refer to missing workspaces.

## Expected data-directory layout

For the application versions currently pinned by the role, the persistence
root may look approximately like this:

```text
<openhands_data_dir>/.openhands/
├── settings.json
├── secrets.json
├── workspaces.json
├── profiles/
├── provider-connections/
├── agent-profiles/
├── meta-profiles/
├── agent-canvas/
│   ├── api-key.txt
│   ├── secret-key.txt
│   ├── automation-kv-secret.txt
│   ├── dev_conversations/
│   │   └── <conversation-uuid>/
│   │       ├── meta.json
│   │       ├── base_state.json
│   │       └── events/
│   │           ├── event-00000-<event-id>.json
│   │           └── ...
│   ├── bash_events/
│   ├── storage/
│   ├── workspaces/
│   └── tmux/
├── automation/
│   ├── automations.db
│   ├── automations.db-wal
│   └── automations.db-shm
├── runtime-control/
│   └── <conversation-uuid>.json
├── runtime-data/
│   └── <conversation-uuid>/
│       ├── persistence/
│       ├── worktrees/
│       └── workspace/
├── skills/
├── plugins/
├── canvas-extensions/
├── auth/
├── cache/
├── memory/
├── hooks.json
└── SOUL.md
```

This is a representative superset, not a list of files that must always exist.
Most entries are created lazily when their feature is first used. Patch-level
application changes may also add, remove, or rename internal paths.

### Settings, secrets, and profiles

The root-level JSON files and profile directories can contain:

- LLM profiles and model settings;
- encrypted API keys and custom secrets;
- provider connections;
- registered workspaces;
- agent and meta-profile configuration.

Temporary lock files such as `.settings.lock`, `.secrets.lock`, and
`.workspaces.lock` may appear during updates.

### Agent Canvas state

`agent-canvas/` contains state managed by the native Canvas launcher:

- `api-key.txt` stores an automatically generated session API key when an
  explicit key was not configured;
- `secret-key.txt` contains the stable key used to encrypt persisted settings
  and secrets;
- `automation-kv-secret.txt` protects Automation key-value state;
- `storage/` contains local file-store data;
- `tmux/` contains persistent tmux runtime data;
- `workspaces/` is used for launcher- or automation-managed workspaces.

The key files are important backup material. Losing or changing an encryption
key can make existing encrypted settings or Automation KV values unreadable.
When `openhands_backend_api_key` is explicitly configured, preserve its source
of truth, normally Ansible Vault or another secret manager, in addition to the
managed host data.

### Conversation history

The native Agent Canvas launcher currently stores conversation records under:

```text
<openhands_data_dir>/.openhands/agent-canvas/dev_conversations/
```

Each conversation normally has a UUID directory containing:

- `meta.json` for conversation metadata, launch configuration, workspace
  selection, tags, and title;
- `base_state.json` for resumable agent and execution state;
- `events/` for user messages, agent messages, actions, observations, and tool
  results.

The `dev_conversations` name is an upstream implementation detail even though
the role runs a production systemd service. Do not rename it.

### Automation database

The bundled Automation service uses SQLite at:

```text
<openhands_data_dir>/.openhands/automation/automations.db
```

It stores automation definitions, schedules, triggers, run records, integration
events, Git synchronization state, and Automation KV data. While the service is
running in write-ahead logging mode, the database can also have live
`automations.db-wal` and `automations.db-shm` sidecar files.

Do not assume that copying only `automations.db` from a running service produces
a consistent backup. Stop the service, use a coordinated filesystem snapshot,
or use SQLite's online backup mechanism.

### Docker conversation-runtime state

The role fixes the conversation runtime to Docker. Agent Server keeps the
associated host-side runtime state under:

```text
<openhands_data_dir>/.openhands/runtime-control/
<openhands_data_dir>/.openhands/runtime-data/
```

`runtime-control/` contains per-conversation provisioning manifests.
`runtime-data/` can contain each container's private persistence, Git worktrees,
and runtime-owned workspace. These host directories allow conversation state to
survive container replacement.

### Optional feature data

Directories such as `skills/`, `plugins/`, `canvas-extensions/`, `auth/`,
`cache/`, and `memory/` appear only when their features are used. Some cache
content may be reproducible, but installed extensions, authentication data,
custom memory, hooks, and agent instructions can be user-created state. Backing
up the complete data directory avoids having to classify every entry.

## Workspace-directory layout

The role's main workspace root defaults to:

```text
/srv/openhands/workspaces/
```

Its exact contents are user- and conversation-defined. It may contain:

```text
/srv/openhands/workspaces/
├── project-a/
│   ├── .git/
│   └── ...
├── project-b/
│   └── ...
└── <conversation-or-automation-workspace>/
    └── ...
```

These files are bind-mounted into conversation containers and can be modified
by agents and their tools. Preserve ownership, permissions, symbolic links, Git
metadata, and extended attributes where the backup system supports them.

The `agent-canvas/workspaces/` directory beneath the data root is separate from
`openhands_workspace_dir`; back up the entire data root so both are included.

## Data that normally does not require backup

The following role-managed paths are reproducible from the role and pinned
configuration:

```text
/opt/openhands/
/etc/systemd/system/openhands.service
/etc/openhands/agent-canvas.env
```

`/opt/openhands/` contains installed application artifacts rather than primary
user data. The unit and environment file are rendered by Ansible. Preserve the
inventory, variable files, Ansible Vault data, and any external secret-manager
records needed to reproduce them.

The environment file can contain an explicitly configured backend API key. It
is therefore sensitive even though it is reproducible and should not be copied
into an insecure backup or diagnostic archive.

Docker images and stopped conversation containers are also reproducible. The
persistent conversation and workspace data is stored on the host paths covered
above rather than relying on an unnamed container filesystem.

## Backup consistency

The simplest consistent backup is to stop OpenHands, copy or snapshot both
configured persistence locations, and then start it again:

```console
sudo systemctl stop openhands.service
sudo tar -C / -czf /path/to/secure-backup/openhands-data.tar.gz \
  var/lib/openhands \
  srv/openhands/workspaces
sudo systemctl start openhands.service
```

Adjust the paths when `openhands_data_dir` or `openhands_workspace_dir` differs
from the defaults. Store the archive in a protected location because it may
contain source code, conversation transcripts, API credentials, encryption
keys, and other secrets.

For larger installations, filesystem or storage-provider snapshots can reduce
downtime. Coordinate snapshots across the data and workspace filesystems when a
conversation must be restored with the exact workspace state it referenced.
Validate that the snapshot mechanism gives SQLite a consistent view, or briefly
stop the service around the snapshot.

## Restore considerations

A restore should preserve:

- file ownership by `openhands_service_user` and
  `openhands_service_group`;
- restrictive permissions on key and secret files;
- symbolic links and Git metadata in workspaces;
- the relationship between conversation records and their workspace paths;
- the original encryption keys used for settings, secrets, and Automation KV
  state.

Restore the data and workspace directories before starting
`openhands.service`. If restoring onto a host with different configured paths,
move the data deliberately and update the role variables; changing the variables
alone does not migrate stored content or rewrite paths embedded in conversation
records.

After a restore, verify the service and inspect its logs:

```console
sudo systemctl start openhands.service
sudo systemctl status openhands.service
sudo journalctl -u openhands.service --since today
```

Then confirm that settings, conversations, automations, and representative
workspace files are visible through Agent Canvas.

## Inspecting an installation

List the persisted hierarchy without displaying secret contents:

```console
sudo find /var/lib/openhands/.openhands -maxdepth 4 -print
```

Review top-level disk usage:

```console
sudo du -h -d 2 /var/lib/openhands/.openhands
sudo du -h -d 2 /srv/openhands/workspaces
```

If the `sqlite3` client is installed, list the Automation database tables
without dumping their contents:

```console
sudo sqlite3 \
  /var/lib/openhands/.openhands/automation/automations.db \
  '.tables'
```

Use the configured role paths instead of these defaults when they have been
overridden.
