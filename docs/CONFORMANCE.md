# RTD conformance contract

Status: **Stable — conformance contract v1**

`rtd-sensor` is the reference implementation for the RTD behavior described by
this contract. The conformance artifacts provide a language-neutral basis for
independent implementations to reproduce that behavior and demonstrate
interoperability without depending on Python internals.

The contract is language-neutral. It defines model identity, conversion
semantics, supported ranges, machine-readable reference cases, numerical
acceptance criteria, and semantic result statuses. It does not prescribe a
particular implementation algorithm or programming-language error mechanism.

Conformance contract v1 is stable. The identifiers and externally observable
semantics described here are frozen under the versioning rules below.

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

The stable v1 machine-readable artifact layout is:

```text
conformance/
└── v1/
    ├── manifest.json
    ├── characteristics.json
    ├── models.json
    ├── model-fixtures.json
    ├── examples/
    │   └── example-conformance-claim.json
    ├── schemas/
    │   ├── characteristic-catalog.schema.json
    │   ├── conformance-claim.schema.json
    │   ├── conformance-manifest.schema.json
    │   ├── model-catalog.schema.json
    │   ├── model-fixture-catalog.schema.json
    │   └── vector-set.schema.json
    └── vectors/
        ├── builtin-temperature-to-resistance.json
        ├── builtin-resistance-to-temperature.json
        ├── builtin-temperature-to-resistance-status.json
        ├── builtin-resistance-to-temperature-status.json
        ├── custom-temperature-to-resistance.json
        ├── custom-resistance-to-temperature.json
        ├── custom-temperature-to-resistance-status.json
        └── custom-resistance-to-temperature-status.json
```

The JSON artifacts are test and interchange data. Their use does not imply that
an embedded implementation must include a JSON parser in production firmware.
The stable v1 schemas are self-contained and use local `$defs`; cross-file
referential integrity and scientific consistency are validated separately from
JSON Schema structure validation.

A portable deployable-model format is a different artifact class from this
conformance tree. The portable model-definition format implemented for 0.6.0 uses its
own `format_version` and does not inherit conformance `contract_version` as its
serialization-compatibility version. It may reuse the same characteristic IDs,
model-kind vocabulary, and parameter meanings, but conformance-only concepts such
as local `fixture_id`, `expected_status`, and intentionally invalid definitions do
not become part of the deployment format. This separation also means that adding
a portable model format does not by itself change stable conformance-v1 behavior. The portable schema is
`portable/v1/model-definition.schema.json`; it is versioned independently from this
conformance contract.

## Versioning

Conformance artifacts carry four distinct version and maturity concepts.

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

### Contract status

`contract_status` records whether the artifact set is still subject to pre-freeze
change or has been declared stable under the contract-version rules.

The initial development value was `draft`. The completed v1 freeze changed it to
`stable` after the acceptance audit. The `draft` to `stable` transition does not
itself change `contract_version`; it freezes the reviewed semantics rather than
redefining them.

Once a contract version is stable, incompatible behavioral changes require a new
`contract_version` rather than returning the stable artifact set to draft status.

### Producing package version

Each generated artifact also records the `rtd-sensor` version that produced or
validated it.

The package version is provenance. It does not replace either `format_version`
or `contract_version`.

### Schema identity

Stable v1 intentionally does not publish JSON Schema `$id` values. The schemas
are self-contained and use local `$defs`, and the project does not yet have a
durable schema-host URI that should become a permanent downstream identity. A
provisional repository or raw-content URL would create a stronger compatibility
commitment than leaving `$id` absent.

Adding the eventual canonical `$id` values, without changing schema structure or
behavior, does not by itself require a `format_version` or `contract_version`
increment. After an `$id` has been published and downstream tooling may cache or
pin it, changing that identity is a separate compatibility decision and must be
reviewed explicitly.

## Identifier rules

