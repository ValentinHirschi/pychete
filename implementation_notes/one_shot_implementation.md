# One-Shot Port Implementation Notes

## Approved Goal

Fully implement pychete's one-shot Matchete-style one-loop matching port on the
`one-shot-port` branch. The objective is to make pychete capable of performing
one-loop EFT matching for the Matchete validation target models, especially
SMEFT UV-complete matching models, while preserving pychete's Pythonic API and
using Symbolica/idenso/spenso/vakint as the computational backends instead of
reimplementing symbolic physics algorithms in Python.

Very important: use Symbolica as much as possible and periodically rescan the
Symbolica Python stub files so the native API stays in context.

Normal pychete tests must be Mathematica-independent. pytest must never require
Mathematica, `wolframscript`, or a runnable Matchete installation. Development
helper Wolfram scripts may load the read-only Matchete checkout to generate
committed pychete-owned fixtures, but runtime code and tests must load only
those fixtures.

Keep the approved implementation plan copied into both
`implementation_notes/one_shot_user.md` and
`implementation_notes/one_shot_implementation.md`, and keep both copies updated
whenever the plan changes. Keep this implementation note continuously updated
with current progress, completed milestones, test status, backend/API
discoveries, dependency patches, blockers, and remaining work.

## Approved Plan

# One-Shot One-Loop Matching Port

## Summary

- Build a Pythonic pychete implementation of Matchete-style one-loop matching,
  prioritizing the default SMEFT UV matching models first, then all Matchete
  validation tests that map cleanly to pychete's architecture.
- Normal pytest must be Mathematica-independent. Development-only Wolfram
  scripts may load Matchete to generate serialized pychete fixtures under the
  repo, but tests load only those committed fixtures.
- Use Symbolica as the symbolic engine, idenso/spenso for gamma, colour,
  metric, and tensor algebra, and vakint for vacuum integral canonicalization,
  tensor reduction, and evaluation.
- Compare results by pychete canonical equality, backed by Symbolica evaluator
  numeric probes for hard-to-canonicalize expressions.

## Key Changes

- Add `helper_mathematica_scripts/` with Wolfram scripts that load Matchete and
  export model definitions, validation expected outputs, supertraces, matching
  conditions, and selected unit-test fixtures into pychete-owned serialized
  assets.
- Add committed fixture assets for Matchete-independent pytest validation;
  never require `wolframscript` in normal tests.
- Extend pychete metadata with gauge groups, representations, CG tensors,
  charges, chiral fermions, ghosts, Goldstones, background fields, coupling
  symmetries, diagonal/unitary metadata, and SMEFT basis metadata using
  Symbolica symbol tags/data.
- Replace the current tiny Mathematica loader as a validation path with fixture
  loading; keep any direct Mathematica-input support explicitly secondary.

## Matching Engine

- Add a one-loop matching API around `Theory.match(..., loop_order=1)` returning
  a structured `MatchingResult` with UV Lagrangian, fluctuation operators,
  individual supertraces, off-shell EFT Lagrangian, on-shell EFT Lagrangian, and
  matching conditions.
- Implement the Matchete pipeline in pychete terms: free Lagrangian
  construction, Feynman rules/functional derivatives, fluctuation-operator
  extraction, heavy/light DoF classification, propagator expansion, supertrace
  generation, loop-momentum tensor reduction, integral evaluation, EFT
  truncation, EOM/on-shell reduction, and effective-coupling mapping.
- Use Symbolica patterns, `replace_multiple`, `series`, `coefficient`,
  `collect`, `derivative`, `Transformer`, and evaluator APIs before adding
  Python traversal logic.
- Route gamma/colour/metric simplification through idenso adapters,
  tensor/CG contraction through spenso adapters, and vacuum integrals through
  vakint adapters.
- If idenso/spenso/vakint are insufficient, add patch files under
  `dependencies/patches/`, make `dependencies/install_dependencies.py` apply
  them after clone/reset and before build, and test the patched behavior from
  Python.

## Validation And Tests

