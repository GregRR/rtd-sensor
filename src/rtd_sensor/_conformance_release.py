# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Build and verify deterministic conformance release bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from . import _conformance_artifacts

_BUNDLE_PREFIX = "rtd-sensor-conformance"
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _load_manifest(conformance_dir: Path) -> dict[str, Any]:
    path = conformance_dir / "manifest.json"
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError("Conformance manifest must be a JSON object")
    return document


def _manifest_files(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("Conformance manifest files must be a JSON array")
    entries: list[dict[str, Any]] = []
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("Conformance manifest file entries must be objects")
        entries.append(entry)
    return entries


def release_tree_errors(conformance_dir: Path) -> tuple[str, ...]:
    """Return integrity errors for the committed machine-readable release tree."""
    errors: list[str] = []
    try:
        manifest = _load_manifest(conformance_dir)
        entries = _manifest_files(manifest)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return (str(exc),)

    expected_version = _conformance_artifacts._project_version()
    if manifest.get("rtd_sensor_version") != expected_version:
        errors.append("manifest rtd_sensor_version does not match the project version")
    if manifest.get("contract_version") != _conformance_artifacts._CONTRACT_VERSION:
        errors.append("manifest contract_version does not match the implementation")
    if manifest.get("contract_status") != _conformance_artifacts._CONTRACT_STATUS:
        errors.append("manifest contract_status does not match the implementation")

    seen_paths: set[str] = set()
    for entry in entries:
        relative_path = entry.get("path")
        expected_sha256 = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if not isinstance(relative_path, str):
            errors.append("manifest contains a file entry without a string path")
            continue
        normalized_path = PurePosixPath(relative_path)
        if (
            normalized_path.is_absolute()
            or ".." in normalized_path.parts
            or normalized_path.as_posix() != relative_path
        ):
            errors.append(f"manifest contains unsafe path: {relative_path}")
            continue
        if relative_path in seen_paths:
            errors.append(f"manifest contains duplicate path: {relative_path}")
            continue
        seen_paths.add(relative_path)

        path = conformance_dir / relative_path
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            errors.append(f"manifest file is missing: {relative_path}")
            continue

        if len(content) != expected_size:
            errors.append(f"manifest size mismatch: {relative_path}")
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            errors.append(f"manifest sha256 mismatch: {relative_path}")

    return tuple(errors)


def _bundle_filename(manifest: dict[str, Any]) -> str:
    contract_version = manifest["contract_version"]
    package_version = manifest["rtd_sensor_version"]
    return f"{_BUNDLE_PREFIX}-v{contract_version}-{package_version}.zip"


def _zip_info(archive_path: str) -> ZipInfo:
    info = ZipInfo(archive_path, date_time=_ZIP_TIMESTAMP)
    info.compress_type = ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build_release_bundle(conformance_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    """Build a deterministic ZIP and SHA-256 sidecar for conformance v1."""
    errors = release_tree_errors(conformance_dir)
    if errors:
        raise ValueError("; ".join(errors))

    manifest = _load_manifest(conformance_dir)
    entries = _manifest_files(manifest)
    bundle_name = _bundle_filename(manifest)
    bundle_root = bundle_name.removesuffix(".zip")

    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / bundle_name
    with ZipFile(bundle_path, mode="w", compression=ZIP_STORED) as archive:
        manifest_bytes = (conformance_dir / "manifest.json").read_bytes()
        archive.writestr(_zip_info(f"{bundle_root}/manifest.json"), manifest_bytes)
        for entry in entries:
            relative_path = entry["path"]
            assert isinstance(relative_path, str)
            content = (conformance_dir / relative_path).read_bytes()
            archive.writestr(
                _zip_info(f"{bundle_root}/{relative_path}"),
                content,
            )

    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    checksum_path = output_dir / f"{bundle_name}.sha256"
    checksum_path.write_text(
        f"{digest}  {bundle_name}\n",
        encoding="utf-8",
        newline="\n",
    )
    return bundle_path, checksum_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify or build the rtd-sensor conformance release bundle."
    )
    parser.add_argument(
        "--conformance-dir",
        type=Path,
        default=Path("conformance/v1"),
        help="Directory containing the committed conformance-v1 tree.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Directory for the release ZIP and SHA-256 sidecar.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify manifest integrity without building release assets.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run release-tree verification or deterministic bundle creation."""
    arguments = _parser().parse_args(argv)
    errors = release_tree_errors(arguments.conformance_dir)
    if errors:
        for error in errors:
            print(error)
        return 1
    if arguments.check:
        return 0

    bundle_path, checksum_path = build_release_bundle(
        arguments.conformance_dir,
        arguments.output_dir,
    )
    print(bundle_path)
    print(checksum_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