Normative identifiers use lowercase ASCII and are case-sensitive. They match
`^[a-z][a-z0-9._-]*$`: an identifier begins with an ASCII letter and may then
contain lowercase ASCII letters, digits, periods, underscores, or hyphens.
Canonical IDs are not silently normalized and are never reused for a different
semantic meaning.

Display names and aliases are descriptive metadata rather than substitutes for
canonical IDs.

### Built-in model IDs

The stable v1 built-in model IDs are:

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

The stable v1 characteristic IDs are:

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
built-in models. The stable v1 characteristic schema distinguishes
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
separate from implementation-derived continuity adjustments. Stable v1 represents
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
  "rtd_sensor_version": "0.5.1",
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

`group_id` and `case_id` are stable diagnostic identifiers. A vector group
contains exactly one target identifier: built-in groups use `model_id`, while
custom/calibrated groups use local `fixture_id`. Case ordering has no semantic
meaning.

Tags are descriptive classifiers used for coverage and diagnostics. They are not
part of the pass/fail rule.

The committed stable-v1 built-in conversion vector sets are generated
deterministically from the authoritative model definitions and runtime behavior.
The successful-result sets contain binary64 reference anchors for all six built-in
models, including minimum and maximum model temperatures, values 0.001 °C inside
each boundary, reference and nearby branch points, representative operating
temperatures, and every source-segment midpoint and join for the piecewise Ni120
characteristic. The forward and inverse sets are paired through the same
temperature anchors so endpoint and round-trip behavior remain directly
comparable. Separate status sets cover range and invalid-input semantics without
attaching numerical acceptance profiles to non-success results.

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

For non-`ok` statuses, a numerical expected value is not present. The initial
built-in status vector sets exercise `out_of_range_low`, `out_of_range_high`, and
`invalid_input`. The custom model fixture catalog exercises `invalid_model` by
marking definitions that must be rejected before conversion is attempted.
`calculation_failure` is reserved for a valid model/input case in which a
required numerical result cannot be produced. No initial v1 vector intentionally
exercises this status because the current published models and valid fixture
inputs do not provide a natural, scientifically meaningful failure case; the
contract does not fabricate one solely to exercise the enum value.

These statuses describe semantics rather than language-specific control flow.
Python exceptions, C/C++ enums, result objects, or protocol status codes may all
represent the same contract status.

For the public Python API, `rtd_sensor.exceptions.RTDOutOfRangeError` groups the
`out_of_range_low` and `out_of_range_high` outcomes under one catchable range
category, while `InvalidRTDModelError` represents invalid public custom-model
configuration where the operation is within this contract's scope.
`UnknownRTDModelError` and `RTDModelSelectionError` are Python discovery/composition
errors rather than conversion-vector statuses. Invalid scalar inputs continue to
use the established `ValueError`/`TypeError` behavior, and no dedicated Python
`calculation_failure` exception is defined until a natural public failure mode
requires one.

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

The initial finite range-status anchors are 0.001 °C outside each temperature
boundary.

For resistance-to-temperature conversion:

- non-finite resistance is `invalid_input`;
- zero or negative resistance is `invalid_input`;
- finite positive resistance below the model's minimum valid resistance is
  `out_of_range_low`;
- finite resistance above the model's maximum valid resistance is
  `out_of_range_high`.

The initial finite resistance range-status anchors are 0.01 Ω outside each
forward-generated model endpoint. These offsets are conformance test inputs, not
extensions of the supported model range.

For a model endpoint, the resistance produced by valid forward conversion at
that endpoint is valid input to inverse conversion and returns the endpoint
within the applicable numerical acceptance tolerance.

## Numerical acceptance

Conformance requires engineering-equivalent numerical behavior rather than
bit-for-bit identity.

Successful reference values are generated by the validated Python reference
implementation.

The stable v1 contract distinguishes two acceptance profiles:

- `binary64_reference`
- `binary32_compatible`

An acceptance profile describes the allowed numerical difference from the
published reference value. It does not require the implementation to use that
floating-point representation internally.

