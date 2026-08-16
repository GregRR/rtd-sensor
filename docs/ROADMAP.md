# rtd-sensor roadmap

This roadmap records planned capabilities and the scientific constraints that
must be satisfied before they become supported public features. It is not a
promise that every item will land in the next release.

The project has evolved from its original Pt100-only scope toward a general RTD
modeling library. Beginning with version 0.4.0, the project identity is:

```text
PyPI distribution:  rtd-sensor
Python import:       rtd_sensor
GitHub repository:   rtd-sensor
```

Version 0.4.0 completes the rename from the historical `pt100-core` distribution
and `rtd` import package. Existing `pt100-core` releases remain part of the
project history; migration requires updating imports to `rtd_sensor` as documented
in the README.

## 0.5.0 integration and public-interface release

Version 0.5.0 packages roadmap items 1 through 7 as one release milestone. It
makes `rtd-sensor` easier to compose with real acquisition code while preserving
the scientific/hardware boundary, freezes stable conformance contract v1,
exposes the public model/catalog/measurement contracts, adds the public exception
taxonomy, and adds tabulated RTD characteristics. The target data flow is:

```text
hardware / acquisition layer
        │
        │ compensated sensor-element resistance in ohms
        ▼
rtd-sensor
        │
        │ temperature / model / tolerance / uncertainty results
        ▼
application layer
```

An MCU, converter, ADC, or other acquisition layer should know how to obtain
the best available estimate of sensor-element resistance. `rtd-sensor`
should remain responsible for interpreting that resistance through an RTD model.
Application code composes the two layers; neither package should duplicate the
other layer's responsibilities.

Items 1 through 7 are implemented and form the 0.5.0 release scope. Release
preparation begins after item 7; feature development should not continue into
item 8 until 0.5.0 has completed its release-readiness gate and been published.

The next planned release is **0.6.0**. Items 8 and 9 are its required roadmap
milestone, with the release boundary immediately after item 9. Item 10 is
ongoing, provenance-dependent built-in expansion: support-ready characteristics
may land during the 0.6.0 cycle, but item 10 is not a blocker for the 0.6.0
release. This explicit boundary is intentional so open-ended characteristic
research cannot silently postpone a completed release milestone.

### Release boundaries

- **0.5.0:** items 1–7; stop after item 7 for release preparation and publication.
- **0.6.0:** items 8–9; stop after item 9 for release preparation and publication.
- **Item 10:** may land when scientifically support-ready, but does not move the
  0.6.0 release boundary.

When the final required item for a named release is complete, the next project
action is the release-readiness process in `docs/RELEASING.md`, not the next
roadmap feature.

### 1. Public RTD model protocol — implemented foundation

The public `rtd_sensor.models.RTDModel` protocol provides one small structural
interface for code that consumes RTD conversion behavior. Built-in sensor
modules, configurable package models, and compatible third-party objects satisfy
it without inheriting from a package-specific base class.

The implemented protocol covers four numerical operations:

```python
from typing import Protocol


class RTDModel(Protocol):
    def celsius_to_resistance(self, temperature_c: float) -> float: ...

    def resistance_to_celsius(self, resistance_ohms: float) -> float: ...

    def resistance_sensitivity_ohms_per_celsius(
        self, temperature_c: float
    ) -> float: ...

    def temperature_sensitivity_celsius_per_ohm(
        self, temperature_c: float
    ) -> float: ...
```

The protocol deliberately excludes valid-range properties as well as identity,
display name, material, aliases, and provenance. The built-in module APIs expose
ranges through their established constants, while configurable model objects
have range properties. Code that needs a uniform range or other discoverable
metadata should use the model-discovery/metadata interface rather than forcing
every structural conversion model to expose one metadata shape. This also keeps
the existing built-in modules valid structural `RTDModel` implementations.

The narrower `uncertainty.RTDUncertaintyModel` protocol remains available for
uncertainty-only callers. `RTDModel` includes that narrower behavior, preserving
third-party implementations that provide only inverse conversion and `dT/dR`.
Simulation model annotations now depend on the structural protocol rather than
the private concrete built-in model class.

Strict mypy regressions verify the intended built-in, configurable, third-party,
and uncertainty-only relationships without changing conversion mathematics or
validation semantics.

### 2. Language-neutral RTD conformance contract — stable v1 complete

