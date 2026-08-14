# Release checklist

Use this checklist for every `rtd-sensor` release. The goal is to keep the
package metadata, citation metadata, documentation, Git tag, GitHub Release, and
PyPI release synchronized.

## 1. Prepare release metadata

- Update `project.version` in `pyproject.toml`.
- Update `uv.lock` if the project metadata change requires it.
- Move the release notes from `Unreleased` into a dated version section in
  `CHANGELOG.md`.
- Update `version` in `CITATION.cff` to the same release version.
- Update `date-released` in `CITATION.cff` to the release date in `YYYY-MM-DD`
  format.
- Regenerate the conformance artifacts after the version change so every
  generated JSON file and `conformance/v1/manifest.json` record the release
  version:

  ```bash
  uv run python -m rtd_sensor._conformance_artifacts
  ```

Do not tag the release while `pyproject.toml`, `CHANGELOG.md`, and
`CITATION.cff` disagree about the release.

## 2. Audit documentation consistency

Before tagging, review the README, DESIGN, ROADMAP, package metadata, citation
metadata, source comments, and tests for documentation drift.

Confirm that:

- the README Scope and `docs/DESIGN.md` describe the same currently supported
  built-in RTD characteristics;
- `docs/ROADMAP.md` does not describe already-shipped functionality as planned
  or future work;
- `pyproject.toml` metadata accurately describes the current package scope;
- `CITATION.cff` identifies the current release version and release date;
- current examples and source comments use the `rtd_sensor` namespace; and
- references to `pt100-core` or the legacy `rtd` namespace occur only where
  historical or migration context requires them.

A useful legacy-name audit is:

```bash
grep -RInE \
  'rtd\.(pt100|pt500|pt1000|ni1000|ni1000_tk5000|ni120|simulation|tolerance|uncertainty)|from rtd import|pt100-core' \
  README.md CHANGELOG.md docs src tests
```

Review every match rather than requiring zero matches: migration examples and
historical changelog entries are intentionally retained.

When a release adds, removes, or changes an RTD characteristic or major
capability, explicitly review every capability inventory rather than assuming
search-and-replace will catch semantic drift.

## 3. Run the release gate

From a clean working tree, run:

```bash
uv lock --check
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run python -m rtd_sensor._conformance_artifacts --check
uv run python -m rtd_sensor._conformance_release --check
git diff --check
git status --short
```

All checks must pass and the working tree must be clean before tagging.

## 4. Build and smoke-test distributions and conformance assets

Build the Python release artifacts without development-only uv source
overrides, then build the deterministic conformance bundle from the verified
manifest:

```bash
rm -rf dist
uv build --no-sources
uv run python -m rtd_sensor._conformance_release --output-dir dist
```

The conformance command writes a versioned ZIP and matching `.sha256` sidecar.
The ZIP contains exactly `conformance/v1/manifest.json` and the machine-readable
files named by that manifest.

Install the wheel into a clean temporary environment and verify the distribution
version, public `rtd_sensor` import, absence of the legacy `rtd` package, and
representative public conversions.

## 5. Tag and publish the GitHub Release

Create an annotated version tag, verify it points at the intended release
commit, and push it:

```bash
git tag -a vX.Y.Z -m "rtd-sensor vX.Y.Z"
git show vX.Y.Z --stat
git push origin vX.Y.Z
```

Create the matching GitHub Release from that tag and attach the conformance ZIP
and `.sha256` sidecar produced in step 4. Publishing the GitHub Release triggers
`.github/workflows/release.yml`.

## 6. PyPI Trusted Publishing

The release workflow reruns the validation gate, builds distributions with
`uv build --no-sources`, and publishes them to PyPI through the `pypi` GitHub
environment using Trusted Publishing. Do not manually run `uv publish` during
the normal release path.

Confirm the GitHub Actions release workflow completes successfully before
considering the release complete.

## 7. Verify the public release

Install the exact released version from PyPI into a clean environment and run a
small public-API smoke test. Confirm that:

- `importlib.metadata.version("rtd-sensor")` reports the released version;
- `import rtd_sensor` succeeds;
- the legacy `rtd` package is absent; and
- representative built-in RTD conversions behave as expected.

Finally, verify that the GitHub Release, PyPI project page, README, changelog,
and `CITATION.cff` all identify the same released version. Also download the
published conformance ZIP and sidecar, verify the ZIP checksum, and confirm its
`manifest.json` records the same `rtd_sensor_version` and intended
`contract_status`.
