#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import threading
import time
import importlib.util
import json
import tempfile
import unittest
from unittest import mock
import errno
import stat
import subprocess
import sys
import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "atomic_state.py"
SPEC = importlib.util.spec_from_file_location("atomic_state", SCRIPT)
atomic_state = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(atomic_state)


class AtomicStateTest(unittest.TestCase):
    def test_concurrent_writers_keep_valid_complete_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"

            def write(index: int) -> None:
                atomic_state.atomic_write_json(path, {"writer": index, "payload": "x" * 2000})

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(write, range(40)))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(saved["writer"], range(40))
            self.assertEqual(saved["payload"], "x" * 2000)
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

    def test_compare_and_swap_rejects_stale_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})
            stale = atomic_state.state_sha256({"revision": 1})
            atomic_state.atomic_write_json(path, {"revision": 2}, expected_sha256=stale)
            with self.assertRaises(atomic_state.StateConflictError):
                atomic_state.atomic_write_json(path, {"revision": 3}, expected_sha256=stale)
            self.assertEqual(atomic_state.read_json(path), {"revision": 2})

    def test_failure_before_replace_preserves_old_state_and_cleans_unique_temp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})

            def interrupt(temp_path: Path) -> None:
                self.assertIn(str(Path(tmp)), str(temp_path))
                raise RuntimeError("simulated_crash_before_replace")

            with self.assertRaises(RuntimeError):
                atomic_state.atomic_write_json(path, {"revision": 2}, before_replace=interrupt)
            self.assertIn(json.loads(path.read_text()) if path.exists() else {}, ({}, {"revision": 1}))
            self.assertTrue(atomic_state.has_uncertainty(path))
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

    def test_locked_update_serializes_read_modify_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"count": 0})

            def increment(_: int) -> None:
                atomic_state.locked_update_json(path, lambda state: {"count": state["count"] + 1})

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(increment, range(50)))
            self.assertEqual(atomic_state.read_json(path), {"count": 50})

    def test_supported_directory_fsync_failure_is_never_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            real_fsync = atomic_state.os.fsync

            def fail_directory_fsync(fd: int) -> None:
                if stat.S_ISDIR(atomic_state.os.fstat(fd).st_mode):
                    raise OSError(errno.EIO, "simulated directory durability failure")
                real_fsync(fd)

            with mock.patch.object(atomic_state.os, "fsync", side_effect=fail_directory_fsync):
                with self.assertRaisesRegex(
                    atomic_state.StateDurabilityError, "directory_fsync_failed"
                ):
                    atomic_state.atomic_write_json(path, {"revision": 1})
            self.assertIn(json.loads(path.read_text()) if path.exists() else {}, ({}, {"revision": 1}))
            self.assertTrue(atomic_state.has_uncertainty(path))

    def test_unsupported_directory_fsync_is_explicitly_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            with mock.patch.object(atomic_state, "fsync_directory", return_value=False):
                with self.assertRaisesRegex(
                    atomic_state.StateDurabilityError, "not_durable"
                ):
                    atomic_state.atomic_write_json(path, {"revision": 1})

    def test_directory_close_failure_is_never_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            real_close = atomic_state.os.close

            def fail_directory_close(fd: int) -> None:
                if stat.S_ISDIR(atomic_state.os.fstat(fd).st_mode):
                    real_close(fd)
                    raise OSError(errno.EIO, "simulated directory close failure")
                real_close(fd)

            with mock.patch.object(atomic_state.os, "close", side_effect=fail_directory_close):
                with self.assertRaisesRegex(
                    atomic_state.StateDurabilityError, "directory_close_failed"
                ):
                    atomic_state.atomic_write_json(Path(tmp) / "state.json", {"revision": 1})

    def test_after_replace_crash_requires_explicit_restart_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})

            def crash_after_replace(_: Path) -> None:
                raise RuntimeError("simulated_after_replace_before_directory_fsync")

            with self.assertRaisesRegex(RuntimeError, "after_replace"):
                atomic_state.atomic_write_json(
                    path,
                    {"revision": 2},
                    expected_sha256=atomic_state.state_sha256({"revision": 1}),
                    after_replace=crash_after_replace,
                )
            self.assertEqual(json.loads(path.read_text()), {"revision": 2})
            self.assertTrue(atomic_state.has_uncertainty(path))
            with self.assertRaises(atomic_state.StateReconciliationRequired):
                atomic_state.atomic_write_json(path, {"revision": 3})
            reconciled = atomic_state.reconcile_atomic_json(path)
            self.assertEqual(reconciled["status"], "postimage_confirmed")
            self.assertFalse(atomic_state.has_uncertainty(path))

    def test_before_replace_crash_reconciles_confirmed_preimage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})

            def crash_before_replace(_: Path) -> None:
                raise RuntimeError("simulated_before_replace")

            with self.assertRaisesRegex(RuntimeError, "before_replace"):
                atomic_state.atomic_write_json(
                    path, {"revision": 2}, before_replace=crash_before_replace
                )
            self.assertEqual(json.loads(path.read_text()), {"revision": 1})
            self.assertTrue(atomic_state.has_uncertainty(path))
            self.assertEqual(
                atomic_state.reconcile_atomic_json(path)["status"], "preimage_restored"
            )

    def test_target_directory_fsync_failure_keeps_marker_for_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            real_fsync = atomic_state.os.fsync
            directory_calls = 0

            def fail_second_directory_fsync(fd: int) -> None:
                nonlocal directory_calls
                if stat.S_ISDIR(atomic_state.os.fstat(fd).st_mode):
                    directory_calls += 1
                    if directory_calls == 2:
                        raise OSError(errno.EIO, "target directory fsync failure")
                real_fsync(fd)

            with mock.patch.object(atomic_state.os, "fsync", side_effect=fail_second_directory_fsync):
                with self.assertRaisesRegex(
                    atomic_state.StateDurabilityError, "directory_fsync_failed"
                ):
                    atomic_state.atomic_write_json(path, {"revision": 1})
            self.assertEqual(json.loads(path.read_text()), {"revision": 1})
            self.assertTrue(atomic_state.has_uncertainty(path))
            self.assertEqual(
                atomic_state.reconcile_atomic_json(path)["status"], "postimage_confirmed"
            )

    def test_all_control_state_files_reconcile_each_write_failure_boundary(self) -> None:
        state_names = ("governor.json", "driver.json", "driver.json.durability.json")
        failure_modes = ("before_replace", "after_replace", "directory_fsync", "directory_close")
        for state_name in state_names:
            for failure_mode in failure_modes:
                with self.subTest(state=state_name, failure=failure_mode), tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / state_name
                    kwargs: dict[str, object] = {}
                    patcher = mock.patch.object(atomic_state.os, "fsync", wraps=atomic_state.os.fsync)

                    if failure_mode == "before_replace":
                        kwargs["before_replace"] = lambda _: (_ for _ in ()).throw(
                            RuntimeError("simulated_before_replace")
                        )
                        expected_exception = RuntimeError
                    elif failure_mode == "after_replace":
                        kwargs["after_replace"] = lambda _: (_ for _ in ()).throw(
                            RuntimeError("simulated_after_replace")
                        )
                        expected_exception = RuntimeError
                    elif failure_mode == "directory_fsync":
                        real_fsync = atomic_state.os.fsync
                        directory_calls = 0

                        def fail_target_fsync(fd: int) -> None:
                            nonlocal directory_calls
                            if stat.S_ISDIR(atomic_state.os.fstat(fd).st_mode):
                                directory_calls += 1
                                if directory_calls == 2:
                                    raise OSError(errno.EIO, "simulated target directory fsync")
                            real_fsync(fd)

                        patcher = mock.patch.object(atomic_state.os, "fsync", side_effect=fail_target_fsync)
                        expected_exception = atomic_state.StateDurabilityError
                    else:
                        real_close = atomic_state.os.close
                        directory_calls = 0

                        def fail_target_close(fd: int) -> None:
                            nonlocal directory_calls
                            if stat.S_ISDIR(atomic_state.os.fstat(fd).st_mode):
                                directory_calls += 1
                                if directory_calls == 2:
                                    real_close(fd)
                                    raise OSError(errno.EIO, "simulated target directory close")
                            real_close(fd)

                        patcher = mock.patch.object(atomic_state.os, "close", side_effect=fail_target_close)
                        expected_exception = atomic_state.StateDurabilityError

                    with patcher:
                        with self.assertRaises(expected_exception):
                            atomic_state.atomic_write_json(path, {"state": state_name}, **kwargs)
                    self.assertTrue(atomic_state.has_uncertainty(path))
                    reconciled = atomic_state.reconcile_atomic_json(path)
                    self.assertIn(
                        reconciled["status"],
                        {"preimage_restored", "empty_preimage_restored", "postimage_confirmed"},
                    )
                    self.assertFalse(atomic_state.has_uncertainty(path))

    def test_reconciliation_confirmation_failure_leaves_a_persistent_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "driver.json"

            def crash_after_replace(_: Path) -> None:
                raise RuntimeError("simulated_after_replace")

            with self.assertRaises(RuntimeError):
                atomic_state.atomic_write_json(
                    path, {"status": "verified"}, after_replace=crash_after_replace
                )
            real_sync = atomic_state.fsync_directory
            sync_calls = 0

            def fail_cleanup_sync(directory: Path) -> bool:
                nonlocal sync_calls
                sync_calls += 1
                if sync_calls == 2:
                    raise atomic_state.StateDurabilityError("simulated_reconcile_cleanup_fsync")
                return real_sync(directory)

            with mock.patch.object(
                atomic_state, "fsync_directory", side_effect=fail_cleanup_sync
            ):
                with self.assertRaisesRegex(
                    atomic_state.StateDurabilityError, "reconcile_cleanup"
                ):
                    atomic_state.reconcile_atomic_json(path)
            self.assertTrue(atomic_state.has_uncertainty(path))
            self.assertTrue(atomic_state.has_confirmation(path))
            with self.assertRaises(atomic_state.StateReconciliationRequired):
                atomic_state.read_confirmed_json(path)
            self.assertEqual(
                atomic_state.reconcile_atomic_json(path)["status"], "postimage_confirmed"
            )
            self.assertEqual(atomic_state.read_confirmed_json(path), {"status": "verified"})

    def test_reconciliation_rejects_marker_for_another_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "driver.json"
            atomic_state.atomic_write_json(path, {"status": "verified"})
            marker = {
                "schema": "ceo_atomic_uncertainty_v1",
                "target": "governor.json",
                "previousSha256": atomic_state.state_sha256({}),
                "intendedSha256": atomic_state.state_sha256({"status": "verified"}),
                "transactionId": "fabricated",
            }
            atomic_state.uncertainty_path(path).write_text(
                json.dumps(marker), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                atomic_state.StateReconciliationRequired, "invalid_uncertainty_marker"
            ):
                atomic_state.reconcile_atomic_json(path)

    def test_new_state_is_private_and_existing_private_mode_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            path.chmod(0o400)
            atomic_state.atomic_write_json(path, {"revision": 2})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)

    def test_unsafe_existing_state_mode_fails_closed_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})
            path.chmod(0o644)
            with self.assertRaisesRegex(
                atomic_state.StatePermissionError, "unsafe_state_mode"
            ):
                atomic_state.atomic_write_json(path, {"revision": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"revision": 1})

    def test_confirmed_loader_rejects_missing_malformed_forged_and_pending_receipts(self) -> None:
        cases = ("missing", "malformed", "forged", "pending")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "state.json"
                atomic_state.atomic_write_json(path, {"allowProviderCalls": True})
                receipt_path = atomic_state.confirmation_path(path)
                if case == "missing":
                    receipt_path.unlink()
                elif case == "malformed":
                    receipt_path.write_text("{not-json", encoding="utf-8")
                    receipt_path.chmod(0o600)
                elif case == "forged":
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    receipt["intendedSha256"] = "0" * 64
                    receipt["previousSha256"] = "1" * 64
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    receipt_path.chmod(0o600)
                else:
                    atomic_state.uncertainty_path(path).write_text(
                        atomic_state.confirmation_path(path).read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                    atomic_state.uncertainty_path(path).chmod(0o600)
                with self.assertRaises(atomic_state.StateReconciliationRequired):
                    atomic_state.read_confirmed_json(path)

    def test_confirmed_loader_rejects_target_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"allowProviderCalls": False})
            path.write_text(json.dumps({"allowProviderCalls": True}), encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(
                atomic_state.StateReconciliationRequired, "confirmed_state_hash_mismatch"
            ):
                atomic_state.read_confirmed_json(path)

    def test_confirmed_loader_serializes_with_concurrent_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})
            writer_entered = threading.Event()
            release_writer = threading.Event()

            def pause_before_replace(_: Path) -> None:
                writer_entered.set()
                release_writer.wait(timeout=5)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                writer = pool.submit(
                    atomic_state.atomic_write_json,
                    path,
                    {"revision": 2},
                    before_replace=pause_before_replace,
                )
                self.assertTrue(writer_entered.wait(timeout=5))
                reader = pool.submit(atomic_state.read_confirmed_json, path)
                time.sleep(0.05)
                self.assertFalse(reader.done())
                release_writer.set()
                writer.result(timeout=5)
                self.assertEqual(reader.result(timeout=5), {"revision": 2})

    def test_completed_receipt_never_authorizes_restored_preimage_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governor.json"
            before = {
                "revision": 1,
                "programGlobalBlock": {"active": False},
                "injectedGenerationIds": ["generation-1"],
            }
            after = {
                "revision": 2,
                "programGlobalBlock": {"active": True, "blockerCode": "global-stop"},
                "injectedGenerationIds": ["generation-1", "generation-2"],
            }
            atomic_state.atomic_write_json(path, before)
            atomic_state.atomic_write_json(path, after)
            receipt = json.loads(
                atomic_state.confirmation_path(path).read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["outcome"], "committed_postimage")
            self.assertEqual(receipt["committedSha256"], atomic_state.state_sha256(after))
            self.assertEqual(receipt["previousSha256"], atomic_state.state_sha256(before))

            path.write_bytes(atomic_state.canonical_json(before))
            path.chmod(0o600)
            with self.assertRaisesRegex(
                atomic_state.StateReconciliationRequired, "confirmed_state_hash_mismatch"
            ):
                atomic_state.confirm_atomic_json(path)
            with self.assertRaises(atomic_state.StateReconciliationRequired):
                atomic_state.read_confirmed_json(path)
            with self.assertRaises(atomic_state.StateReconciliationRequired):
                atomic_state.atomic_write_json(path, before)

    def test_concurrent_restart_readers_and_writers_cannot_accept_committed_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governor.json"
            before = {
                "revision": 7,
                "programGlobalBlock": {"active": False},
                "injectedGenerationIds": ["generation-7"],
            }
            after = {
                "revision": 8,
                "programGlobalBlock": {"active": True, "blockerCode": "global-stop"},
                "injectedGenerationIds": ["generation-7", "generation-8"],
            }
            atomic_state.atomic_write_json(path, before)
            atomic_state.atomic_write_json(path, after)
            path.write_bytes(atomic_state.canonical_json(before))
            path.chmod(0o600)

            def attempt(index: int) -> str:
                try:
                    if index % 2:
                        atomic_state.read_confirmed_json(path)
                    else:
                        atomic_state.atomic_write_json(
                            path,
                            before,
                            expected_sha256=atomic_state.state_sha256(before),
                        )
                except atomic_state.StateReconciliationRequired:
                    return "blocked"
                return "unexpected_allow"

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                outcomes = list(pool.map(attempt, range(32)))
            self.assertEqual(outcomes, ["blocked"] * 32)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), before)

    @unittest.skipUnless(sys.platform == "darwin", "macOS ACL probe")
    def test_existing_acl_is_preserved_by_refusing_unsupported_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_state.atomic_write_json(path, {"revision": 1})
            subprocess.run(
                ["chmod", "+a", f"{getpass.getuser()} allow read", str(path)],
                check=True,
            )
            try:
                with self.assertRaisesRegex(
                    atomic_state.StatePermissionError,
                    "state_acl_requires_platform_preserving_writer",
                ):
                    atomic_state.atomic_write_json(path, {"revision": 2})
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"revision": 1})
                self.assertTrue(atomic_state.has_extended_acl(path))
            finally:
                subprocess.run(["chmod", "-a#", "0", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
