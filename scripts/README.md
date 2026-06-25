# Optional Matchete Conversion Scripts

These scripts are convenience entry points for users who have Mathematica and
the read-only Matchete reference checkout available. They are not imported by
pychete and are not used by pytest; normal pychete runtime and tests remain
Mathematica- and Matchete-independent.

## Loaded Model State

One-command optional export and conversion:

```sh
wolframscript -file scripts/convert_matchete_model_state.wls \
  --raw-out /tmp/pychete_model_state \
  --fixtures-dir assets/validation/pychete \
  --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs
```

This wrapper uses `dependencies/.venv/bin/python` when it exists, otherwise
`python3`. Pass `--python /path/to/python` to override it.

Export loaded Matchete model state:

```sh
wolframscript -file scripts/export_matchete_model_state.wls \
  --out /tmp/pychete_model_state \
  --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs
```

Convert that RawJSON state into pychete-owned model fixtures:

```sh
PYTHONPATH=src dependencies/.venv/bin/python scripts/convert_matchete_model_state.py \
  /tmp/pychete_model_state/*.model_state.json \
  --fixtures-dir assets/validation/pychete
```

## Previous Matching Results

Export raw matching snapshots for development inspection:

```sh
wolframscript -file scripts/export_matchete_matching_snapshots.wls \
  --out /tmp/pychete_matching_snapshots \
  --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs
```

Convert Matchete's committed previous matching-result files into pychete-owned
fixtures:

```sh
PYTHONPATH=src dependencies/.venv/bin/python scripts/convert_matchete_previous_results.py \
  --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs \
  --fixtures-dir assets/validation/pychete
```

The committed fixtures under `assets/validation/pychete/` are the artifacts
used by pychete tests and users who do not have Mathematica. These scripts are
optional convenience wrappers over `helper_mathematica_scripts/`; pychete does
not depend on Mathematica or Matchete at runtime.
