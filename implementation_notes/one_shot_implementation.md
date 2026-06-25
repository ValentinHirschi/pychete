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
  Smoke probes and single-test runs are allowed while exploring, but a slice
  should not keep bouncing through the whole suite while still being designed.
- Before starting each one-shot slice, review the remaining implementation
  frontier and choose a larger coherent feature family that can be completed as
  a unit. If focused tests expose a design issue, refactor within that slice
  and then rerun the narrowest relevant gate; reserve full-suite validation for
  larger green milestones.
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
- Last pushed green milestone:
  `9cd2c6b Complete SMEFT Warsaw operator metadata coverage`.
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
  - EFT truncation and using the now-complete Wilson operator metadata in the
    default SMEFT-oriented matching pipeline;
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

## Current Slice: Wilson Operator Projection Metadata

- The next matching-condition frontier needs structural SMEFT operator
  metadata rather than another loader-specific parser branch. This slice stores
  optional Wilson/operator monomials directly on the theory-owned external
  Symbolica label, so the data survives checkpoint serialization before any
  later expression parsing can create an untyped symbol.
- Implemented:
  - added `operator` metadata to `define_external(...)` and
    `define_wilson_coefficient(...)`;
  - exposed it through `ExternalDefinition.operator_expr`;
  - preserved it in theory JSON and the Symbolica symbol manifest;
  - extended `MatchingConditionTarget` with `projection_expression`, so Wilson
    targets with stored operator metadata project with native
    `Expression.coefficient(operator)`;
  - added focused definition/checkpoint and matching-projection regressions.
- Targeted validation for this slice:
  - exact metadata tests:
    `pytest tests/unit/definitions/test_theory_definitions.py::test_wilson_coefficients_store_basis_and_matching_target_metadata tests/unit/definitions/test_theory_definitions.py::test_matching_condition_targets_expose_symbolica_role_metadata -q`:
    2 passed.
  - exact projection tests:
    `pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_conditions_with_symbolica_coefficients tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_wilson_conditions_from_operator_metadata -q`:
    2 passed.
  - grouped metadata gate:
    `pytest -m definitions tests/unit/definitions -q`: 59 passed.
  - `python -m mypy`: success, no issues in 32 source files.
  - `git diff --check`: clean.

## Current Slice: SMEFT Warsaw Operator Registry

- User reiterated that larger implementation slices should be planned and
  finished before paying broad validation costs. This slice therefore keeps to
  a coherent operator-metadata feature family and validates only the affected
  definition, converter, fixture, public API, typing, and diff-hygiene paths.
- Added `pychete.smeft` as the pychete-owned registry for SMEFT Warsaw operator
  metadata. It currently builds pychete-native Symbolica monomials for:
  `cG`, `cGt`, `cW`, `cWt`, `cH`, `cHBox`, `cHD`, `cHG`, `cHGt`, `cHW`,
  `cHWt`, `cHB`, `cHBt`, `cHWB`, `cHWtB`, `cHl1`, `cHl3`, `cHe`, `cHq1`,
  `cHq3`, `cHu`, `cHd`, `ceH`, `cuH`, and `cdH`.
- Added public helpers through `pychete.api` and package root:
  `SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES`, `smeft_warsaw_operator_names`,
  `smeft_warsaw_operator`, and `define_smeft_wilson_coefficient`.
- Updated the previous-result fixture converter so left-hand-side SMEFT Wilson
  targets are predeclared through the registry. Known Warsaw targets now carry
  operator metadata in their Symbolica symbol data; unsupported targets such
  as `ceW` remain registered as Wilson coefficients with `operator=None`.
- Regenerated the default validation fixtures and deliberately restored the
  previously committed `state.expressions` payloads after detecting unrelated
  expression text drift around barred indices in the round-trip conversion
  path. The final fixture diff is scoped to theory external/symbol metadata:
  matching results and stored reference expressions are unchanged.
- Fixture sanity counts after the scoped update:
  - `E_VLL`: 64 Wilson coefficients, 25 with operator metadata.
  - `S1S3LQs`: 64 Wilson coefficients, 25 with operator metadata.
  - `Singlet_Scalar_Extension`: 64 Wilson coefficients, 25 with operator
    metadata.
  - `VLF_toy_model`: 0 Wilson coefficients.
