---
title: Measurement & uncertainty
description: Understand rtd-sensor's hardware-neutral measurement boundary, resistance readers, IEC tolerance classes, sensitivity-based propagation, and temperature uncertainty budgets.
---

# Measurement & uncertainty

Converting a number is only one part of a real temperature measurement. You
also need to know where the resistance came from, what uncertainty belongs to
that measurement, and which limits or assumptions apply to the physical sensor.

This section keeps those ideas separate:

- [Hardware/acquisition boundary](acquisition-boundary.md)
- [ResistanceReader composition](resistance-reader.md)
- [IEC 60751 tolerance classes](tolerance.md)
- [Uncertainty fundamentals](uncertainty.md)
- [Resistance uncertainty propagation](resistance-propagation.md)
- [Temperature uncertainty budgets](uncertainty-budgets.md)

!!! important "Tolerance and uncertainty are not synonyms"
    An IEC tolerance class gives a bounded conformity limit. A standard
    uncertainty is a statistical quantity used in an uncertainty analysis.
    Turning a tolerance bound into a standard uncertainty requires an explicit
    probability-model assumption made by the user.
