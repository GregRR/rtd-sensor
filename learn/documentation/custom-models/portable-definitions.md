---
title: Portable model definitions
description: Serialize and reconstruct supported rtd-sensor configurable and fitted models with the versioned language-neutral portable model-definition format.
---

# Portable model definitions

A calibration fit or characterized model is useful only if you can reproduce it
later. `rtd_sensor.portable` converts supported model objects into a versioned,
language-neutral definition that can be stored, transferred, validated, and
reconstructed without rerunning a fit.

**Available since:** rtd-sensor 0.6.0.

## Supported model families in format version 1

- characterized IEC 60751 PT-385 models;
- custom Callendar–Van Dusen models;
- global polynomial models; and
- piecewise-polynomial models.

Tabulated-model portability is not part of version 1.

## Serialize a model

```python
from rtd_sensor import portable
from rtd_sensor.models import IEC60751RTDModel

model = IEC60751RTDModel(
    r0_ohms=100.017,
    minimum_temperature_c=-50.0,
    maximum_temperature_c=250.0,
)

artifact = portable.model_to_portable_definition(
    model,
    metadata={"source": "calibration record 2026-08"},
)
```

The returned artifact is an ordinary Python dictionary suitable for JSON
serialization.

## Reconstruct it

```python
loaded = portable.model_from_portable_definition(artifact)

print(loaded.model.r0_ohms)
print(loaded.metadata["source"])
```

`PortableModelDefinition` keeps the reconstructed model and non-behavioral
metadata separate.

## Behavior versus metadata

The numerical `definition` controls model behavior. Optional `metadata` can
carry application-neutral provenance, but it is not allowed to silently change
how the curve is calculated.

Physical probe inventory, hardware channel settings, SPI configuration, and
application-specific equipment identity should remain outside this scientific
model artifact.

## Strict validation

The format has its own `format_version`. Unsupported versions, model kinds,
unknown behavior-changing fields, malformed structures, and scientifically
invalid numerical definitions are rejected rather than guessed.

A malformed or unsupported artifact raises
`InvalidPortableModelDefinitionError`.

## Portable format versus conformance artifacts

Portable model definitions answer:

> “How do I preserve and reconstruct this particular model?”

Conformance artifacts answer:

> “How can an independent implementation demonstrate that its behavior matches
> the published rtd-sensor contract?”

They are related interoperability features but intentionally different formats.

## Language-neutral schema

The canonical schema and format notes live in the repository's
[`portable/README.md`](https://github.com/GregRR/rtd-sensor/blob/main/portable/README.md)
and `portable/v1/model-definition.schema.json`.

## Related features

- [Calibration fitting](calibration-fitting.md)
- [Advanced cross-language use](../../advanced/cross-language-embedded.md)
- [Conformance](../../advanced/conformance.md)
