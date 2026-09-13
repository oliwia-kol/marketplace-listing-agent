# ADR 0005: installed runtime and evidence-producing CI

Status: accepted, 2026-09-13.

Runtime data belongs in the operating-system application directory, while code and
packaged defaults belong in the wheel. CI installs the locked project non-editably,
runs lint/tests/data and secret checks, builds a wheel, then smoke-tests that wheel
outside the checkout. This caught a Python 3.14 editable-install failure that unit tests
with an explicit source path did not expose.

The decision costs a reinstall after source changes in local non-editable environments.
It provides a much closer approximation of the program the user will actually launch.