Each successful built-in conversion vector publishes both acceptance profiles.
The successful characterized-reference-resistance fixture vectors described
below also publish both profiles. Other custom fixture families remain
`binary64_reference` only until their numerical behavior is separately studied.

The `binary64_reference` tolerance is `1e-9` in the vector set's output unit.
The `binary32_compatible` tolerances are `0.002 Ω` for
temperature-to-resistance conversion and `0.001 °C` for
resistance-to-temperature conversion. These are interoperability allowances for
floating-point evaluation, representation, and inversion differences; they are
not RTD sensor tolerances, calibration uncertainties, or
measurement-uncertainty statements.

The numerical pass rule is:

```text
abs(actual - expected) <= absolute_tolerance
```

The actual result must also be finite.

Absolute tolerances are used for the initial conversion contract because the
outputs are engineering quantities with explicit units and temperature relative
error is not useful around 0 °C.

These profile values are normative for stable conformance v1. Changes that
would alter the published acceptance semantics are governed by the contract-version
rules above.

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

## Independent implementation verification

The repository includes an independent C11 conformance consumer under
`conformance/consumers/c11/`. It consumes data derived only from the committed
conformance catalogs and vectors and does not import or link against
`rtd_sensor`.

The consumer supports the three characteristic representations currently used
by built-in and custom fixtures and verifies both conversion directions plus the
published range and invalid-input statuses. It also constructs every published
custom/calibrated fixture and independently verifies each fixture's expected
`ok` or `invalid_model` definition status. For piecewise fixtures, it consumes
the published derived continuity adjustments and independently verifies their
bounds, closed joins, and reference-temperature anchoring; it does not re-derive
those adjustments from the source coefficients. Its inverse implementation uses
bounded global bisection for every characteristic rather than reproducing the
Python implementation's curve-specific inversion strategies.

The C11 consumer is a verification implementation, not a required runtime
architecture for downstream systems. A separate single-precision build verifies
the published built-in `binary32_compatible` profile, and the same genuinely
single-precision path verifies the characterized-reference-resistance fixture
subset. Their derivations and measured error envelopes are documented in
`conformance/consumers/c11/BINARY32.md` and
`conformance/consumers/c11/BINARY32_CHARACTERIZED_R0.md`. Successful execution
demonstrates that the published built-in and custom-fixture contract contains
sufficient information for an independent implementation to reproduce the
specified behavior.

## Coverage represented by conversion vectors

The stable v1 built-in conversion vector sets define coverage for the following
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

Custom-model conformance is a separately claimable layer. The generated
`model-fixtures.json` catalog defines synthetic custom/calibrated model cases
using local `fixture_id` values. These fixtures are interoperability test data,
not additional built-in RTD identities or independent scientific reference
measurements.

Each fixture records an `expected_status` of `ok` or `invalid_model`. A fixture
with `expected_status: "ok"` must construct a valid model before conversion is
attempted. A fixture with `expected_status: "invalid_model"` must be rejected
as a model definition; its intentionally invalid numerical or structural
semantics are therefore allowed by the fixture catalog schema even though the
corresponding runtime model constructor rejects them.

The fixture catalog uses four definition kinds: `characteristic_model`,
`callendar_van_dusen`, `polynomial`, and `piecewise_polynomial`.

The initial custom-model layer covers:

- characterized reference resistance on the PT-385 characteristic at multiple
  resistance scales and both full and narrowed validity ranges;
- custom Callendar-Van Dusen coefficients;
- positive-only and negative-only declared ranges;
- a valid positive-only model whose resistance ratio crosses 1 at 60 °C rather
  than at the excluded 0 °C reference point;
- a polynomial model with a non-zero reference temperature;
- piecewise-polynomial models with local segment origins;
- explicitly authorized piecewise continuity adjustments; and
- invalid non-positive-R0, missing-C, non-monotonic, decreasing, gapped, and
  unapproved-discontinuity definitions.

