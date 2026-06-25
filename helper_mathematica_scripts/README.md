# Helper Mathematica Scripts

These scripts are development-only tooling for generating pychete-owned
validation fixtures from the read-only Matchete checkout. Runtime pychete code
and pytest must not call these scripts or require Mathematica.

Top-level wrappers are also available under `scripts/` for users who want the
optional convenience workflow from a more discoverable location:
`scripts/export_matchete_model_state.wls` and
`scripts/convert_matchete_model_state.py`. Those wrappers delegate to the
maintained helper implementation here and remain optional; pychete itself stays
Mathematica- and Matchete-independent.

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

`export_matchete_model_state.wls` is the initial loaded-model-state exporter
for that route. It loads each model through Matchete's `LoadModel[...]`, reads
the post-load Matchete metadata through public getters such as `GetFields[]`,
`GetCouplings[]`, `GetGaugeGroups[]`, `GetGlobalGroups[]`,
`GetFlavorIndices[]`, and `GetRepresentations[]`, and writes a neutral RawJSON
contract. Convert that RawJSON into normal pychete model fixtures with
`convert_matchete_model_state.py`.

```sh
wolframscript -file helper_mathematica_scripts/export_matchete_model_state.wls \
  --out assets/validation/matchete/model_state \
  --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs

source "$HOME/.bashrc"
PYTHONPATH=src dependencies/.venv/bin/python \
  helper_mathematica_scripts/convert_matchete_model_state.py \
  assets/validation/matchete/model_state/*.model_state.json
```

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
  --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs \
  --update-model-fixture-wilson-metadata
```

Use `--update-model-fixture-wilson-metadata` when refreshing the committed
default SMEFT fixtures so the paired model fixtures receive the exact
theory-owned Wilson target metadata parsed from Matchete's matching-condition
left-hand sides.
