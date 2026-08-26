# References

This is the canonical bibliography for external scientific, standards,
metrology, manufacturer, industrial, validation, and interoperability sources
used or retained by `rtd-sensor`. Citations follow APA style as closely as the
available publication metadata permits.

The bibliography intentionally includes both sources that support released
behavior and sources retained for documented future research. Inclusion does
not imply that every source defines a supported model or implemented method.
Each entry therefore records its project role using one or more of these
labels:

- **Implementation basis** — directly supplies a released equation,
  coefficient set, range, tolerance rule, or uncertainty method.
- **Independent validation** — checks released behavior independently of the
  implementation source.
- **Corroborating/design source** — supports interpretation or a design choice
  without independently defining released numerical behavior.
- **Research/future** — retained for planned work and not evidence for current
  released behavior.
- **Documented discrepancy** — intentionally retained because a reputable
  source differs from the project's selected characteristic definition.
- **Design precedent** — informed interchange, conformance, provenance, or
  software-engineering design rather than RTD mathematics.

## Citation and provenance policy

When an external source materially supports an equation, coefficient set,
characteristic identity, valid range, tolerance rule, uncertainty method,
calibration method, validation dataset, numerical acceptance criterion, or
scientific/engineering design decision, the source must be added to or verified
in this file in the same change.

Source code should keep a short citation at the implementation point when that
helps trace a scientific rule, for example:

```python
# Source: IEC (2022), IEC 60751:2022, Table 2; see docs/REFERENCES.md.
```

Tests should distinguish independent checks from implementation provenance:

```python
# Validation source: UST Umweltsensortechnik (2022); see docs/REFERENCES.md.
```

The full citation belongs here rather than being duplicated in every source
file. Built-in characteristic definitions may additionally carry structured
source-reference metadata that is exported through the public catalog and
conformance artifacts.

## Standards and current metrology basis

Bureau International des Poids et Mesures. (2019). *The International System
of Units (SI)* (9th ed.). https://www.bipm.org/en/publications/si-brochure

**Project use:** Design precedent for explicit SI-derived unit semantics in
language-neutral conformance work.

International Electrotechnical Commission. (2022). *IEC 60751:2022:
Industrial platinum resistance thermometers and platinum temperature sensors*
(3rd ed.). https://webstore.iec.ch/en/publication/63753

**Project use:** Implementation basis for the built-in IEC PT-385 platinum
characteristic and IEC 60751 platinum tolerance calculations.

Joint Committee for Guides in Metrology. (2008). *Evaluation of measurement
data—Guide to the expression of uncertainty in measurement* (JCGM 100:2008).
Bureau International des Poids et Mesures.
https://doi.org/10.59161/JCGM100-2008E

**Project use:** Implementation basis for measurement-uncertainty terminology,
standard uncertainty, first-order propagation, covariance-aware propagation,
combination of independent components, and expanded uncertainty. Sections 5.1-5.2
provide the law of propagation used for fitted-parameter covariance propagation
into both forward resistance and first-order inverse temperature results and for
the 0.8.0 first-order two-current self-heating uncertainty propagation.
Appendix H.3 is the implementation basis
for the least-squares thermometer-calibration treatment used in v0.7.0,
including fitted-parameter variance/covariance, residual degrees of freedom, and
the distinction between residual-derived variance and independently established
measurement variance.

Heckert, N. A., Filliben, J. J., Croarkin, C. M., Hembree, B., Guthrie, W. F.,
Tobias, P., & Prinz, J. (2002). *Handbook 151: NIST/SEMATECH e-Handbook of
Statistical Methods*. National Institute of Standards and Technology.
https://www.nist.gov/publications/handbook-151-nistsematech-e-handbook-statistical-methods

Relevant sections: 4.1.4.1, *Linear least squares regression*; 4.1.4.3,
*Weighted least squares regression*; and 4.4.3.1, *Least squares*.
https://www.itl.nist.gov/div898/handbook/pmd/section1/pmd141.htm
https://www.itl.nist.gov/div898/handbook/pmd/section1/pmd143.htm
https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm

**Project use:** Implementation/corroborating source for the residual-variance-scaled
ordinary-least-squares parameter covariance used by the 0.8.0 multi-observation
self-heating fit and for the distinction between that fixed-coordinate/common-variance
model and later weighted fitting. Section 4.4.3.1 gives the residual standard
deviation estimate ``sqrt(SSE / (n - p))`` and discusses dependence between fitted
line parameters; section 4.1.4.3 describes inverse-variance weighting when
random-error variance is not constant.

Taylor, B. N., & Kuyatt, C. E. (1994). *Guidelines for evaluating and
expressing the uncertainty of NIST measurement results* (NIST Technical Note
1297). National Institute of Standards and Technology.
https://www.nist.gov/pml/nist-technical-note-1297

**Project use:** Implementation basis and public corroboration for Type B
uncertainty treatment, rectangular/triangular distributions, combination of
standard uncertainties, expanded uncertainty, and covariance-aware first-order
propagation. Appendix A gives the law of propagation and its sensitivity/co-
variance terms used by the fitted-model resistance- and temperature-uncertainty
implementations.

## Platinum RTD implementation and validation

ABB. (n.d.). *Technical note 153: Process variable measurement using an RTD*.
https://library.e.abb.com/public/f23fd36098164ef18489c604a0eb1308/Technical_Note_153_ProcessVariableMeasurementUsingARTD.pdf

**Project use:** Independent validation/corroboration for Pt1000 reference
values over part of the IEC PT-385 range.

Analog Devices. (2015). *MAX31865: RTD-to-digital converter data sheet*
(Rev. 3).
https://www.analog.com/media/en/technical-documentation/data-sheets/MAX31865.pdf

**Project use:** Corroborating/design source for the Callendar–Van Dusen form
and standard PT-385 coefficients; not the normative basis for IEC behavior.

Beamex. (n.d.). *Pt100 temperature sensor—Useful things to know*.
https://blog.beamex.com/pt100-temperature-sensor

**Project use:** Corroborating/design source for traceable custom
Callendar–Van Dusen coefficient models, including the treatment of ranges that
do not extend below 0 °C.

Fluke Calibration. (n.d.). *PT100 calculator: Convert resistance and
temperature*. Retrieved August 4, 2026, from
https://www.fluke.com/en-ca/learn/tools-calculators/pt100-calculator

**Project use:** Independent validation for selected Pt100 values and
cross-checks of the common IEC PT-385 relationship.

Italcoppie Sensori. (2022). *Pt1000 resistance chart: Values according to DIN
EN IEC 60751*.
https://www.italcoppie.com/wp-content/uploads/2022/08/Pt1000-Resistance-Chart-A4.pdf

**Project use:** Primary independent Pt1000 resistance/temperature validation
source.

UST Umweltsensortechnik GmbH. (2022). *Platinum thinfilm temperature sensor
elements—Pt500 series: Basic resistance values* (Rev. 00). Retrieved August
10, 2026, from
https://www.umweltsensortechnik.de/fileadmin/assets/downloads/platin/datenblaetter/pt500-basic-resistance-values-202201-Rev00.pdf

**Project use:** Primary independent Pt500 resistance/temperature validation
source.

## Nickel RTD implementation and validation

ABB Automation Products GmbH. (2013). *Industrial temperature measurement:
Basics and practice*.
https://library.e.abb.com/public/8c3af5f513714b339b6c350362d7a126/03_TEMP_EN_E02.pdf

**Project use:** Implementation basis/corroboration for the former-DIN 43760
Nickel 6178/6180 ppm/K characteristic.

E+E Elektronik. (n.d.). *R-T characteristics: Ni1000 TK5000 DIN B*.
https://www.epluse.com/fileadmin/data/product/r-t_characteristics/R_T_Characteristics_Ni1000_TK5000.pdf

**Project use:** Primary independent resistance/temperature validation source
for the built-in Ni1000 TK5000 characteristic.

Honeywell Inc. (2022). *MERLIN NX IP and MS/TP VAV controller installation
instructions* (EN1Z-1076GE51 R0722).
https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/manuals-and-guides/installation-guides/moved-ss/hbt-bms-MERLINNX-en1z1076-ge51r0422-InstallationGuide.pdf

**Project use:** Independent validation/corroboration for former-DIN Ni1000 and
TK5000 resistance tables used by real building-control equipment.