Successful custom fixture conversions are published in
`custom-temperature-to-resistance.json` and
`custom-resistance-to-temperature.json`. Matching custom status sets exercise
declared range boundaries, invalid numerical inputs, and the explicit exclusion
of 0 °C from the positive-only and negative-only CVD validity intervals. Their
vector groups reference `fixture_id` rather than `model_id`. Successful
`characteristic_model` fixtures using `iec60751_pt385` publish both
`binary64_reference` and `binary32_compatible`; all other custom model families
remain `binary64_reference` only. The built-in binary32 tolerances are reused for
the characterized-R0 subset only after the independent empirical study recorded
in `conformance/consumers/c11/BINARY32_CHARACTERIZED_R0.md`.

For valid piecewise fixtures, source segment coefficients remain in the fixture
definition while implementation-derived continuity offsets are serialized
separately as derived metadata.

Custom fixture definitions remain local to the conformance fixture catalog and
do not acquire built-in `model_id` values.

The characterized-reference-resistance `binary32_compatible` profile remains
fixture-scoped for conformance purposes. An implementation may claim it only for
the explicit characterized-R0 fixture subjects allowed by the claim schema and
for which a binary32 acceptance envelope and vectors have been published. That
additive claim does not create a new canonical `model_id` and does not imply
binary32 support for the other custom fixture kinds.

The repository's independent C11 consumer verifies this layer without importing
Python model constructors. The generated binary64 C runner constructs all
fixture definitions from `model-fixtures.json`, requires the ten valid
definitions to validate, requires the six intentionally invalid definitions to
return `invalid_model`, and runs the complete custom binary64 conversion and
status vector sets. A separate float runner executes only the characterized-R0
fixture subset against `binary32_compatible` acceptance and status vectors. The
consumer's polynomial-shape validation is deliberately limited to the published
fixture claim rather than presented as a general replacement for the Python
package's analytical arbitrary-polynomial validator.

## Conformance claims

`schemas/conformance-claim.schema.json` defines a small machine-readable claim
format. A claim records `format_version`, `contract_version`, and one or more
independent claim entries. Each entry names exactly one capability, one subject
set, and one acceptance profile. Built-in subjects use `model_ids`; custom
conformance subjects use `fixture_ids`.

For example:

```json
{
  "artifact_type": "conformance_claim",
  "format_version": 1,
  "contract_version": 1,
  "claims": [
    {
      "capability_id": "conversion.resistance_to_temperature",
      "model_ids": ["pt100", "pt1000"],
      "acceptance_profile": "binary32_compatible"
    }
  ]
}
```

Claims are intentionally separated by capability and subject set. A
`binary32_compatible` built-in claim therefore does not imply binary32 support
for arbitrary custom coefficients. Fixture claims may use
`binary32_compatible` only for the explicit characterized PT-385 fixture IDs
listed by the claim schema; other fixture IDs remain `binary64_reference` only.
Claim validators must also check model and fixture identifiers against the
catalogs in the same conformance release; identifier existence is a cross-file
semantic check rather than a JSON Schema concern.

This claim does not imply support for other conversion directions, nickel
models, custom coefficients, tolerance calculations, uncertainty analysis,
simulation, or any hardware interface. A local `fixture_id` never becomes a
canonical `model_id`.

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

## Release bundle and stability

`manifest.json` is a generated release manifest for the machine-readable v1
tree. It records the producing `rtd-sensor` version, contract version/status, and
SHA-256 plus byte size for every schema, catalog, example, and vector file in
the release bundle except the manifest itself. The current manifest records
`contract_status: "stable"`.

The deterministic release ZIP contains exactly the manifest and the files it
names. A SHA-256 sidecar covers the ZIP itself. This gives downstream projects a
versioned artifact they can vendor or archive while keeping the normative prose
specification in this document at the corresponding project tag.

The stable-v1 declaration establishes the normative v1 behavioral contract and
records `contract_status: "stable"` in the manifest. The producing package version
is provenance and may advance without changing `contract_version` when the published
behavior remains compatible.

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
