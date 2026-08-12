# RTD conformance contract

Status: **Draft — conformance contract v1**

`rtd-sensor` is the reference implementation for the RTD behavior described by
this contract. The conformance artifacts provide a language-neutral basis for
independent implementations to reproduce that behavior and demonstrate
interoperability without depending on Python internals.

The contract is language-neutral. It defines model identity, conversion
semantics, supported ranges, machine-readable reference cases, numerical
acceptance criteria, and semantic result statuses. It does not prescribe a
particular implementation algorithm or programming-language error mechanism.

Until a release explicitly declares conformance contract v1 stable, the
identifiers and structures described here remain draft.

## Scope

Conformance v1 is centered on RTD model behavior:

- temperature-to-resistance conversion;
- resistance-to-temperature conversion;
- canonical built-in model identity;
- characteristic identity and model composition;
- supported temperature ranges and corresponding resistance boundaries;
- language-neutral result statuses;
- numerical acceptance profiles; and
- machine-readable reference vectors and metadata.

The contract is independent of hardware acquisition. ADC configuration,
reference-resistor measurement, lead-wire compensation performed by a device,
SPI/I²C/GPIO access, RTD-interface IC drivers, PID control, and actuator logic
are outside its scope.

An implementation may claim only the subset of models and capabilities it
supports. Conformance with one subset does not imply support for the complete
Python package.

## Terminology

### Characteristic

An RTD **characteristic** defines the normalized mathematical relationship
between temperature and resistance ratio.

A characteristic has its own identity, valid range, equation or table
representation, and scientific provenance.

### Model

An RTD **model** combines a characteristic with the parameters needed to
represent a concrete nominal or characterized sensor model, including its
reference resistance and declared valid range.

Several models may share one characteristic. For example, the IEC 60751 PT-385
Pt100, Pt500, and Pt1000 models use the same normalized platinum
characteristic while differing in reference resistance.

### Capability

A **capability** identifies one independently claimable behavior, such as:

```text
conversion.temperature_to_resistance
conversion.resistance_to_temperature
```

Additional capabilities may be defined in later contract revisions without
requiring every implementation to support them.

## Interchange format

Conformance artifacts use UTF-8 JSON.

Their structure is validated with JSON Schema Draft 2020-12. Normative objects
use explicit required fields and closed schemas so unknown or misspelled fields
cannot silently alter their meaning.

The draft v1 artifact layout is:

```text
conformance/
└── v1/
    ├── schemas/
    │   ├── characteristic-catalog.schema.json
    │   ├── model-catalog.schema.json
    │   └── vector-set.schema.json
    ├── characteristics.json
    ├── models.json
    └── vectors/
        ├── builtin-temperature-to-resistance.json
        └── builtin-resistance-to-temperature.json
```

The JSON artifacts are test and interchange data. Their use does not imply that
an embedded implementation must include a JSON parser in production firmware.
The draft v1 schemas are self-contained and use local `$defs`; cross-file
referential integrity and scientific consistency are validated separately from
JSON Schema structure validation.

## Versioning

Conformance artifacts carry three distinct version concepts.

### Format version

`format_version` identifies the structure of the JSON artifact.

The initial value is:

```json
"format_version": 1
```

A new format version is required when an existing consumer must change how it
parses an artifact.

### Contract version

`contract_version` identifies the externally observable behavioral semantics of
the conformance contract.

The initial value is:

```json
"contract_version": 1
```

An incompatible change to an existing model identity, characteristic identity,
status meaning, operation semantic, boundary rule, or published acceptance
requirement requires a new contract version.

The addition of a new model, characteristic, vector set, or separately
claimable capability does not by itself change the meaning of existing
contract-version-1 behavior.

### Producing package version

Each generated artifact also records the `rtd-sensor` version that produced or
validated it.

The package version is provenance. It does not replace either `format_version`
or `contract_version`.

## Identifier rules

Normative identifiers use lowercase ASCII and are case-sensitive. They match
`^[a-z][a-z0-9._-]*$`: an identifier begins with an ASCII letter and may then
contain lowercase ASCII letters, digits, periods, underscores, or hyphens.
Canonical IDs are not silently normalized and are never reused for a different
semantic meaning.

Display names and aliases are descriptive metadata rather than substitutes for
canonical IDs.