The detailed conformance design is maintained in `docs/CONFORMANCE.md`. The
roadmap section below records its goals and sequencing; the design document is
the implementation reference for identifiers, schemas, statuses, numerical
acceptance, and artifact structure.

Implementation foundation completed so far: the reviewed authoritative
characteristic/model definition layer, the initial Draft 2020-12 schemas,
deterministic characteristic/model catalogs, generated built-in conversion and
status vectors, an independent C11 consumer, and an empirically derived
`binary32_compatible` acceptance profile verified with real single-precision C
arithmetic, plus generated custom/calibrated model fixtures spanning valid and
invalid configurable-model behavior. The independent C11 consumer now verifies
that custom fixture layer as well, including model-definition rejection. Release
integration is also in place: the v1 tree has a generated checksum manifest, a
machine-readable claim schema/example, deterministic ZIP packaging with a
SHA-256 sidecar, and release-checklist verification. The final acceptance and
schema-freeze audit is complete, and conformance contract v1 is now stable.
Further incompatible behavioral changes require a new contract version. The next
0.5 integration focus is public built-in model discovery and immutable metadata
views from the same authoritative definitions.

Establish `rtd-sensor` as the authoritative reference implementation for RTD
conversion behavior, not merely as one Python implementation of the same
equations. A future MCU implementation in C/C++ or another language should be
able to reproduce the supported subset of `rtd-sensor` behavior and prove that
compatibility without reverse-engineering Python source code.

The goal is a shared behavioral contract:

```text
                    rtd-sensor
              Python reference library
                     │
                     │ conformance contract
                     ▼
        machine-readable reference artifacts
                     │
          ┌──────────┴──────────┐
          │                     │
   Python verification     embedded / other
                           implementations
```

This work does **not** imply a full embedded port of `rtd-sensor`. A constrained
MCU implementation may intentionally support only selected built-in
characteristics, resistance-to-temperature conversion, calibrated reference
resistance, range validation, and deterministic status output. It need not
implement the Python package's simulation framework, rich custom-model API,
uncertainty analysis, fitting tools, or every future characteristic.

Begin this work before production MCU conversion code is established. Once a
second implementation depends on copied coefficients, model names, boundary
behavior, or error interpretation, correcting ambiguity becomes a
cross-project compatibility problem rather than a local library change.

#### 2.1 Machine-readable conformance vectors

The Draft 2020-12 vector-set schema and deterministic artifact generator are in
place. Committed built-in vectors now cover successful temperature-to-resistance
and resistance-to-temperature behavior for all six current models using both
`binary64_reference` and `binary32_compatible` acceptance profiles, plus
separate status sets for finite out-of-range inputs, non-finite values, and
zero/negative resistance.

An independent C11 consumer now compiles against model/characteristic data
derived from the committed artifacts and passes the complete published built-in
conversion and status vector set using a different inverse strategy from
Python. Generated custom/calibrated fixtures now cover characterized R0, custom
CVD one- and two-sided ranges, the off-zero R/R0 crossing regression, polynomial
and piecewise models, bounded continuity stitching, representative
`invalid_model` definitions, and explicit custom range/status behavior. Their
successful vectors currently claim only the `binary64_reference` profile. The
independent C11 consumer now constructs every fixture definition, verifies its
expected `ok` or `invalid_model` construction status, and reproduces all
published custom binary64 conversion and status vectors.

#### 2.2 Representative coverage, not exported test-suite duplication

Conformance artifacts should cover every supported behavior an external
implementation may claim, but they should not simply export thousands of Python
unit tests.

Representative vector sets should eventually cover:

- Pt100, Pt500, and Pt1000;
- Ni1000 6178/6180, Ni1000 TK5000, and Ni120;
- characterized reference resistance / calibrated `R0`;
- custom Callendar-Van Dusen coefficient sets;
- single-polynomial and piecewise-polynomial models;
- tabulated models once implemented; and
- other future characteristics only after they become supported.

Each capability should be separable so an embedded implementation can claim a
specific conformance profile without implying support for the entire Python
package.

#### 2.3 Deliberate boundary and branch cases

Reference vectors must exercise behavior that tends to diverge between
implementations, including:

