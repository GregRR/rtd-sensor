---
title: Conformance artifacts
description: Learn how rtd-sensor's versioned conformance catalogs, schemas, vectors, manifests, and release bundles are intended to be consumed.
---

# Conformance artifacts

The repository's `conformance/v1/` tree contains language-neutral artifacts that
independent implementations can consume during development, testing, code
generation, or CI.

Examples include model and characteristic catalogs, fixtures, schemas, and the
manifest that records released artifact integrity.

## Do not import Python internals as the contract

A non-Python implementation should consume released conformance artifacts and
the published specification rather than reverse-engineering private Python
classes or constants.

That protects the implementation from internal refactoring and keeps the
scientific contract explicit.

## Runtime JSON is not required

The artifacts are JSON-friendly because that is useful for interchange and
testing. An MCU does not need a JSON parser at runtime. Build tooling can read
artifacts and generate static C/C++ data, or tests can use them entirely off
target.

## Released artifacts matter

Conformance files are generated deterministically and checked as part of the
project's release process. Consumers should tie validation to a known released
contract/artifact set rather than to a random working-tree snapshot.

## Exact files

Browse the canonical tree in
[`conformance/`](https://github.com/GregRR/rtd-sensor/tree/main/conformance) and
read the exact contract in
[`docs/CONFORMANCE.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/CONFORMANCE.md).