### Built-in model IDs

The draft v1 built-in model IDs are:

| `model_id` | Meaning |
| --- | --- |
| `pt100` | nominal 100 Ω IEC 60751 PT-385 platinum model |
| `pt500` | nominal 500 Ω IEC 60751 PT-385 platinum model |
| `pt1000` | nominal 1000 Ω IEC 60751 PT-385 platinum model |
| `ni1000` | nominal 1000 Ω former-DIN 6178/6180 nickel model |
| `ni1000_tk5000` | nominal 1000 Ω TK5000 / 5000 ppm/K nickel model |
| `ni120` | nominal 120 Ω North-American 6720 ppm/K nickel model |

A future model that would otherwise share a familiar nominal name but uses a
different characteristic receives a different canonical `model_id`. Existing
IDs retain their original meaning.

### Built-in characteristic IDs

The draft v1 characteristic IDs are:

| `characteristic_id` | Meaning |
| --- | --- |
| `iec60751_pt385` | IEC 60751 PT-385 Callendar-Van Dusen characteristic |
| `ni6180_din43760` | former DIN 43760 / 6178-6180 ppm/K nickel characteristic |
| `ni5000_tk5000` | TK5000 / Nickel NL 5000 ppm/K characteristic |
| `ni6720_north_american` | North-American 6720 ppm/K piecewise nickel characteristic |

The initial model-to-characteristic relationship is:

```text
pt100          ─┐
pt500           ├── iec60751_pt385
pt1000         ─┘

ni1000             ── ni6180_din43760
ni1000_tk5000      ── ni5000_tk5000
ni120               ── ni6720_north_american
```

Characteristic identity remains separate from reference resistance so a shared
normalized curve is represented once.

### Custom-model fixture IDs

Conformance vectors for custom CVD, calibrated-reference-resistance,
polynomial, or piecewise models use local `fixture_id` values.

A fixture ID identifies a conformance test fixture. It is not a globally
registered built-in RTD model identity.

## Units

Basic conversion contract v1 uses fixed SI-derived units:

| Quantity | Machine token |
| --- | --- |
| temperature | `degree_celsius` |
| resistance | `ohm` |

A vector set declares its input and output units explicitly. Model metadata uses
unit-specific field names where appropriate, such as
`reference_resistance_ohms`.

General-purpose unit conversion is not part of conformance v1.

## Model and characteristic catalogs

The characteristic catalog describes the normalized RTD characteristics used by
built-in models. The draft v1 characteristic schema distinguishes
Callendar-Van Dusen, polynomial, and piecewise-polynomial records explicitly
rather than encoding equations as arbitrary expression strings. A characteristic
record includes, as applicable:

- `characteristic_id`;
- display name;
- material;
- characteristic representation;
- reference temperature;
- supported characteristic range;
- equation coefficients, polynomial coefficients, piecewise segments, or table
  data; and
- provenance metadata.

The model catalog composes characteristics into built-in model definitions. A
model record includes:

- `model_id`;
- display name;
- `characteristic_id`;
- reference resistance;
- declared valid model range; and
- model-specific provenance where applicable.

A model may declare a range narrower than its underlying characteristic. The
model range controls model-level validity.

For piecewise-polynomial characteristics, published segment coefficients remain
separate from implementation-derived continuity adjustments. Draft v1 represents
the adjustments as additive offsets to normalized resistance ratio, one offset
per segment in segment order, together with the documented maximum allowed
adjustment ratio and the reason for applying the adjustment. Cross-field checks
such as matching the number of adjustments to the number of segments are part
of conformance artifact integrity validation in addition to JSON Schema
validation.

The committed `characteristics.json` and `models.json` catalogs are generated
deterministically from the authoritative built-in definitions used by the Python
runtime. Repository validation requires regeneration to reproduce the committed
files exactly, so these catalogs are not maintained as independent copies of the
scientific model data.

## Vector sets

A vector set contains metadata shared by a capability and one or more groups of
test cases.

A representative structure is:

```json
{
  "artifact_type": "vector_set",
  "format_version": 1,
  "contract_version": 1,
  "rtd_sensor_version": "0.5.0",
  "capability_id": "conversion.temperature_to_resistance",
  "input_unit": "degree_celsius",
  "output_unit": "ohm",
  "test_groups": [
    {
      "group_id": "pt100.temperature_to_resistance",
      "model_id": "pt100",
      "cases": [
        {
          "case_id": "pt100.temperature_to_resistance.reference_0c",
          "tags": ["reference_temperature"],
          "input": {"value": 0.0},
          "expected": {
            "status": "ok",
            "value": 100.0,
            "acceptance": {
              "binary64_reference": {"absolute_tolerance": 1e-9}
            }
          }
        }
      ]
    }
  ]
}
```

`group_id` and `case_id` are stable diagnostic identifiers. Case ordering has no
semantic meaning.

Tags are descriptive classifiers used for coverage and diagnostics. They are not
part of the pass/fail rule.

The committed draft-v1 built-in conversion vector sets are generated
deterministically from the authoritative model definitions and runtime behavior.
They contain valid-domain binary64 reference anchors for all six built-in models.
The anchors include minimum and maximum model temperatures, reference and nearby
branch points, representative operating temperatures, and every source-segment
midpoint and join for the piecewise Ni120 characteristic. The forward and inverse
sets are paired through the same temperature anchors so endpoint and round-trip
behavior remain directly comparable. Error/status vectors are a separate
conformance layer and are not implied by these initial successful-result sets.

## Input representation

Ordinary finite numerical inputs use:

```json
"input": {"value": 100.0}
```

JSON does not represent NaN or positive/negative infinity as numbers. Vectors
that test non-finite input use symbolic values:

```json
"input": {"special": "nan"}
```

The initial symbolic values are:

```text
nan
positive_infinity
negative_infinity
```

Exactly one ordinary numeric value or special symbolic value is present for an
input.

Schema-validation failures are distinct from RTD model-evaluation results.

## Result statuses

Every vector case has an expected semantic status.

| Status | Meaning |
| --- | --- |
| `ok` | the operation produces a valid finite result |
| `out_of_range_low` | a finite, otherwise valid input is below the model's supported physical range |
| `out_of_range_high` | a finite, otherwise valid input is above the model's supported physical range |
| `invalid_input` | the supplied input is not a valid physical/numerical value for the operation |
| `invalid_model` | a supplied custom or calibrated model definition is invalid |
| `calculation_failure` | the model and input are valid but the required numerical result cannot be produced |

For `status: "ok"`, a finite expected numerical value is present.

For non-`ok` statuses, a numerical expected value is not required.

These statuses describe semantics rather than language-specific control flow.
Python exceptions, C/C++ enums, result objects, or protocol status codes may all
represent the same contract status.

`unsupported_model` is reserved for capability negotiation. It indicates that
an implementation does not claim the requested model or capability and is not a
successful conformance result for a vector that the implementation claims to
support.

### Range semantics

For temperature-to-resistance conversion:

- non-finite temperature is `invalid_input`;
- finite temperature below the model's declared minimum is
  `out_of_range_low`;
- finite temperature above the model's declared maximum is
  `out_of_range_high`.

For resistance-to-temperature conversion:

- non-finite resistance is `invalid_input`;
- zero or negative resistance is `invalid_input`;
- finite positive resistance below the model's minimum valid resistance is
  `out_of_range_low`;
- finite resistance above the model's maximum valid resistance is
  `out_of_range_high`.

For a model endpoint, the resistance produced by valid forward conversion at
that endpoint is valid input to inverse conversion and returns the endpoint
within the applicable numerical acceptance tolerance.

## Numerical acceptance

Conformance requires engineering-equivalent numerical behavior rather than
bit-for-bit identity.

Successful reference values are generated by the validated Python reference
implementation.

The draft v1 contract distinguishes two acceptance profiles:

- `binary64_reference`
- `binary32_compatible`

An acceptance profile describes the allowed numerical difference from the
published reference value. It does not require the implementation to use that
floating-point representation internally.

Each successful vector carries the applicable absolute tolerance for each
published profile. The initial built-in conversion vectors publish only the
`binary64_reference` profile, with an absolute tolerance of `1e-9` in the
vector set's output unit. This tolerance is an interoperability allowance for
floating-point evaluation and inversion differences; it is not an RTD sensor
tolerance, calibration uncertainty, or measurement-uncertainty statement.