- minimum and maximum supported temperatures;
- values immediately inside supported boundaries;
- 0 °C and other model reference temperatures;
- important published standard/reference points;
- representative negative and positive temperatures;
- both sides of piecewise or equation branches;
- segment joins for piecewise models;
- values that stress inverse convergence and floating-point conditioning;
- representative engineering operating points; and
- forward/inverse round-trip cases.

The purpose is behavioral equivalence, especially where a superficially correct
implementation is most likely to differ.

#### 2.4 Explicit numerical compatibility tolerances

The initial built-in conversion vectors define `binary64_reference` with an
absolute tolerance of `1e-9` in the output unit. This is a cross-implementation
floating-point allowance, not a sensor tolerance or measurement-uncertainty
claim.

The `binary32_compatible` profile is now published for the built-in conversion
vectors with absolute tolerances of `0.002 Ω` for
temperature-to-resistance and `0.001 °C` for resistance-to-temperature. The
profile was selected from measured single-precision behavior across the full
published vectors plus dense/random stress samples and is verified by the
independent C11 float consumer.

#### 2.5 Authoritative equations, coefficients, and numerical decisions

An external implementer must not need to read private Python source to discover
the required behavior. For every conformant model or model family, document:

- the equation or table formulation;
- the complete coefficient set;
- reference resistance and reference-temperature semantics;
- valid temperature range and derived resistance limits where applicable;
- branch or segment rules;
- inversion method or required inversion behavior;
- source/standard/manufacturer provenance;
- published-source precision relevant to the implementation;
- continuity adjustments or other explicitly authorized transformations; and
- numerical decisions that materially affect cross-language reproduction.

The Python implementation, documentation, and exported artifacts must derive
from the same authoritative model definitions wherever practical rather than
maintaining independent copies.

#### 2.6 Language-neutral range and error semantics

Define semantic outcomes separately from Python exception mechanics. External
implementations do not need to raise Python exceptions, but they should agree
on the meaning of failures such as:

- input below the supported model range;
- input above the supported model range;
- invalid model configuration;
- invalid or non-finite numeric input;
- impossible/non-monotonic model configuration; and
- inverse-calculation or convergence failure.

The stable v1 language-neutral status vocabulary is:

```text
ok
out_of_range_low
out_of_range_high
invalid_input
invalid_model
calculation_failure
```

Built-in status vectors currently exercise the range and invalid-input outcomes.
The custom fixture catalog now exercises `invalid_model` through definitions
that must fail model construction. `calculation_failure` remains reserved for a
valid model/input whose required numerical result cannot be produced. These
semantic names map independently to
Python exceptions, C/C++ enums, protocol status codes, or other
language-appropriate mechanisms.

This work should coordinate with the public exception taxonomy later in this
roadmap so Python application exceptions and cross-language statuses describe
the same underlying conditions rather than evolving independently.

#### 2.7 Layered conformance profiles

Do not create one monolithic "supports rtd-sensor" claim. Define separable
conformance layers such as:

```text
conversion/
    standard built-in Pt/Ni resistance ↔ temperature behavior

calibration/
    characterized reference resistance
    custom coefficient sets

models/
    single polynomial
    piecewise polynomial
    tabulated characteristics

tolerance/
    tolerance-class examples where a sourced rule exists
```

An embedded implementation may then claim, for example, basic Pt100/Pt1000
conversion conformance without claiming uncertainty analysis, arbitrary custom
models, or every built-in characteristic.

Profile names, required vectors, and capability declarations should be
machine-readable enough for CI to verify a claimed subset.

#### 2.8 Keep hardware acquisition outside the conformance layer

The conformance boundary remains **sensor-element resistance ↔ temperature/model
behavior**. Do not add SPI, I²C, GPIO, ADC configuration, converter registers,
lead-wire acquisition logic, PID, actuator control, or platform-specific
drivers to `rtd-sensor` merely to support an MCU.

The intended composition remains:

```text
hardware driver / acquisition
            │
            │ compensated resistance
            ▼
embedded RTD implementation
            │
            │ temperature + semantic status
            ▼
host / controller / application
```

Changing from one ADC, converter, MCU, or host platform to another must not
change the definition of the RTD characteristic.

#### 2.9 Generated authoritative artifacts

Investigate generating implementation-neutral artifacts directly from
`rtd-sensor` model definitions so constants and metadata do not drift across
implementations. Candidate artifacts include:

