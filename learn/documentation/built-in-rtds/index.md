---
title: Built-in RTDs
description: Verified rtd-sensor built-in Pt100, Pt500, Pt1000, Ni1000 6180, Ni1000 TK5000, and Ni120 6720 models.
---

# Built-in RTDs

`rtd-sensor` includes six verified built-in RTD models. Each provides
temperature-to-resistance conversion, resistance-to-temperature conversion, and
both local sensitivity directions.

| Module | Characteristic | R0 | Range |
| --- | --- | ---: | ---: |
| `pt100` | IEC 60751 PT-385 platinum | 100 Ω | -200 to 850 °C |
| `pt500` | IEC 60751 PT-385 platinum | 500 Ω | -200 to 850 °C |
| `pt1000` | IEC 60751 PT-385 platinum | 1000 Ω | -200 to 850 °C |
| `ni1000` | former DIN 43760 / Nickel ND | 1000 Ω | -60 to 250 °C |
| `ni1000_tk5000` | Nickel NL 5000 ppm/K | 1000 Ω | -60 to 250 °C |
| `ni120` | North American / Minco NA | 120 Ω | -80 to 260 °C |

Choose the sensor page that matches the documented characteristic of your
physical RTD:

- [Pt100](pt100.md)
- [Pt500](pt500.md)
- [Pt1000](pt1000.md)
- [Ni1000 6180](ni1000.md)
- [Ni1000 TK5000](ni1000-tk5000.md)
- [Ni120 6720](ni120.md)

!!! warning "Nominal resistance is not enough"
    `ni1000` and `ni1000_tk5000` both have 1000 Ω nominal resistance at 0 °C,
    but they use different nickel characteristics. A Pt1000 is different from
    both. Identify the characteristic from the sensor's documentation.
