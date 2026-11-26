"""Integration checks for OpenHands absent-state cleanup."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ABSENT_FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "state-absent.yml"
ANSIBLE_PLAYBOOK = shutil.which("ansible-playbook")


@unittest.skipUnless(ANSIBLE_PLAYBOOK, "ansible-playbook is not installed")
class AbsentStateTests(unittest.TestCase):
    def run_case(
        self, *, remove_containers: bool = False, docker_fails: bool = False
    ) -> tuple[subprocess.CompletedProcess[str], Path, str]:
        temporary_directory = tempfile.TemporaryDirectory(prefix="openhands-absent-test-")
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        for directory in ("software", "data", "workspaces", "backups", "etc", "systemd"):
            (root / directory).mkdir()
        (root / "software" / "tool.txt").write_text("managed software\n")
        (root / "data" / "persistent.txt").write_text("persistent data\n")
        (root / "data" / "capture-runtime-logs.sh").write_text("managed helper\n")
        (root / "workspaces" / "workspace.txt").write_text("workspace data\n")
        (root / "backups" / "checkpoint.tar.gz").write_text("backup\n")
        (root / "etc" / "agent-canvas.env").write_text("secret=not-a-secret\n")
        (root / "systemd" / "openhands.service").write_text("unit\n")
        (root / "systemd" / "openhands-runtime-logs.service").write_text("unit\n")

        docker_log = root / "docker.log"
        failure_marker = root / "docker-fails"
        if docker_fails:
            failure_marker.touch()
        docker_script = root / "docker"
        docker_script.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$*\" >> {shlex.quote(str(docker_log))}\n"
            f"if [ -f {shlex.quote(str(failure_marker))} ]; then exit 1; fi\n"
            "case \"$1\" in\n"
            "  ps) if [ \"$2\" = \"--all\" ]; then printf 'running-id\\nstopped-id\\n'; else printf 'running-id\\n'; fi ;;\n"
            "  stop|rm) exit 0 ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n"
        )
        docker_script.chmod(0o755)

        variables = {
            "absent_test_root": str(root),
            "absent_test_docker": str(docker_script),
            "absent_test_remove_containers": remove_containers,
            "openhands_data_dir": str(root / "data"),
            "openhands_workspace_dir": str(root / "workspaces"),
            "openhands_install_prefix": str(root / "software"),
            "openhands_environment_file": str(root / "etc" / "agent-canvas.env"),
            "openhands_systemd_unit": str(root / "systemd" / "openhands.service"),
            "openhands_runtime_logs_systemd_unit": str(
                root / "systemd" / "openhands-runtime-logs.service"
            ),
        }
        result = subprocess.run(
            [
                ANSIBLE_PLAYBOOK,
                "-i",
                "localhost,",
                "-c",
                "local",
                str(ABSENT_FIXTURE),
                "--extra-vars",
                json.dumps(variables),
            ],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "ANSIBLE_NOCOLOR": "1"},
        )
        return result, root, docker_log.read_text() if docker_log.exists() else ""

    def test_absent_stops_but_preserves_containers_and_persistence(self) -> None:
        result, root, docker_log = self.run_case()

        self.assertEqual(
            result.returncode,
            0,
            msg=f"cleanup failed:\n{result.stdout}\n{result.stderr}",
        )
        self.assertIn("ps --quiet --filter label=ai.openhands.runtime-owner", docker_log)
        self.assertIn("stop running-id", docker_log)
        self.assertNotIn(" rm ", f" {docker_log} ")
        self.assertFalse((root / "software").exists())
        self.assertFalse((root / "etc" / "agent-canvas.env").exists())
        self.assertFalse((root / "systemd" / "openhands.service").exists())
        self.assertFalse((root / "systemd" / "openhands-runtime-logs.service").exists())
        self.assertFalse((root / "data" / "capture-runtime-logs.sh").exists())
        self.assertTrue((root / "data" / "persistent.txt").exists())
        self.assertTrue((root / "workspaces" / "workspace.txt").exists())
        self.assertTrue((root / "backups" / "checkpoint.tar.gz").exists())

    def test_opt_in_removal_removes_running_and_stopped_containers(self) -> None:
        result, _, docker_log = self.run_case(remove_containers=True)

        self.assertEqual(
            result.returncode,
            0,
            msg=f"cleanup failed:\n{result.stdout}\n{result.stderr}",
        )
        self.assertIn("ps --all --quiet --filter label=ai.openhands.runtime-owner", docker_log)
        self.assertIn("rm running-id stopped-id", docker_log)

    def test_docker_failure_is_reported_after_software_cleanup(self) -> None:
        result, root, _ = self.run_case(docker_fails=True)

        output = f"{result.stdout}\n{result.stderr}"
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Docker conversation container cleanup failed", output)
        self.assertFalse((root / "software").exists())
        self.assertFalse((root / "etc" / "agent-canvas.env").exists())
        self.assertTrue((root / "data" / "persistent.txt").exists())


if __name__ == "__main__":
    unittest.main()