```text
model_metadata.json
coefficients.json
reference_vectors.json
```

The first priority is stable machine-readable data, not generated source code.
Generated C/C++ constants may be considered later if doing so clearly reduces
duplication without making the Python build system responsible for embedded
application architecture.

Any generated artifact must be reproducible from version-controlled source
definitions and covered by tests that detect accidental changes.

#### 2.10 Version the conformance contract

Once another implementation consumes exported conformance data, the contract
itself becomes a compatibility surface.

Every exported artifact should identify at least:

- conformance schema/version;
- `rtd-sensor` version that produced or validates it;
- canonical model identifier;
- conformance profile/capabilities;
- source characteristic/standard identity where relevant; and
- numerical-tolerance policy/version where needed.

Do not assume the package version alone is sufficient forever. A lightweight
conformance version can begin at `1` and evolve only when the external contract
changes materially.

A downstream implementation should eventually be able to vendor or fetch a
specific conformance release and run its own CI against that exact contract.

#### 2.11 Stable model identity for host/MCU interoperability

The conformance design must establish stable canonical model identifiers that
can safely appear in configuration files, logs, recorded measurements, or
future host↔MCU protocols.

The existing Python identities such as `pt100` are useful application-facing
names, but the conformance design should explicitly decide whether they are
also sufficient as long-lived wire identifiers or whether a more explicit
characteristic identifier is needed. Do not invent a protocol-specific naming
scheme in the roadmap; define the identity once and let downstream protocols
reference it.

The same principle applies to semantic status values: a protocol should carry a
stable RTD status meaning, not independently redefine what an out-of-range or
invalid-model result means.

#### 2.12 Implementation sequence and acceptance criteria

Preferred sequence:

1. complete the public RTD model protocol in item 1;
2. define conformance scope, canonical model identity, status vocabulary,
   schema, units, and tolerance policy;
3. generate and validate conversion/status vectors for the existing built-in
   models;
4. test the exported built-in contract with at least one deliberately
   independent consumer that does not import `rtd-sensor`;
5. measure and publish a justified `binary32_compatible` acceptance profile;
6. add layered vectors for calibrated/custom model capabilities;
7. complete any remaining equation/provenance documentation required for those
   additional layers; and
8. only then treat an MCU RTD implementation as ready to claim the corresponding
   conformance subset.

Done when an independent implementation can select a declared profile, consume
the published model metadata and reference vectors, reproduce the specified
behavior within documented tolerances, and map failures to the defined semantic
statuses without inspecting Python implementation internals.

### 3. Public built-in model discovery and immutable metadata — implemented

The public `rtd_sensor.catalog` module provides read-only discovery without exposing the internal registries themselves:

```python
from rtd_sensor import catalog

model_ids = catalog.supported_models()
model = catalog.get_model("pt100")
info = catalog.model_info("pt100")
```

`supported_models()` returns the stable canonical built-in IDs in authoritative definition order. `get_model()` returns a cached immutable adapter exposing only the public `RTDModel` numerical protocol rather than the private concrete runtime model. `model_info()` returns a frozen `BuiltinRTDModelInfo` descriptor containing canonical model and characteristic identity, display names, material, curve kind, reference resistance and temperature, valid temperature range, and immutable source references.

The metadata view is generated directly from the authoritative `_definitions` layer used by runtime model construction and conformance generation, so applications, configuration files, CLIs, and GUIs do not need a separately maintained capability table. Pt100, Pt500, and Pt1000 therefore retain distinct model identities while correctly sharing the `iec60751_pt385` characteristic identity.

Unknown canonical IDs raise `UnknownRTDModelError` (a `KeyError` subclass), non-string IDs raise `TypeError`, and identifiers are not silently normalized or aliased. There is intentionally no public plugin/registration mechanism yet; user-defined structural `RTDModel` implementations remain independent of the closed set of verified built-in identities.

Regression tests lock the descriptor view to the authoritative definitions, preserve nested immutability, verify stable package-owned lookup adapters, prevent leakage of private runtime-model attributes, cross-check model behavior against discovery metadata, and statically verify that catalog lookups satisfy the public `RTDModel` protocol.

### 4. Neutral resistance-reader interface outside `simulation` — implemented

