# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

* Added a public structural `rtd_sensor.models.RTDModel` protocol covering forward and inverse resistance/temperature conversion plus local `dR/dT` and `dT/dR` sensitivity. Built-in sensor modules, public configurable models, and compatible third-party model objects can satisfy the protocol without package-specific inheritance.

### Changed

* Centralized the full RTD model protocol and the existing narrower `uncertainty.RTDUncertaintyModel` contract so every `RTDModel` is uncertainty-compatible without requiring existing uncertainty-only third-party implementations to add unused methods.
* Updated internal simulation model annotations to depend on the shared structural model protocol rather than the private concrete built-in model class.

## 0.4.0 — 2026-08-10

### Added

* Added IEC 60751 Pt500 resistance-to-temperature and temperature-to-resistance conversion using the shared PT-385 curve with `R0 = 500 Ω`.
* Added independently sourced Pt500 reference-value tests using the UST Umweltsensortechnik Pt500 resistance table, plus round-trip, boundary, scaling, simulation, and uncertainty-propagation coverage.
* Added built-in Ni1000 6178/6180 ppm/K conversion for the former DIN 43760 nickel characteristic, including analytical sensitivity, -60 °C through 250 °C range validation, simulation support, and independently sourced resistance-table tests.
* Added built-in Ni1000 TK5000 / 5000 ppm/K conversion as a characteristic distinct from the former-DIN 6180 Ni1000 model, with analytical sensitivity, simulation support, and independent E+E resistance-table tests.
* Added built-in North American Ni120 / 6720 ppm/K conversion using Minco's twelve-segment nickel characteristic, with auditable continuity stitching, simulation and uncertainty support, and independent Pyromation R/T tests.
* Added a public `PolynomialRTDModel` for traceable single-polynomial RTD characteristics with an explicit reference resistance, reference temperature, declared range, coefficient provenance, analytical sensitivity, and dependency-free inverse conversion.
* Added public `PiecewisePolynomialRTDModel` and `PiecewisePolynomialSegment` infrastructure for traceable multi-interval RTD characteristics, including analytical segment validation, bounded inversion, deterministic boundary sensitivity, and explicit auditable continuity stitching for rounded source equations.
* Added polynomial curve validation that checks finite positive resistance and locates analytical-slope extrema so non-monotonic regions cannot hide between arbitrary sampling points.
* Added `docs/ROADMAP.md` to preserve planned additional nickel, Cu10/Cu100, tabulated-characteristic, calibration-fitting, and other future RTD work.

### Changed

* Renamed the PyPI distribution and repository from `pt100-core` to `rtd-sensor` and the Python import package from `rtd` to `rtd_sensor`. Version 0.4.0 intentionally does not ship an `rtd` compatibility package; applications migrating from 0.3.x must update their imports.
* Generalized simulation model identity around one immutable built-in RTD registry, with discoverable supported identities and registry-driven mismatch/immutability regression coverage that expands automatically as new built-in characteristics are added. `simulation.RTDType` is now a string alias backed by strict runtime registry validation instead of a separately maintained closed `Literal[...]` union.
* Generalized the internal RTD scaling model from a hard-coded 0 °C resistance assumption to an explicit curve reference resistance/temperature while preserving the established Pt100/Pt500/Pt1000 and CVD model behavior.

### Fixed

* Fixed custom Callendar-Van Dusen models so coefficient-shape validation and inversion honor exactly the caller-declared validity interval rather than silently widening one-sided calibration ranges to include the 0 °C `R0` reference point.
* Hardened the built-in RTD identity registry with regression coverage for immutability, duplicate registration, invalid/whitespace identities, and clean type errors for non-string identities.

## 0.3.0 — 2026-08-09

### Added

* Public `IEC60751RTDModel` for individually characterized `R0` values and declared temperature ranges on the standard IEC 60751 PT-385 curve.
* Public `CallendarVanDusenRTDModel` for traceable user-supplied `R0`, `A`, `B`, and optional `C` coefficient sets with explicit validity ranges and curve-shape validation.
* IEC 60751:2022 tolerance calculations for standard thermometer classes AA/A/B/C and bare platinum-resistor W/F classes, with construction-specific validity ranges.
* GUM-style measurement-uncertainty primitives for bounded Type B conversions, independent root-sum-square combination, expanded uncertainty, and exact analytical RTD sensitivity.
* Structured RTD resistance-to-temperature uncertainty propagation and named independent-component temperature uncertainty budgets with optional coverage-factor reporting and provenance metadata.

### Changed

* Public physical/numerical inputs now reject Boolean values instead of silently coercing `True`/`False` to `1.0`/`0.0`.
* Public modules no longer expose imported internal RTD model/curve singletons as accidental module attributes; supported public exports remain unchanged.

### Fixed

* Model-aware simulation readers now reject conflicting explicit RTD-type overrides, preventing a Pt1000 resistance stream from being silently interpreted with the Pt100 model (or vice versa).
* Built-in simulation readers keep their RTD identity read-only after construction so their declared `rtd_type` cannot diverge from the model cached during initialization.
* Exact model-boundary resistance round trips no longer fail when floating-point `R0 × ratio` followed by `R / R0` lands one representable value outside the normalized curve boundary.
* Positive-temperature CVD inversion now uses a numerically stable quadratic form to reduce cancellation near resistance-ratio boundaries.

## 0.2.0 — 2026-08-09

### Added

* IEC 60751 Pt1000 resistance-to-Celsius and Celsius-to-resistance conversion.
* Independently sourced Pt1000 reference-value tests covering the standardized range.
* Shared internal RTD curve and model infrastructure for verified RTD variants.
* Model-aware simulation for Pt100 and Pt1000 while preserving Pt100 as the default.

### Changed

* Development workflow migrated to uv with a locked Python 3.14 environment.
* Project metadata and documentation now describe both supported RTD models.

## 0.1.0 — 2026-08-04

Initial release.

### Added

* IEC 60751 PT-385 Pt100 resistance-to-Celsius conversion.
* Celsius-to-resistance conversion for simulation and testing.
* Support for the standard -200 °C through 850 °C range.
* Input validation for non-finite, invalid, and out-of-range values.
* Analytic positive-temperature conversion and bounded numerical inversion below 0 °C.
* Independent reference-value tests based on the Fluke PT100 table generator.
* Exact boundary, round-trip, monotonicity, and invalid-input tests.
* Fixed resistance simulation.
* Finite and repeating resistance sequences.
* Temperature-defined simulation sequences.
* Reproducible Gaussian-noise simulation.
* Public `rtd.pt100` and `rtd.simulation` APIs.
* Python 3.14 support.
* GitHub Actions continuous integration.
* Mozilla Public License 2.0.