Innovative Sensor Technology AG. (n.d.). *RTD nickel sensors* [Application
note; Nickel ND 6180 ppm/K and Nickel NL 5000 ppm/K coefficient tables].
https://www.ist-ag.com/sites/default/files/downloads/ATN_E.pdf

**Project use:** Implementation basis for the Nickel ND 6180 ppm/K and Nickel
NL/TK5000 5000 ppm/K characteristic coefficients.

Innovative Sensor Technology AG. (n.d.). *Ni1000 temperature sensor: Nickel NL
(5000 ppm/K)* [Data sheet].
https://www.mouser.com/datasheet/2/1426/nl1k0_520_2fw_b_007-2950467.pdf

**Project use:** Corroborating source for the built-in Ni1000 TK5000 / Nickel
NL characteristic.

Minco. (n.d.). *Resistance thermometry: Principles and applications of
resistance thermometers and thermistors*.
https://www.minco.com/wp-content/uploads/Resistance-Thermometry.pdf

**Project use:** Implementation basis for the North American/Minco NA 6720
ppm/K twelve-segment Ni120 characteristic.

Minco. (n.d.). *NA in degrees C—7-120* [Resistance/temperature table].
https://www.minco.com/wp-content/uploads/NA-in-deg-C-7-120.pdf

**Project use:** Corroborating/research source retained for the North American
Ni120 characteristic and table-code interpretation.

Minco. (n.d.). *RTD temperature vs. resistance table*. Retrieved August 17,
2026, from
https://www.minco.com/resource-center/rtd-temperature-vs-resistance-table/

**Project use:** Corroborating source for Minco resistance/temperature table
codes used in Ni120 provenance documentation.

Pyromation. (n.d.). *120 ohm nickel RTD—0.00672 coefficient, degree Celsius*
[Resistance/temperature table].
https://www.pyromation.com/downloads/data/672_c.pdf

**Project use:** Primary independent resistance/temperature validation source
for the built-in Ni120 6720 ppm/K characteristic.

TE Connectivity / HL-Planartechnik. (2015). *Ni1000SOT temperature sensor*
[Technical data sheet]. https://www.farnell.com/datasheets/2301873.pdf

**Project use:** Independent validation/corroboration for the former-DIN
6178/6180 ppm/K Ni1000 characteristic.

## Nickel characteristic research and discrepancy sources

Heraeus Nexensos GmbH. (2019). *Ni1000 temperature sensor* (Product 100489-6)
[Data sheet].
https://www.mouser.com/datasheet/2/619/hera_s_a0009182606_1-2289114.pdf

**Project use:** Documented discrepancy. Its printed polynomial differs from
the ABB/IST/TE/Honeywell coefficient consensus used by the built-in former-DIN
Ni1000 characteristic. The disagreement is retained rather than averaged away.

Innovative Sensor Technology AG. (n.d.). *Temperature sensors* [Product and
characteristic documentation]. Retrieved August 17, 2026, from
https://www.ist-ag.com/en/temperature-sensors

**Project use:** Research/future source for additional nickel characteristic
families and aliases, including 6370 and 6720 ppm/K variants that must not be
assumed equivalent to existing built-ins.

National Instruments. (n.d.). *Resistance temperature detectors (RTDs)*.
https://www.ni.com/docs/en-US/bundle/ni-dmm/page/resistance-temperature-detector-rtds.html

**Project use:** Research/background source for industrial RTD terminology and
characteristic investigation; not an implementation basis for current built-ins.

Schneider Electric. (n.d.). *What are the differences between the Ni1000
sensor characteristics and how should the correct characteristic be selected?*
[FAQ FA282624]. https://www.se.com/be/fr/faqs/FA282624/

**Project use:** Research/corroborating source documenting that nominal
"Ni1000" can refer to materially different 6180 ppm/K and 5000 ppm/K
characteristics and therefore cannot safely identify a curve by R0 alone.

## Calibration, self-heating, stability, and experiment-design research

ASTM International. (2020). *Standard specification for industrial platinum
resistance thermometers* (ASTM E1137/E1137M-08(2020)).
https://doi.org/10.1520/E1137_E1137M-08R20

**Project use:** Research/future industrial source for PRT performance,
qualification, self-heating, and stability concepts. It does not replace IEC
60751 as the current built-in platinum characteristic basis.

