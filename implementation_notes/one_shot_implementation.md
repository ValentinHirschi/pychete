# One-Shot Port Implementation Notes

## Active Plan And Guidelines

- Continue the one-shot Matchete-style one-loop matching port on branch
  `one-shot-port`, targeting the default SMEFT-oriented Matchete models first:
  `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Normal pychete runtime code and pytest must remain Mathematica- and
  Matchete-independent. Optional scripts under `scripts/` and
  `helper_mathematica_scripts/` may use Wolfram/Matchete only to generate
  committed pychete-owned fixtures.
- Use Symbolica as the canonical expression engine. Before adding symbolic
  algorithms, check native Symbolica APIs: patterns, `match`, `matches`,
  `replace`, `replace_multiple`, `replace_wildcards`, `series`,
  `coefficient`, `coefficient_list`, `collect`, `derivative`, `Transformer`,
  polynomial/rational-polynomial tools, and evaluators.
- Use idenso for gamma, colour, metric, and abstract-index algebra; spenso for
  tensor-network and CG/tensor contractions; vakint for topology-independent
  tensor reduction and as an optional single-scale analytic cross-check.
  pychete owns the Matchete-style one-loop vacuum-integral evaluator for
  single-scale, zero-mass, and mixed-mass analytic cases.
- Keep local symbol metadata in Symbolica tags/data through `Theory.symbol`.
  Use enum/constant metadata internally; normalize strings only at external
  boundaries.
- Keep free-Lagrangian conventions explicit with `FreeLagConvention`:
  `PYCHETE` is the default canonical pychete convention with expanded
  scalarized Abelian currents, while `MATCHETE` is for `.m` loader
  compatibility with implicit covariant derivatives and `1/g^2` gauge
  normalization.
- Preserve public API discoverability through `pychete.api` and package root
  `pychete`. Public objects and user-facing methods need useful docstrings and
  Jupyter-friendly `_repr_html_` / `_repr_latex_` where relevant.
- Use larger implementation slices with focused tests while building, then
  grouped targeted gates (`definitions`, `models`, `matching`, `backend`,
  `validation`, `not slow`) before green milestone commits. Avoid running the
  full/slow suite after every small edit. Plan and implement complete feature
  families first, then run the smallest marker group that exercises the slice.
- Commit and push only coherent green milestones to `origin/one-shot-port`.
  Keep these notes current with status, validation, backend discoveries, and
  remaining gaps.

## History Files

- `implementation_notes/one_shot_implementation_part_A.md` keeps the first
  long implementation log unchanged.
- `implementation_notes/one_shot_implementation_part_B.md` keeps the second
  long implementation log unchanged. It ends at commit `e54615a` and records
  the vector/gauge, Abelian-current, charged-fermion, and explicit
  free-Lagrangian-convention slices.

## Summary Of Part B Status

- Test batching was added so implementation can use targeted marker groups and
  avoid frequent full slow-suite runs.
- Vector/gauge free-kinetic handling was extended:
  - `FieldStrength(label, ...)^2` and cross-label
    `FieldStrength(label_a, ...) * FieldStrength(label_b, ...)` are recognized
    as vector inverse-propagator data;
  - vector modes can be discovered from registered `FieldStrength(...)` atoms;
  - massive vectors now contribute scalarized mass terms and denominator
    metadata;
  - field-dependent and off-diagonal kinetic terms remain in interaction
    blocks after free-inverse subtraction.
- Abelian charge-aware `Theory.free_lag(...)` support was added for pychete's
  canonical convention:
  - gauged U(1) charge expressions resolve through Symbolica group symbol data;
  - complex scalar and fermion free terms include scalarized Abelian current
    interactions;
  - global U(1) charges remain metadata-only;
  - charged self-conjugate scalars fail explicitly in canonical `free_lag`.
- Fermion free-inverse subtraction now handles field-dependent gamma-current
  terms by recognizing the registered slash/mass part after Symbolica
  replacement-rule removal of tagged fields. Abelian gauge currents stay in
  `interaction_entry(...)` instead of being folded into the mass slot.
- `FreeLagConvention` was added and exported:
  - `FreeLagConvention.PYCHETE` is the default canonical pychete convention;
  - `FreeLagConvention.MATCHETE` preserves Matchete loader semantics for
    `FreeLag[...]`, including implicit covariant derivatives and `1/g^2` gauge
    kinetic normalization.
- The Mathematica model loader now uses `FreeLagConvention.MATCHETE` for
  parsed `FreeLag[...]`. VLF Python and Mathematica assets intentionally share
  theory metadata but use distinct free-Lagrangian expression conventions.
- Last pushed green milestone: `3bf2ccc Improve loader parity and targeted
  test grouping`.
- Last broader non-slow gate at that milestone:
  `263 passed, 1 skipped, 50 deselected`; the skip was the expected GammaLoop
  manifest skip for a local dependency build without GammaLoop requested.

## Current Remaining Work

- Recheck the default fixture gap frontier after the vector/gauge convention
  work using targeted slow validation only when the next slice explicitly
  touches those fixtures.
- Continue extending one-loop matching toward Matchete parity:
  - non-Abelian covariant derivatives and generator/CG handling through
    idenso/spenso-backed paths;
  - broader tensor and Dirac/NCM simplification in generated supertraces;
  - EFT truncation and Wilson-condition projection improvements for the
    default SMEFT-oriented fixtures;
  - stronger canonical/numeric-probe acceptance for remaining Matchete
    matching-condition gaps.
- Keep implementation notes manageable. When this live file grows large again,
  move it unchanged to `one_shot_implementation_part_C.md` and replace it with
  a compact updated status note.

## Current Slice: Test Grouping And VLF Loader Parity

- User requested fewer whole-suite runs and larger, better-planned
  implementation slices. The workflow is now to batch coherent feature work,
  use smoke probes during exploration, run focused marker groups for the slice,
  and reserve broad `not slow` or slow validation gates for coherent green
  milestones.
- Added pytest marker groups for `definitions`, `dependencies`, `eft`,
  `functional`, `integration`, `loaders`, `models`, `typing`, and `unit`, in
  addition to the existing `backend`, `matching`, `validation`, and `slow`
  groups.
- While probing the next model-loader parity slice, the direct supported-subset
  loader for `assets/models/VLF_toy_model.m` still differed from the committed
  Matchete-exported model fixture after the `FreeLagConvention.MATCHETE`
  change. The remaining differences were:
  - `PlusHc[...]` expanded to an opaque `Bar(body)` instead of a supported
    hermitian conjugate chain;
  - parsed Mathematica `NCM[...]` operands and Matchete-convention fermion
    kinetic terms used bare `PR`/`PL`/`Gamma` instead of Matchete fixture-style
    `DiracProduct(...)` wrappers.
- Implemented a public `hermitian_conjugate(...)` helper that reuses pychete's
  supported field/coupling metadata-aware conjugation rules, updated
  `PlusHc[...]` parsing to call it, and normalized only the Mathematica loader
  / Matchete free-Lagrangian convention paths to fixture-style
  `DiracProduct(...)` wrappers.
- Added a regression test that the direct VLF Mathematica asset matches the
  committed Matchete-exported model fixture after deterministic dummy-index
  relabeling.
- Extended the supported-subset Mathematica loader so module-local symbols
  used as field, coupling, and CG-tensor indices are coerced to
  `Index(label, representation)` using the registered Symbolica metadata for
  the field/coupling/CG tensor. This avoids leaking local names like `i`, `p`,
  `J`, and `alpha` as generic external functions in parsed parent-model child
  Lagrangians.
- Planned targeted validation for this slice:
  - `pytest -m functional tests/unit/functional`: 11 passed.
  - `pytest -m definitions tests/unit/definitions`: 59 passed.
  - `pytest -m loaders tests/unit/loaders tests/integration/models`: 25 passed.
  - `pytest --collect-only -q -m "loaders or models or functional or definitions"`
    collected 95 selected tests and deselected 221.
  - `python -m mypy`: success, no issues in 32 source files.
  - `git diff --check`: clean.

## Current Slice: Opt-In Parent Lagrangian Loading

- The direct supported-subset Mathematica loader can parse `assets/models/SM.m`
  including its Lagrangian after the recent `PlusHc`, `DiracProduct`, and
  module-local index improvements.
- Added an explicit `include_parent_lagrangian=True` option to
  `load_matchete_model(...)`. Parent-model declarations still always load
  metadata, and the default remains to skip parent Lagrangian expressions so
  the direct loader stays a conservative supported-subset loader. When the
  option is enabled, supported parent Lagrangians are parsed first and stored
  as `expressions["parent_lagrangian"]`; `expressions["lagrangian"]` contains
  parent plus child terms.
- Added regression coverage for `Singlet_Scalar_Extension`, `E_VLL`, and
  `S1S3LQs`, confirming the opt-in path includes SM parent fields and the
  child heavy fields while preserving registered expression validation.
- Targeted validation so far:
  - `pytest -m loaders tests/unit/loaders tests/integration/models`: 26 passed.
