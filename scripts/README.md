# Optional Matchete Conversion Scripts

These scripts are convenience entry points for users who have Mathematica and
the read-only Matchete reference checkout available. They are not imported by
pychete and are not used by pytest; normal pychete runtime and tests remain
Mathematica- and Matchete-independent.

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

The committed fixtures under `assets/validation/pychete/` are the artifacts
used by pychete tests and users who do not have Mathematica.