Betta, G., & Dell'Isola, M. (1996). Optimum choice of measurement points for
sensor calibration. *Measurement, 17*(2), 115–125.
https://doi.org/10.1016/0263-2241(96)00019-X

**Project use:** Research/future peer-reviewed source for calibration experiment
design, including point location, point count, repetitions, and fitted-curve
uncertainty.

Bartel, T. W., Stoudt, S., & Possolo, A. (2016). Force calibrations using
errors-in-variables regression and Monte Carlo uncertainty evaluations.
*Metrologia, 53*(3), 965–980. https://doi.org/10.1088/0026-1394/53/3/965

**Project use:** Implementation/design basis for keeping uncertainty in the
calibration independent variable distinct from dependent-variable weighting. NIST's
calibration work documents the ordinary-least-squares assumption that the applied
reference values are effectively known and uses errors-in-variables regression when
that assumption is not adequate. `rtd-sensor` therefore records temperature-coordinate
standard uncertainty separately and does not silently convert it into resistance
uncertainty.

Bureau International des Poids et Mesures, Consultative Committee for
Thermometry. (2021). *Guide to the realization of the ITS-90: Platinum
resistance thermometry*.
https://www.bipm.org/en/committees/cc/cct/guides-to-thermometry

**Project use:** Implementation basis for the 0.8.0 two-current zero-power
resistance extrapolation in `rtd_sensor.self_heating`, especially section 5.3.3
and Equation 34. It also remains a research source for reference resistance
thermometry, measurement-current effects, and interpretation of larger
self-heating observation sets. The project does not claim ITS-90 realization
support.

Joint Committee for Guides in Metrology. (2008). *Evaluation of measurement
data—Supplement 1 to the “Guide to the expression of uncertainty in
measurement”—Propagation of distributions using a Monte Carlo method*
(JCGM 101:2008). Bureau International des Poids et Mesures.
https://doi.org/10.59161/JCGM101-2008

**Project use:** Research/future source retained for advanced uncertainty work
when first-order propagation is insufficient.

Joint Committee for Guides in Metrology. (2011). *Evaluation of measurement
data—Supplement 2 to the “Guide to the expression of uncertainty in
measurement”—Extension to any number of output quantities* (JCGM 102:2011).
Bureau International des Poids et Mesures.
https://doi.org/10.59161/JCGM102-2011

**Project use:** Research/future source for multivariate/covariance-aware
uncertainty work.

Mangum, B. W. (1987). *Platinum resistance thermometer calibrations* (NBS
Special Publication 250-22). National Bureau of Standards.
https://doi.org/10.6028/NBS.SP.250-22

**Project use:** Research/future historical calibration-method reference.

Minor, D. B., & Strouse, G. F. (2005). *Stabilization of SPRTs for ITS-90
calibrations* [Conference paper]. NCSLI Conference.
https://www.nist.gov/publications/stabilization-sprts-its-90-calibrations

**Project use:** Research/future source for stability, annealing, and
measurement-assurance concepts relevant to later drift analysis.

National Institute of Standards and Technology. (2025). *Industrial
thermometer calibrations*.
https://www.nist.gov/pml/sensor-science/thermodynamic-metrology/industrial-thermometer-calibrations

**Project use:** Research/future source for current industrial comparison
calibration practice, ranges, and published calibration uncertainties.

Pearce, J., Rusby, R., Yamazawa, K., Rudtsch, S., Iacomini, L., Lopardo, G.,
White, D. R., & Tew, W. L. (2022). *Guide on secondary thermometry: Industrial
platinum resistance thermometers*. Bureau International des Poids et Mesures.
https://www.nist.gov/publications/guide-secondary-thermometry-industrial-platinum-resistance-thermometers

