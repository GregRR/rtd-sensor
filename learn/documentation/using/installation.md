---
title: Installation
description: Install rtd-sensor 0.6.1 on Python 3.11 or later with pip or uv and understand the distribution and import package names.
---

# Installation

The current `rtd-sensor` release supports **Python 3.11 and later** and has no
runtime dependencies.

**Changed in:** rtd-sensor 0.6.1 — the supported Python floor was expanded to
Python 3.11.

## Install with pip

Inside the Python environment where you want to use the package:

```console
python -m pip install rtd-sensor
```

Confirm the installation:

```python
from rtd_sensor import pt100

print(pt100.celsius_to_resistance(0.0))
```

Expected result:

```text
100.0
```

## Add it to a uv project

```console
uv add rtd-sensor
```

This records `rtd-sensor` as a project dependency using uv's normal dependency
workflow.

## Distribution name versus import name

Python packaging uses two spellings:

```text
PyPI/distribution: rtd-sensor
Python import:     rtd_sensor
```

So this is correct:

```python
from rtd_sensor import pt100
```

and this is not:

```python
# Wrong: hyphens cannot be used in a Python import name.
# from rtd-sensor import pt100
```

## Verify your Python version

```console
python --version
```

If your system uses `python3`, use that command instead. A Python version older
than 3.11 is outside the supported package range.

## Development versions versus released versions

For normal use, install the released package from PyPI. Repository development
setup, test matrices, and release tooling are engineering concerns documented in
the project repository rather than requirements for package users.

## Related pages

- [Start Here](../../start-here.md)
- [Temperature ↔ resistance](conversion.md)
- [Migrating from pt100-core](migration.md)
