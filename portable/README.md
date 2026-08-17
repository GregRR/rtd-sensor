# Portable RTD Model Definitions

`portable/v1/model-definition.schema.json` defines RTD-Sensor's version-1
language-neutral portable model artifact. The format is intended for moving a
validated configurable or fitted numerical model between processes or language
implementations without rerunning calibration fitting.

Portable model definitions are **not conformance fixtures**. They use their own
`format_version` and cannot represent intentionally invalid models,
`fixture_id`, `expected_status`, or other conformance-test semantics.

A version-1 artifact has this shape:

```json
{
  "artifact_type": "portable_model_definition",
  "format_version": 1,
  "model_kind": "polynomial",
  "definition": {
    "reference_resistance_ohms": 100.0,
    "reference_temperature_c": 0.0,
    "coefficients": [0.0039, -0.0000005],
    "minimum_temperature_c": -50.0,
    "maximum_temperature_c": 200.0
  },
  "metadata": {
    "source": "example only"
  }
}
```

## Version-1 model kinds

Version 1 supports:

- `characteristic_model` — a characterized reference resistance composed with
  a published RTD characteristic. RTD-Sensor 0.6.0 reconstructs
  `iec60751_pt385` as `IEC60751RTDModel`.
- `callendar_van_dusen` — custom `R0`, `A`, `B`, optional `C`, and validity
  range.
- `polynomial` — normalized global polynomial with explicit reference
  resistance, reference temperature, coefficients, and validity range.
- `piecewise_polynomial` — ordered source segments plus the explicitly
  authorized maximum continuity adjustment.

Tabulated-model portability is intentionally outside version 1 and is not a
0.6.0 release requirement.

The schema constrains identifier syntax independently from the set of model or
characteristic identifiers a particular RTD-Sensor release can reconstruct. In
version 1, `characteristic_model` uses the shared identifier grammar, while the
0.6.0 loader currently reconstructs only `iec60751_pt385`. Schema validation
therefore establishes structural validity, not support by a particular loader or
scientific validity of the resulting model.

`format_version` is an integer-valued JSON number. JSON Schema treats `1` and
`1.0` as the same integer-valued number, and the Python loader accepts both as
version 1. Boolean values are never accepted as version numbers.

## Metadata and identity

`metadata` is optional, open, non-behavioral JSON data. A consumer should
preserve it even when it does not interpret every entry. Metadata cannot alter
conversion behavior.

The portable numerical definition does not contain hardware configuration,
installation location, channel identity, probe asset identity, or
application-specific semantics. Human-readable model names and Python-specific
provenance fields are likewise not automatically copied into the portable
artifact; callers may place appropriate application-neutral provenance in
`metadata` explicitly.

## Piecewise continuity

Piecewise definitions preserve the source segment coefficients and
`maximum_continuity_adjustment_ratio`. Applied constant offsets are derived
deterministically from those source values by the piecewise model semantics and
are not serialized as a second independent numerical source of truth.

For each source segment, coefficients are in ascending-power order. With
`x = temperature_c - temperature_origin_c`, the normalized resistance ratio is

```text
R(T) / Rref = c0 + c1*x + c2*x^2 + ... + cn*x^n
```

The reference implementation evaluates that polynomial with Horner's method,
starting from the highest-order coefficient. Segments are ordered by increasing
temperature and must meet exactly at adjacent boundaries. Interior boundaries
route to the segment on the right; the final endpoint routes to the final
segment.

Continuity stitching is anchored at `reference_temperature_c`. The anchor
segment is normalized to exactly `R/Rref = 1` when its source-level reference
error is only machine roundoff. From that anchor, constant ratio offsets are
propagated outward: moving right, each segment is shifted so its value at the
join equals the already-adjusted segment on its left; moving left, each segment
is shifted so its value at the join equals the already-adjusted segment on its
right. Each derived shift must remain within the declared
`maximum_continuity_adjustment_ratio`, apart from the reference implementation's
machine-roundoff allowance.

This evaluation and anchor/propagation order defines the reference semantics for
deriving the offsets. Independent implementations using different floating-point
evaluation rules can differ at machine-roundoff scale and should validate those
differences under an appropriate numerical acceptance profile rather than
serializing derived offsets as another source of truth.

## Python API

The Python package provides `rtd_sensor.portable`:

```python
from rtd_sensor import portable
from rtd_sensor.models import IEC60751RTDModel

model = IEC60751RTDModel(
    r0_ohms=100.017,
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)

artifact = portable.model_to_portable_definition(
    model,
    metadata={"source": "calibration record 2026-08"},
)
loaded = portable.model_from_portable_definition(artifact)

assert loaded.model.r0_ohms == 100.017
assert loaded.metadata["source"] == "calibration record 2026-08"
```

The loader rejects unsupported format versions, unknown model kinds, unknown
behavior-changing fields, invalid characteristic IDs, and numerically invalid
model definitions instead of guessing at their meaning.
