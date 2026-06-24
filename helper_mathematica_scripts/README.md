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

`convert_matchete_previous_results.py` converts existing Matchete validation
result files into committed pychete `MatchingResult` fixtures. The current
converter supports the `VLF_toy_model` previous result, whose Matchete
`Matching Conditions` entry is `None`; nontrivial matching-condition rule lists
are left for the next converter slice.

Run the converter from the repository root with the managed environment:

```sh
source "$HOME/.bashrc"
PYTHONPATH=src dependencies/.venv/bin/python \
  helper_mathematica_scripts/convert_matchete_previous_results.py \
  --models VLF_toy_model
```
