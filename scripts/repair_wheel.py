#!/usr/bin/env python3
"""Cross-platform wheel repair script that handles .chug (ChucK plugin) files.

Wheel repair tools only scan platform-standard shared library extensions:
  - macOS (delocate): .dylib, .so
  - Linux (auditwheel): .so
  - Windows (delvewheel): .pyd, .dll

ChucK plugins use the .chug extension, so they are silently skipped during
repair. This script works around the limitation by:

1. Renaming .chug -> platform-native extension inside the wheel
2. Running the platform repair tool on the modified wheel
3. Renaming back to .chug in the repaired wheel

Usage:
  python scripts/repair_wheel.py <wheel> <dest_dir> [--delocate-archs ARCHS]

The platform is auto-detected. On macOS, pass --delocate-archs to forward
the {delocate_archs} placeholder from cibuildwheel.
"""

import argparse
import csv
import hashlib
import io
import os
import platform
import subprocess
import sys
import tempfile
from base64 import urlsafe_b64encode
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

NATIVE_EXT = {
    "darwin": ".dylib",
    "linux": ".so",
    "windows": ".dll",
}


def detect_platform() -> str:
    s = platform.system().lower()
    if s == "darwin":
        return "darwin"
    if s == "linux":
        return "linux"
    if s == "windows":
        return "windows"
    print(f"Unsupported platform: {s}", file=sys.stderr)
    sys.exit(1)


def get_repair_cmd(
    plat: str, wheel: str, dest_dir: str, delocate_archs: str | None
) -> list[str]:
    """Standard repair command (no chugins to handle)."""
    if plat == "darwin":
        cmd = ["delocate-wheel", "-w", dest_dir, "-v", wheel]
        if delocate_archs:
            cmd[1:1] = ["--require-archs", delocate_archs]
        return cmd
    if plat == "linux":
        return ["auditwheel", "repair", "-w", dest_dir, wheel]
    return ["delvewheel", "repair", "-w", dest_dir, wheel]


def get_repair_cmd_with_chugins(
    plat: str,
    wheel: str,
    dest_dir: str,
    delocate_archs: str | None,
    no_mangle_names: list[str],
) -> list[str]:
    """Repair command for wheels with renamed chugin libraries."""
    if plat == "darwin":
        # delocate scans all .dylib files it finds -- no extra flag needed
        cmd = ["delocate-wheel", "-w", dest_dir, "-v", wheel]
        if delocate_archs:
            cmd[1:1] = ["--require-archs", delocate_archs]
        return cmd
    if plat == "linux":
        # auditwheel scans all .so files it finds -- no extra flag needed
        return ["auditwheel", "repair", "-w", dest_dir, wheel]
    # windows: delvewheel needs --analyze-existing to scan non-.pyd DLLs,
    # and --no-mangle to prevent renaming the chugin DLLs
    no_mangle = ";".join(sorted(no_mangle_names))
    return [
        "delvewheel", "repair",
        "--analyze-existing",
        "--no-mangle", no_mangle,
        "-w", dest_dir,
        wheel,
    ]


def _record_path(zf: ZipFile) -> str | None:
    """Find the RECORD file path inside a wheel."""
    for name in zf.namelist():
        if name.endswith(".dist-info/RECORD"):
            return name
    return None