- First green milestone: fixture-generation scripts plus committed fixtures for
  the default integration models: `VLF_toy_model`,
  `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Then port mappable unit validations for definitions, covariant derivatives,
  EFT counting, Feynman rules, loop integration, Dirac/NCM algebra,
  simplifications, coupling manipulation, flavor/group/CG behavior, SSB, and
  dimensional reduction.
- Exclude tests that only assert Matchete's internal structure, caching,
  package globals, print forms, or Mathematica-specific behavior with a
  documented skip map.
- For every symbolic equality test, canonicalize with
  pychete/Symbolica/idenso/spenso/vakint; where canonical equality is fragile,
  add Symbolica `Evaluator`-based numeric probes with deterministic sample
  points.
- Keep `pytest` and `mypy` green at each committed milestone.

## Workflow

- During implementation, create and maintain
  `implementation_notes/one_shot_user.md` and
  `implementation_notes/one_shot_implementation.md`.
- Commit and push only green, coherent milestones to remote branch
  `one-shot-port`.
- Preserve the existing public API discipline: intended user APIs are exported
  through `pychete.api` and package root `pychete`, with docstrings and Jupyter
  `_repr_html_` / `_repr_latex_` where relevant.

## Assumptions

- Public API should remain Pythonic pychete, with Matchete-inspired helpers only
  where they reduce friction.
- Pytest must not depend on Mathematica, Matchete runtime loading, or
  `wolframscript`.
- Full validation means "all tests that map to pychete's implementation model,"
  with one-loop SMEFT matching treated as the primary acceptance target.

## Live Progress

- Current branch: `one-shot-port`.
- Current baseline commit at start of one-shot implementation: `a8abd5c`.
- The Matchete reference checkout exists under `Mathematica_reference/Matchete`
  and is treated as read-only.
- Completed the first implementation slice:
  - recorded the approved plan in both one-shot notes;
  - added a Mathematica-independent validation fixture loader backed by
    `PycheteState`;
  - added the default Matchete matching target manifest for
    `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`;
  - added development-only Mathematica helper script scaffolding for raw
    Matchete matching snapshots.
- Completed the second implementation slice:
  - added public `MatchingResult` as the structured carrier for UV Lagrangian,
    fluctuation operators, individual supertraces, off-shell EFT Lagrangian,
    on-shell EFT Lagrangian, matching conditions, and metadata;
  - added validation fixture support for reconstructing `MatchingResult` from
    committed JSON expression references;
  - kept `load_validation_fixture` out of the package-root public API while
    promoting `MatchingResult` as a public result object;
  - added Jupyter repr coverage for `MatchingResult`.
- Completed the third implementation slice:
  - added `pychete.validation.evaluator_probe_equal`, which compares two
    expressions through `Expression.evaluator_multiple` rather than Python-side
    substitution;
  - added `NumericProbeResult` to carry equality, maximum absolute difference,
    and per-sample differences;
  - added NumPy to the managed dependency bootstrap because Symbolica evaluator
    calls require the NumPy array API at runtime;
  - pinned the managed NumPy dependency to `numpy<2.5` because NumPy 2.5 stubs
    require Python 3.12 syntax while pychete's mypy target is Python 3.11.
- Completed the fourth implementation slice:
  - added `FieldChirality` and stored field chirality in Symbolica symbol data;
  - added field gauge-charge metadata stored in Symbolica symbol data;
  - added `Theory.group_charge(...)` for Pythonic U(1)-charge construction;
  - taught the supported Matchete model loader path to preserve simple
    `Charges`, `Indices`, and `Chiral` field options;
  - updated the VLF toy model Python asset so the Python and supported
    Mathematica assets agree on U(1) charge metadata.
- Completed the fifth implementation slice:
  - added the first committed pychete-owned fixture asset at
    `assets/validation/pychete/VLF_toy_model.model_fixture.json`;
  - added pytest coverage that loads this committed asset without Mathematica
    and compares it to the Python VLF model asset;
  - fixed `Theory.from_json_obj` so the group registry is restored alongside
    group symbols, which is required for `Theory.group_charge(...)` after
    loading fixtures or checkpoints.
- Completed the sixth implementation slice:
  - added Matchete-style coupling metadata to `CouplingDefinition` and
    Symbolica symbol data: indexed coupling representations, EFT order,
    boolean or permutation-valued self-conjugation, symmetry expressions,
    diagonal-coupling flags, thermal power counting, and unitary flags;
  - added central Symbolica heads for `SymmetricIndices`,
    `AntisymmetricIndices`, `SymmetricPermutation`,
    `AntisymmetricPermutation`, and `SymmetryOverride` through the
    `SymbolStore`;
  - taught `Theory.from_json_obj` to restore the new coupling metadata through
    the existing symbol-manifest-first checkpoint path;
  - added a coupling symbol-manifest normalization path so older committed
    fixtures that predate the new coupling keys load into the current
    structural symbol-data shape before expressions are parsed;
  - extended the supported Matchete model loader path to preserve
    `DefineCoupling` options instead of dropping them, including list-valued
    `DefineCoupling[{...}, ...]`.
- Completed the seventh implementation slice:
  - added pychete-owned model input assets for the remaining default one-loop
    matching targets: `Singlet_Scalar_Extension.m`, `E_VLL.m`, and
    `S1S3LQs.m`;
  - added the pychete-owned `SM.m` parent model asset required by those three
    default target files;
  - updated the default matching target manifest so every target points to a
    repository-owned `model_asset` and explicit `parent_assets` instead of
    requiring tests to read from `Mathematica_reference/Matchete`;
  - kept the status as `pending_matching_fixture` because the actual one-loop
    matching-result fixtures are still not generated.
- Completed the eighth implementation slice:
  - added metadata-only loading for the supported Matchete model subset through
    `load_matchete_model(..., include_lagrangian=False)`;
  - added parent-model expansion for `ParentModel["SM"]`, loading parent
    definitions into the child theory namespace before child-specific
    definitions;
  - added loader support for `ParameterDefault`, `DefineFlavorIndex`, optional
    `DefineGaugeGroup` arguments, `SU@N` group heads, quoted Mathematica
    strings in top-level splitters, broader Greek-name preprocessing, and
    `Bar@` / `CConj@` prefix application in metadata expressions;
  - added central `CConj` Symbolica head support;
  - generated committed metadata-only model-definition fixtures for `SM`,
    `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`;
  - updated the default matching target manifest to point at the committed
    model-definition fixtures for all default targets.
- Completed the ninth implementation slice:
  - extended the supported Mathematica expression normalizer for child target
    Lagrangians with integer factorials, simple implicit products, Mathematica
    list braces, and general `**` noncommutative chains;
  - changed parent expansion so child model expression loading uses parent
    metadata but does not attempt to parse or include the parent SM Lagrangian;
  - parsed and committed child-Lagrangian expressions for
    `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs` in their
    model-definition fixtures;
  - skipped local delayed helper definitions such as `tauSU2L[...] := ...`
    during direct parsing for now, leaving their calls as registered external
    heads until the CG adapter layer can lower them through spenso/idenso;
  - added tests proving those child Lagrangians parse from the pychete-owned
    model assets and restore from committed fixtures without Mathematica.

## Backend/API Discoveries

- Symbolica state restoration already supports the structural guarantee needed
  for validation fixtures: `PycheteState.from_json_obj` restores registered
  theory symbols before parsing stored expressions.
- Existing idenso APIs include direct gamma, colour, metric, index wrapping, and
  dangling-index routines; these should be the first line for algebra adapters.
- Existing vakint APIs include `to_canonical`, `tensor_reduce`,
  `evaluate_integral`, and `evaluate`, which map directly onto the planned loop
  integral backend.
- Rescanned the Symbolica Python stub sections for `Expression.match`,
  `Expression.matches`, `Expression.evaluator`, and `Expression.evaluator_multiple`.
  The numeric-probe validation layer should use these evaluator APIs rather than
  Python substitution/evaluation.
- Directly tested `Expression.evaluator` and `Expression.evaluator_multiple` in
  the managed venv. Both return NumPy arrays; without NumPy installed the
  Symbolica evaluator path aborts before Python can raise a normal exception.
- Matchete `DefineField` stores `Charges`, `Indices`, and `Chiral` as first-class
  field options. The pychete representation now persists the first simple slice
  of that metadata through Symbolica symbol data and JSON checkpoints.
- The first committed fixture asset surfaced that restoring group symbols is not
  enough: the Python `Theory.groups` registry must also be restored before later
  code can build charges or inspect gauge-field metadata.
- Rescanned the Symbolica Python stub sections for symbol `data`, tags,
  `Expression.get_symbol_data`, and `Expression.get_tags`. Coupling metadata
  now stays on Symbolica symbols through the same structural data path as field
  mass/charge metadata.
- Matchete `DefineCoupling` stores `Indices`, `EFTOrder`, `SelfConjugate`,
  `Symmetries`, `DiagonalCoupling`, `ThermalPowerCounting`, and `Unitary`.
  It also requires unitary couplings to be square matrix couplings with
  `EFTOrder -> 0`; pychete now enforces the matching structural checks.
- Symbolica refuses to redefine an already-created symbol with different custom
  data. The fixture loader therefore normalizes older coupling manifest data to
  include the current default keys before registering theory symbols, preserving
  the structural guarantee that expressions parse only after the symbol registry
  has the intended data.
- The remaining default Matchete integration models all use `ParentModel["SM"]`.
  pychete now owns copies of those child model files and the SM parent input,
  but the loader still needs an explicit parent-model expansion path and CG
  function handling before these inputs can become full committed model-state
  fixtures.
- Parent-model expansion now works for metadata-only loading of the default
  targets. Full Lagrangian parsing for the SM-backed targets still requires the
  broader Mathematica expression subset around local CG helper definitions,
  implicit multiplication, noncommutative chains, and charge-conjugation
  expressions, or a Wolfram-generated pychete-owned fixture path for those
  expressions.
- Child-Lagrangian parsing now works for the three SM-backed default targets
  using parent metadata. The committed expressions intentionally do not include
  the SM parent Lagrangian yet; S1/S3 local CG helper calls are preserved as
  registered external Symbolica heads until they are routed through the planned
  spenso/idenso CG adapter layer.

## Test Status

- `dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py`
  passed: 3 passed.
- `dependencies/.venv/bin/python -m mypy` passed: no issues found in 18 source
  files.
- `dependencies/.venv/bin/python -m pytest tests` passed: 58 passed, 1 skipped.
  The skip is the existing GammaLoop API import check because GammaLoop was not
  requested in the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed: 10 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the `MatchingResult`
  slice: no issues found in 18 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  `MatchingResult` slice: 60 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py` passed: 3 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the numeric-probe slice:
  no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the numeric-probe
  slice: 63 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_public_api.py` passed after the field metadata
  slice: 16 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the field metadata slice:
  no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the field
  metadata slice: 64 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/definitions/test_theory_definitions.py` passed after the committed
  fixture slice: 14 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the committed fixture
  slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the committed
  fixture slice: 65 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py` passed after the coupling
  metadata slice: 16 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the coupling metadata
  slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the coupling
  metadata slice: 69 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py` passed after the
  default model asset slice: 6 passed.
