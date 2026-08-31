from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "source_manifest.py"
SPEC = importlib.util.spec_from_file_location("source_manifest", SCRIPT)
source_manifest = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(source_manifest)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


class SourceManifestTest(unittest.TestCase):
    def test_manifest_is_deterministic_and_detects_changed_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as left_tmp, tempfile.TemporaryDirectory() as right_tmp:
            left = Path(left_tmp)
            right = Path(right_tmp)
            (left / "nested").mkdir()
            (right / "nested").mkdir()
            (left / "nested/file.txt").write_text("same\n", encoding="utf-8")
            (right / "nested/file.txt").write_text("same\n", encoding="utf-8")
            first = source_manifest.manifest(left)
            self.assertEqual(first, source_manifest.manifest(left))
            self.assertEqual(first, source_manifest.manifest(right))
            (right / "nested/file.txt").write_text("changed\n", encoding="utf-8")
            self.assertNotEqual(first, source_manifest.manifest(right))

    def make_repo(self, root: Path) -> str:
        git(root, "init", "-q")
        git(root, "config", "user.email", "candidate@example.invalid")
        git(root, "config", "user.name", "Candidate Test")
        (root / "tracked.txt").write_text("frozen\n", encoding="utf-8")
        git(root, "add", "tracked.txt")
        git(root, "commit", "-qm", "candidate")
        return git(root, "rev-parse", "HEAD")

    def test_clean_git_candidate_binds_head_tree_and_tracked_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            head = self.make_repo(repo)
            result = source_manifest.build_result(
                repo, verify_self=True, require_clean_git=True, expected_head=head
            )
            candidate = result["gitCandidate"]
            self.assertEqual(candidate["headSha"], head)
            self.assertEqual(candidate["treeSha"], git(repo, "rev-parse", "HEAD^{tree}"))
            self.assertTrue(candidate["clean"])
            self.assertEqual(candidate["trackedFileCount"], 1)
            self.assertRegex(result["candidateSha256"], r"^[0-9a-f]{64}$")

    def test_modified_or_untracked_candidate_fails_closed(self) -> None:
        for name, mutate in (
            ("modified", lambda repo: (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")),
            ("untracked", lambda repo: (repo / "extra.txt").write_text("extra\n", encoding="utf-8")),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                self.make_repo(repo)
                mutate(repo)
                with self.assertRaisesRegex(ValueError, "candidate_worktree_not_clean"):
                    source_manifest.build_result(repo, require_clean_git=True)

    def test_wrong_head_and_nested_root_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo)
            with self.assertRaisesRegex(ValueError, "candidate_head_mismatch"):
                source_manifest.build_result(repo, require_clean_git=True, expected_head="0" * 40)
            nested = repo / "nested"
            nested.mkdir()
            with self.assertRaisesRegex(ValueError, "candidate_root_must_equal_git_toplevel"):
                source_manifest.build_result(nested, require_clean_git=True)

    def test_symlink_hashes_link_text_without_reading_external_target(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as root_tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root = Path(root_tmp)
            outside = Path(outside_tmp) / "secret.txt"
            outside.write_text("first-secret\n", encoding="utf-8")
            link = root / "external-link"
            link.symlink_to(outside)
            first = source_manifest.manifest(root)
            outside.write_text("different-secret\n", encoding="utf-8")
            self.assertEqual(first, source_manifest.manifest(root))
            self.assertEqual(
                first["external-link"],
                source_manifest.sha256_bytes(os.readlink(link).encode("utf-8", "surrogateescape")),
            )


if __name__ == "__main__":
    unittest.main()
