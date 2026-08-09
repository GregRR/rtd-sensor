# Changelog

All notable changes to this project will be documented in this file.

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
