# Helper Mathematica Scripts

These scripts are development-only tooling for generating pychete-owned
validation fixtures from the read-only Matchete checkout. Runtime pychete code
and pytest must not call these scripts or require Mathematica.

The intended flow is:

1. Run a helper script against `Mathematica_reference/Matchete`.
2. Convert the raw Matchete snapshots into pychete fixture JSON.
3. Commit the pychete fixture JSON under `assets/validation/`.
4. Test only against committed pychete fixtures.

The first script is intentionally a raw snapshot exporter. The Python-side
fixture converter will become stricter as the one-loop matching data model
lands.
