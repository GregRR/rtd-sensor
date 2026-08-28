# Release readiness and publishing

Use this process for every `rtd-sensor` release. A release is ready only when
this question can be answered yes:

> Is the exact commit, documentation, metadata, artifact, and publishing
> mechanism about to be exposed to users internally consistent and demonstrably
> correct?

Repository beautification is not a release gate. Branch deletion, commit
squashing, interactive rebasing, and similar history cleanup belong in normal
maintenance rather than release preparation.

## 1. Define the release

Before changing release metadata:

- [ ] Confirm the target version.
- [ ] Review the diff from the previous release tag.
- [ ] Confirm the intended fixes/features/documentation are present.
- [ ] Confirm intentionally deferred work remains documented as deferred.
- [ ] Confirm no known release-blocking issue remains.
- [ ] Confirm the release scope matches what will be described to users.

For corrective releases, explicitly record what is *not* in scope so a patch
release cannot silently become the next feature milestone.

## 2. Version and package metadata

Review every authoritative or duplicated version/identity location:

- [ ] `project.version` in `pyproject.toml` is the target release version.
- [ ] `uv.lock` agrees with the project metadata.
- [ ] `CITATION.cff` has the target `version` and `date-released`.
- [ ] `CHANGELOG.md` contains a dated section for the target version.
- [ ] Distribution name is `rtd-sensor`.
- [ ] Import package is `rtd_sensor`.
- [ ] `requires-python`, dependency constraints, classifiers, URLs, license,
      author metadata, and build configuration are current.
- [ ] Repository searches for the previous version have been investigated.

After changing `project.version`, regenerate the version-bearing conformance
artifacts:

```bash
uv run --locked python -m rtd_sensor._conformance_artifacts
```

Do not tag while `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `CITATION.cff`, or
the generated conformance artifacts disagree about the intended release.

### Declaring a conformance contract stable

Declaring a conformance contract stable is a one-time freeze operation, not a
routine release step. Before changing `contract_status` from `draft` to
`stable`:

- complete the final conformance acceptance/schema-freeze review;
- resolve every finding required for stability;
- obtain narrow verification of pre-freeze corrections without mixing unrelated
  feature work into the freeze;
- deliberately set the package version that identifies the source state
  producing the first stable artifacts;
- change only the contract maturity/version-provenance state required for the
  freeze, then regenerate all conformance artifacts and the manifest;
- run both conformance `--check` commands and the complete release gate; and
- inspect the regenerated manifest before committing the freeze.

Do not use the stability declaration commit to introduce new conformance
semantics.

## 3. Documentation-drift audit

**This is a hard release gate.** Review the complete documentation set, not only
the files expected to change:

- [ ] `README.md`
- [ ] `docs/DESIGN.md`
- [ ] `docs/CONFORMANCE.md`
- [ ] `docs/ROADMAP.md`
- [ ] `docs/REFERENCES.md`
- [ ] `docs/RELEASING.md`
- [ ] `CHANGELOG.md`
- [ ] `CITATION.cff`
- [ ] the complete `learn/` documentation and Playground tree
- [ ] `zensical.toml` navigation/site configuration
- [ ] public API docstrings and source comments
- [ ] examples, installation instructions, and command snippets
- [ ] package/import names, supported-version statements, and release highlights

For the documentation set as a whole, verify:

- [ ] implemented functionality is described as implemented;
- [ ] planned/deferred functionality is still described as planned/deferred;
- [ ] public APIs match the current code;
- [ ] examples use current imports, names, arguments, and behavior;
- [ ] installation commands are current;
- [ ] old project/package/import names occur only in intentional history or
      migration material;
- [ ] old version numbers occur only where historical or otherwise intentional;
- [ ] terminology is consistent across documents;
- [ ] documents do not contradict one another;
- [ ] documentation does not claim unsupported behavior;
- [ ] important newly implemented user-facing behavior is not omitted;
- [ ] every new or changed public API is reflected in the Learn API reference and
      the appropriate explanatory/user-guide page, or its omission is deliberate;
- [ ] Learn/API version labels do not still describe implemented target-release
      functionality as planned;
- [ ] the README and package `Documentation` URL lead users to the canonical Learn
      site while engineering documents remain directly discoverable;
- [ ] every external source that materially supports a new or changed equation,
      coefficient set, range, tolerance rule, uncertainty/calibration method,
      validation dataset, numerical criterion, or scientific/engineering decision
      is added to or verified in `docs/REFERENCES.md` in the same change;
- [ ] implementation-level `Source:` comments or structured provenance identify
      the specific basis of non-obvious scientific rules, while independent test
      data are clearly distinguished as validation sources; and
- [ ] research-only or conflicting sources are labeled as such rather than being
      presented as support for released behavior.

A document that is individually accurate can still conflict with another
current document. Cross-document consistency is an explicit release check. In
particular, treat `learn/` as part of the released product documentation rather
than as a secondary website that can lag behind the README or engineering docs.

Build the Learn site strictly as part of this gate using the same pinned Zensical
version as `.github/workflows/docs.yml`:

```bash
uvx --from "zensical==0.0.55" zensical build --clean --strict
```

The strict build must complete without broken links, missing navigation targets, or
other documentation validation errors.

## 4. Repository drift sweep

Search broadly outside the major documentation files for stale values and
obsolete interfaces. Investigate every match rather than blindly replacing it.

A useful legacy-name audit is:

```bash
grep -RInE \
  'rtd\.(pt100|pt500|pt1000|ni1000|ni1000_tk5000|ni120|simulation|tolerance|uncertainty)|from rtd import|pt100-core' \
  README.md CHANGELOG.md docs src tests
