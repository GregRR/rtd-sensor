---
title: API Reference
description: Concise rtd-sensor public API reference with signatures, parameters, return values, exceptions, minimal examples, and version history.
---

# API Reference

This section is the fast lookup for people who already know what they want to
do. It focuses on public interfaces rather than teaching the underlying RTD or
metrology concepts.

## Version labels

API entries record when a public interface first appeared. Project releases
0.1.0 through 0.3.0 were published as **pt100-core** and used the Python import
package `rtd`. The current **rtd-sensor** distribution and `rtd_sensor` import
package began with 0.4.0.

For APIs that survived that rename, the reference gives both the original
project release and the version in which the current `rtd_sensor` path became
available. This avoids implying that a modern import path works unchanged on a
pre-0.4.0 installation.

- [Built-in sensor modules](builtins.md)
- [`batch`](batch.md)
- [`catalog`](catalog.md)
- [`exceptions`](exceptions.md)
- [`fitting`](fitting.md)
- [`measurement`](measurement.md)
- [`models`](models.md)
- [`portable`](portable.md)
- [`simulation`](simulation.md)
- [`tolerance`](tolerance.md)
- [`uncertainty`](uncertainty.md)

For explanations and broader examples, use the
[full documentation](../documentation/index.md).
