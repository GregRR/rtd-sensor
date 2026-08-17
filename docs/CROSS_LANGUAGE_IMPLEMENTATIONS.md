# Cross-language implementation guide

This guide consolidates the rules for implementing a compatible subset of
`rtd-sensor` outside Python. The normative behavioral contract remains
[`CONFORMANCE.md`](CONFORMANCE.md); this document is an implementation-oriented
entry point.

## Choose an explicit subset

A downstream implementation should claim only the operation, subject, and
numerical profile it actually supports. Conformance v1 currently distinguishes:

- canonical built-in `model_id` subjects, such as `pt100`; and
- local conformance `fixture_id` subjects for calibrated/custom model cases.

A claim for one conversion direction does not imply the other direction, and a
claim for one model or fixture does not imply support for the entire Python
package.

For example, a small controller may support only:

```text
contract_version: 1
model_id: pt100
capability: conversion.resistance_to_temperature
acceptance_profile: binary32_compatible
```

A characterized PT-385 implementation may instead claim one or more explicitly
published characterized-R0 fixture IDs. Those fixture identities remain
conformance subjects; they do not become built-in model IDs.

## Numerical profiles

`binary64_reference` is the high-precision interoperability profile.
`binary32_compatible` is an empirically measured engineering-equivalence profile;
it does not merely mean that an implementation happens to use a type named
`float`.

The binary32 profile is currently established for:

- all published built-in conversion vectors; and
- the explicit characterized PT-385 reference-resistance fixtures documented in
  [`../conformance/consumers/c11/BINARY32_CHARACTERIZED_R0.md`](../conformance/consumers/c11/BINARY32_CHARACTERIZED_R0.md).

It is **not** currently established for arbitrary custom CVD, polynomial,
piecewise-polynomial, or tabulated models. Those families require separate
numerical studies before acquiring a binary32 claim.

The original built-in derivation is documented in
[`../conformance/consumers/c11/BINARY32.md`](../conformance/consumers/c11/BINARY32.md).

## Consume released artifacts, not Python internals

The versioned files under `conformance/v1/` define model/characteristic metadata,
fixtures, vectors, statuses, claim shape, and release integrity. A downstream
project may vendor the deterministic conformance ZIP or otherwise pin the exact
contract files from a tagged release and run them in its own CI.

The Python source is the reference implementation, but an external consumer
should not need to inspect private Python classes or copy undocumented constants
to understand the claimed behavior.

## Runtime JSON is optional

Firmware does not need a JSON parser. JSON is an interchange, generation, test,
and CI format. A constrained target may compile validated constants or
structures generated from a pinned release, provided the resulting runtime
behavior still satisfies the claimed vectors and statuses.

Similarly, the portable model-definition format under `portable/` is a deployment
interchange format, not a requirement that an MCU parse JSON at runtime.
Portable model identities and conformance fixture identities are deliberately
separate.

## Preserve model and status identity

Use the stable model/characteristic identifiers and semantic RTD statuses from
the conformance contract. Do not invent a second RTD vocabulary in a host/MCU
protocol when the conformance contract already defines the scientific meaning.

The RTD status domain includes meanings such as:

- `ok`;
- `out_of_range_low`;
- `out_of_range_high`;
- `invalid_input`;
- `invalid_model`; and
- `calculation_failure`.

A non-Python implementation may represent them as an enum, integer code, or
other native form, but the meanings should remain equivalent.

## Keep acquisition outside RTD conversion

The conformance boundary begins with the best available estimate of sensing-
element resistance in ohms. SPI/I²C communication, ADC conversion, reference-
resistor calculations, two/three/four-wire compensation, open/short detection,
converter faults, stale samples, and actuator/PID logic belong to acquisition or
application layers.

A system may report both acquisition status and RTD conversion status, but it
should not redefine an acquisition fault as an RTD model result.

## Independent implementation and CI

A useful downstream CI sequence is:

1. pin one released conformance contract/bundle;
2. select the exact model or fixture IDs and capabilities implemented;
3. construct native constants/structures from the released definitions;
4. run the matching conversion and status vectors;
5. compare successful values with the claimed numerical profile;
6. verify semantic status outcomes; and
7. publish a machine-readable conformance claim when useful.

The repository's C11 implementation under `conformance/consumers/c11/` is an
example of an independent verification path. It is intentionally not presented
as the production embedded library that every downstream project must use.

## Scope of a constrained implementation

A target may omit anything it does not claim. In particular, an MCU conversion
library need not implement batch conversion, fitting, simulation, tolerance
calculation, uncertainty propagation, every model family, or the Python
exception API.

If future embedded use justifies generated headers, lookup tables, or a separate
production C/C++ sibling library, those should remain downstream representations
of the same published scientific contract rather than a competing definition
system.
