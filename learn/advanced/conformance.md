---
title: Conformance in plain English
description: Understand what rtd-sensor's language-neutral conformance contract guarantees and how behavioral conformance differs from copying Python internals.
---

# Conformance in plain English

The `rtd-sensor` conformance system lets an independent implementation answer:

> “For the behavior I claim to support, do I produce results compatible with the
> published rtd-sensor contract?”

It is **behavioral**, not algorithmic. A C implementation does not need to copy
Python's classes, inversion algorithm, or source-code structure. It needs to
match the published behavior within the numerical profile it claims.

**Stable conformance contract v1 since:** rtd-sensor 0.5.0.

## What the contract describes

The stable conformance material includes concepts such as:

- canonical built-in model IDs;
- characteristic IDs separate from model IDs;
- units;
- conversion capabilities;
- model and characteristic catalogs;
- conversion vectors and boundary/error statuses;
- numerical acceptance profiles;
- conformance claims; and
- artifact/version provenance.

## Model versus characteristic

A **characteristic** describes a normalized scientific resistance-temperature
relationship. A **model** applies that characteristic with parameters such as
reference resistance. Pt100, Pt500, and Pt1000 share a platinum characteristic
but remain distinct built-in models.

## Claim only what you implement

A constrained implementation can support only a subset. For example, an MCU may
support only:

```text
model: pt100
operation: resistance → temperature
numerical profile: binary32_compatible
```

That does not imply support for nickel RTDs, fitting, uncertainty, simulation,
or even the reverse temperature-to-resistance operation.

## Exact specification

The authoritative detailed specification remains
[`docs/CONFORMANCE.md`](https://github.com/GregRR/rtd-sensor/blob/main/docs/CONFORMANCE.md).
This page is the approachable user/implementer introduction, not a replacement
for the versioned contract.
