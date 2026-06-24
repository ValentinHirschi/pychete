# Helper Mathematica Scripts

These scripts are development-only tooling for generating pychete-owned
validation fixtures from the read-only Matchete checkout. Runtime pychete code
and pytest must not call these scripts or require Mathematica.

The intended flow is:

1. Run a helper script against `Mathematica_reference/Matchete`.
2. Convert the raw Matchete snapshots into pychete fixture JSON.
3. Commit the pychete fixture JSON under `assets/validation/`.
4. Test only against committed pychete fixtures.

Use this route for complicated Mathematica models. The direct Python loader in
`src/pychete/loaders/mathematica.py` intentionally supports only a small
declarative Matchete/Wolfram subset; it should not be expanded into a general
Wolfram Language parser. For richer model files, write a Wolfram helper that
lets Matchete load the model, extracts the already-parsed Matchete internals
needed by pychete, and emits pychete-owned serialized state or Python fixture
files that can be committed and loaded like native pychete inputs.

The first script is intentionally a raw snapshot exporter. The Python-side
fixture converter will become stricter as the one-loop matching data model
lands.

`convert_matchete_previous_results.py` converts existing Matchete validation
result files into committed pychete `MatchingResult` fixtures. Matching
condition rules are stored as RHS expressions keyed by the canonical pychete
expression for the Matchete rule left-hand side.

Run the converter from the repository root with the managed environment:

```sh
source "$HOME/.bashrc"
PYTHONPATH=src dependencies/.venv/bin/python \
  helper_mathematica_scripts/convert_matchete_previous_results.py \
  --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs
```