The public `rtd_sensor.measurement.ResistanceReader` protocol now owns the
hardware-neutral resistance-reading contract:

```python
class ResistanceReader(Protocol):
    def read_resistance_ohms(self) -> float: ...
```

The interface is structural and intentionally contains only one operation.
Hardware or application objects do not need to inherit from an `rtd-sensor`
class; they qualify by returning the best available sensor-element resistance
estimate in ohms. Acquisition details such as GPIO, SPI, I²C,
ADC/reference-resistor configuration, MAX31865 handling, wiring topology, and
lead compensation remain outside this package.

Simulation readers implement the same neutral protocol, and
`rtd_sensor.simulation.ResistanceReader` remains an exact compatibility
re-export so existing documented imports continue to work. The protocol does
not require RTD identity or model metadata: acquisition produces resistance,
while model selection remains a separate composition concern.

This item intentionally moves only the acquisition contract. Model-object
conversion and its precedence rules remain item 5.

### 5. Model-object conversion for resistance readers — implemented

The neutral `rtd_sensor.measurement.read_temperature_celsius()` helper now
combines any `ResistanceReader` with an arbitrary structural `RTDModel`:

```python
model = get_model("pt100")
temperature_c = read_temperature_celsius(reader, model=model)
```

Individually characterized probes use the same path:

```python
model = IEC60751RTDModel(r0_ohms=100.037)
temperature_c = read_temperature_celsius(reader, model=model)
```

The existing built-in `rtd_type` convenience and historical Pt100 default for
untyped readers are retained for compatibility. Selection is deliberately
unambiguous: callers may pass `model` or `rtd_type`, not both. A reader that
declares `rtd_type` may use that declaration implicitly or with the same
explicit built-in type, but it cannot be combined with an explicit model
object because the structural `RTDModel` protocol contains no identity metadata
with which to prove compatibility. Invalid or contradictory declarations are
rejected before a source reading is consumed.

`rtd_sensor.simulation.read_temperature_celsius` is an exact compatibility
re-export of the neutral helper. Acquisition exceptions and model-conversion
exceptions propagate unchanged, preserving the hardware/scientific boundary for
the small public exception taxonomy considered in item 6. Higher-level channel
composition remains outside `rtd-sensor`.

### 6. Small public exception taxonomy — implemented

The public `rtd_sensor.exceptions` module now provides one small domain hierarchy:

```text
RTDError
├── UnknownRTDModelError     (also KeyError)
├── RTDOutOfRangeError       (also ValueError)
├── InvalidRTDModelError     (also ValueError)
└── RTDModelSelectionError   (also ValueError)
```

The dual inheritance preserves the package's established catch behavior while giving applications stable exception classes for unknown built-in identity, supported-range failure, invalid custom-model configuration, and reader/model selection ambiguity. Built-in and configurable model conversions use `RTDOutOfRangeError` only for finite values outside the supported range; non-finite/non-positive scalar validation keeps its previous `ValueError` behavior.

Custom public model constructors translate mathematically invalid model definitions into `InvalidRTDModelError` while retaining `TypeError` for type-category mistakes. Catalog lookup uses `UnknownRTDModelError`, and the neutral measurement composition layer uses `RTDModelSelectionError` for package-owned selection conflicts. Hardware-reader exceptions and arbitrary third-party `RTDModel` exceptions continue to propagate unchanged rather than being relabeled as RTD-domain failures.

This Python hierarchy intentionally does not mirror every stable conformance-v1 status one-for-one. `RTDOutOfRangeError` groups the language-neutral low/high range statuses, unknown-model lookup remains a capability/selection concern, and `calculation_failure` stays reserved until a natural public numerical failure mode requires a dedicated Python exception.

### 7. Tabulated RTD characteristics — implemented

Implemented `TabulatedRTDModel` and immutable `TabulatedRTDPoint` rows for authoritative resistance/temperature tables. The model participates in the same public `RTDModel` protocol as equation-backed characteristics, preserves source rows without fitting, uses documented piecewise-linear interpolation with exact interval inversion, exposes local sensitivity and provenance/precision metadata, and rejects extrapolation beyond the source table.

Tables must contain at least two finite rows with strictly increasing temperature and strictly increasing positive resistance. Interior-knot sensitivity follows the interval on the right and the final knot follows the last interval, matching the deterministic one-sided convention already used for piecewise characteristics.

