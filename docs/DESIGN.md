# pt100-core Design

## 1. Purpose

`pt100-core` provides a small, dependable, platform-independent implementation of resistance-to-temperature and temperature-to-resistance conversion for standardized platinum resistance temperature detectors.

The currently supported sensor models are:

- Pt100: nominal resistance 100 Ω at 0 °C
- Pt1000: nominal resistance 1000 Ω at 0 °C
- standard: IEC 60751
- normalized platinum curve: PT-385, α ≈ 0.00385

The project exists so applications can share one tested scientific conversion layer while keeping hardware acquisition code separate.

## 2. Core architectural boundary

The project begins only after a hardware or simulated measurement has been expressed as resistance in ohms.

```text
raw ADC or digital-interface data
              |
              v
hardware-specific measurement and compensation
              |
              v
resistance in ohms
              |
              v
pt100-core
              |
              v
temperature in Celsius
```

`pt100-core` does not determine how raw electrical signals become resistance. That responsibility belongs to hardware-facing code.

This boundary allows identical conversion code to be used with:

- BeagleBone Black
- Raspberry Pi
- desktop computers
- microcomputer test environments
- MAX31865 interfaces
- custom analog front ends
- recorded datasets
- simulated data

## 3. Design principles

### 3.1 Platform independence

The core package must not depend on GPIO, SPI, I²C, ADC, or board-specific libraries.

### 3.2 Scientific transparency

The implementation should identify the standard, equation, constants, assumptions, and supported range. Constants must not appear as unexplained magic numbers.

### 3.3 Small public API

The public interfaces for supported RTD models should remain parallel and simple:

```python
from rtd import pt100, pt1000

temperature_c = pt100.resistance_to_celsius(resistance_ohms)
resistance_ohms = pt100.celsius_to_resistance(temperature_c)

pt1000_temperature_c = pt1000.resistance_to_celsius(resistance_ohms)
pt1000_resistance_ohms = pt1000.celsius_to_resistance(temperature_c)
```

### 3.4 Simulation as a first-class use case

Temperature-to-resistance conversion is part of the supported public API, not merely an internal helper. It enables application testing without attached hardware.

### 3.5 No premature hardware coupling

Wire compensation, excitation circuits, ADC scaling, amplifier gain, reference resistors, and device-register handling must not leak into the scientific conversion layer.

### 3.6 Verifiability

Results must be tested against authoritative IEC 60751 reference values or independently reproduced reference tables.

## 4. Mathematical model

Version 1 will use the IEC 60751 Callendar–Van Dusen relationship.

For temperatures at or above 0 °C:

```text
R(T) = R0 × (1 + A×T + B×T²)
```

For temperatures below 0 °C:

```text
R(T) = R0 × [1 + A×T + B×T² + C×(T - 100)×T³]
```

For the standard IEC 60751 PT-385 curve:

```text
A  = 3.9083 × 10⁻³ °C⁻¹
B  = -5.775 × 10⁻⁷ °C⁻²
C  = -4.183 × 10⁻¹² °C⁻⁴
```

The supported models differ in nominal resistance at 0 °C:

```text
Pt100:  R0 = 100 Ω
Pt1000: R0 = 1000 Ω
```

Resistance-to-temperature conversion above 0 °C may use the analytic inverse of the quadratic equation. Below 0 °C, the implementation may use a bounded numerical solution of the complete equation.

The implementation must document numerical tolerances and must avoid silently extrapolating beyond its supported range.

## 5. Supported public API

The supported model modules are `rtd.pt100` and `rtd.pt1000`. Each exposes the same conversion interface:

```python
def resistance_to_celsius(resistance_ohms: float) -> float:
    ...

def celsius_to_resistance(temperature_c: float) -> float:
    ...
```

Potential future convenience functions may include:

```python
def resistance_to_fahrenheit(resistance_ohms: float) -> float:
    ...

def fahrenheit_to_resistance(temperature_f: float) -> float:
    ...
```