**Project use:** Implementation and research anchor for industrial PRT calibration.
Section 4.1 provides the implementation basis for linear resistance-versus-current-
squared self-heating extrapolation, larger observation sets used to inspect that
linearity, repeated-current cycles when drift makes a single pair unreliable, and
the stable-external-temperature requirement. Its treatment of self-heating effect
versus applied power and of setup-specific self-heating coefficients/dissipation
constants is the basis for retaining experiment context and for reporting a named
coefficient only from a positive fitted self-heating relationship with that context
attached. The guide also cautions that self-heating behavior can vary with
temperature, supporting the API/documentation rule that a derived coefficient is
local to the experiment's fitted temperature and sampled power range rather than
universally transferable. The guide's °C/mW coefficient and reciprocal mW/°C
dissipation-constant forms also define the public unit conventions. Appendix 1
documents the modern Callendar–Van Dusen `R0`, `A`, `B`, `C` form, the
zero-above-0-°C role of `C`, and the historical determination of CVD parameters
from calibration measurements. It also remains a research source for hysteresis,
reproducibility, and long-term stability. JCGM 100:2008 is the implementation basis
for the current first-order self-heating uncertainty propagation.

Strouse, G. F., Mangum, B. W., Vaughn, C. D., & Xu, E. Y. (1998). *A new NIST
automated calibration system for industrial-grade platinum resistance
thermometers* (NISTIR 6225). National Institute of Standards and Technology.
https://doi.org/10.6028/NIST.IR.6225

**Project use:** Corroborating source for industrial comparison-calibration
practice, uncertainty analysis, and the use of Callendar–Van Dusen or least-squares
coefficient models in calibration reports.

## Data interchange, conformance, and provenance design sources

Bray, T. (2017). *The JavaScript Object Notation (JSON) data interchange
format* (RFC 8259). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8259

**Project use:** Implementation/design basis for JSON conformance artifacts,
including the decision to represent non-finite test inputs symbolically rather
than as invalid JSON numbers.

Hutton, B., Andrews, H., Wright, A., & Dennis, G. (2022). *JSON Schema: A media
type for describing JSON documents* (Draft 2020-12).
https://json-schema.org/draft/2020-12/json-schema-core.html

**Project use:** Implementation/design basis for the conformance artifact
schemas.

National Institute of Standards and Technology. (n.d.). *Cryptographic
Algorithm Validation Program (CAVP)*.
https://csrc.nist.gov/Projects/Cryptographic-Algorithm-Validation-Program

**Project use:** Design precedent retained during conformance development for
capability-oriented validation vectors and claims; it is not an RTD normative
source.

Rundgren, A., Jordan, B., & Erdtman, S. (2020). *JSON Canonicalization Scheme
(JCS)* (RFC 8785). https://doi.org/10.17487/RFC8785

**Project use:** Design precedent considered for canonical JSON. The project
deliberately requires deterministic generated artifacts but does not currently
require third-party consumers to implement JCS.

Saint-Andre, P., & Klensin, J. (2017). *Uniform Resource Names (URNs)* (RFC
8141). Internet Engineering Task Force. https://doi.org/10.17487/RFC8141

**Project use:** Design precedent considered when deciding not to invent a
project-specific formal URN namespace for conformance IDs.

Schadow, G., & McDonald, C. J. (2024). *The Unified Code for Units of Measure*
(Version 2.2). https://unitsofmeasure.org/ucum

**Project use:** Design precedent considered for generalized unit interchange;
contract v1 deliberately uses fixed `degree_celsius` and `ohm` identifiers
instead.

Smith, A. M., Katz, D. S., Niemeyer, K. E., & FORCE11 Software Citation
Working Group. (2016). Software citation principles. *PeerJ Computer Science,
2*, e86. https://doi.org/10.7717/peerj-cs.86

**Project use:** Design precedent for keeping explicit citation/provenance
information in research software source, documentation, and citation metadata.

Wright, A., Andrews, H., Hutton, B., & Dennis, G. (2022). *JSON Schema
validation: A vocabulary for structural validation of JSON* (Draft 2020-12).
https://json-schema.org/draft/2020-12/json-schema-validation.html

**Project use:** Implementation/design basis for validation constraints in the
conformance schemas.

## Provenance interpretation

Generated conformance vectors are not independent scientific validation of the
Python formulas that generated them. The project uses two distinct layers:
standards/manufacturer/reference data validate the Python scientific behavior,
and generated conformance vectors validate whether another implementation
reproduces that already validated behavior.

When reputable sources disagree, the disagreement should be retained and
resolved scientifically rather than averaged or silently reconciled. A source
that appears in the research sections above does not become an implementation
basis until the relevant feature explicitly adopts it and documents the exact
section, equation, table, assumptions, and validation used.
