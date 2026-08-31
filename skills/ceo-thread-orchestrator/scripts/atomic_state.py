#!/usr/bin/env python3
"""Locked, atomic JSON state persistence with optional compare-and-swap."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import uuid
import re
import stat
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

try:
    import fcntl  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised by native Windows CI.
    fcntl = None
try:
    import msvcrt  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - non-Windows platforms.
    msvcrt = None


class StateConflictError(RuntimeError):
    """The state changed after the caller read it."""


class StateDurabilityError(RuntimeError):
    """Atomic replacement completed but durable directory commit was not confirmed."""


class StateReconciliationRequired(StateDurabilityError):
    """A prior atomic replacement has an unresolved durability marker."""


class StatePermissionError(PermissionError):
    """A state file has an unsafe mode or cannot preserve its owner boundary."""


UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "EINVAL", None),
        getattr(errno, "ENOTSUP", None),
        getattr(errno, "EOPNOTSUPP", None),
    )
    if value is not None
)
UNCERTAINTY_SCHEMA = "ceo_atomic_uncertainty_v1"
CONFIRMATION_SCHEMA = "ceo_atomic_confirmation_v2"


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def state_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _read_json_unchecked(path: Path) -> dict[str, Any]:
    try:
        secure_target_mode(path)
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def read_json(path: Path) -> dict[str, Any]:
    if has_uncertainty(path):
        raise StateReconciliationRequired(f"state_reconciliation_required:{path}")
    if has_confirmation(path):
        confirm_atomic_json(path)
    return _read_json_unchecked(path)


def _read_confirmed_json_unlocked(path: Path) -> dict[str, Any]:
    target_exists = path.exists()
    pending_exists = has_uncertainty(path)
    confirmed_exists = has_confirmation(path)
    if not target_exists and not pending_exists and not confirmed_exists:
        return {}
    if pending_exists:
        raise StateReconciliationRequired(f"state_reconciliation_required:{path}")
    if not target_exists:
        raise StateReconciliationRequired(f"confirmed_state_target_missing:{path}")
    if not confirmed_exists:
        raise StateReconciliationRequired(f"confirmed_state_receipt_missing:{path}")
    confirm_atomic_json(path)
    return _read_json_unchecked(path)


def read_confirmed_json(path: Path) -> dict[str, Any]:
    """Read authorization state and its receipt under one exact state lock."""

    with state_lock(path):
        return _read_confirmed_json_unlocked(path)


def fsync_directory(path: Path) -> bool:
    """Confirm directory durability, returning False only for documented unsupported filesystems."""

    try:
        directory_fd = os.open(path, os.O_RDONLY)
    except OSError as exc:
        raise StateDurabilityError(f"directory_open_failed:{path}:{exc.errno}") from exc
    durability_error: BaseException | None = None
    result = True
    try:
        try:
            os.fsync(directory_fd)
        except OSError as exc:
            if exc.errno in UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS:
                result = False
            else:
                durability_error = StateDurabilityError(
                    f"directory_fsync_failed:{path}:{exc.errno}"
                )
    finally:
        try:
            os.close(directory_fd)
        except OSError as exc:
            if durability_error is None:
                durability_error = StateDurabilityError(
                    f"directory_close_failed:{path}:{exc.errno}"
                )
    if durability_error is not None:
        raise durability_error
    return result


def uncertainty_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.uncertain")


def confirmation_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.confirmed")


def has_uncertainty(path: Path) -> bool:
    return uncertainty_path(path).exists()


def has_confirmation(path: Path) -> bool:
    return confirmation_path(path).exists()


def has_extended_acl(path: Path) -> bool:
    if not path.exists():
        return False
    if sys.platform == "darwin":
        completed = subprocess.run(
            ["/bin/ls", "-lde", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return any(re.match(r"^\s*\d+:\s", line) for line in completed.stdout.splitlines()[1:])
    if hasattr(os, "listxattr"):
        return any(
            name in {"system.posix_acl_access", "system.posix_acl_default"}
            for name in os.listxattr(path)
        )
    return False


def secure_target_mode(path: Path) -> int:
    try:
        metadata = path.stat()
    except FileNotFoundError:
        return 0o600
    mode = stat.S_IMODE(metadata.st_mode)
    if mode & 0o077:
        raise StatePermissionError(f"unsafe_state_mode:{path}:{mode:04o}")
    if hasattr(os, "geteuid") and metadata.st_uid != os.geteuid():
        raise StatePermissionError(f"state_owner_mismatch:{path}:{metadata.st_uid}")
    if has_extended_acl(path):
        raise StatePermissionError(f"state_acl_requires_platform_preserving_writer:{path}")
    return mode


def set_file_mode(file_descriptor: int, path: Path, mode: int) -> None:
    if hasattr(os, "fchmod"):
        os.fchmod(file_descriptor, mode)
    else:  # pragma: no cover - native Windows CI boundary.
        os.chmod(path, mode)


def _replace_bytes(
    path: Path,
    payload: bytes,
    before_replace: Callable[[Path], None] | None = None,
    after_replace: Callable[[Path], None] | None = None,
) -> bool:
    target_mode = secure_target_mode(path)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("xb") as temp_file:
            set_file_mode(temp_file.fileno(), temp_path, target_mode)
            temp_file.write(payload)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        if before_replace:
            before_replace(temp_path)
        os.replace(temp_path, path)
        if after_replace:
            after_replace(path)
        return fsync_directory(path.parent)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def remove_pending_marker(
    marker_path: Path, marker_payload: bytes, *, failure_code: str
) -> None:
    """Remove a pending marker only when its directory commit is durable."""

    try:
        marker_path.unlink()
        if not fsync_directory(marker_path.parent):
            raise StateDurabilityError(
                f"directory_fsync_unsupported:{marker_path.parent}:{failure_code}"
            )
    except BaseException as cleanup_exc:
        try:
            restored = _replace_bytes(marker_path, marker_payload)
            if not restored:
                raise StateDurabilityError(
                    f"directory_fsync_unsupported:{marker_path.parent}:pending_marker_restore"
                )
        except BaseException as restore_exc:
            raise StateDurabilityError(
                f"{failure_code}:pending_marker_restore_failed:{marker_path}"
            ) from restore_exc
        if isinstance(cleanup_exc, StateDurabilityError):
            raise cleanup_exc
        raise StateDurabilityError(f"{failure_code}:{marker_path}") from cleanup_exc


def replace_from_unique_temp(
    path: Path,
    payload: bytes,
    before_replace: Callable[[Path], None] | None = None,
    after_replace: Callable[[Path], None] | None = None,
    *,
    previous_sha256: str,
) -> bool:
    marker_path = uncertainty_path(path)
    intended_sha256 = hashlib.sha256(payload).hexdigest()
    marker_payload = canonical_json(
        {
            "schema": UNCERTAINTY_SCHEMA,
            "target": path.name,
            "previousSha256": previous_sha256,
            "intendedSha256": intended_sha256,
            "transactionId": uuid.uuid4().hex,
        }
    )
    if has_uncertainty(path):
        raise StateReconciliationRequired(f"state_reconciliation_required:{path}")
    marker_durable = _replace_bytes(marker_path, marker_payload)
    if not marker_durable:
        raise StateDurabilityError(
            f"directory_fsync_unsupported:{path.parent}:uncertainty_marker_not_durable"
        )
    try:
        durable = _replace_bytes(path, payload, before_replace, after_replace)
        if not durable:
            raise StateDurabilityError(
                f"directory_fsync_unsupported:{path.parent}:state_not_confirmed_durable"
            )
    except BaseException:
        raise
    try:
        marker = json.loads(marker_payload.decode("utf-8"))
        committed_payload = canonical_json(
            marker
            | {
                "schema": CONFIRMATION_SCHEMA,
                "outcome": "committed_postimage",
                "committedSha256": intended_sha256,
            }
        )
        if not _replace_bytes(confirmation_path(path), committed_payload):
            raise StateDurabilityError(
                f"directory_fsync_unsupported:{path.parent}:committed_receipt_not_durable"
            )
        remove_pending_marker(
            marker_path,
            marker_payload,
            failure_code="pending_marker_cleanup_not_durable",
        )
    except StateDurabilityError:
        raise
    except BaseException as exc:
        raise StateDurabilityError(f"uncertainty_marker_confirmation_failed:{path}") from exc
    return True


def reconcile_atomic_json(path: Path) -> dict[str, Any]:
    """Commit an intended postimage or restore the last already-confirmed preimage."""

    with state_lock(path):
        marker_path = uncertainty_path(path)
        if not marker_path.exists():
            return {"status": "not_required", "sha256": state_sha256(read_json(path))}
        try:
            marker_payload = marker_path.read_bytes()
            marker = json.loads(marker_payload.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StateReconciliationRequired(f"invalid_uncertainty_marker:{path}") from exc
        if (
            not isinstance(marker, dict)
            or marker.get("schema") != UNCERTAINTY_SCHEMA
            or marker.get("target") != path.name
            or not isinstance(marker.get("transactionId"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", str(marker.get("previousSha256") or ""))
            or not re.fullmatch(r"[0-9a-f]{64}", str(marker.get("intendedSha256") or ""))
        ):
            raise StateReconciliationRequired(f"invalid_uncertainty_marker:{path}")
        current = _read_json_unchecked(path)
        current_sha256 = state_sha256(current)
        allowed = {marker.get("previousSha256"), marker.get("intendedSha256")}
        if current_sha256 not in allowed:
            raise StateReconciliationRequired(f"uncertain_state_hash_mismatch:{path}")
        if current_sha256 == marker.get("previousSha256"):
            prior_confirmation = confirmation_path(path)
            if path.exists():
                if not prior_confirmation.exists():
                    raise StateReconciliationRequired(
                        f"preimage_has_no_prior_confirmation:{path}"
                    )
                prior = confirm_atomic_json(path)
                if prior.get("sha256") != current_sha256:
                    raise StateReconciliationRequired(
                        f"preimage_prior_confirmation_mismatch:{path}"
                    )
            elif prior_confirmation.exists():
                raise StateReconciliationRequired(
                    f"missing_preimage_has_stale_confirmation:{path}"
                )
            try:
                remove_pending_marker(
                    marker_path,
                    marker_payload,
                    failure_code="preimage_restore_cleanup_not_durable",
                )
            except StateDurabilityError:
                raise
            except BaseException as exc:
                raise StateDurabilityError(
                    f"uncertainty_marker_preimage_restore_failed:{path}"
                ) from exc
            return {
                "status": "preimage_restored" if path.exists() else "empty_preimage_restored",
                "sha256": current_sha256,
                "transactionId": marker.get("transactionId"),
            }

        committed_payload = canonical_json(
            marker
            | {
                "schema": CONFIRMATION_SCHEMA,
                "outcome": "committed_postimage",
                "committedSha256": marker["intendedSha256"],
            }
        )
        try:
            if not _replace_bytes(confirmation_path(path), committed_payload):
                raise StateDurabilityError(
                    f"directory_fsync_unsupported:{path.parent}:reconcile_receipt"
                )
            remove_pending_marker(
                marker_path,
                marker_payload,
                failure_code="reconcile_pending_cleanup_not_durable",
            )
        except StateDurabilityError:
            raise
        except BaseException as exc:
            raise StateDurabilityError(
                f"uncertainty_marker_reconcile_confirmation_failed:{path}"
            ) from exc
        return {
            "status": "postimage_confirmed",
            "sha256": current_sha256,
            "transactionId": marker.get("transactionId"),
        }


def confirm_atomic_json(path: Path) -> dict[str, Any]:
    """Validate the persistent confirmed transaction receipt against target bytes."""

    receipt_path = confirmation_path(path)
    if not receipt_path.exists():
        return {"status": "not_required", "sha256": state_sha256(_read_json_unchecked(path))}
    try:
        secure_target_mode(receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateReconciliationRequired(f"invalid_confirmation_marker:{path}") from exc
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != CONFIRMATION_SCHEMA
        or receipt.get("target") != path.name
        or receipt.get("outcome") != "committed_postimage"
        or not re.fullmatch(r"[0-9a-f]{32}", str(receipt.get("transactionId") or ""))
        or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("previousSha256") or ""))
        or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("intendedSha256") or ""))
        or receipt.get("committedSha256") != receipt.get("intendedSha256")
    ):
        raise StateReconciliationRequired(f"invalid_confirmation_marker:{path}")
    current_sha256 = state_sha256(_read_json_unchecked(path))
    if current_sha256 != receipt["committedSha256"]:
        raise StateReconciliationRequired(f"confirmed_state_hash_mismatch:{path}")
    if not fsync_directory(path.parent):
        raise StateDurabilityError(f"directory_fsync_unsupported:{path.parent}:confirm")
    return {
        "status": "postimage_confirmed",
        "sha256": current_sha256,
        "transactionId": receipt.get("transactionId"),
    }


@contextmanager
def state_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    with lock_path.open("a+b") as lock_file:
        set_file_mode(lock_file.fileno(), lock_path, 0o600)
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:  # pragma: no cover - native Windows CI boundary.
            if lock_file.seek(0, os.SEEK_END) == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            raise StatePermissionError("platform_lock_implementation_unavailable")
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None:  # pragma: no cover - native Windows CI boundary.
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
    *,
    expected_sha256: str | None = None,
    before_replace: Callable[[Path], None] | None = None,
    after_replace: Callable[[Path], None] | None = None,
) -> str:
    """Persist one JSON object atomically; reject a stale expected digest."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with state_lock(path):
        current = _read_confirmed_json_unlocked(path)
        current_sha256 = state_sha256(current)
        if expected_sha256 is not None and current_sha256 != expected_sha256:
            raise StateConflictError(
                json.dumps(
                    {
                        "code": "state_compare_and_swap_conflict",
                        "expectedSha256": expected_sha256,
                        "actualSha256": current_sha256,
                    },
                    sort_keys=True,
                )
            )

        payload = canonical_json(value)
        durable = replace_from_unique_temp(
            path,
            payload,
            before_replace,
            after_replace,
            previous_sha256=current_sha256,
        )
        if not durable:
            raise StateDurabilityError(
                f"directory_fsync_unsupported:{path.parent}:state_not_confirmed_durable"
            )
        return hashlib.sha256(payload).hexdigest()


def locked_update_json(path: Path, update: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    """Read-modify-write one state while holding its advisory lock."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with state_lock(path):
        current = _read_confirmed_json_unlocked(path)
        updated = update(current)
        if not isinstance(updated, dict):
            raise TypeError("state update must return a JSON object")
        payload = canonical_json(updated)
        durable = replace_from_unique_temp(
            path, payload, previous_sha256=state_sha256(current)
        )
        if not durable:
            raise StateDurabilityError(
                f"directory_fsync_unsupported:{path.parent}:state_not_confirmed_durable"
            )
        return updated