With item 7 complete, the next action is the 0.5.0 release-readiness and
publication process described in `docs/RELEASING.md`. Calibration fitting starts
the 0.6.0 development line only after that release is complete.

### 8. Calibration fitting — planned for 0.6.0

Implement the fitting work described under **Calibration and model fitting**
after the public model interface is stable. A fit should produce a normal model
object plus auditable fit results, retaining observations, residuals, RMS and
maximum error, fitting range, weighting/uncertainty inputs, and reproducibility
assumptions.

### 9. Batch and vector conversion conveniences — planned 0.6.0 release boundary

Add batch conversion only after the scalar model interface is stable. Prefer a
small dependency-free iterable API first if it can be specified clearly. Do not
make NumPy a mandatory runtime dependency for convenience; if acceleration later
matters, consider an optional adapter/extra and verify scalar/batch numerical
equivalence at boundaries.

### 10. Additional built-in RTD characteristics — ongoing, not a 0.6.0 blocker

Continue adding platinum, nickel, copper, or manufacturer-specific built-ins
only when authoritative characteristic definitions and independent validation
justify them. New built-ins should reuse the public model, discovery, and
measurement interfaces rather than expanding those interfaces ad hoc. Provenance
and support-readiness remain more important than maximizing the sensor count.

The 0.4.x foundation that this milestone builds upon is summarized below.

## 0.4.x development direction

### Completed foundation

- Pt100 IEC 60751 PT-385 support.
- Pt500 IEC 60751 PT-385 support with independent reference values.
- Pt1000 IEC 60751 PT-385 support with independent reference values.
- Configurable IEC 60751 models with characterized `R0`.
- Custom Callendar-Van Dusen coefficient models.
- IEC 60751 platinum tolerance calculations.
- Analytical sensitivity and first-order measurement-uncertainty tools.
- Model-aware simulation.
- Generic single-polynomial RTD characteristics with an explicit reference
  resistance and reference temperature.
- Generic piecewise-polynomial RTD characteristics with preserved source
  segments, analytical validation, bounded inversion, and explicit auditable
  continuity stitching for independently rounded source fits.

### Characteristic architecture

The general RTD architecture must treat the *characteristic* as distinct from
material, nominal resistance, and TCR. Two sensors must not be assumed to share
a curve merely because they have the same `R0` or the same nominal ppm/K value.

The target internal/public model family is:

```text
RTD characteristic
├── Callendar-Van Dusen platinum characteristic
├── single polynomial characteristic
├── piecewise polynomial characteristic          implemented foundation
└── tabulated characteristic                     implemented

RTD model
├── characteristic
├── reference resistance
├── reference temperature
├── declared valid range
└── provenance / characteristic identity
```

All invertible characteristics must provide:

- forward temperature-to-resistance conversion;
- bounded resistance-to-temperature inversion;
- analytical or otherwise well-defined local `dR/dT` sensitivity;
- explicit valid temperature range;
- finite, positive resistance throughout that range;
- strict monotonicity over the supported range; and
- floating-point-safe boundary round trips.

### Nickel characteristics introduced in 0.4.0

Nickel support proceeds characteristic-by-characteristic, with equation provenance
and independent reference values for each one. Version 0.4.0 introduced:

- **Ni1000 6180 ppm/K** — implemented as `rtd_sensor.ni1000` using the former DIN
  43760 / Nickel ND characteristic. The mathematical -60 °C through 250 °C
  range is kept separate from narrower physical-product ratings.
- **Ni1000 TK5000 / 5000 ppm/K** — implemented as `rtd_sensor.ni1000_tk5000`
  using the IST Nickel NL cubic and independently validated against the E+E
  TK5000 R/T table. It remains a distinct identity from `rtd_sensor.ni1000`.
- **Ni120 North-American 6720 ppm/K** — implemented as `rtd_sensor.ni120` using
  Minco's twelve-segment `NA` characteristic from -80 °C through 260 °C, with
  explicit bounded stitching for printed-coefficient join mismatches and
  independent Pyromation R/T validation.

The support-readiness process used for these characteristics, and required for
future built-ins, includes:

- authoritative forward equation or table provenance;
- explicit characteristic identity and common aliases;
- reference resistance and reference temperature;
- defensible mathematical validity range;
- an independent resistance/temperature validation source;
- published source precision reflected in test tolerances;
- boundary, monotonicity, round-trip, and out-of-range tests;
- simulation integration if a built-in convenience sensor module is added;
- user documentation that identifies exactly which characteristic is meant;
- tolerance semantics researched independently from IEC 60751 platinum
  classes.

### Additional nickel characteristics to investigate

Keep these on the research roadmap even if they do not land in 0.4.x:

- Nickel NJ / approximately 6370 ppm/K and its actual nominal-resistance
  variants and industry aliases.
- IST/manufacturer-specific NA 6720 characteristics that differ from the
  Minco/Pyromation Ni120 curve away from the 0-to-100 °C TCR interval.
- Other documented Balco/nickel characteristics encountered in industrial or
  building-automation equipment.

## Copper RTDs

Copper support remains planned as a later expansion now that the initial nickel
architecture is established.
Candidates include:

- **Cu10**, particularly legacy motor/generator winding and industrial
  monitoring applications.
- **Cu100**, if research establishes a sufficiently useful and well-defined
  characteristic to justify first-class support.

Do not assume that a nominal name such as Cu10 uniquely defines the reference
temperature, alpha value, valid range, or complete curve. Each supported copper
characteristic must pass the same provenance and independent-validation policy
as platinum and nickel.

## User-defined characteristics

The library should eventually support manufacturer, calibration-laboratory,
and legacy-equipment curves that are not built into the package.

### Single polynomial models

Implemented foundation: users can supply a normalized polynomial, reference
resistance, reference temperature, declared range, name, and coefficient
provenance. The package validates positivity and monotonicity before allowing
inversion.

### Piecewise polynomial models

Implemented foundation. Some authoritative RTD characteristics are published
as different polynomials over different temperature intervals. The public
model now:

- retains source segment boundaries, complete coefficient tuples, local
  temperature origins, and coefficient provenance;
- validates every segment analytically for positive resistance and strict
  monotonicity;
- rejects temperature gaps and overlaps;
- preserves the reference-temperature segment as the continuity anchor;
- rejects source-level join discontinuities by default;
- can explicitly authorize bounded constant-term stitching when independently
  rounded source fits are demonstrably intended to represent one continuous
  characteristic;
- exposes every applied continuity adjustment for auditability;
- provides one monotonic bounded inverse across the complete stitched
  characteristic; and
- preserves exact endpoint, reference-temperature, and segment-boundary round
  trips.

The Minco North-American 120-ohm nickel stepwise approximation is the first
built-in consumer of this representation. Its published 12-segment cubic
coefficients motivate the explicit stitching policy because printed coefficient
precision leaves very small join mismatches even though the source describes one
standard nickel curve.

### Tabulated characteristics

Implemented. A manufacturer's resistance/temperature table may be more scientifically authoritative than fitting a new polynomial to it. `TabulatedRTDModel` therefore retains immutable source points and uses dependency-free piecewise-linear interpolation rather than fitting a new curve.

The implemented table contract:

- retains the supplied source rows without fitting or adjustment;
- requires strictly increasing temperature and resistance for a unique inverse;
- uses documented piecewise-linear interpolation;
- prohibits extrapolation outside the table range;
- exposes `interpolation_method == "linear"` plus optional source-precision metadata;
- preserves optional table provenance; and
- uses the same four-operation public `RTDModel` protocol and one-sided knot-sensitivity convention as the other characteristic forms.

## Calibration and model fitting

Later work may construct a characteristic from measured calibration points,
but fitting must remain separate from simply *using* a published equation.

Potential fitting capabilities:

- fit a user-selected polynomial degree from `(temperature, resistance)`
  observations;
- retain the original calibration observations;
- report residuals for every point;
- report RMS and maximum residual error;
- retain weighting and calibration-point uncertainty when supplied;
- declare the range over which the fit is considered valid;
- validate positivity and monotonicity of the fitted characteristic;
- warn against or prohibit unvalidated extrapolation;
- support covariance of fitted coefficients in a later uncertainty layer.

A fitted curve must never be presented as a manufacturer or standards-defined
characteristic unless that provenance is actually established.

## Tolerance and uncertainty

- Keep nominal conversion, calibration, tolerance, and measurement uncertainty
  as separate layers.