- `dependencies/.venv/bin/python -m pytest tests` passed after the default
  model asset slice: 69 passed, 1 skipped. The skip is the existing GammaLoop
  API import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/models/test_model_loaders.py
  tests/integration/validation/test_validation_fixtures.py` passed after the
  parent-model metadata fixture slice: 14 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the parent-model metadata
  fixture slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  parent-model metadata fixture slice: 72 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in the
  current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/models/test_model_loaders.py
  tests/integration/validation/test_validation_fixtures.py` passed after the
  child-Lagrangian fixture slice: 15 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the child-Lagrangian
  fixture slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  child-Lagrangian fixture slice: 73 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.

## Remaining Work

- Add committed validation fixture assets for the four default Matchete matching
  integration models. Model input assets and model-definition fixtures now exist
  for all four default targets and the SM parent; actual one-loop
  matching-result fixtures are still pending.
- Add full SM/CG Lagrangian expression parsing to the model loader or replace
  direct source parsing for those expressions with generated pychete-owned state
  fixtures.
- Convert raw Matchete snapshots into pychete-owned fixture JSON that pytest can
  consume without Mathematica.
- Add the first real one-loop matching-result fixture asset using the
  `MatchingResult` fixture schema.
- Use `evaluator_probe_equal` in fixture comparison tests when canonical
  equality is insufficient.
- Extend field metadata further for background fields, Goldstones, ghosts,
  representation reality, and SMEFT basis data.
- Extend theory metadata further for background fields, Goldstones, ghosts,
  representation reality, global groups, CG tensors, and SMEFT basis data.
- Extend the matching engine toward one-loop matching.
