---
title: Start here
description: Set up Python and rtd-sensor for the Learn rtd-sensor beginner experiments. No RTD sensor or electronics are required for the first lessons.
---

# Start here

The first Learn `rtd-sensor` experiments need only a computer, Python, and the
`rtd-sensor` package. You do **not** need a Pt100 or any electronics yet.

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
these lessons.

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

[Continue to your first Pt100 experiment](experiments/first-pt100-experiment.md)
{ .md-button .md-button--primary }
