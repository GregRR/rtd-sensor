---
title: Migrating from pt100-core
description: Update imports and package names when moving from historical pt100-core 0.3.x releases to rtd-sensor 0.4.0 and later.
---

# Migrating from pt100-core

`rtd-sensor` began as the Pt100-focused `pt100-core` project. Version 0.4.0
renamed both the distribution and Python package as support expanded beyond
Pt100.

```text
Old distribution:  pt100-core
New distribution:  rtd-sensor
Old Python import: rtd
New Python import: rtd_sensor
```

## Update imports

Old code:

```python
from rtd import pt100
```

Current code:

```python
from rtd_sensor import pt100
```

Advanced imports change the same way:

```python
# Old
from rtd.models import IEC60751RTDModel

# Current
from rtd_sensor.models import IEC60751RTDModel
```

## No compatibility `rtd` package

`rtd-sensor` intentionally does not ship a compatibility package named `rtd`.
Applications migrating from `pt100-core` must update their imports explicitly.
Historical `pt100-core` releases remain part of the old release line; they are
not aliases for current `rtd-sensor` releases.

## Why the rename matters

The current package supports platinum and nickel RTDs, custom and calibrated
models, fitting, uncertainty, simulation, conformance, and other capabilities
that no longer fit a Pt100-only project identity.
