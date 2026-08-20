---
title: Simulation & testing
description: Use rtd-sensor simulation readers to test RTD applications with fixed, sequenced, temperature-derived, and reproducibly noisy measurements.
---

# Simulation & testing

`rtd_sensor.simulation` produces RTD resistance readings without physical
hardware. The simulated readers use the same resistance boundary as a real
acquisition layer, so application code can often switch between simulated and
physical readers without changing its RTD model logic.

[Simulation readers](simulation.md) cover fixed resistance, resistance
sequences, temperature sequences, reproducible Gaussian temperature noise, and
selection of any verified built-in RTD type.
