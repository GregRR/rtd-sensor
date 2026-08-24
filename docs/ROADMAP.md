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
resistance-measurement source
        │
        │ trustworthy estimate of sensor-element resistance in ohms
        ▼
rtd-sensor
        │
        │ temperature / model / tolerance / uncertainty results
        ▼
application layer
```

An MCU, converter, ADC, or other acquisition layer is one way to obtain the best
available estimate of sensor-element resistance, but it is not a mandatory hop.
An instrument, RTD interface, DAQ, resistance bridge, multimeter, or recorded data
source that already provides a trustworthy RTD-element resistance in ohms can feed
`rtd-sensor` directly. `rtd-sensor` remains responsible for interpreting that
resistance through an RTD model; acquisition, hardware, and application concerns
remain outside the scientific model layer.

Items 1 through 7 shipped in version 0.5.0 on 2026-08-16. Version 0.5.1 was a
corrective documentation/release-process release and did not add roadmap feature
scope. Items 8 through 11 shipped in version 0.6.0 on 2026-08-17. Version 0.6.1
shipped on 2026-08-19 and expanded supported Python versions from Python 3.14
only to Python 3.11 through 3.14 without adding roadmap feature scope. The 0.7.0
calibration and statistical foundation is implemented.

Item 12 remains an ongoing, provenance-dependent built-in expansion track rather
than a release gate. New characteristics may land whenever their equations, source
provenance, independent validation, range, and tests are support-ready.

### Release boundaries

- **0.5.0:** items 1–7; published 2026-08-16.
- **0.5.1:** corrective documentation/release-process release; published 2026-08-16.
- **0.6.0:** items 8–11; published 2026-08-17.
- **0.6.1:** Python 3.11–3.14 compatibility release; published 2026-08-19.
- **0.7.0:** calibration and statistical foundation; implementation complete.
- **0.8.0:** industrial measurement effects, including self-heating characterization
  and zero-power correction.
- **0.9.0:** calibration experiment design, tabulated interoperability completion,
  characteristic-compatibility promotion decision, and pre-1.0 API review.
- **1.0.0:** stability release for the mature scientific, calibration, uncertainty,
  portability, and interoperability interfaces.
- **Item 12:** version-independent characteristic expansion; it does not move a
  named release boundary.

When the final required item for a named release is complete, the next project
action is the release-readiness process in `docs/RELEASING.md`, not the next
roadmap feature.

## Road to 1.0

Version 1.0 is not defined as "every plausible RTD feature is implemented." It is
the point at which the project's core scientific interfaces and semantics are
mature enough for an explicit long-term compatibility commitment. The planned
sequence deliberately lets new calibration and metrology APIs mature before that
commitment is made.

Scientific and industrial claims introduced by these releases must remain
traceable to primary standards, metrology guidance, calibration literature, or
manufacturer documentation as appropriate. Relevant source material should be
retained in the repository and cited in implementation/design documentation so a
reader can reproduce the reasoning rather than relying on undocumented package
convention.

### 0.7.0 — calibration and statistical foundation

Build on the 0.6.0 polynomial-fitting foundation so later metrology features can
reason about fitted-model uncertainty rather than only fitted coefficients. The
implemented 0.7.0 scope includes:

- fit a characterized standard-model reference resistance from calibration
  observations;
- research and implement custom Callendar–Van Dusen parameter fitting where the
  available observations make the requested parameters identifiable and the
  assumptions are scientifically defensible;
- retain coefficient covariance for supported fitted models and expose it as
  auditable fit evidence;
- propagate fitted-coefficient covariance into predicted resistance/temperature
  uncertainty where the model and assumptions support it;
- strengthen fit-quality and conditioning diagnostics needed by later calibration
  planning;
- explicitly represent calibration/reference-temperature standard uncertainty,
  reject it by default in ordinary least-squares fitting, and require an explicit
  opt-in to retain it as unmodeled evidence rather than silently treating
  independent-variable uncertainty as resistance uncertainty; and
- retain application-neutral calibration provenance with fit evidence without
  merging that provenance or the fit evidence into the portable deployable model
  definition.

The 0.7.0 work must preserve the existing separation among calibration
observations, fit evidence, the accepted numerical model, and any downstream
deployment representation. A fitted curve must not acquire standards/manufacturer
provenance that its source data do not justify.

### 0.8.0 — self-heating characterization and zero-power correction

Self-heating characterization is a required pre-1.0 feature. Resistance
thermometry requires measurement current, and the resulting Joule heating can make
the sensing element warmer than the environment being measured. The effect depends
on both thermometer construction and the thermal environment, so it must not be
modeled as an immutable property of an RTD characteristic alone.

Planned scope includes:

- observations containing measurement current and measured resistance under a
  stable thermal condition;
- two-current zero-power extrapolation, with support for additional observations
  where a statistically justified fit versus dissipated power is useful;
- explicit `zero_power_resistance_ohms` and corresponding zero-power temperature
  through a supplied RTD model;
- self-heating temperature rise at an observed/current operating point;
- self-heating coefficient or dissipation constant when the observations and
  environmental context justify reporting one;
- auditable evidence, residuals/consistency checks, and uncertainty propagation;
- optional non-behavioral context such as medium, flow condition, mounting, or
  calibration setup without making those hardware/application details part of the
  core RTD model identity; and
- clear warnings when observations do not support a stable zero-power
  extrapolation.

The package will analyze supplied current/resistance observations. It will not
control excitation current, ADCs, bridges, MAX31865 devices, or other acquisition
hardware. Manufacturer self-heating coefficients may be represented as provenance
or supporting information, but a generic correction must not assume that a value
measured in one medium or mounting condition transfers unchanged to another.

### 0.9.0 — calibration intelligence and pre-1.0 API freeze

Use the fitting, covariance, and uncertainty foundation prospectively to help users
design calibration experiments rather than only analyze completed calibrations. A
first public calibration experiment designer should make its optimization objective
explicit rather than claiming that one point set is universally "optimal."

Planned capabilities include:

- recommend calibration-point locations for a selected model family, operating
  range, number of available points, and stated optimization criterion;
- account for already measured calibration points and recommend a next-best point;
- consider whether an additional distinct temperature or a repeated measurement at
  an existing point better reduces the selected uncertainty criterion;
- support user-prioritized operating intervals rather than assuming every
  temperature in the range matters equally;
- report expected conditioning and predicted fitted-curve uncertainty so the reason
  for a recommendation is inspectable;
- identify diminishing returns when additional calibration effort is unlikely to
  improve the selected criterion materially; and
- keep the output as a scientific experiment plan, not a controller for baths,
  fixed-point cells, bridges, or other laboratory hardware.

The initial experiment-design scope may be limited to polynomial models until the
uncertainty and identifiability behavior of other fitting families is sufficiently
well characterized. Published optimization criteria and their assumptions must be
documented alongside the implementation.

0.9.0 should also complete the currently deferred tabulated-model portable
representation and conformance coverage, then perform a deliberate pre-1.0 review
of the public model, fitting, uncertainty, portable-format, self-heating, and
calibration-design interfaces. Interfaces found to be provisional should be revised
or explicitly deferred before the 1.0 compatibility commitment.

#### Characteristic compatibility and identifiability promotion gate

Research and Playground prototyping for characteristic compatibility may proceed
during 0.8 development. Before the 0.9 feature/API scope is frozen, evaluate whether
a bounded public capability for comparing observed `(temperature, resistance)` data
against known RTD characteristics is mature enough to include before 1.0.

Promote a public characteristic-comparison API into 0.9 only if **all five** of the
following criteria are satisfied:

1. **Scientific validity is demonstrated.** Known-characteristic, noisy, perturbed,
   and deliberately ambiguous cases produce scientifically defensible outcomes. A
   lowest residual must never be treated as proof of physical sensor identity.
2. **Result semantics have stabilized.** The project can state what an observation,
   candidate, residual/comparison metric, ambiguity result, and retained evidence
   mean without continuing to redesign those concepts.
3. **A useful minimal API is apparent.** The capability can be expressed as a small,
   inspectable comparison operation rather than a collection of hidden heuristics,
   mode switches, or application-specific rules.
4. **The capability has value outside the Playground.** At least two or three
   credible non-tutorial scientific or interoperability workflows can be stated
   clearly enough to justify a maintained public API.
5. **The implementation is bounded enough for the pre-1.0 commitment.** It does not
   require redesigning model identity, fitting, calibration, or uncertainty
   contracts and does not create unresolved semantics that would have to be frozen
   prematurely at 1.0.

The promotion review must include a small validation corpus with expected outcomes.
At minimum it should cover:

- clearly distinguishable candidate cases;
- deliberately close or ambiguous candidate cases;
- one-observation cases that are insufficient to distinguish candidates;
- multiple-observation cases in which added evidence resolves an ambiguity;
- noisy and perturbed observations;
- candidate range violations and invalid comparisons; and
- observations inconsistent with an asserted or expected characteristic.

Uncertainty-aware comparison should be investigated during prototyping, but it need
not be mandatory for the first public API if a deterministic residual-based subset
has honest, stable ambiguity semantics. The initial capability must not claim
automatic sensor identification, silently select or rewrite a user's model, or infer
identity from resistance alone.

If any promotion criterion remains unsatisfied at the 0.9 scope freeze, explicitly
defer the public API to post-1.0 while retaining the Playground prototype, validation
corpus, and research results for later development.

### 1.0.0 — stable scientific platform

Version 1.0 should primarily be a stability release rather than another large
feature drop. Its release gate should include:

- explicit compatibility/deprecation policy for the public Python APIs;
- stable semantics for supported model, fitting, uncertainty, self-heating, and
  calibration-design results;
- stable commitments for the portable model format and the language-neutral
  conformance surfaces that are advertised as public contracts;
- complete user/developer documentation for the supported pre-1.0 feature set,
  including retained scientific/industrial sources and reproducible derivations;
- clear interoperability documentation that `rtd-sensor` consumes trustworthy
  RTD-element resistance regardless of source and does not require a particular
  acquisition path when resistance in ohms is already available;
- examples that exercise the major public workflows from calibration observations
  through validated/deployable models;
- resolution, redesign, or explicit post-1.0 deferral of provisional APIs; and
- the full project release-readiness process against the exact 1.0 release
  candidate.

Additional built-in RTD characteristics may continue to land before or after 1.0
when they satisfy the package's provenance and validation policy; they are not part
of the architectural definition of 1.0 readiness.

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
Further incompatible behavioral changes require a new contract version. Public
built-in model discovery and immutable metadata views from the same authoritative
definitions shipped in 0.5.0 as roadmap item 3.

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
`invalid_model` definitions, and explicit custom range/status behavior.
Characterized PT-385 R0 fixtures publish both `binary64_reference` and the
empirically justified `binary32_compatible` profile; other custom families
remain binary64-only. The independent C11 consumer constructs every fixture
definition, verifies its expected `ok` or `invalid_model` construction status,
reproduces all published custom binary64 vectors, and independently verifies the
characterized-R0 binary32 subset.

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
- tabulated models when their conformance representation is added; and
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

This contract is coordinated with the implemented public exception taxonomy in
item 6 so Python application exceptions and cross-language statuses describe the
same underlying conditions without requiring a one-to-one mapping.

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

Items 1 through 7 shipped in 0.5.0. The 0.5.1 corrective release was limited to
documentation consistency and release-process hardening. Items 8 through 11 are
implemented for 0.6.0, so feature development has stopped at the documented
release boundary and the project is in release preparation.

### 8. Calibration fitting — implemented for 0.6.0

Implemented the initial polynomial fitting scope described under **Calibration and
model fitting**, including immutable observations and fit evidence, optional
weighting, scaled Householder-QR least squares, conditioning diagnostics, and
validated `PolynomialRTDModel` results. Rank-deficient, severely ill-conditioned,
and scientifically invalid fitted models are rejected rather than returned as
deployable curves. Portable reconstruction of a successful result remains item 10.

### 9. Batch and vector conversion conveniences — implemented for 0.6.0

Implemented the dependency-free `rtd_sensor.batch` convenience layer specified in
`DESIGN.md`: eager ordered list results, fail-fast scalar-equivalent exceptions,
and one-pass iterable inputs without extending the public `RTDModel` protocol.
NumPy remains optional and is not a runtime dependency.

### 10. Portable configurable and fitted model definitions — implemented for 0.6.0

Implemented the version-1 `portable_model_definition` artifact and Draft 2020-12
schema with an independent `format_version`, plus dependency-free Python
serialization/reconstruction in `rtd_sensor.portable`. The format reuses the
established scientific vocabulary while excluding conformance-only fixture
semantics, keeps non-behavioral metadata separate, and supports characterized
IEC 60751 PT-385, custom CVD, polynomial, and piecewise-polynomial definitions.
Fitted polynomial results can therefore be reconstructed without rerunning the
fit. Tabulated portability remains future work and is not a 0.6.0 blocker.

### 11. Characterized-reference-resistance binary32 conformance — implemented for 0.6.0

Extended `binary32_compatible` conformance to four explicit characterized
IEC 60751 PT-385 reference-resistance fixtures using the independent real
single-precision C11 path. A deterministic 1,320,843-case stress study across
±5% R0 bands around 100 Ω, 500 Ω, and 1000 Ω measured worst-case differences
well inside the existing 0.002 Ω forward and 0.001 °C inverse tolerances; the
method, measured envelope, representation effects, and engineering margin are
recorded in `conformance/consumers/c11/BINARY32_CHARACTERIZED_R0.md`. Claims
remain fixture-scoped and do not imply binary32 compatibility for arbitrary
custom CVD, polynomial, piecewise-polynomial, or tabulated models. Downstream
implementation guidance is consolidated in
`docs/CROSS_LANGUAGE_IMPLEMENTATIONS.md`.

### 12. Additional built-in RTD characteristics — ongoing, version-independent

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

### Additional platinum characteristics to investigate

- **JPt100 / approximately 0.00392 platinum** — establish the exact characteristic
  identity, authoritative equation or table, reference conventions, validity range,
  historical aliases, and independent validation before considering built-in
  support. It must remain distinct from the existing IEC 60751 PT-385 identity.

## Copper RTDs

Copper support remains planned as a later expansion now that the initial nickel
architecture is established.
Candidates include:

- **Cu10**, particularly legacy motor/generator winding and industrial
  monitoring applications.
- **Cu25**, if authoritative characteristic identity, range, and independent
  validation establish a support-ready curve.
- **Cu50**, if provenance research establishes a precise and independently
  validated industrial characteristic suitable for first-class support.
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

Version 0.6.0 implements initial polynomial calibration fitting from measured
calibration points, while keeping fitting separate from simply *using* a
published equation. Fit evidence and the portable numerical model definition are
separate outputs: consumers can reconstruct a fitted model without rerunning the
fit while retaining the observations and diagnostics that justify it.

Implemented fitting capabilities:

- fit a user-selected polynomial degree from `(temperature, resistance)`
  observations;
- retain the original observations, including repeated-temperature measurements
  rather than silently averaging them;
- report per-point residuals plus unweighted RMS and maximum absolute residual
  error, retaining separate weighted diagnostics when weights or point
  uncertainties affect the fit;
- retain the declared fitting range and numerical conditioning diagnostics;
- reject insufficient/rank-deficient observations, severe ill-conditioning, and
  candidate curves that fail positivity, monotonicity, or unique-inverse
  validation over the complete fitted range;
- prohibit silent extrapolation for polynomial fits; 0.7.0 shape-coefficient CVD
  fits are likewise constrained to the observation span, while characterized
  `R0`-only fits may use an independently justified applicability range as
  documented in `DESIGN.md`; and
- support covariance of fitted coefficients through the implemented 0.7.0
  calibration and statistical foundation.

The detailed failure semantics, batch API contract, and portable-format decision
are normative design material in `DESIGN.md` rather than duplicated here. A fitted
curve must never be presented as a manufacturer or standards-defined
characteristic unless that provenance is actually established.

## Tolerance and uncertainty

- Keep nominal conversion, calibration, tolerance, and measurement uncertainty
  as separate layers.
- Never apply IEC 60751 platinum AA/A/B/C tolerance classes to nickel or copper
  without an applicable source.
- Research nickel/copper tolerance rules per characteristic or product family.
- Keep tolerance limits distinct from probability distributions and standard
  uncertainties.
- Fitted-parameter covariance and covariance-aware fitted-model propagation are
  implemented in 0.7.0. Later uncertainty work may add covariance between
  arbitrary budget components, effective degrees of freedom, and Monte Carlo
  methods.

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
sensor-element resistance from any trustworthy source. A separate acquisition layer
is useful when raw converter or electrical observations still need compensation,
calibration, diagnostics, or conversion into resistance, but it is not required when
an instrument, interface, DAQ, bridge, multimeter, or recorded dataset already
provides the desired RTD-element resistance in ohms.

These concerns remain outside this package:

- ADC and reference-resistor configuration;
- 2-/3-/4-wire acquisition and lead compensation;
- MAX31865 or other converter register handling;
- GPIO/SPI/I²C access;
- Raspberry Pi, BeagleBone, MCU, or other platform-specific drivers.

A hardware/acquisition package can feed compensated resistance values to
`rtd-sensor` without duplicating the characteristic mathematics, while systems that
already expose trustworthy resistance may connect directly at the same boundary.
The language-neutral conformance contract above exists so an embedded implementation
can reproduce the same conversion behavior without moving hardware concerns into
this package.

## Post-1.0 feature ideas

These ideas are deliberately outside the 1.0 release gate unless a later roadmap
revision explicitly moves one forward. Recording them now preserves the design
intent without allowing them to expand the pre-1.0 scope.

### Calibration drift and stability analysis

Compare successive calibration results for the same physical thermometer and
distinguish changes that are meaningful relative to the retained calibration and
measurement uncertainty. Potential outputs include:

- change in characterized reference resistance versus change in curve shape;
- maximum temperature-equivalent drift over a declared operating range;
- localized versus systematic drift;
- uncertainty-aware significance of observed changes;
- hysteresis/thermal-cycle comparisons when the observation protocol supports
  them; and
- retained calibration history without making physical asset identity part of an
  RTD mathematical model.

### Characteristic compatibility and identifiability analysis

If the 0.9 promotion gate does not move a bounded characteristic-comparison API
into the pre-1.0 release sequence, retain it as an explicit post-1.0 candidate. A
future capability may compare one or more independent `(temperature, resistance)`
observations against a caller-visible set of known characteristics and report
inspectable residuals, range failures, candidate ordering, and whether the supplied
evidence distinguishes the candidates.

The capability must report compatibility and identifiability rather than claiming
physical sensor detection. The lowest residual is not proof of identity, ambiguity
must remain visible, and uncertainty-aware comparison may be added where the
measurement evidence supports it. Automatic model switching and resistance-only
identity inference remain out of scope.

### RTD replacement and interchangeability analysis

Compare an existing and candidate replacement model across an operating range and
answer application-neutral questions such as where they disagree most and whether
they remain within a caller-defined temperature-equivalent limit. Future work may
include uncertainty-aware equivalence when both models have calibration evidence.
This feature should compare scientific models; inventory, maintenance scheduling,
and process-control decisions remain downstream concerns.

### Advanced uncertainty methods

Potential additions include effective degrees of freedom, expanded-uncertainty
helpers, Monte Carlo propagation, nonlinear-distribution propagation, and richer
covariance handling. These should follow the applicable JCGM/GUM guidance rather
than introducing package-specific statistical terminology.

### Broader binary32 custom-model profiles

Investigate empirically validated `binary32_compatible` profiles for custom CVD,
polynomial, piecewise-polynomial, and eventually tabulated model families. Each
family requires its own conditioning/range study and independently exercised
single-precision path; the characterized-R0 result from 0.6.0 must not be
generalized without evidence.

### Embedded and generated deployment ecosystem

Potential additions include generated C headers/C++ `constexpr` definitions,
compact selected-model data, and lookup tables or other derived approximations for
constrained systems when real profiling justifies them. A maintained production
C/C++ embedded sibling project may be created if downstream MCU work shows that a
dedicated runtime API is useful. The Python package should remain free of
hardware-driver and embedded-build-system concerns.

Any derived deployment representation must remain subordinate to its authoritative
RTD model rather than becoming a new characteristic identity. Its contract should
retain or document, as applicable:

- source model/characteristic identity and source contract/artifact version;
- supported conversion direction and valid range;
- numeric representation such as binary32, integer, or fixed point;
- generation, interpolation, or approximation method;
- independently measured maximum error and the acceptance/engineering margin;
- boundary behavior and representative conditioning limits; and
- the exact conformance or error-envelope claim supported by validation.

A generated table or approximation must never be presented as though it has the
provenance of an authoritative tabulated RTD characteristic.

### Rich calibration-certificate and provenance metadata

A later metadata layer may retain certificate identifiers, laboratories, dates,
reference standards, calibration methods, ranges, uncertainty statements, source
precision, and related traceability information. It should remain separable from
the numerical model so deployment formats do not require full certificate records.

### Public model registration and plugin mechanisms

A public registration mechanism remains deferred. Verified package built-ins and
arbitrary user-defined models have different provenance/support guarantees, and a
future plugin design must preserve that distinction rather than making registration
look equivalent to package verification.

### Diagnostics with sufficient acquisition context

Sensor/open/short plausibility helpers may be useful when the caller can supply
enough acquisition context to make the inference scientifically defensible. Raw
ADC faults, wiring topology, converter-register interpretation, and hardware safety
logic remain outside this package.

### Reference-grade interpolation research

ITS-90/reference-thermometry interpolation or related high-accuracy features may be
investigated after 1.0. They should enter this package only if their scientific
scope fits a general RTD modeling library and can be supported without confusing
industrial RTD conversion with the realization of a temperature scale.

## Scientific and industrial source set for 0.7.0–1.0 planning

These sources are retained as research anchors for the planned calibration,
self-heating, uncertainty, drift, and calibration-design work. They do not by
themselves define an API or prove that a proposed algorithm is correct. Each
implementation should cite the specific sections, equations, assumptions, and
independent validation used when the feature is designed and tested.

- BIPM/CCT, *Guide on Secondary Thermometry: Industrial Platinum Resistance
  Thermometers*. Sections on self-heating, hysteresis, reproducibility, long-term
  stability, calibration, and uncertainty are especially relevant:
  https://www.bipm.org/en/committees/cc/cct/guides-to-thermometry
  https://www.nist.gov/publications/guide-secondary-thermometry-industrial-platinum-resistance-thermometers
- BIPM/CCT, *Guide to the Realization of the ITS-90: Platinum Resistance
  Thermometry*. Retain for resistance-thermometry measurement-current and
  self-heating methodology, including two-current zero-power extrapolation:
  https://www.bipm.org/en/committees/cc/cct/guides-to-thermometry
- JCGM 100:2008, *Evaluation of measurement data — Guide to the expression of
  uncertainty in measurement*, and the JCGM uncertainty supplements. Use these as
  the primary vocabulary/methodology source for covariance and later advanced
  uncertainty work:
  https://www.bipm.org/en/committees/jc/jcgm/publications
- NIST, *Industrial Thermometer Calibrations*, for current industrial calibration
  ranges, comparison methods, and published calibration uncertainties:
  https://www.nist.gov/pml/sensor-science/thermodynamic-metrology/industrial-thermometer-calibrations
- Strouse, Mangum, Vaughn, and Xu, *A New NIST Automated Calibration System for
  Industrial-Grade Platinum Resistance Thermometers*, NISTIR 6225, for industrial
  comparison-calibration practice and uncertainty considerations:
  https://www.nist.gov/publications/new-nist-automated-calibration-system-industrial-grade-platinum-resistance-thermometers
- ASTM E1137/E1137M, *Standard Specification for Industrial Platinum Resistance
  Thermometers*. Retain as an industrial source for PRT performance/qualification
  concepts including self-heating and stability; implementation must use the
  edition actually consulted:
  https://store.astm.org/e1137_e1137m-08r20.html
- Betta and Dell'Isola, *Optimum choice of measurement points for sensor
  calibration*, Measurement 17(2), 1996, 115–125. Retain for calibration
  experiment-design research concerning point location, number of points, and
  repetitions versus fitted-curve uncertainty:
  https://doi.org/10.1016/0263-2241(96)00019-X
- Minor and Strouse, *Stabilization of SPRTs for ITS-90 Calibrations*, for
  calibration stability/measurement-assurance concepts relevant to later drift
  analysis:
  https://www.nist.gov/publications/stabilization-sprts-its-90-calibrations
- Mangum, *Platinum Resistance Thermometer Calibrations*, NBS Special Publication
  250-22, retained as historical NIST calibration-method documentation:
  https://www.nist.gov/publications/platinum-resistance-thermometer-calibrations

When sources disagree or use different measurement contexts, preserve the
difference and determine whether they describe different measurands, thermometer
classes, calibration methods, or operating environments rather than averaging or
silently reconciling them.

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