- Never apply IEC 60751 platinum AA/A/B/C tolerance classes to nickel or copper
  without an applicable source.
- Research nickel/copper tolerance rules per characteristic or product family.
- Keep tolerance limits distinct from probability distributions and standard
  uncertainties.
- Later uncertainty work may add covariance-aware propagation, effective
  degrees of freedom, coefficient covariance, and Monte Carlo methods.

## Simulation and model identity

Simulation identity is now driven by one immutable built-in model registry rather
than a separately maintained `Literal[...]` and lookup table. Each verified
built-in declares its identity alongside its internal model definition,
`simulation.SUPPORTED_RTD_TYPES` is generated from that registry, and the
conflict/identity regression matrix expands automatically as new built-ins are
registered. The existing rule remains unchanged: a model-aware reader cannot be
silently interpreted using a contradictory sensor identity.

A public plugin/registration mechanism remains intentionally deferred. User-defined
RTD models and verified package built-ins have different provenance and support
contracts, so simulation should not blur them merely to make registration dynamic.

## Hardware boundary

The scientific RTD package continues to consume the best available estimate of
sensor-element resistance. These concerns remain outside this package:

- ADC and reference-resistor configuration;
- 2-/3-/4-wire acquisition and lead compensation;
- MAX31865 or other converter register handling;
- GPIO/SPI/I²C access;
- Raspberry Pi, BeagleBone, MCU, or other platform-specific drivers.

A later hardware/acquisition package can feed compensated resistance values to
`rtd-sensor` without duplicating the characteristic mathematics. The
language-neutral conformance contract above exists so an embedded implementation
can reproduce the same conversion behavior without moving hardware concerns into
this package.

## Longer-term performance and convenience work

Potential later additions include:

- generated lookup tables for constrained systems;
- alternative standardized platinum characteristics;
- richer calibration-certificate metadata;
- diagnostic helpers for sensor/open/short plausibility when enough hardware
  context is available at the appropriate layer.

## Nickel research source set to retain

These sources have been identified during the 0.4.x research phase and should
be retained for coefficient/range/alias verification and independent tests.
A source appearing here does not by itself make a characteristic supported.

- Schneider Electric FAQ on Ni1000 characteristic differences and controller
  selection:
  https://www.se.com/be/fr/faqs/FA282624/
- TE / Farnell Ni1000SOT technical data for the former-DIN 6178/6180 ppm/K
  characteristic:
  https://www.farnell.com/datasheets/2301873.pdf
- Heraeus Nexensos 100489-6 Ni1000 data sheet: useful corroboration for the
  -60 °C through 250 °C DIN 43760 range, but its printed polynomial differs
  from the ABB/IST/TE/Honeywell coefficient consensus (including `5.481e-3`
  for the linear term and a positive sixth-order term). Retain this as a
  documented source discrepancy rather than silently averaging coefficients:
  https://www.mouser.com/datasheet/2/619/hera_s_a0009182606_1-2289114.pdf
- IST AG nickel application note with the Nickel NL (5000 ppm/K) cubic
  coefficients used by `rtd_sensor.ni1000_tk5000`:
  https://www.mouser.com/datasheet/2/1426/nl1k0_520_2fw_b_007-2950467.pdf
- E+E Ni1000 TK5000 resistance/temperature table used for independent
  implementation validation:
  https://www.epluse.com/fileadmin/data/product/r-t_characteristics/R_T_Characteristics_Ni1000_TK5000.pdf
- Minco resistance-thermometry engineering material and North-American nickel
  characteristic tables:
  https://www.minco.com/wp-content/uploads/Resistance-Thermometry.pdf
  https://www.minco.com/wp-content/uploads/NA-in-deg-C-7-120.pdf
- Pyromation 120-ohm / 0.00672 nickel reference table:
  https://www.pyromation.com/downloads/data/672_c.pdf
- IST AG nickel characteristic/product documentation for 6180, 5000, 6370,
  6720 ppm/K and related element variants:
  https://www.ist-ag.com/en/temperature-sensors
- National Instruments RTD background/reference documentation:
  https://www.ni.com/docs/en-US/bundle/ni-dmm/page/resistance-temperature-detector-rtds.html

When two reputable sources disagree, preserve the disagreement and determine
whether they represent distinct characteristics rather than averaging or
silently reconciling their coefficients.