def _hash_digest(data: bytes) -> str:
    """Compute wheel RECORD hash: sha256=<urlsafe-b64-nopad>."""
    digest = hashlib.sha256(data).digest()
    return "sha256=" + urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _regenerate_record(zf_out: ZipFile, record_path: str) -> None:
    """Write a fresh RECORD into the wheel."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for item in zf_out.infolist():
        if item.filename == record_path:
            continue
        data = zf_out.read(item.filename)
        writer.writerow([item.filename, _hash_digest(data), len(data)])
    # RECORD itself has no hash
    writer.writerow([record_path, "", ""])
    zf_out.writestr(record_path, buf.getvalue())


def _validate_record(wheel_path: str) -> None:
    """Validate that the wheel RECORD matches actual ZIP contents.

    Raises SystemExit on any mismatch (smuggled files, dangling entries,
    hash or size mismatches).

    See: https://blog.pypi.org/posts/2025-08-07-wheel-archive-confusion-attacks/
    """
    errors: list[str] = []
    with ZipFile(wheel_path, "r") as zf:
        record_name = _record_path(zf)
        if record_name is None:
            print(f"RECORD validation FAILED: no RECORD in {wheel_path}", file=sys.stderr)
            sys.exit(1)

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

        for name in sorted(actual_files - recorded_files):
            errors.append(f"file in ZIP but not in RECORD: {name}")
        for name in sorted(recorded_files - actual_files):
            errors.append(f"file in RECORD but not in ZIP: {name}")

        for name in sorted(actual_files & recorded_files):
            data = zf.read(name)
            exp_hash, exp_size = recorded[name]
            if exp_hash and _hash_digest(data) != exp_hash:
                errors.append(f"hash mismatch: {name}")
            if exp_size and str(len(data)) != exp_size:
                errors.append(f"size mismatch: {name}")

    if errors:
        print(f"RECORD validation FAILED for {wheel_path}:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        sys.exit(1)
    print(f"RECORD validation passed: {wheel_path}")


def rename_in_wheel(
    src_wheel: str,
    dst_wheel: str,
    old_ext: str,
    new_ext: str,
    only_stems: set[str] | None = None,
) -> set[str]:
    """Copy wheel, renaming files matching old_ext -> new_ext.

    Args:
        only_stems: If provided, only rename files whose stem is in this set.
                    This prevents renaming bundled dependency libraries that
                    the repair tool added.

    Returns the set of stems that were renamed.
    """
    renamed_stems: set[str] = set()
    with ZipFile(src_wheel, "r") as zin, ZipFile(dst_wheel, "w", ZIP_DEFLATED) as zout:
        record_path = _record_path(zin)
        for item in zin.infolist():
            data = zin.read(item.filename)
            stem = Path(item.filename).stem
            should_rename = (
                item.filename.endswith(old_ext)
                and (only_stems is None or stem in only_stems)
            )
            if should_rename:
                renamed_stems.add(stem)
                new_name = item.filename[: -len(old_ext)] + new_ext
                new_item = ZipInfo(new_name)
                new_item.compress_type = ZIP_DEFLATED
                new_item.external_attr = item.external_attr
                zout.writestr(new_item, data)
            elif item.filename == record_path:
                # Skip RECORD -- we regenerate it below
                continue
            else:
                new_item = ZipInfo(item.filename)
                new_item.compress_type = ZIP_DEFLATED
                new_item.external_attr = item.external_attr
                zout.writestr(new_item, data)
        if record_path:
            _regenerate_record(zout, record_path)
    return renamed_stems


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair wheel with .chug support")
    parser.add_argument("wheel", help="Path to the wheel file")
    parser.add_argument("dest_dir", help="Output directory for repaired wheel")
    parser.add_argument(
        "--delocate-archs",
        default=None,
        help="Architecture string for delocate (macOS only)",
    )
    args = parser.parse_args()

    plat = detect_platform()
    native_ext = NATIVE_EXT[plat]

    # Check if the wheel contains any .chug files
    has_chugins = False
    with ZipFile(args.wheel, "r") as zf:
        has_chugins = any(n.endswith(".chug") for n in zf.namelist())

    if not has_chugins:
        # No chugins -- run the standard repair tool directly
        cmd = get_repair_cmd(plat, args.wheel, args.dest_dir, args.delocate_archs)
        subprocess.check_call(cmd)
        # Validate the repaired wheel's RECORD
        for whl in Path(args.dest_dir).glob("*.whl"):
            _validate_record(str(whl))
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Step 1: Rename .chug -> native extension in a copy of the wheel
        renamed_wheel = str(tmp_path / os.path.basename(args.wheel))
        chug_stems = rename_in_wheel(args.wheel, renamed_wheel, ".chug", native_ext)
        print(f"Renamed {len(chug_stems)} .chug -> {native_ext}: {sorted(chug_stems)}")

        # Step 2: Run the platform repair tool on the renamed wheel
        repaired_dir = str(tmp_path / "repaired")
        os.makedirs(repaired_dir)
        no_mangle_names = [f"{s}{native_ext}" for s in chug_stems]
        cmd = get_repair_cmd_with_chugins(
            plat, renamed_wheel, repaired_dir,
            args.delocate_archs, no_mangle_names,
        )
        subprocess.check_call(cmd)

        # Find the single repaired wheel
        repaired_wheels = list(Path(repaired_dir).glob("*.whl"))
        if len(repaired_wheels) != 1:
            print(
                f"Expected 1 repaired wheel, found {len(repaired_wheels)}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Step 3: Rename native extension -> .chug ONLY for original chugins
        # (the repair tool may have added new .dylib/.so/.dll dependencies
        # that must keep their native extension)
        os.makedirs(args.dest_dir, exist_ok=True)
        final_wheel = os.path.join(args.dest_dir, repaired_wheels[0].name)
        rename_in_wheel(
            str(repaired_wheels[0]), final_wheel, native_ext, ".chug",
            only_stems=chug_stems,
        )
        with ZipFile(final_wheel, "r") as zf:
            chug_count = sum(1 for n in zf.namelist() if n.endswith(".chug"))
        print(f"Final wheel: {final_wheel} ({chug_count} .chug files)")

        # Validate the final wheel's RECORD
        _validate_record(final_wheel)


if __name__ == "__main__":
    main()
