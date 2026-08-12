# Independent C11 conformance consumer

This directory contains a deliberately small C11 implementation used to verify
that the published `rtd-sensor` conformance artifacts are sufficient for an
implementation that does not depend on Python internals.

The consumer is **not** the embedded RTD library promised by any downstream
project, and it is not part of the Python package's runtime API. Its purpose is
to exercise the public conformance contract from another language.

The implementation:

- accepts characteristic and model data supplied from the committed conformance
  catalogs;
- supports the three curve kinds currently published by conformance v1;
- uses Horner polynomial evaluation;
- uses one bounded global-bisection inverse for all characteristics rather than
  reproducing Python's curve-specific inversion strategies; and
- returns the language-neutral conformance status vocabulary defined by
  `docs/CONFORMANCE.md`.

The pytest driver in `tests/test_c_conformance_consumer.py` reads only the
committed JSON artifacts when constructing the C test data. It compiles this
consumer with an available C compiler and runs the complete published built-in
conversion and status vector sets.

Run the consumer verification directly with:

```bash
uv run --locked pytest tests/test_c_conformance_consumer.py -v
```

If no C compiler is available, the test is skipped. Project CI environments
intended to verify cross-language conformance should provide a C compiler so
this test is executed rather than skipped.