The numerical pass rule is:

```text
abs(actual - expected) <= absolute_tolerance
```

The actual result must also be finite.

Absolute tolerances are used for the initial conversion contract because the
outputs are engineering quantities with explicit units and temperature relative
error is not useful around 0 °C.

The numerical tolerance values are not part of this draft document. They become
normative when the corresponding acceptance profile is published in stable v1
artifacts.

## Behavioral rather than algorithmic conformance

The contract defines externally observable behavior.

It does not require an independent implementation to use the same root solver,
iteration count, polynomial evaluation strategy, or internal floating-point
workaround as Python.

An implementation is conformant for a claimed capability when it:

- accepts the same semantic input domain;
- reports the required semantic status;
- produces successful numerical results within the claimed acceptance profile;
  and
- satisfies the published boundary and branch behavior.

Implementation-specific techniques that preserve those behaviors are not part
of the external contract.

## Coverage represented by conversion vectors

The draft v1 built-in conversion vector sets define coverage for the following
case classes for each claimed model and conversion direction:

- minimum and maximum supported temperatures;
- the reference temperature;
- endpoint resistances used in inverse conversion;
- values inside and outside supported boundaries;
- representative negative and positive temperatures;
- independently sourced reference anchors where available;
- Callendar-Van Dusen branch behavior around 0 °C;
- polynomial representative points;
- piecewise-polynomial joins;
- inverse-conditioning cases; and
- round-trip anchors.

The vector collection is intended to exercise distinct behavior rather than act
as a dense lookup table.

## Custom-model conformance

Custom-model conformance is a separately claimable layer.

The custom-model layer defines fixture families for:

- characterized non-nominal reference resistance;
- custom Callendar-Van Dusen coefficients;
- positive-only and negative-only declared ranges;
- valid custom models whose resistance ratio crosses 1 away from 0 °C;
- polynomial models;
- piecewise-polynomial models;
- explicitly represented continuity adjustments; and
- invalid, non-monotonic, gapped, overlapping, or otherwise unsupported model
  definitions.

Custom fixture definitions are local to their fixture catalog or vector set and
do not acquire built-in `model_id` values.

## Conformance claims

An implementation claim identifies at least:

- `contract_version`;
- supported capability IDs;
- supported canonical `model_id` values; and
- numerical acceptance profile or profiles passed.

For example:

```text
contract_version: 1
capabilities:
  - conversion.resistance_to_temperature
models:
  - pt100
  - pt1000
acceptance:
  - binary32_compatible
```

This claim does not imply support for other conversion directions, nickel
models, custom coefficients, tolerance calculations, uncertainty analysis,
simulation, or any hardware interface.

A future host/MCU protocol may reuse these identifiers and contract versions.
The protocol references the conformance contract rather than redefining their
scientific meaning.

## Artifact provenance and scientific authority

The conformance artifacts describe the behavior of the validated
`rtd-sensor` reference implementation.

Model and characteristic metadata preserve source and provenance information
needed to identify the underlying RTD characteristic and its scientific basis.

Conformance vectors complement rather than replace independently sourced
scientific validation. Agreement with generated vectors demonstrates behavioral
compatibility with the reference implementation; the project's independent
standards, manufacturer data, and resistance/temperature references remain the
evidence used to validate the reference implementation itself.

## Release stability

The first release that explicitly declares conformance contract v1 stable
establishes the normative v1 artifact set.

After that point:

- published identifiers retain their meanings;
- released artifacts remain reproducible from the corresponding project
  release;
- incompatible behavioral changes use a new `contract_version`;
- compatible additions may extend the available models, capabilities, or vector
  sets without redefining existing behavior; and
- release notes identify material conformance-contract changes.

A scientific correction may require a contract-version change when it changes
previously published externally observable behavior.

## References

Contract v1 relies on the following external specifications for interchange
format, schema validation, and unit definitions:

- IETF RFC 8259, *The JavaScript Object Notation (JSON) Data Interchange
  Format*;
- JSON Schema Draft 2020-12 Core and Validation specifications; and
- BIPM, *The International System of Units (SI)*, 9th edition.

Contract v1 does not define a project-specific URN namespace, canonical JSON
byte serialization, or a general-purpose unit grammar.
