---
title: Binary32 compatibility
description: Understand rtd-sensor's binary32_compatible numerical profile for constrained implementations using real single-precision floating point.
---

# Binary32 compatibility

**Binary32** is the IEEE 754 single-precision floating-point format commonly
represented by C `float` on embedded systems. It has less precision than the
binary64 floating point normally used by Python.

`rtd-sensor` does not simply assume that a single-precision implementation will
be “close enough.” Its `binary32_compatible` conformance profile is based on
independent single-precision evaluation and explicit acceptance criteria for the
behavior covered by that profile.

**Built-in binary32 profile available since:** rtd-sensor 0.5.0.
**Characterized IEC 60751 reference-resistance coverage added in:** 0.6.0.

## Why this matters to an MCU

A constrained target may want only:

```text
Pt100
resistance → temperature
binary32_compatible
```

That can be a legitimate subset claim without implementing the complete Python
package.

## What the claim does not mean

`binary32_compatible` does not mean:

- every arbitrary user coefficient set is safe in binary32;
- every future model family is automatically covered;
- binary32 and binary64 are bit-identical; or
- the physical sensor uncertainty is determined by floating-point precision.

It means the implementation satisfies the published numerical acceptance for
the specific claimed contract subset.

## Related features

- [Numerical acceptance](numerical-acceptance.md)
- [Independent C11 verification](c11.md)
- [Cross-language & embedded use](cross-language-embedded.md)
