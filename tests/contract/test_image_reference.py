"""Tests for the conversation image reference validation policy."""

from __future__ import annotations

import re
import unittest


def is_valid_image_reference(reference: str) -> bool:
    """Return whether *reference* is a non-empty, whitespace-free image value."""
    return bool(reference) and re.search(r"\s", reference) is None


class ImageReferenceContractTests(unittest.TestCase):
    def test_accepts_python_image_references(self) -> None:
        references = (
            "ghcr.io/openhands/agent-server:1.2.3-python",
            "docker.io/example/agent:latest",
            "registry.example:5000/team/image:custom-tag",
            "ghcr.io/openhands/agent-server@sha256:" + "a" * 64,
        )
        for reference in references:
            with self.subTest(reference=reference):
                self.assertTrue(is_valid_image_reference(reference))

    def test_rejects_empty_or_whitespace_containing_values(self) -> None:
        for reference in ("", "ghcr.io/example/image:tag with-space", " image:tag"):
            with self.subTest(reference=reference):
                self.assertFalse(is_valid_image_reference(reference))


if __name__ == "__main__":
    unittest.main()
