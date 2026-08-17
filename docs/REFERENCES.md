# References

This bibliography consolidates the external standards, metrology guidance,
manufacturer literature, and independently published resistance/temperature
sources used to define, validate, or document `rtd-sensor`. Citations follow
APA style as closely as the available publication metadata permits.

Sources that were only investigated for possible future roadmap work are not
included here unless they also support the current implementation,
validation, or documented design. Source-specific rationale remains in
`docs/DESIGN.md`, module documentation, and tests.

## Standards and metrology

Bureau International des Poids et Mesures. (2019). *The International System
of Units (SI)* (9th ed.). https://www.bipm.org/en/publications/si-brochure

International Electrotechnical Commission. (2022). *IEC 60751:2022:
Industrial platinum resistance thermometers and platinum temperature sensors*
(3rd ed.). https://webstore.iec.ch/en/publication/63753

Joint Committee for Guides in Metrology. (2008). *Evaluation of measurement
data—Guide to the expression of uncertainty in measurement* (JCGM 100:2008).
Bureau International des Poids et Mesures.
https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf

Taylor, B. N., & Kuyatt, C. E. (1994). *Guidelines for evaluating and
expressing the uncertainty of NIST measurement results* (NIST Technical Note
1297). National Institute of Standards and Technology.
https://www.nist.gov/pml/nist-technical-note-1297

## Platinum RTD sources

ABB. (n.d.). *Technical note 153: Process variable measurement using an RTD*.
https://library.e.abb.com/public/f23fd36098164ef18489c604a0eb1308/Technical_Note_153_ProcessVariableMeasurementUsingARTD.pdf

Analog Devices. (2015). *MAX31865: RTD-to-digital converter data sheet*.
https://www.analog.com/media/en/technical-documentation/data-sheets/MAX31865.pdf

Beamex. (n.d.). *Pt100 temperature sensor—Useful things to know*.
https://blog.beamex.com/pt100-temperature-sensor

Fluke Calibration. (n.d.). *PT100 calculator: Convert resistance and
temperature*. Retrieved August 4, 2026, from
https://www.fluke.com/en-ca/learn/tools-calculators/pt100-calculator

Italcoppie Sensori. (2022). *Pt1000 resistance chart: Values according to DIN
EN IEC 60751*.
https://www.italcoppie.com/wp-content/uploads/2022/08/Pt1000-Resistance-Chart-A4.pdf

UST Umweltsensortechnik GmbH. (2022). *Platinum thinfilm temperature sensor
elements—Pt500 series: Basic resistance values* (Rev. 00). Retrieved August
10, 2026, from
https://www.umweltsensortechnik.de/fileadmin/assets/downloads/platin/datenblaetter/pt500-basic-resistance-values-202201-Rev00.pdf

## Nickel RTD sources

ABB. (n.d.). *Industrial temperature measurement: Basics and practice*
[Technical handbook; nickel measurement characteristics according to DIN
43760].

E+E Elektronik. (n.d.). *R-T characteristics: Ni1000 TK5000 DIN B*.
https://www.epluse.com/fileadmin/data/product/r-t_characteristics/R_T_Characteristics_Ni1000_TK5000.pdf

Honeywell. (2022). *MERLIN NX IP and MS/TP VAV controller installation guide*.

Innovative Sensor Technology AG. (n.d.). *RTD nickel sensors* [Application
note; Nickel ND 6180 ppm/K and Nickel NL 5000 ppm/K coefficient tables].
https://www.ist-ag.com/sites/default/files/downloads/ATN_E.pdf

Innovative Sensor Technology AG. (n.d.). *Ni1000 temperature sensor: Nickel NL
(5000 ppm/K)* [Data sheet].
https://www.mouser.com/datasheet/2/1426/nl1k0_520_2fw_b_007-2950467.pdf

Minco. (n.d.). *Resistance thermometry: Principles and applications of
resistance thermometers and thermistors*.
https://www.minco.com/wp-content/uploads/Resistance-Thermometry.pdf

Minco. (n.d.). *RTD temperature vs. resistance table*. Retrieved August 17,
2026, from
https://www.minco.com/resource-center/rtd-temperature-vs-resistance-table/

Pyromation. (n.d.). *120 ohm nickel RTD—0.00672 coefficient, degree Celsius*
[Resistance/temperature table].
https://www.pyromation.com/downloads/data/672_c.pdf

TE Connectivity / HL-Planartechnik. (n.d.). *Ni1000SOT temperature sensor*
[Technical data sheet].

## Data interchange and conformance specifications

Bray, T. (2017). *The JavaScript Object Notation (JSON) data interchange
format* (RFC 8259). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8259

Hutton, B., Andrews, H., Wright, A., & Dennis, G. (2022). *JSON Schema: A media
type for describing JSON documents* (Draft 2020-12).
https://json-schema.org/draft/2020-12/json-schema-core.html

Wright, A., Andrews, H., Hutton, B., & Dennis, G. (2022). *JSON Schema
validation: A vocabulary for structural validation of JSON* (Draft 2020-12).
https://json-schema.org/draft/2020-12/json-schema-validation.html

## Source-use notes

IEC 60751 is the normative scientific basis for the built-in PT-385 platinum
models and IEC tolerance calculations. Public manufacturer tables and
calculators provide independent resistance/temperature checks so internal
round-trip agreement is not treated as external validation.

The nickel implementations intentionally preserve distinct published
characteristics rather than averaging or reconciling them: former-DIN
6178/6180 ppm/K Ni1000, Ni1000 TK5000 / 5000 ppm/K, and North American Ni120 /
6720 ppm/K remain separate model identities.

The project currently relies primarily on standards, metrology publications,
and industrial/manufacturer technical literature. No peer-reviewed journal
paper is presently cited as a scientific basis for a current built-in model.
