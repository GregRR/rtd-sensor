---
title: Your first Pt100 experiment
description: Explore how Pt100 resistance changes with temperature using Python and rtd-sensor. No sensor, electronics, or other hardware required.
tags:
  - Pt100
  - RTD
  - Python
  - beginner
  - no hardware
---

# Your first Pt100 experiment

**Make a Pt100 do something before you even own one.**

In this experiment, Python will be our virtual temperature lab. We will change
the temperature of an ideal Pt100, watch its resistance change, and then run
the calculation backward as if we had measured a real sensor.

- **Hardware:** none
- **Time:** about 10–15 minutes
- **You need:** Python 3.14+ and `rtd-sensor`

If you have not installed the package yet, start with [Start here](../start-here.md).

## The question

A Pt100 is a temperature sensor, but what does it actually measure?

More specifically:

> **What happens to the electrical resistance of a Pt100 when its temperature
> changes?**

We can answer that with just a few lines of Python.

## Two facts before we begin

RTD stands for **resistance temperature detector**. Its electrical resistance
changes in a predictable way as its temperature changes.

The name **Pt100** gives us two useful clues:

- **Pt** means the sensing element is platinum.
- **100** means an ideal Pt100 has a resistance of **100 ohms at 0 °C**.


!!! note "rtd-sensor is an interpreter"
    `rtd-sensor` is not pretending that your computer has a temperature probe
    attached to it at this point. It calculates the standardized relationship 
    between resistance and temperature. Later, we will feed it measurements from real
    hardware.

## Experiment 1: discover the "100" in Pt100

Start at 0 °C:

```python
from rtd_sensor import pt100

resistance = pt100.celsius_to_resistance(0.0)
print(f"At 0 °C: {resistance:.4f} ohms")
```

You should see:

```text
At 0 °C: 100.0000 ohms
```

So the **100** in Pt100 is not just a model number. At 0 °C, the ideal
standardized sensor really is 100 ohms.

## Experiment 2: warm up the virtual sensor

Before running the next example, make a prediction.

!!! question "Predict first"
    If the Pt100 warms from **0 °C to 20 °C**, do you expect its resistance to
    be **higher than 100 ohms**, **lower than 100 ohms**, or **still exactly
    100 ohms**?

Now change the temperature:

```python
from rtd_sensor import pt100

resistance = pt100.celsius_to_resistance(20.0)
print(f"At 20 °C: {resistance:.4f} ohms")
```

The result is:

```text
At 20 °C: 107.7935 ohms
```

The temperature went up, and so did the resistance.

Try 25 °C:

```python
resistance = pt100.celsius_to_resistance(25.0)
print(f"At 25 °C: {resistance:.4f} ohms")
```

```text
At 25 °C: 109.7347 ohms
```

That gives us our first useful rule of thumb:

> **For a Pt100, resistance increases as temperature increases.**

## Experiment 3: make a resistance table

One value at a time does not show us much of a pattern. Let's ask for several
values:

```python
from rtd_sensor import pt100

for temperature_c in [0, 10, 20, 30, 40, 50, 100]:
    resistance = pt100.celsius_to_resistance(temperature_c)
    print(f"{temperature_c:>3} °C  ->  {resistance:.4f} ohms")
```

You should get:

```text
  0 °C  ->  100.0000 ohms
 10 °C  ->  103.9025 ohms
 20 °C  ->  107.7935 ohms
 30 °C  ->  111.6729 ohms
 40 °C  ->  115.5408 ohms
 50 °C  ->  119.3971 ohms
100 °C  ->  138.5055 ohms
```

### What happened?

Three things should stand out:

1. At 0 °C, the ideal Pt100 is 100 ohms.
2. Resistance rises as temperature rises.
3. A 10 °C temperature change changes the resistance by only a few ohms.

Now look more closely at the 10-degree steps. Does the resistance increase by
**exactly** the same amount every time?

It is close, but not quite.

That small clue will matter in a later experiment when we ask whether a Pt100 is
really linear.

## Experiment 4: pretend we measured a real Pt100

So far we have started with temperature and asked for resistance:

```text
temperature  ->  resistance
```

A real thermometer usually needs to do the opposite. Hardware measures the
sensor's resistance, and we need to determine the temperature:

```text
measured resistance  ->  temperature
```

Imagine that some measurement hardware reports a Pt100 resistance of
**119.3971 ohms**.

Ask `rtd-sensor` what temperature that represents:

```python
from rtd_sensor import pt100

measured_resistance = 119.3971
temperature_c = pt100.resistance_to_celsius(measured_resistance)

print(f"Measured resistance: {measured_resistance:.4f} ohms")
print(f"Temperature: {temperature_c:.2f} °C")
```

You should see:

```text
Measured resistance: 119.3971 ohms
Temperature: 50.00 °C
```

That is the basic job `rtd-sensor` will eventually perform with a physical
sensor: take the best available estimate of the Pt100's resistance and convert
it to temperature.

!!! info "Where the resistance comes from"
    `rtd-sensor` does not read a multimeter, ADC, or a MAX31865 itself. Those
    devices obtain the resistance measurement. `rtd-sensor` handles the resistance 
    temperature detector (RTD) model that turns that resistance into temperature.

## Try your own experiments

Do not stop with the values above. Change something and see what happens.

- What resistance does a Pt100 have at **37 °C**?
- What about **-20 °C**?
- Change the temperature from **20 °C to 21 °C**. How much does the resistance
  change?
- Pick a temperature of your own, calculate its resistance, then feed that
  resistance into `pt100.resistance_to_celsius()`. Do you get back where you
  started?
- Try this mystery resistance: **114.3817 ohms**. What temperature is it close
  to?

!!! tip "Build intuition, not just output"
    For at least one experiment, write down your prediction before running the
    code. Being wrong is useful: the interesting part is figuring out why the
    result differed from what you expected.

!!! note "Stay inside the model range"
    The built-in Pt100 model supports **-200 °C through 850 °C**. We will talk
    later about why software should reject values outside a model's valid
    range instead of blindly extrapolating.

## What changes when the Pt100 is real?

Our values so far came from the ideal standardized Pt100 curve. A physical
measurement introduces more questions:

- Is the real probe exactly on the ideal curve?
- How accurately did we measure its resistance?
- Did the wires add resistance of their own?
- Is the probe actually at the same temperature as the thing we are trying to
  measure?

We do **not** need to solve those problems yet. For now, the important thing is
that the resistance-to-temperature relationship itself makes sense.

Later experiments will add those real-world effects one at a time.

## What you learned

You have now made your first virtual Pt100 measurement and discovered that:

- a Pt100 is a platinum resistance temperature detector;
- an ideal Pt100 is 100 ohms at 0 °C;
- its resistance increases as temperature increases;
- the relationship is close to linear over ordinary ranges, but not exactly;
- `rtd-sensor` can calculate temperature → resistance;
- `rtd-sensor` can also calculate resistance → temperature;
- real measurement hardware and the RTD model have different jobs.

And you did all of it without owning a sensor.

## Next experiment

A table hints at the shape of the Pt100 relationship. A graph makes it much
easier to see.

**Next:** Plot an RTD curve and see what the Pt100 looks like from -200 °C to
850 °C.
