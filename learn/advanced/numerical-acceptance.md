---
title: Numerical acceptance
description: Understand why rtd-sensor conformance uses explicit numerical acceptance profiles instead of assuming every language and floating-point environment is bit-identical.
---

# Numerical acceptance

Independent implementations can use different floating-point types, math
libraries, and inversion algorithms while still representing the same RTD
behavior. The conformance system therefore defines **numerical acceptance
profiles** instead of pretending every platform should produce bit-for-bit
identical floating-point results.

## Why an acceptance profile is needed

Python normally performs these calculations with binary64 floating point. Many
microcontrollers use binary32 `float` for speed, memory, or hardware support.
Small differences can arise from:

- input rounding;
- coefficient representation;
- intermediate precision;
- operation ordering; and
- inverse-solver behavior.

A useful compatibility claim must say what numerical behavior was actually
tested and accepted.

## Acceptance is empirical, not arbitrary

A profile should be justified with independent calculations across representative
and boundary cases. A tolerance is not selected merely because it “looks small.”

The project's built-in binary32 profile is backed by an independent C11 path.
See [Binary32 compatibility](binary32.md).

## Scientific precision is a different question

Numerical agreement between two implementations does not make a sensor,
coefficient source, or published table more accurate than its evidence. A
computer may print many digits while the physical measurement or source table
supports far fewer.