Those convenience functions are not required for the first release. Celsius is the native temperature representation because the governing standard is expressed in Celsius.

## 6. Validation and errors

The conversion functions should reject:

- non-finite numeric values
- non-positive resistance values
- temperatures outside the documented supported range
- resistance values that cannot represent a temperature inside that range

Errors should use clear `ValueError` messages unless a dedicated exception hierarchy becomes justified.

The package should not silently clamp values.

## 7. Simulation

Simulation should support two levels.

### 7.1 Exact reference simulation

The inverse conversion function generates ideal resistance from a requested temperature:

```python
resistance = pt100.celsius_to_resistance(65.0)
```

This is sufficient for deterministic tests of application behavior.

### 7.2 Measurement-stream simulation

The simulation module currently provides fixed resistance readings, finite and repeating resistance sequences, temperature-defined sequences, and reproducible seeded temperature noise. Temperature-based readers are model-aware and support both Pt100 and Pt1000. Pt100 remains the default for backward compatibility.

Future simulation additions may include ramps, heating and cooling profiles, and injected open-circuit or short-circuit faults.

Simulation components expose resistance values so they exercise the same application path as real hardware.

## 8. Testing strategy

Tests should include:

- 0 °C equals exactly 100 Ω
- representative negative temperatures
- representative positive temperatures
- round-trip temperature → resistance → temperature
- round-trip resistance → temperature → resistance
- boundary values
- invalid input
- non-finite values
- monotonicity across the supported range
- known IEC reference-table values

Round-trip tests alone are insufficient because the forward and inverse implementations could share the same error. At least some expected values must come from an independent reference source.

## 9. Accuracy boundaries

The core conversion describes the ideal standardized curve. It does not by itself account for:

- sensor tolerance class
- individual probe calibration
- lead-wire resistance
- self-heating
- excitation-current error
- amplifier offset or gain
- ADC quantization
- reference-resistor tolerance
- thermal gradients
- immersion depth
- response time

Hardware and calibration layers may correct these effects before passing resistance into the core, or may apply a documented calibration model afterward.

## 10. Package structure

Initial structure:

```
src/rtd/
├── __init__.py
├── _curves.py
├── _models.py
├── models.py
├── pt100.py
├── pt1000.py
└── simulation.py

tests/
├── test_models.py
├── test_package_api.py
├── test_pt100.py
├── test_pt1000.py
└── test_simulation.py
```

The `rtd` namespace is intentionally broader than the initial repository name.

## 11. Repository and namespace strategy

The repository begins as `pt100-core` because users commonly search for the specific term “Pt100.”

The Python import namespace begins as `rtd`:

```python
from rtd import pt100
```

Once the project genuinely supports additional RTD families, the repository may be renamed `rtd-core`. The Python import path would remain unchanged.


## 12. Generalized RTD architecture and future support

The conversion architecture separates the normalized resistance-temperature curve from the nominal resistance of a particular RTD model.

A curve describes the relationship:

```text
R(T) / R0
```

independently of the absolute value of `R0`.

An RTD model combines:

* a curve;
* a nominal or calibrated resistance at 0 °C (`R0`);
* a model identity.

This permits multiple RTD models to share one verified standardized curve without duplicating conversion logic.

The implementation defines the IEC 60751 PT-385 Callendar–Van Dusen curve once and combines it with model-specific `R0` values. Pt100 uses `R0 = 100 Ω`; Pt1000 uses `R0 = 1000 Ω`.

The curve and model infrastructure remains internal until the public API for user-defined and calibrated models has been deliberately designed.


### Public configurable IEC 60751 model

The first public advanced-model API is intentionally narrower than the internal curve/model architecture. `rtd.models.IEC60751RTDModel` represents an RTD that retains the standardized IEC 60751 PT-385 curve while allowing:

* an individually characterized or calibrated `R0`;
* a human-readable model or probe name; and
* a declared valid temperature range that may be narrower than the full IEC curve.

The built-in `rtd.pt100` and `rtd.pt1000` modules remain the preferred APIs for nominal standard sensors. The public configurable model is for cases where an individual probe's `R0` is known more precisely or its usable/calibrated range should be enforced.