- Targeted validation for this slice:
  - `pytest tests/unit/definitions/test_theory_definitions.py::test_smeft_warsaw_operator_builders_attach_wilson_operator_metadata tests/unit/definitions/test_public_api.py tests/unit/loaders/test_matchete_previous_results_converter.py::test_previous_result_converter_predeclares_lhs_wilson_targets_only tests/integration/validation/test_validation_fixtures.py::test_committed_matching_fixtures_store_smeft_wilson_metadata -q`:
    8 passed.
  - `python -m mypy`: success, no issues in 33 source files.

## Current Slice: Complete Warsaw Operator Metadata Coverage

- Expanded `pychete.smeft` from the initial 25-operator subset to the complete
  64-name `SMEFTWilsonCoefficients[]` set used by Matchete's
  `SMEFT_Warsaw.m` reference model.
- Added a central `Sigma` Symbolica head to the reusable `SymbolStore` so
  dipole and tensor four-fermion operators use pychete-native Dirac primitives
  rather than ad hoc external symbols.
- Added pychete-native builders for:
  - the Weinberg-like `cllHH` operator;
  - all electroweak/QCD dipoles: `ceW`, `ceB`, `cuG`, `cuW`, `cuB`, `cdG`,
    `cdW`, `cdB`;
  - `cHud`;
  - vector-current four-fermion operators including singlet, triplet, and
    colour-octet variants;
  - scalar/tensor four-fermion operators `cledq`, `cquqd1`, `cquqd8`,
    `clequ1`, and `clequ3`;
  - baryon-number-violating operators `cduq`, `cqqu`, `cqqq`, and `cduu`.
- The builders are expression-construction metadata only; matching-condition
  projection continues to use native Symbolica coefficient extraction through
  `MatchingConditionTarget.projection_expression`.
- Regenerated the default matching fixtures through the converter, then
  restored previously committed `state.expressions` payloads to avoid
  unrelated round-trip text drift. Matching results and stored reference
  expressions remain unchanged.
- Fixture sanity counts after the scoped update:
  - `E_VLL`: 64 Wilson coefficients, 64 with operator metadata.
  - `S1S3LQs`: 64 Wilson coefficients, 64 with operator metadata.
  - `Singlet_Scalar_Extension`: 64 Wilson coefficients, 64 with operator
    metadata.
  - `VLF_toy_model`: 0 Wilson coefficients.
- Targeted validation for this slice:
  - `pytest tests/unit/definitions/test_theory_definitions.py::test_smeft_warsaw_operator_builders_attach_wilson_operator_metadata tests/unit/definitions/test_public_api.py tests/unit/loaders/test_matchete_previous_results_converter.py::test_previous_result_converter_predeclares_lhs_wilson_targets_only tests/integration/validation/test_validation_fixtures.py::test_committed_matching_fixtures_store_smeft_wilson_metadata -q`:
    8 passed.
  - `python -m mypy`: success, no issues in 33 source files.

## Current Slice: Registered Wilson Projection Selector

- User emphasized again that the one-shot work should batch larger coherent
  implementation chunks and avoid whole-suite churn. This slice therefore
  closes the next Wilson metadata projection family by letting matching APIs
  consume the complete theory-owned Wilson registry directly, then validates
  only selector/projection/public-API/type paths.
- Added `registered_wilson_matching_condition_targets(theory, ...)` as a public
  helper. It constructs matching-condition target expressions from
  `ExternalDefinition` metadata: external Symbolica label, registered index
  expressions, EFT order, Wilson kind, basis name, and stored operator
  monomial. By default it returns only Wilson coefficients with operator
  metadata, because those can be projected from the EFT Lagrangian by native
  Symbolica `Expression.coefficient(...)`.
- Extended `MatchingResult.project_matching_conditions(...)`,
  `MatchingResult.with_projected_matching_conditions(...)`, `match_one_loop`,
  and `Theory.match(...)` to accept the selector string
  `registered_wilsons`. This projects all registered Wilson coefficients with
  stored operator metadata without requiring fixture-derived target maps.
- The projection implementation remains Symbolica-first: selector resolution
  only builds target expressions; coefficient extraction still uses
  `MatchingConditionTarget.projection_expression` and
  `Expression.coefficient(...)`.
