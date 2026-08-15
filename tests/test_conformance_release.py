# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from rtd_sensor import _conformance_artifacts, _conformance_release

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFORMANCE_DIR = _REPO_ROOT / "conformance" / "v1"
_SCHEMA_DIR = _CONFORMANCE_DIR / "schemas"
_EXAMPLE_DIR = _CONFORMANCE_DIR / "examples"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    assert isinstance(document, dict)
    return document


def test_release_manifest_is_valid_and_records_stable_contract_status() -> None:
    schema = _load_json(_SCHEMA_DIR / "conformance-manifest.schema.json")
    manifest = _load_json(_CONFORMANCE_DIR / "manifest.json")

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)
    assert manifest["contract_status"] == "stable"
    assert manifest["contract_version"] == 1
    assert manifest["rtd_sensor_version"] == _conformance_artifacts._project_version()


def test_release_manifest_covers_static_and_generated_machine_readable_files() -> None:
    manifest = _load_json(_CONFORMANCE_DIR / "manifest.json")
    entries = manifest["files"]
    assert isinstance(entries, list)
    manifest_paths = {entry["path"] for entry in entries}

    actual_paths = {
        path.relative_to(_CONFORMANCE_DIR).as_posix()
        for path in _CONFORMANCE_DIR.rglob("*.json")
        if path.name != "manifest.json"
    }
    assert manifest_paths == actual_paths
    assert _conformance_release.release_tree_errors(_CONFORMANCE_DIR) == ()


def test_release_tree_verification_detects_modified_file(tmp_path: Path) -> None:
    _conformance_artifacts.write_generated_artifacts(tmp_path)
    static_artifacts = _conformance_artifacts._static_release_json_artifacts()
    for relative_path, content in static_artifacts.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    assert _conformance_release.release_tree_errors(tmp_path) == ()
    model_path = tmp_path / "models.json"
    model_path.write_text("{}\n", encoding="utf-8")

    assert _conformance_release.release_tree_errors(tmp_path) == (
        "manifest size mismatch: models.json",
        "manifest sha256 mismatch: models.json",
    )


def test_release_tree_rejects_unsafe_manifest_path(tmp_path: Path) -> None:
    manifest = _load_json(_CONFORMANCE_DIR / "manifest.json")
    entries = manifest["files"]
    assert isinstance(entries, list)
    first_entry = entries[0]
    assert isinstance(first_entry, dict)
    first_entry["path"] = "../outside.json"
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    errors = _conformance_release.release_tree_errors(tmp_path)
    assert "manifest contains unsafe path: ../outside.json" in errors


def test_release_bundle_is_deterministic_and_matches_manifest(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_bundle, first_checksum = _conformance_release.build_release_bundle(
        _CONFORMANCE_DIR,
        first_dir,
    )
    second_bundle, second_checksum = _conformance_release.build_release_bundle(
        _CONFORMANCE_DIR,
        second_dir,
    )

    assert first_bundle.read_bytes() == second_bundle.read_bytes()
    assert first_checksum.read_text(encoding="utf-8") == second_checksum.read_text(
        encoding="utf-8"
    )

    digest = hashlib.sha256(first_bundle.read_bytes()).hexdigest()
    assert first_checksum.read_text(encoding="utf-8") == (
        f"{digest}  {first_bundle.name}\n"
    )

    manifest = _load_json(_CONFORMANCE_DIR / "manifest.json")
    entries = manifest["files"]
    assert isinstance(entries, list)
    expected_suffixes = {"manifest.json"}
    expected_suffixes.update(entry["path"] for entry in entries)
    bundle_root = first_bundle.name.removesuffix(".zip")

    with ZipFile(first_bundle) as archive:
        archived_suffixes = {
            name.removeprefix(f"{bundle_root}/") for name in archive.namelist()
        }
        assert archived_suffixes == expected_suffixes
        assert all(
            info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()
        )


def test_example_conformance_claim_validates() -> None:
    schema = _load_json(_SCHEMA_DIR / "conformance-claim.schema.json")
    example = _load_json(_EXAMPLE_DIR / "example-conformance-claim.json")

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)


def test_custom_fixture_claim_cannot_use_builtin_binary32_profile() -> None:
    schema = _load_json(_SCHEMA_DIR / "conformance-claim.schema.json")
    claim = {
        "artifact_type": "conformance_claim",
        "format_version": 1,
        "contract_version": 1,
        "claims": [
            {
                "capability_id": "conversion.temperature_to_resistance",
                "fixture_ids": ["custom_cvd_two_sided"],
                "acceptance_profile": "binary32_compatible",
            }
        ],
    }

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(claim)
