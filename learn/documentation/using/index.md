---
title: Using rtd-sensor
description: Everyday rtd-sensor usage: temperature and resistance conversion, range handling, sensitivity, batch conversion, model discovery, and model selection.
---

# Using rtd-sensor

The simplest `rtd-sensor` workflow is:

```text
RTD resistance in ohms → RTD model → temperature in °C
```

The reverse direction is equally useful when simulating, testing, or predicting
what a sensor should read:

```text
temperature in °C → RTD model → expected resistance in ohms
```

The pages in this section cover the package features most users need first.

- [Installation](installation.md) — install on Python 3.11+ and understand package/import naming.
- [Temperature ↔ resistance](conversion.md) — scalar conversion in both directions.
- [Valid ranges and errors](ranges-errors.md) — what happens at boundaries and with invalid input.
- [Sensitivity](sensitivity.md) — understand how much resistance changes per degree and vice versa.
- [Batch conversion](batch.md) — convert ordered iterables without NumPy.
- [Discovering built-in models](catalog.md) — inspect verified model IDs and metadata.
- [Choosing the right model](choosing-model.md) — decide between a built-in, characterized, custom, fitted, or tabulated model.
- [Migrating from pt100-core](migration.md) — update historical package names and imports.
