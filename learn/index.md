---
title: Learn rtd-sensor
description: Learn how Pt100 and other RTD temperature sensors work through beginner-friendly Python experiments, then move on to real measurements, calibration, uncertainty, and embedded systems.
---

# Learn rtd-sensor

**Learn RTDs by experimenting with them. No hardware is required to start.**

`rtd-sensor` is a Python library for resistance temperature detector (RTD)
conversion and modeling. This site is the hands-on companion to the project:
short experiments that let you change values, make predictions, and see what
happens.

You can begin with only Python and `rtd-sensor`. Later experiments add a real
Pt100, a multimeter, a MAX31865, and a Raspberry Pi.

## Start with a Pt100

A **Pt100** is a platinum RTD whose ideal resistance is 100 ohms at 0 °C. In the
first experiment, Python will act as the measurement lab: you will ask what
resistance a Pt100 should have at different temperatures and then run the
calculation in reverse.

[Start your first Pt100 experiment](experiments/first-pt100-experiment.md)
{ .md-button .md-button--primary }

## Where this goes

The experiments will gradually move from software-only exploration to real
hardware:

1. calculate Pt100 resistance and temperature;
2. plot an RTD curve;
3. test whether a Pt100 is really linear;
4. compare Pt100, Pt500, and Pt1000 sensors;
5. measure a real Pt100 with a multimeter;
6. connect a MAX31865 and Raspberry Pi;
7. explore calibration, tolerance, uncertainty, and portable models;
8. go deeper into cross-language and embedded RTD implementations.

!!! note "This is the learning site"
    The main repository documentation remains the engineering reference for
    `rtd-sensor`. These pages are deliberately experiment-first and
    beginner-friendly.