```

Also search for:

- previous release versions;
- old CLI/API names and deprecated arguments;
- obsolete examples or URLs;
- stale feature names;
- TODOs/comments that describe completed work as unfinished;
- tests or configuration using obsolete interfaces; and
- stale names/versions in CI or release workflows.

Historical changelog and migration references are intentionally retained when
they are still accurate.

## 5. Source validation

Run the complete source-tree gate from the intended release candidate:

```bash
uv lock --check
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked python -m rtd_sensor._conformance_artifacts --check
uv run --locked python -m rtd_sensor._conformance_release --check
git diff --check
git status --short
```

All checks must pass. Any failure must be understood and consciously resolved;
an unexplained failure is release-blocking.

Before declaring the release candidate final, all intended release changes must
be tracked and committed and the working tree must be clean. At that point,
plain `git diff --check` has no working-tree diff left to inspect, so also check
the complete committed release delta from the previous release tag:

```bash
git diff --check vPREVIOUS..HEAD
```

Replace `vPREVIOUS` with the actual previous release tag (for example,
`v0.5.1` while preparing 0.6.0).

## 6. Build and inspect the actual release artifacts

Source-tree success does not prove the distributable artifacts are correct.
Build from the intended release candidate without development-only uv source
overrides:

```bash
rm -rf dist
uv build --no-sources
uv run --locked python -m rtd_sensor._conformance_release --output-dir dist
```

Then verify:

- [ ] exactly the expected wheel and source distribution were produced;
- [ ] package filenames and versions are correct;
- [ ] wheel/source contents contain expected package files and no unintended
      local/generated material;
- [ ] package metadata inside the artifact is correct;
- [ ] the conformance ZIP and `.sha256` sidecar were produced;
- [ ] the conformance ZIP contains exactly the manifest and files named by it;
- [ ] the conformance manifest records the intended package version and stable
      contract status; and
- [ ] the checksum sidecar validates the conformance ZIP.

Install the Python artifacts into clean temporary environments and verify the
installed distribution rather than the source checkout:

- [ ] `importlib.metadata.version("rtd-sensor")` reports the target version;
- [ ] `import rtd_sensor` succeeds;
- [ ] the legacy `rtd` package is absent;
- [ ] representative built-in conversion succeeds; and
- [ ] representative public APIs, including catalog/model composition, batch
      conversion, calibration fitting, self-heating analysis, and portable-model
      round trips, are importable and usable.

## 7. User-facing installation and quickstart test

Follow the README exactly as a new user would. Do not substitute a command that
is known to work for the command the documentation actually gives users.

From a clean environment:

- [ ] run the documented installation command exactly;
- [ ] run the documented basic-usage example exactly;
- [ ] run representative advanced examples relevant to the release;
- [ ] confirm no undocumented setup is required;
- [ ] confirm package/import/API names and arguments are current;
- [ ] verify described outputs and behavior remain sensible; and
- [ ] verify the documented minimum Python version when feasible.

If the primary documentation fails this test, the release is not ready even if
the package itself works.

## 8. CI and release automation

Before publishing:

- [ ] required CI jobs pass on the exact release commit;
- [ ] local `HEAD` and remote `main` identify the same intended release commit;
- [ ] `.github/workflows/ci.yml` has been reviewed;
- [ ] `.github/workflows/docs.yml` has been reviewed;
- [ ] `.github/workflows/release.yml` has been reviewed;
- [ ] workflow triggers and tag/version assumptions are correct;
- [ ] action/runtime/tool versions and permissions are intentional;
- [ ] Trusted Publishing uses the `pypi` environment as intended;
- [ ] build and publish commands target `rtd-sensor` exactly once; and
- [ ] the workflow validates/builds from the requested release tag.

The release workflow is a safety net, not a substitute for the manual
release-candidate review. Do not assume it is correct merely because an earlier
release worked.

## 9. Release-candidate review

**STOP HERE BEFORE TAGGING OR PUBLISHING.** Everything through this point should
remain reversible.

Confirm:

- [ ] working tree is clean;
- [ ] local `HEAD` is the intended release commit;
- [ ] remote `main` points to the intended release commit;
- [ ] target version is correct everywhere;
- [ ] changelog/release highlights are complete;
- [ ] documentation-drift audit passed;
- [ ] repository drift sweep passed;
- [ ] source validation passed;
- [ ] release artifacts built and were inspected;
- [ ] built artifacts were installed and smoke-tested in clean environments;
- [ ] README installation/quickstart succeeded from a clean environment;
- [ ] CI is green on the exact release commit;
- [ ] release automation has been reviewed; and
- [ ] no unresolved release-blocking issue remains.

Only after every applicable item passes should the release candidate be
approved.

## 10. Tag and publish

Commit and push any final release-preparation changes, then confirm CI on that
exact pushed commit before creating the tag.

Create and verify the annotated tag:

```bash
git tag -a vX.Y.Z -m "rtd-sensor vX.Y.Z"
git show vX.Y.Z --stat
git push origin vX.Y.Z
```

Push the specific intended tag rather than using `git push --tags`.

Create the matching GitHub Release from that tag and attach the conformance ZIP
and `.sha256` sidecar produced in step 6. Publishing the GitHub Release triggers
`.github/workflows/release.yml`.

The release workflow validates the requested tag, builds the Python
distributions, smoke-tests the built artifacts, and publishes them to PyPI
through Trusted Publishing. Do not manually run `uv publish` during the normal
release path.

The workflow also supports an explicit manual `workflow_dispatch` tag input for
recovery from a publishing-workflow failure after a GitHub Release already
exists. Use that recovery path only after the workflow defect is corrected and
the requested tag is re-verified; never rebuild or retag an already published
version merely to retry publishing.

## 11. Post-release verification

A green publishing workflow does not prove the public release is correct.
Verify the externally visible release itself:

- [ ] GitHub Release exists and points to the correct tag;
- [ ] tag points to the correct commit;
- [ ] PyPI shows the expected version;
- [ ] public package metadata is correct;
- [ ] expected artifacts are present and unexpected artifacts are absent;
- [ ] the exact published version installs into a fresh environment;
- [ ] the installed version is the newly published version;
- [ ] representative public-API smoke tests pass against the published package;
- [ ] README and release notes render correctly;
- [ ] the published Learn site renders the release's API/status wording correctly;
- [ ] documentation links and relevant badges/version links work;
- [ ] the normal public installation command resolves to the new release;
- [ ] the published conformance ZIP checksum validates;
- [ ] the conformance manifest records the same package version and intended
      contract status; and
- [ ] post-release follow-up work is recorded before development advances to the
      next release cycle.

The release is complete only after the public artifact itself has been verified.

## Maintenance deliberately excluded from the release gate

The following may be useful repository maintenance, but they do not normally
block a release:

- deleting stale or merged branches;
- squashing cosmetic commits;
- interactive rebasing for prettier history;
- rewriting already-shared history;
- general repository beautification; and
- nonessential issue/project-board cleanup.

Release readiness stays focused on the exact commit, documentation, metadata,
artifacts, and publishing mechanism being exposed to users.