- Added regressions covering:
  - registered Wilson selector projection in a direct `Theory.match(...)`
    heavy-scalar integration test;
  - basis filtering and `include_without_operator=True` behavior for the
    public helper;
  - default validation fixtures exposing exactly the same complete Wilson
    target set through the registered selector as through stored matching
    targets.
- Targeted validation for this slice:
  - frontier smoke before the selector edit:
    `pytest tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_projected_matching_condition_frontier_without_mathematica -q`:
    1 passed in 50.94s.
  - exact selector/API gate:
    `pytest tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_can_project_requested_matching_conditions tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_wilson_conditions_from_operator_metadata tests/integration/validation/test_validation_fixtures.py::test_committed_matching_fixtures_store_smeft_wilson_metadata tests/unit/definitions/test_public_api.py -q`:
    8 passed.
  - `python -m mypy`: success, no issues in 33 source files.
  - `git diff --check`: clean.

## Current Slice: Registered Wilson Metadata In Model Fixtures

- The previous selector slice exposed a structural gap: matching fixtures had
  the full 64 SMEFT Wilson externals with operator metadata, but the paired
  model fixtures used to build candidate previews did not. Consequently,
  projected validation reports still had to fall back to reference-owned
  Wilson targets.
- A generic "define all SMEFT Wilsons" enrichment is not safe for committed
  fixtures because Symbolica rejects reusing the same namespaced symbol with
  different symbol data. The model fixture and matching fixture must carry
  identical Wilson symbol data, including flavor-index labels and operator
  monomial strings.
- Updated `convert_matchete_previous_results.py` with
  `--update-model-fixture-wilson-metadata`, which writes the exact Wilson
  target metadata parsed from Matchete matching-condition left-hand sides back
  into the paired model fixture when regenerating previous-result fixtures.
- Enriched the committed `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`
  model fixtures with exact external symbol metadata copied from their matching
  fixtures. Each now carries 64 Wilson coefficients with operator metadata.
  `VLF_toy_model` remains unchanged because its reference has no matching
  conditions.
- Changed validation projection target construction so
  `one_loop_preview_gap_report(..., project_reference_matching_conditions=True)`
  prefers theory-registered Wilson targets, matches indexed Wilsons by
  external symbol data name when canonical condition names use different dummy
  labels, and only falls back to reference Wilson targets when no registered
  candidate-theory target exists. Non-Wilson matching targets still come from
  the reference result.
- `MatchingFixtureGapReport` now records projection target source counts and
  names: registered Wilson targets, reference non-Wilson targets, and reference
  Wilson fallbacks.
- Targeted validation for this slice:
  - focused structural projection regression:
    `pytest tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_projects_registered_wilsons_before_reference_targets -q`:
    1 passed.
  - affected projection frontier:
    `pytest tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_projects_registered_wilsons_before_reference_targets tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_can_project_conditions_through_public_match_api tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_projected_matching_condition_frontier_without_mathematica -q`:
    3 passed.
  - fixture/converter metadata gate:
    `pytest tests/integration/validation/test_validation_fixtures.py::test_committed_model_fixtures_store_matching_smeft_wilson_metadata tests/integration/validation/test_validation_fixtures.py::test_committed_matching_fixtures_store_smeft_wilson_metadata tests/unit/loaders/test_matchete_previous_results_converter.py -q`:
    3 passed.
  - `python -m mypy`: success, no issues in 33 source files.

## Current Slice: Power-Type Internal Integral Results

- Reviewed the next one-loop backend frontier before running broad tests. The
  internal scalar one-loop backend already supports single-scale, massless, and
  mixed-mass analytic topologies through Symbolica replacement/coefficient
  primitives, while the intentionally single-scale helper and native vakint
  evaluation paths still reject unsupported topologies.
- Added `OneLoopSetup.power_type_internal_matching_result(...)`, mirroring the
  existing interaction-only internal result path for the full power-type
  aggregate. It keeps raw vakint topology sums, internally evaluated sums,
  pole parts, finite parts, named supertraces, and explicit metadata showing
  `integral_backend="pychete_internal"`.
