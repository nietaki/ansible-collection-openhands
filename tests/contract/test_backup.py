"""Integration coverage for pre-upgrade checkpoint detection and output."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKUP_FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "backup-transaction.yml"
ANSIBLE_PLAYBOOK = shutil.which("ansible-playbook")
CAN_BECOME_ROOT = (
    hasattr(os, "geteuid")
    and (
        os.geteuid() == 0
        or (
            shutil.which("sudo") is not None
            and subprocess.run(
                ["sudo", "-n", "true"], check=False, capture_output=True
            ).returncode
            == 0
        )
    )
)


@unittest.skipUnless(
    ANSIBLE_PLAYBOOK and CAN_BECOME_ROOT,
    "backup transaction tests require ansible-playbook and passwordless root access",
)
class BackupTransactionTests(unittest.TestCase):
    def run_case(
        self,
        *,
        state_exists: bool,
        canvas_version: str | None,
        canvas_exits_successfully: bool = True,
        include_workspaces: bool = False,
        expected_checkpoint: bool,
        expected_previous_version: str | None = None,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="openhands-backup-test-") as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            workspace_dir = root / "workspaces"
            binary_dir = root / "bin"
            binary_dir.mkdir()
            if state_exists:
                data_dir.mkdir()
                (data_dir / "data-marker.txt").write_text("persistent state\n")
                workspace_dir.mkdir()
                (workspace_dir / "workspace-marker.txt").write_text("workspace\n")

            canvas_bin = binary_dir / "agent-canvas"
            if canvas_version is not None:
                canvas_output = (
                    f"printf '%s\\n' '{canvas_version}'\nexit 0\n"
                    if canvas_exits_successfully
                    else "exit 1\n"
                )
                canvas_bin.write_text(f"#!/bin/sh\n{canvas_output}")
                canvas_bin.chmod(0o755)

            docker_bin = binary_dir / "docker"
            docker_bin.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = ps ]; then exit 0; fi\n"
                "exit 2\n"
            )
            docker_bin.chmod(0o755)

            variables = {
                "backup_test_root": str(root),
                "backup_test_canvas_bin": str(canvas_bin),
                "backup_test_docker_bin": str(docker_bin),
                "backup_test_include_workspaces": include_workspaces,
                "backup_test_expected": expected_checkpoint,
                "backup_test_previous_version": expected_previous_version
                or (canvas_version if canvas_exits_successfully else "unknown"),
            }
            command = [
                ANSIBLE_PLAYBOOK,
                "-i",
                "localhost,",
                "-c",
                "local",
                str(BACKUP_FIXTURE),
                "--extra-vars",
                json.dumps(variables),
            ]
            if os.geteuid() != 0:
                command.insert(1, "--become")

            result = subprocess.run(
                command,
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, "ANSIBLE_NOCOLOR": "1"},
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"backup scenario failed:\n{result.stdout}\n{result.stderr}",
            )

    def test_version_mismatch_creates_complete_data_checkpoint(self) -> None:
        self.run_case(
            state_exists=True,
            canvas_version="1.0.0",
            expected_checkpoint=True,
        )

    def test_fresh_install_does_not_create_checkpoint(self) -> None:
        self.run_case(
            state_exists=False,
            canvas_version=None,
            expected_checkpoint=False,
        )

    def test_matching_version_does_not_create_checkpoint(self) -> None:
        self.run_case(
            state_exists=True,
            canvas_version="2.0.0",
            expected_checkpoint=False,
        )

    def test_unknown_version_with_existing_state_creates_checkpoint(self) -> None:
        self.run_case(
            state_exists=True,
            canvas_version="1.0.0",
            canvas_exits_successfully=False,
            expected_checkpoint=True,
            expected_previous_version="unknown",
        )

    def test_missing_version_binary_with_existing_state_creates_checkpoint(self) -> None:
        self.run_case(
            state_exists=True,
            canvas_version=None,
            expected_checkpoint=True,
            expected_previous_version="unknown",
        )

    def test_workspace_inclusion_is_opt_in(self) -> None:
        self.run_case(
            state_exists=True,
            canvas_version="1.0.0",
            include_workspaces=True,
            expected_checkpoint=True,
        )


if __name__ == "__main__":
    unittest.main()
