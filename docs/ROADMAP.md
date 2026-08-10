# pt100-core / future rtd-sensor roadmap

This roadmap records planned capabilities and the scientific constraints that
must be satisfied before they become supported public features. It is not a
promise that every item will land in the next release.

The project is evolving from its original Pt100-only scope toward a general RTD
modeling library. The intended project identity after that transition is:

```text
PyPI distribution:  rtd-sensor
Python import:       rtd_sensor
GitHub repository:   rtd-sensor
```

The rename is planned for a release in which multiple non-Pt100 RTD families
are genuinely supported. Existing `pt100-core` releases remain part of the
project history and will need a documented migration path.

## 0.4.0 development direction

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
└── tabulated characteristic                     planned

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

### Nickel targets for 0.4.x

Research and implementation should proceed characteristic-by-characteristic,
with equation provenance and independent reference values for each one.

Likely near-term targets:

- **Ni1000 6180 ppm/K** — implemented as `rtd.ni1000` using the former DIN
  43760 / Nickel ND characteristic. The mathematical -60 °C through 250 °C
  range is kept separate from narrower physical-product ratings.
- **Ni1000 TK5000 / 5000 ppm/K** — implemented as `rtd.ni1000_tk5000`
  using the IST Nickel NL cubic and independently validated against the E+E
  TK5000 R/T table. It remains a distinct identity from `rtd.ni1000`.
- **Ni120 North-American 6720 ppm/K** — implement the specific documented
  Minco/Pyromation-style characteristic rather than assuming every 120-ohm or
  6720-ppm nickel sensor shares one global polynomial.

Before each characteristic is publicly exported, require:

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

Keep these on the research roadmap even if they do not land in 0.4.0:

- Nickel NJ / approximately 6370 ppm/K and its actual nominal-resistance
  variants and industry aliases.
- IST/manufacturer-specific NA 6720 characteristics that differ from the
  Minco/Pyromation Ni120 curve away from the 0-to-100 °C TCR interval.
- Other documented Balco/nickel characteristics encountered in industrial or
  building-automation equipment.

## Copper RTDs

Copper support is planned after the nickel architecture is established.
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
planned built-in consumer. Its published 12-segment cubic coefficients motivate
the explicit stitching policy because printed coefficient precision leaves very
small join mismatches even though the source describes one standard nickel
curve.

### Tabulated characteristics

Planned. A manufacturer's resistance/temperature table may be more
scientifically authoritative than fitting a new polynomial to it. Future table
support should:

- retain the source points unchanged;
- require monotonic data for an invertible RTD characteristic;
- use a documented monotonic interpolation method;
- avoid extrapolation by default;
- expose interpolation behavior and source precision clearly;
- preserve table provenance.

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

The current simulation type registry is appropriate for the small set of
built-in platinum models but should be generalized before many nickel/copper
characteristics are added. The future design should avoid an ever-growing
hard-coded binary/ternary decision tree and should preserve the existing rule
that a model-aware reader cannot be silently interpreted using a contradictory
sensor identity.

## Hardware boundary

The scientific RTD package continues to consume the best available estimate of
sensor-element resistance. These concerns remain outside this package:

- ADC and reference-resistor configuration;
- 2-/3-/4-wire acquisition and lead compensation;
- MAX31865 or other converter register handling;
- GPIO/SPI/I²C access;
- Raspberry Pi, BeagleBone, MCU, or other platform-specific drivers.

A later hardware/acquisition package can feed compensated resistance values to
`rtd-sensor` without duplicating the characteristic mathematics.

## Longer-term performance and convenience work

Potential later additions include:

- vectorized conversion;
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
  coefficients used by `rtd.ni1000_tk5000`:
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