- Added `OneLoopSetup.power_type_internal_minimal_subtraction_result(...)` so
  full power-type previews can subtract poles through the internal analytic
  backend instead of requiring native vakint evaluation. This is important for
  mixed heavy/light mass topologies where vakint's analytic single-scale
  evaluator must not be used.
- Updated docstrings for internal power-type and interaction-power evaluation
  to state that pychete's internal one-loop scalar backend covers single-scale,
  massless, and mixed-mass analytic cases after optional vakint tensor
  reduction.
- Targeted validation so far:
  - exact mixed-mass power-type internal result regression:
    `pytest tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_propagator_plan_recovers_masses_from_symbol_data -q`:
    1 passed.
  - matching marker gate:
    `pytest -m matching tests/integration/matching -q`: 65 passed.
  - `python -m mypy`: success, no issues in 33 source files.
  - `git diff --check`: clean.

## Current Slice: On-Shell Reduction Hook

- The current one-loop preview results still mark `on_shell_reduced=False`.
  This slice adds a narrow on-shell reduction hook without pretending the full
  Matchete EOM reduction pipeline is complete.
- Added optional `OneLoopMatchOptions.on_shell_replacements` plus
  `on_shell_replacement_repeat`. Replacements may be exact expression mappings
  or native Symbolica `Replacement` objects. They are applied with
  `Expression.replace_multiple(...)`, preserving the Symbolica-first rule and
  allowing future EOM rules to use native pattern restrictions.
- Added `MatchingResult.with_on_shell_reduction(...)`, which preserves the
  off-shell EFT Lagrangian, stores before/after on-shell stages in
  `supertraces`, updates on-shell metadata, and lets subsequent matching
  condition projection read the reduced `on_shell_eft_lagrangian`.
- Wired `match_one_loop(...)` so optional on-shell replacements run after
  backend evaluation/normalization and before matching-condition projection.
- Kept the `OnShellReplacementInput` typing alias local to
  `matching_options`; package-root exports continue to contain only
  docstring-bearing public objects.
- Targeted validation so far:
  - exact result-level and public `Theory.match(..., loop_order=1)` regressions:
    `pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_applies_on_shell_replacements_with_symbolica_rules tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_applies_on_shell_reduction_before_condition_projection -q`:
    2 passed.
  - combined changed-surface gate:
    `pytest tests/integration/matching tests/integration/validation/test_numeric_probes.py tests/unit/definitions/test_public_api.py -q`:
    93 passed.
  - `python -m mypy`: success, no issues in 33 source files.
  - `git diff --check`: clean.

## Current Slice: EOM-Derived On-Shell Replacement Rules

- Continued the on-shell-reduction feature family with a structural EOM rule
  builder instead of making users hand-write every replacement. The helper is
  intentionally narrow: it isolates one requested target from a linear
  Euler-Lagrange equation and returns a native Symbolica `Replacement`.
- Added `eom_replacement_rule(...)` in `functional.py` and exposed it as
  `Theory.eom_replacement_rule(...)`. The implementation derives the EOM with
  the existing Symbolica variation path, isolates `solve_for` using native
  `Expression.coefficient(...)`, checks that the residual no longer contains
  the solved target via `Expression.contains(...)`, and returns a
  `Replacement` usable directly by `MatchingResult.with_on_shell_reduction(...)`
  and `OneLoopMatchOptions.on_shell_replacements`.
- This keeps the symbolic work in Symbolica primitives: no Python equation
  solver, tree walker, or atom-type dispatch was added. More general future
  EOM reduction can build on this by generating pattern-restricted
  `solve_for` targets and passing the resulting `Replacement` objects through
  the existing `replace_multiple` hook.
- Added regressions covering:
  - isolation of a scalar box term in a phi-four EOM with a source term;
  - rejection of absent targets with a clear `ValueError`;
  - applying a theory-generated EOM replacement to a `MatchingResult` before
    Symbolica coefficient projection of matching conditions;
  - public method docstring coverage for `Theory.eom_replacement_rule`.
- Targeted validation for this slice:
  - `pytest tests/unit/functional/test_scalar_eom.py tests/integration/validation/test_numeric_probes.py::test_matching_result_applies_theory_eom_replacement_before_projection tests/unit/definitions/test_public_api.py -q`:
    19 passed.
  - `python -m mypy`: success, no issues in 33 source files.
