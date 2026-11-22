"""Tests for the official OpenHands Agent Server image contract."""

from __future__ import annotations

import re
import unittest


IMAGE_PATTERN = re.compile(
    r"^ghcr\.io/openhands/agent-server:(?P<version>[^:@/\s]+)-golang"
    r"(?:@(?P<digest>sha256:[0-9a-f]{64}))?$"
)


def is_official_golang_image(reference: str) -> bool:
    """Return whether *reference* follows the pinned official image contract."""
    match = IMAGE_PATTERN.fullmatch(reference)
    if match is None:
        return False

    version = match.group("version")
    return version not in {"latest", "main"} and bool(version)


class OfficialImageContractTests(unittest.TestCase):
    def test_accepts_versioned_official_image(self) -> None:
        self.assertTrue(
            is_official_golang_image(
                "ghcr.io/openhands/agent-server:1.2.3-golang"
            )
        )

    def test_accepts_versioned_image_with_manifest_digest(self) -> None:
        self.assertTrue(
            is_official_golang_image(
                "ghcr.io/openhands/agent-server:1.2.3-golang@"
                "sha256:" + "a" * 64
            )
        )

    def test_accepts_release_branch_image(self) -> None:
        self.assertTrue(
            is_official_golang_image(
                "ghcr.io/openhands/agent-server:rel-1.62.0-golang"
            )
        )

    def test_rejects_floating_tags(self) -> None:
        self.assertFalse(
            is_official_golang_image(
                "ghcr.io/openhands/agent-server:latest-golang"
            )
        )
        self.assertFalse(
            is_official_golang_image(
                "ghcr.io/openhands/agent-server:main-golang"
            )
        )

    def test_rejects_non_official_or_non_golang_images(self) -> None:
        invalid_references = (
            "docker.io/openhands/agent-server:1.2.3-golang",
            "ghcr.io/openhands/agent-server:1.2.3",
            "ghcr.io/openhands/custom-agent-server:1.2.3-golang",
            "ghcr.io/openhands/agent-server:1.2.3-golang@sha256:not-a-digest",
        )
        for reference in invalid_references:
            with self.subTest(reference=reference):
                self.assertFalse(is_official_golang_image(reference))


if __name__ == "__main__":
    unittest.main()
