---
title: Discovering built-in models
description: Discover verified rtd-sensor built-in model IDs, retrieve models, and inspect immutable metadata and source provenance.
---

# Discovering built-in models

The `rtd_sensor.catalog` module provides a read-only view of the verified
built-in RTD registry. Use it when an application needs to populate a selector,
inspect model metadata, or obtain a built-in model by canonical ID.

**Available since:** rtd-sensor 0.5.0.

## List supported IDs

```python
from rtd_sensor import catalog

print(catalog.supported_models())
```

The returned tuple follows the package's authoritative built-in definition
order.

## Get a model by ID

```python
from rtd_sensor import catalog

model = catalog.get_model("pt100")
temperature_c = model.resistance_to_celsius(119.3971)
```

The returned object exposes the structural numerical model behavior. It does
not expose package-private curve coefficients or identity internals.

## Inspect model metadata

```python
from rtd_sensor import catalog

info = catalog.model_info("pt100")

print(info.display_name)
print(info.material)
print(info.reference_resistance_ohms)
print(info.minimum_temperature_c, info.maximum_temperature_c)
```

`BuiltinRTDModelInfo` also includes:

- canonical `model_id`;
- `characteristic_id` and display name;
- material (`"platinum"` or `"nickel"`);
- curve kind;
- reference resistance and reference temperature;
- supported characteristic range;
- immutable source references.

## Model identity versus characteristic identity

Pt100, Pt500, and Pt1000 are three different **models** because they have
different reference resistances. They share one normalized IEC 60751 PT-385
**characteristic**.

That distinction becomes important in software that needs to record exactly
what scientific curve was used without confusing it with the nominal resistance
of a particular model.

## Unknown IDs

```python
from rtd_sensor import catalog, exceptions

try:
    catalog.get_model("pt200")
except exceptions.UnknownRTDModelError:
    ...
```

The catalog intentionally provides no user registration API. User-defined
models are ordinary model objects rather than entries inserted into the
package's verified built-in registry.

## Related features

- [Choosing the right model](choosing-model.md)
- [Built-in RTDs](../built-in-rtds/index.md)
- [RTDModel interface](../integration/rtdmodel-interface.md)
