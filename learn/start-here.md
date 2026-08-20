---
title: Start Here
description: >-
Get productive with rtd-sensor quickly: RTD and Pt100 basics, installation for Python 3.11+, essential terminology, and first conversion examples.
---

# Start Here

This page is the quick route for people who already know Python and want to start
using `rtd-sensor`.

!!! tip "Need a more detailed introduction?"
    The [RTD Playground](playground/index.md) takes a slower, experiment-driven
    approach and explains each step as you go. It is designed for beginner to
    intermediate learners and requires no hardware for the first exercises.

## What is an RTD?

A **resistance temperature detector**, usually shortened to **RTD**, is a
temperature sensor whose electrical resistance changes predictably with
temperature. Software can use a known resistance-versus-temperature
characteristic to convert a measured resistance into temperature, or calculate
the resistance expected at a known temperature.

`rtd-sensor` handles that conversion and modeling layer. It does not read an
ADC, communicate over SPI or I²C, or perform lead-wire compensation itself.
Hardware and acquisition code should first produce the best available estimate
of the RTD element's resistance in ohms.

## What does Pt100 mean?

**Pt100** means a platinum RTD with a nominal resistance of **100 Ω at 0 °C**.
The built-in `rtd_sensor.pt100` model uses the IEC 60751 PT-385 platinum
characteristic. `rtd-sensor` also includes Pt500 and Pt1000 models that use the
same normalized platinum characteristic with different nominal resistances, as
well as several documented nickel RTD characteristics.

## Install rtd-sensor

`rtd-sensor` requires **Python 3.11 or later** and has no runtime dependencies.

With pip:

```console
python -m pip install rtd-sensor
```

With uv in an existing project:

```console
uv add rtd-sensor
```

The distribution name uses a hyphen, `rtd-sensor`, while Python imports use an
underscore, `rtd_sensor`.

Check that the package imports and performs a known Pt100 calculation:

```python
from rtd_sensor import pt100

print(pt100.celsius_to_resistance(0.0))
```

The result is:

```text
100.0
```

If Python environments, installation, or running small scripts are still new to
you, the [RTD Playground](playground/index.md) provides more guided setup and
examples.

## Units and terminology

`rtd-sensor` deliberately keeps the numerical API simple:

| Term | Meaning in `rtd-sensor` |
| --- | --- |
| Temperature | Degrees Celsius (°C) |
| Resistance | Ohms (Ω) |
| `R0` or reference resistance | The model's resistance at its reference temperature, commonly 0 °C |
| Characteristic | The mathematical resistance-temperature relationship, such as IEC 60751 PT-385 |
| Model | A particular usable RTD definition: a characteristic plus parameters such as reference resistance and valid range |
| Forward conversion | Temperature → resistance |
| Inverse conversion | Resistance → temperature |
| Sensitivity | The local rate at which resistance or temperature changes with the other quantity |

The built-in modules expose temperatures and resistances as ordinary numeric
values. Physical numeric inputs reject Python Boolean values so `True` and
`False` cannot silently become `1.0` and `0.0`.

## Your first calculations

### Temperature to resistance

Ask what resistance an ideal Pt100 should have at 25 °C:

```python
from rtd_sensor import pt100

resistance_ohms = pt100.celsius_to_resistance(25.0)
print(resistance_ohms)
```

### Resistance to temperature

If an acquisition system has measured 119.3971 Ω from a Pt100:

```python
from rtd_sensor import pt100

temperature_c = pt100.resistance_to_celsius(119.3971)
print(temperature_c)
```

That returns approximately 50 °C.

### Use a different built-in RTD

The same style of API works for other verified built-ins:

```python
from rtd_sensor import pt1000

resistance_ohms = pt1000.celsius_to_resistance(100.0)
temperature_c = pt1000.resistance_to_celsius(resistance_ohms)
```

For model discovery, custom/calibrated models, batch work, uncertainty, and
other capabilities, continue into the documentation.

## Where to go next

### Full documentation

Detailed, approachable explanations of every major `rtd-sensor` feature, with
multiple examples, limits, common mistakes, and links to deeper technical
material.

[Go to full documentation](documentation/index.md)
{ .md-button .md-button--docs }

### API Reference

Straight-to-the-point signatures, parameters, return values, exceptions, and
minimal examples for people who already know what they need.

[Open the API Reference](api/index.md)
{ .md-button }

### RTD Playground

Beginner-to-intermediate guided exercises for learning RTDs and `rtd-sensor` by
predicting, changing values, plotting, measuring, and experimenting.

[Go to the RTD Playground](playground/index.md)
{ .md-button .md-button--primary }
