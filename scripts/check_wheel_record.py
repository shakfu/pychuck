#!/usr/bin/env python3
"""Validate that wheel RECORD files match actual ZIP contents.

Checks that:
  1. Every file in the ZIP is listed in RECORD (no smuggled files)
  2. Every file in RECORD exists in the ZIP (no dangling entries)
  3. SHA256 hashes match for all recorded files
  4. File sizes match for all recorded files
  5. No directory entries (names ending in "/") appear in the ZIP or RECORD --
     these carry the empty-content hash and pass a naive hash check, but PyPI's
     strict parser rejects them as "file contents do not match RECORD"

See: https://blog.pypi.org/posts/2025-08-07-wheel-archive-confusion-attacks/

Usage:
  python scripts/check_wheel_record.py dist/*.whl
  python scripts/check_wheel_record.py wheelhouse/*.whl
"""

import csv
import hashlib
import io
import sys
from base64 import urlsafe_b64encode
from pathlib import Path
from zipfile import ZipFile


def hash_sha256(data: bytes) -> str:
    """Compute sha256=<urlsafe-b64-nopad> digest matching wheel RECORD format."""
    digest = hashlib.sha256(data).digest()
    return "sha256=" + urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def find_record(zf: ZipFile) -> str | None:
    """Find the RECORD file path inside a wheel."""
    for name in zf.namelist():
        if name.endswith(".dist-info/RECORD"):
            return name
    return None


def validate_wheel(path: str) -> list[str]:
    """Validate a single wheel's RECORD against its ZIP contents.

    Returns a list of error strings (empty means valid).
    """
    errors: list[str] = []

    with ZipFile(path, "r") as zf:
        record_name = find_record(zf)
        if record_name is None:
            return [f"no RECORD file found in {path}"]

        # Parse RECORD
        record_data = zf.read(record_name).decode("utf-8")
        recorded: dict[str, tuple[str, str]] = {}
        for row in csv.reader(io.StringIO(record_data)):
            if not row or row[0] == record_name:
                continue
            name = row[0]
            file_hash = row[1] if len(row) > 1 else ""
            file_size = row[2] if len(row) > 2 else ""
            recorded[name] = (file_hash, file_size)

        actual_files = {n for n in zf.namelist() if n != record_name}
        recorded_files = set(recorded.keys())

        # Reject directory entries (names ending in "/"). Canonical wheels
        # contain only files. A directory entry carries the empty-content hash
        # in RECORD, so it slips past the hash/size checks below, but PyPI's
        # strict parser rejects it as "file contents do not match RECORD".
        for name in sorted(n for n in actual_files if n.endswith("/")):
            errors.append(f"directory entry in ZIP (not allowed): {name}")
        for name in sorted(n for n in recorded_files if n.endswith("/")):
            errors.append(f"directory entry in RECORD (not allowed): {name}")

        # Check for files in ZIP but not in RECORD (smuggled files)
        extra = sorted(actual_files - recorded_files)
        for name in extra:
            errors.append(f"file in ZIP but not in RECORD: {name}")

        # Check for files in RECORD but not in ZIP (dangling entries)
        missing = sorted(recorded_files - actual_files)
        for name in missing:
            errors.append(f"file in RECORD but not in ZIP: {name}")

        # Verify hashes and sizes for files present in both
        for name in sorted(actual_files & recorded_files):
            data = zf.read(name)
            exp_hash, exp_size = recorded[name]

            if exp_hash:
                actual_hash = hash_sha256(data)
                if actual_hash != exp_hash:
                    errors.append(
                        f"hash mismatch: {name} "
                        f"(expected {exp_hash}, got {actual_hash})"
                    )

            if exp_size:
                actual_size = str(len(data))
                if actual_size != exp_size:
                    errors.append(
                        f"size mismatch: {name} "
                        f"(expected {exp_size}, got {actual_size})"
                    )

    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <wheel> [<wheel> ...]", file=sys.stderr)
        sys.exit(2)

    wheels = sys.argv[1:]
    total_errors = 0

    for whl in wheels:
        if not Path(whl).exists():
            print(f"SKIP {whl} (not found)")
            continue

        errors = validate_wheel(whl)
        if errors:
            print(f"FAIL {whl}")
            for err in errors:
                print(f"  {err}")
            total_errors += len(errors)
        else:
            print(f"OK   {whl}")

    if total_errors:
        print(f"\n{total_errors} error(s) found")
        sys.exit(1)
    else:
        print(f"\nAll {len(wheels)} wheel(s) passed RECORD validation")


if __name__ == "__main__":
    main()
