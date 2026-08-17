---
title: Your first Pt100 experiment
description: Use Python and rtd-sensor to explore how Pt100 resistance changes with temperature and convert resistance back to temperature, with no hardware required.
tags:
  - Pt100
  - Python
  - beginner
  - no hardware
---

# Your first Pt100 experiment

**Question:** What happens to the resistance of a Pt100 when its temperature
changes?

You can answer that without owning a sensor. In this experiment, `rtd-sensor`
will give us the ideal Pt100 behavior so we can explore it with a few lines of
Python.

- **Hardware:** none
- **Time:** about 10 minutes
- **You need:** Python 3.14+ and `rtd-sensor`

If you have not installed the package yet, start with [Start here](../start-here.md).

## A tiny bit of background

RTD stands for **resistance temperature detector**. An RTD is a temperature
sensor whose electrical resistance changes with temperature.

The name **Pt100** gives us two useful clues:

- **Pt** means the sensing element is platinum.
- **100** means the ideal sensor has a resistance of **100 ohms at 0 °C**.

For now, that is enough theory. Let's make it do something.

## Try this: ask for the resistance at 20 °C

Run this code:

```python
from rtd_sensor import pt100

resistance = pt100.celsius_to_resistance(20.0)
print(f"At 20 °C: {resistance:.4f} ohms")
```

You should get:

```text
At 20 °C: 107.7935 ohms
```

!!! question "Can you predict the result first?"
    Before changing the code, decide what you expect at **25 °C**. Will the
    resistance be higher, lower, or unchanged?

Change `20.0` to `25.0` and run it again:

```python
resistance = pt100.celsius_to_resistance(25.0)
print(f"At 25 °C: {resistance:.4f} ohms")
```

The result is:

```text
At 25 °C: 109.7347 ohms
```

The temperature went up, and so did the resistance.

## Experiment: make a small resistance table

Instead of trying one temperature at a time, ask for several:

```python
from rtd_sensor import pt100

for temperature_c in [0, 10, 20, 30, 40, 50, 100]:
    resistance = pt100.celsius_to_resistance(temperature_c)
    print(f"{temperature_c:>3} °C  ->  {resistance:.4f} ohms")
```

You should see:

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

Three things are already visible:

1. At 0 °C, the ideal Pt100 is exactly 100 ohms.
2. Resistance increases as temperature increases.
3. The resistance changes by only a few ohms for each 10 °C change.

Do the 10-degree steps change the resistance by **exactly** the same amount each
time? Keep that question in mind. A later experiment will test whether a Pt100
is really linear.

## Now run the calculation backward

A real measurement system usually starts with a measured resistance and needs
the corresponding temperature.

Let's take the resistance for 25 °C and convert it back:

```python
from rtd_sensor import pt100

resistance = pt100.celsius_to_resistance(25.0)
temperature_c = pt100.resistance_to_celsius(resistance)

print(f"Resistance: {resistance:.4f} ohms")
print(f"Temperature: {temperature_c:.2f} °C")
```

The result is:

```text
Resistance: 109.7347 ohms
Temperature: 25.00 °C
```

You have now used the Pt100 model in both directions:

```text
temperature  ->  resistance
resistance   ->  temperature
```

That second direction is the one you will eventually use with a physical Pt100:
a multimeter or an RTD interface measures resistance, and software turns that
resistance into temperature.

## Change something

Try a few experiments before moving on:

- What resistance does the model predict at **room temperature** where you are?
- What does it predict at **0 °C**? Did the name Pt100 give that one away?
- What about **100 °C**?
- Change the temperature by only **1 °C**. How much does the resistance change?
- Pick a resistance from your table and feed it to
  `pt100.resistance_to_celsius()`. Do you recover the original temperature?

!!! tip "Predict before you run"
    For at least one change, write down whether you expect the resistance to go
    up or down before Python gives you the answer. The point of these lessons is
    to build intuition, not just produce numbers.

## What you learned

You now know the basic idea behind a Pt100:

- temperature and resistance are related;
- a Pt100 is 100 ohms at 0 °C on its ideal standardized curve;
- warmer temperatures produce higher resistance over the Pt100's supported
  range;
- `rtd-sensor` can calculate the relationship in either direction.

You did all of that without any electronics.

## Next experiment

A table is useful, but a graph makes the shape of the RTD relationship much
easier to see.

**Next:** Plot an RTD curve and look at the whole Pt100 temperature range.
