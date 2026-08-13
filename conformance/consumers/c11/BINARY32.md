# Binary32 compatibility profile

The draft conformance-v1 `binary32_compatible` profile defines numerical
acceptance for implementations that use single-precision arithmetic or otherwise
produce engineering-equivalent results at that precision.

For the current built-in conversion vectors, the published absolute tolerances
are:

| Capability | Output unit | Absolute tolerance |
| --- | --- | ---: |
| `conversion.temperature_to_resistance` | ohm | 0.002 Ω |
| `conversion.resistance_to_temperature` | degree Celsius | 0.001 °C |

These are interoperability tolerances. They are not RTD sensor tolerances,
calibration uncertainties, or measurement-uncertainty statements.

## Empirical basis

The initial profile was derived using an independent C11 `float` implementation
that consumes the committed conformance catalogs. The implementation uses
single-precision coefficients and intermediate arithmetic and a bounded global
bisection inverse rather than the Python implementation's curve-specific
inversion strategies.

The study exercised:

- every published successful and status vector;
- GCC 14.2 and Clang 17 builds at `-O0`, `-O2`, and `-O3` on x86-64;
- builds permitting floating-point contraction/FMA while retaining normal
  NaN/infinity semantics;
- a deterministic 0.25 °C sweep covering 16,446 in-range points; and
- 120,090 deterministic random and near-boundary points across all six built-in
  models.

The largest observed errors in the 120,090-point study were approximately
`6.51e-4 Ω` for temperature-to-resistance conversion and `2.33e-4 °C` for
resistance-to-temperature conversion. The published profile therefore retains
substantial margin over the largest observed single-precision differences.

## Endpoint representation

At the Pt100, Pt500, and Pt1000 resistance endpoints, conversion of the
binary64 reference-vector resistance to `float` can place the resulting value
one or two binary32 ULPs outside the resistance independently produced by
single-precision forward evaluation.

The independent binary32 consumer uses a four-ULP endpoint guard solely to
preserve the contract's endpoint-success semantics after representation
rounding. The guard does not extend the physical RTD model range. The published
resistance range-error anchors remain 0.01 Ω outside the binary64 endpoints and
remain unambiguously outside the guard.

## Floating-point compiler modes

The conformance status vocabulary includes explicit NaN and infinity behavior.
Compiler modes that assume NaN or infinity cannot occur can invalidate those
semantics even when ordinary finite numerical results remain close to the
reference implementation. Such a build can claim the binary32 profile only if
it independently preserves every status behavior required by the published
vectors.
