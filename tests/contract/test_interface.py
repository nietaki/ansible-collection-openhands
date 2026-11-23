"""Integration checks for the public role interface."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPOSITORY_ROOT / "tests" / "fixtures"
CONTRACT_RUNTIME_DIR = Path("/tmp/openhands-interface")
ANSIBLE_PLAYBOOK = shutil.which("ansible-playbook")


@unittest.skipUnless(ANSIBLE_PLAYBOOK, "ansible-playbook is not installed")
class InterfaceContractTests(unittest.TestCase):
    def run_fixture(self, fixture_name: str) -> subprocess.CompletedProcess[str]:
        shutil.rmtree(CONTRACT_RUNTIME_DIR, ignore_errors=True)
        try:
            return subprocess.run(
                [
                    ANSIBLE_PLAYBOOK,
                    "-i",
                    "localhost,",
                    "-c",
                    "local",
                    str(FIXTURES / fixture_name),
                ],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        finally:
            shutil.rmtree(CONTRACT_RUNTIME_DIR, ignore_errors=True)

    def test_valid_configuration_passes(self) -> None:
        result = self.run_fixture("interface-valid.yml")

        self.assertEqual(
            result.returncode,
            0,
            msg=f"valid configuration failed:\n{result.stdout}\n{result.stderr}",
        )

    def test_invalid_public_configuration_fails(self) -> None:
        result = self.run_fixture("interface-invalid.yml")
        output = f"{result.stdout}\n{result.stderr}"

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OpenHands configuration is invalid", output)

    def test_malformed_non_empty_checksum_fails(self) -> None:
        result = self.run_fixture("interface-invalid-checksum.yml")
        output = f"{result.stdout}\n{result.stderr}"

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OpenHands configuration is invalid", output)

    def test_invalid_health_configuration_fails(self) -> None:
        result = self.run_fixture("interface-invalid-health.yml")
        output = f"{result.stdout}\n{result.stderr}"

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OpenHands configuration is invalid", output)

    def test_floating_conversation_image_fails(self) -> None:
        result = self.run_fixture("interface-invalid-image.yml")
        output = f"{result.stdout}\n{result.stderr}"

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OpenHands configuration is invalid", output)

    def test_missing_docker_executable_fails_preflight(self) -> None:
        result = self.run_fixture("docker-missing.yml")
        output = f"{result.stdout}\n{result.stderr}"

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Check Docker executable", output)
        self.assertNotIn("Create the OpenHands data directory", output)

    def test_inaccessible_docker_daemon_fails_preflight(self) -> None:
        result = self.run_fixture("docker-daemon-inaccessible.yml")
        output = f"{result.stdout}\n{result.stderr}"

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Check Docker daemon reachability", output)
        self.assertIn("simulated Docker daemon unavailable", output)
        self.assertNotIn("Create the OpenHands data directory", output)

    def test_service_template_preserves_directive_boundaries(self) -> None:
        result = self.run_fixture("service-template.yml")

        self.assertEqual(
            result.returncode,
            0,
            msg=f"service template rendering failed:\n{result.stdout}\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
