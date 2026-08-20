---
title: RTD Playground
description: Beginner-to-intermediate rtd-sensor exercises that teach RTDs through Python experiments, starting with no hardware required.
---

# RTD Playground

The **RTD Playground** is the experiment-driven side of Learn `rtd-sensor`.
It is for beginner to intermediate learners who want to understand RTDs by
trying things, making predictions, changing values, and seeing what happens.

The first exercises need only a computer, Python 3.11 or later, and the
`rtd-sensor` package. You do **not** need a Pt100 or any electronics to begin.

## What you need

- Python 3.11 or later
- a terminal or command prompt
- a text editor, Python IDE, or interactive Python prompt
- the `rtd-sensor` package

Check your Python version:

```console
python --version
```

If your system uses `python3` instead of `python`, use that command throughout
the exercises.

## Install rtd-sensor

If you already have a Python 3.11+ virtual environment:

```console
python -m pip install rtd-sensor
```

If you use `uv` for Python projects:

```console
uv add rtd-sensor
```

Then confirm that Python can import the package:

```python
from rtd_sensor import pt100

print(pt100.celsius_to_resistance(0.0))
```

You should see:

```text
100.0
```

That number is already telling you something important about a Pt100.

## Current Playground exercises

### 1. Your first Pt100 experiment

Use Python as a virtual measurement lab. Predict resistance values, convert
temperature to resistance and back again, and discover the basic Pt100
relationship without owning a sensor.

[Start your first Pt100 experiment](../experiments/first-pt100-experiment.md)
{ .md-button .md-button--primary }

More beginner-to-intermediate exercises will be added later. For now, the
Playground intentionally stops after the first experiment while the complete
user documentation is built out.