A declared temperature range constrains use of the model; it does not modify the underlying IEC curve. It may therefore represent a manufacturer operating range, a calibration range, or another application-specific validity interval.

User-supplied Callendar–Van Dusen coefficients are deliberately not exposed in this first public-model batch. A custom coefficient set changes the curve itself and requires explicit validation rules and provenance expectations before becoming a stable public API.

### Measurement boundary

The core library begins with the best available estimate of the RTD sensing element's resistance in ohms.

Two-wire, three-wire, and four-wire topology affects acquisition and compensation rather than the standardized resistance-temperature relationship. Wiring topology, excitation, ADC configuration, reference-resistor calculations, lead-resistance compensation, and hardware fault detection therefore belong to hardware-facing acquisition layers.

The scientific conversion layer must not require a wire-count parameter.

### Potential future additions

Potential future additions include:

* Pt500
* alternate standardized platinum curves
* user-supplied Callendar–Van Dusen coefficients
* calibrated coefficient sets
* tolerance-class calculations
* uncertainty propagation
* vectorized conversion
* tabular or lookup-based conversion for constrained systems

Nominal conversion, calibration, tolerance, and uncertainty are related but separate concerns. Basic resistance-temperature conversion should continue to return the ideal value represented by the selected model. Calibration, tolerance, and uncertainty should be layered on top rather than silently altering nominal conversion behavior.

The scalar, dependency-free implementation should remain the reference calculation. Future vectorized or lookup implementations should be verified against it.

### Support-readiness policy

An RTD type or standardized curve must not be described as supported merely because the generalized implementation is mathematically capable of calculating it.

Before an additional RTD type is publicly exported or advertised, the project must include:

* the applicable equation or curve definition;
* authoritative coefficient provenance;
* the documented valid temperature range;
* independently sourced reference values;
* representative negative- and positive-temperature tests where applicable;
* boundary and out-of-range tests;
* round-trip and monotonicity tests;
* public-API tests;
* user documentation;
* simulation tests where simulation support is provided.

Unfinished RTD types should not be exposed as placeholder modules, constants, or documented supported features.

### Completed Pt1000 milestone

Pt1000 is now implemented as a verified public RTD type. The milestone established:

1. the internal normalized curve abstraction;
2. the reusable RTD model abstraction;
3. Pt100 on the shared model without changing its public API;
4. generic model tests for R0 behavior, normalized resistance, boundaries, validation, monotonicity, and round trips;
5. Pt1000 reference provenance and independent reference-value tests;
6. the public `rtd.pt1000` conversion module; and
7. model-aware simulation supporting Pt100 and Pt1000 while preserving Pt100 defaults.

No additional RTD type should be added merely because the shared engine can represent it. Each future type must independently satisfy the support-readiness policy above.


Pt500 and other RTD variants should follow the same process rather than being assumed supported merely because they can share the generalized calculation engine.


## 13. Related future repositories

Possible companion projects include:

```text
pt100-hardware
    Shared hardware-facing interfaces and measurement models

pt100-max31865
    MAX31865 driver independent of host platform

pt100-bbb
    BeagleBone-specific acquisition adapters

pt100-rpi
    Raspberry Pi-specific acquisition adapters

pt100-examples
    Complete applications and integration examples
```

These names are provisional. Hardware packages should be split by actual abstraction boundary rather than created in advance.

## 14. Explicit non-goals for version 1

Version 1 will not include:

- board-specific hardware drivers
- ADC configuration
- GPIO, SPI, or I²C access
- analog circuit design
- lead-wire compensation algorithms tied to a circuit
- MAX31865 register handling
- process-control logic
- heater or relay control
- data logging
- graphical interfaces
- network services

## 15. Deferred design decisions

The following decisions remain intentionally deferred:

1. The public API for user-supplied Callendar–Van Dusen coefficients and alternate RTD curves.
2. The public representation of calibrated coefficient sets and their provenance/validity requirements.
3. Tolerance-class calculation APIs.
4. Uncertainty-propagation APIs and result types.
5. Optional vectorized conversion support.
6. Lookup-table generation and interpolation APIs.
7. Whether the distribution and repository should eventually be renamed
   after multiple RTD families are genuinely supported.




## References and calculations

### Normative standard

* International Electrotechnical Commission. **IEC 60751:2022,
  Industrial platinum resistance thermometers and platinum temperature
  sensors**, Edition 3.0, published January 27, 2022.

  IEC 60751 is the normative basis for the standardized resistance-
  temperature relationship and requirements for industrial platinum
  resistance thermometers and platinum temperature sensors.

  https://webstore.iec.ch/en/publication/63753

The complete standard is not reproduced in this repository because it
is a copyrighted publication available from the IEC.

### Public technical verification

* Analog Devices. **MAX31865 RTD-to-Digital Converter Data Sheet**,
  “Temperature Conversion” section.

  This data sheet provides an openly accessible description of the
  Callendar–Van Dusen relationship used for platinum RTDs and publishes
  the standard PT-385 coefficients used by this implementation.

  https://www.analog.com/media/en/technical-documentation/data-sheets/MAX31865.pdf

* Fluke Calibration. **PT100 Calculator: Convert Resistance and
  Temperature**.

  The Fluke calculator publishes the PT-385 equation and coefficients
  and identifies IEC 60751, ASTM E1137, and JIS C 1604 as its source
  standards. It is used as an independently accessible check of
  selected resistance-temperature reference values.

  https://www.fluke.com/en-ca/learn/tools-calculators/pt100-calculator

  Accessed August 4, 2026.

* Italcoppie Sensori. **Pt1000 Resistance Chart**.

  The manufacturer-published table states that its values are according
  to DIN EN IEC 60751 and spans -200 °C through 850 °C in 1 °C
  increments. Selected rounded values are used as the primary independent
  Pt1000 reference dataset.

  https://www.italcoppie.com/wp-content/uploads/2022/08/Pt1000-Resistance-Chart-A4.pdf

* ABB. **Technical Note 153: Process variable measurement using an RTD**.

  ABB publishes an independent Pt1000 resistance table over a central
  portion of the range. These values corroborate the Italcoppie Pt1000
  references at their published precision.

  https://library.e.abb.com/public/f23fd36098164ef18489c604a0eb1308/Technical_Note_153_ProcessVariableMeasurementUsingARTD.pdf

### Implemented curve and models

The implementation supports the standard IEC 60751 PT-385 curve:

```text
A  = 3.9083 × 10⁻³ °C⁻¹
B  = -5.775 × 10⁻⁷ °C⁻²
C  = -4.183 × 10⁻¹² °C⁻⁴
```

The currently supported models are:

```text
Pt100:  R0 = 100.0 Ω
Pt1000: R0 = 1000.0 Ω
```

For temperatures from 0 °C through 850 °C:

```text
R(t) = R0 × (1 + A×t + B×t²)
```

For temperatures from -200 °C through 0 °C:

```text
R(t) = R0 × [1 + A×t + B×t² + C×(t - 100)×t³]
```

The implementation models the ideal standardized curve. It does not
include individual probe calibration, sensor tolerance, lead-wire
resistance, self-heating, or measurement-circuit errors.

### Test provenance

Pt100 reference-value tests use selected, rounded PT-385 values independently
checked against the Fluke PT100 calculator and published standard-compatible
tables. Pt1000 reference-value tests use selected rounded values from the
Italcoppie Pt1000 resistance chart, with ABB values providing an additional
independent cross-check over part of the range.

Exact supported-range boundary tests use values calculated from the full
Callendar–Van Dusen equation rather than rounded two-decimal table
values. This avoids rejecting a rounded boundary value such as 18.52 Ω
when the equation-defined resistance at -200 °C is slightly greater.

Round-trip tests are supplementary and are not treated as independent
verification, because forward and inverse implementations could share
the same defect.
