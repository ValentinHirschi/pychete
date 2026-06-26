# One-Shot Port Implementation Notes

## Active Plan And Guidelines

- Continue the one-shot Matchete-style one-loop matching port on branch
  `one-shot-port`, targeting the default SMEFT-oriented Matchete models first:
  `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Runtime pychete and pytest must remain Mathematica- and Matchete-independent.
  Optional Wolfram scripts may only generate committed pychete-owned fixtures.
- Use Symbolica as the canonical symbolic engine. Before implementing symbolic
  manipulation, check native Symbolica patterns, `match`, `matches`, replacement
  rules, `replace_multiple`, `series`, `coefficient`, `coefficient_list`,
  `collect`, `derivative`, `Transformer`, polynomial/rational tools,
  `canonize_tensors`, and evaluators. Avoid Python tree walkers and handwritten
  simplifiers unless native APIs are insufficient for that exact operation.
- Use idenso for gamma, colour, metric, and abstract-index algebra; spenso for
  tensor-network and CG/tensor contractions; vakint for topology-independent
  tensor reduction and as an optional single-scale analytic cross-check.
  pychete owns the Matchete-style analytic one-loop vacuum-integral evaluator
  for single-scale, zero-mass, and mixed-mass cases.
- Keep symbol metadata in Symbolica tags/data through `Theory.symbol`. Use
  enum/constant metadata internally; normalize strings only at external
  boundaries.
- Public API discoverability remains through `pychete.api` and package root
  `pychete`. Public objects and user-facing methods need docstrings and
  Jupyter-friendly repr methods where relevant.
- Use larger coherent implementation slices. Run focused tests during the
  slice, grouped targeted gates before a green milestone commit, and full/slow
  gates only when the milestone justifies it.
- Keep performance in view for heavy symbolic stages: avoid mandatory global
  expansion when native factored coefficient extraction is enough, expose
  controls for expensive simplifier/projection stages, and prefer algorithms
  scaling with selected targets or backend operations.
- Commit and push only coherent green milestones to `origin/one-shot-port`.
  Keep this live file current; when it grows large again, move it unchanged to
  the next `one_shot_implementation_part_*.md` file and rewrite a compact live
  summary.

## History Files

- `implementation_notes/one_shot_implementation_part_A.md` keeps the first long
  implementation log unchanged.
- `implementation_notes/one_shot_implementation_part_B.md` records work through
  commit `e54615a`, including vector/gauge, Abelian-current,
  charged-fermion, and explicit free-Lagrangian-convention slices.
- `implementation_notes/one_shot_implementation_part_C.md` records Wilson
  projection, complete SMEFT Wilson metadata, internal integral result,
  on-shell/EOM reduction, final EFT truncation, and opt-in Abelian
  covariant-derivative expansion slices.
- `implementation_notes/one_shot_implementation_part_D.md` records
  non-Abelian infrastructure, colour/idenso/spenso bridges, vakint namespace
  decoding, projection canonicalization, heavy-scalar dummy freshening,
  derivative/IBP projection improvements, covariant-commutator
  emission/lowering, CDE expansion planning, scalar CDE NCM projection, and
  cyclic closed-trace OpenCD action through commit `36755c2`.
- `implementation_notes/one_shot_implementation_part_E.md` preserves the long
  implementation log through commit `c3cc55c`, including hybrid CDE source
  composition, vakint tensor/CD decode, field-strength metric simplification,
  native colour-chain decode, heavy-substituted projection, coupling
  mass-dimension filtering, inferred Matchete coupling dimensions, and the
  latest Symbolica tensor-index canonicalization reminder.

## Current Status

- Current pushed milestone: `c3cc55c Infer Matchete coupling mass dimensions`.
- The latest milestone added public
  `infer_coupling_mass_dimensions(theory, lagrangian)`, refactored the optional
  Matchete model-state converter to infer missing dimensions in a temporary
  probe theory before final symbol creation, and refreshed E_VLL/S1S3LQs model
  and matching fixtures with coupling `mass_dimension` metadata.
- The converter path now preserves the structural invariant that Symbolica
  symbol data is attached before fixture expressions are parsed. Do not mutate
  coupling symbol data after final symbols exist.
- Projection and comparison paths already use Symbolica
  `Expression.canonize_tensors(...)` through `tensor_index_specs(...)` and
  `canonize_tensor_indices(...)`, preserving the canonical expression,
  external-index list, and ordered dummy-index list for alpha-equivalent
  contractions.
- `MatchingExpressionComparison` now keeps the per-term
  `TensorCanonization` payloads returned by Symbolica when comparison used
  tensor-index canonicalization, so diagnostics can show which canonical
  external/dummy indices were compared.
- Public one-loop CDE requests use a hybrid source:
  selected CDE supertrace families replace only the selected interaction-power
  families while unselected interaction-power contributions remain in the
  source.
- Selected CDE vakint aggregates now stage native canonicalization,
  tensor-reduction, and evaluation per generated CDE term before summing
  decoded outputs. Raw diagnostic sums remain raw sums.
- Vakint namespace decode now maps native metric/CG/CD/list wrappers back to
  pychete-facing heads where the registered theory metadata makes that
  unambiguous.
- Vakint loop-momentum numerator lowering now maps full pychete `Index(...)`
  arguments in `LoopMomentum(index)` to flat backend-safe symbols before native
  vakint/FORM tensor reduction, then decodes returned metric wrappers back to
  the original pychete index metadata.
- Python-side construction of native vakint wrapper symbols is attribute-safe
  before native import; in particular `vakint::g` is created symmetric so later
  native vakint initialization does not abort on symbol redefinition.
- Field-strength metric cleanup removes metric-traced antisymmetric
  field-strength terms before public projection.
- Native colour-wrapper decoding is bounded and decode-only for public
  generated results; full idenso colour simplification remains available on
  controlled kernels/subexpressions.
- Heavy-scalar substitution and target-local projection now recover the
  focused Singlet-like `A*kappa^2*muphi` contribution to `cH`, but full Singlet
  matching parity is still blocked by basis/on-shell reductions and broader
  source coverage.

## Latest Validation Evidence

- Focused dimension inference/converter/API/tensor-canonicalization gate:
  `pytest tests/unit/eft/test_eft_counting.py tests/unit/loaders/test_matchete_model_state_converter.py tests/unit/definitions/test_public_api.py tests/integration/validation/test_numeric_probes.py -k "canoniz or mass_dimension or truncates_projected_coefficients" -q`
  passed with 8 tests and 60 deselected.
- Fixture metadata/load gate:
  `pytest tests/integration/validation/test_validation_fixtures.py -k "metadata or default_model_fixtures_load or matching_fixture or model_fixture" -q`
  passed with 5 tests and 32 deselected.
- `python -m mypy` passed.
- `git diff --check` passed before commit `c3cc55c`.
- Post-`c3cc55c` default projected matching-condition frontier test:
  `pytest tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_projected_matching_condition_frontier_without_mathematica -q`
  passed.
- Focused Symbolica tensor-index canonicalization diagnostics:
  `pytest tests/integration/validation/test_numeric_probes.py -k "canoniz" -q`
  passed with 5 tests and 47 deselected.
- Full numeric-probe comparison/projection file:
  `pytest tests/integration/validation/test_numeric_probes.py -q` passed with
  52 tests.
- `python -m mypy` passed after the comparison-payload slice.
- `git diff --check` passed after the comparison-payload slice.
- Vakint backend safe-loop-index gate:
  `pytest tests/unit/backends/test_vakint_backend.py -q` passed with 33 tests.
- Adjacent vacuum-integral backend gate:
  `pytest tests/unit/backends/test_vacuum_integrals_backend.py -q` passed with
  37 tests.
- Focused CDE generated-integral safe-index regression:
  `pytest tests/integration/matching/test_fluctuation_operator.py::test_interaction_bosonic_cde_expansion_maps_selected_trace_to_kernel_and_vakint -q`
  passed.
- Focused CDE tensor-reduction/public-output gate:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k "vakint_tensors or order_four_covariant_derivatives or metric_traced_field_strengths" -q`
  passed with 3 tests and 67 deselected.
- A tiny native vakint tensor-reduction smoke with
  `LoopMomentum(Index(mu))*LoopMomentum(Index(nu))` now completes without the
  previous Rust/FORM symbol-redefinition abort and decodes the returned metric
  to `Metric(Index(mu, Lorentz), Index(nu, Lorentz))`.
- CDE/vakint staging regression:
  `pytest tests/integration/matching/test_fluctuation_operator.py::test_interaction_bosonic_cde_expansion_maps_selected_trace_to_kernel_and_vakint -q`
  passed and verifies a three-entry generated CDE plan calls the native tensor
  reducer once per generated term.
- Native vakint import-order reproducer:
  `pytest tests/integration/matching/test_fluctuation_operator.py::test_interaction_bosonic_cde_expansion_maps_selected_trace_to_kernel_and_vakint tests/integration/matching/test_fluctuation_operator.py::test_bosonic_cde_internal_tensor_reduction_decodes_native_vakint_tensors -q -s`
  passed after making `vakint::g` Python construction symmetric.
- Broader non-slow bosonic CDE gate:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k "bosonic_cde and not heavy_solution" -q`
  passed with 11 tests and 59 deselected.
- Backend gate after staging:
  `pytest tests/unit/backends/test_vakint_backend.py tests/unit/backends/test_vacuum_integrals_backend.py -q`
  passed with 71 tests.
- `python -m mypy` passed after the CDE/vakint staging slice.
- `git diff --check` passed after the CDE/vakint staging slice.

## Current Validation Frontier

- Post-`c3cc55c` focused projected-condition probe for default models used
  `max_trace_order=1`, internal minimal subtraction, public `Theory.match(...)`,
  and registered Wilson projection:
  - `Singlet_Scalar_Extension`: 72/72 projected targets, 42 accepted, 30
    different; 39/64 Wilson targets accepted.
  - `E_VLL`: 72/72 projected targets, 27 accepted, 45 different; 25/64 Wilson
    targets accepted.
  - `S1S3LQs`: 72/72 projected targets, 12 accepted, 60 different; 12/64
    Wilson targets accepted.
- The first remeasurement after the coupling-dimension inference milestone
  passed and kept these counts unchanged.
- Focused CDE regressions already produce nonzero projected `cHW`, `cHB`,
  `cHWB`, `cHD`, and `cH` coefficients in small heavy-scalar/Higgs models.
  The default fixtures still need more basis/on-shell/IBP and source-coverage
  work before these focused improvements translate to full parity.
- A broad real Singlet CDE probe with `hScalar`, `hScalar-hScalar`, and
  `hScalar-hScalar-hScalar` selected at trace order 3 is currently too heavy
  for routine slice validation. The immediate native vakint/FORM crash class
  from pychete `Index(...)` wrappers in loop-momentum vector slots has a
  focused fix and tests, and native CDE aggregate staging now avoids monolithic
  selected-CDE tensor-reduction/evaluation calls. Broad default CDE still needs
  more source filtering and basis reductions before it should be enabled by
  default.

## Next Work

- Choose one coherent basis/projection/backend feature family from the
  remeasured frontier. Priority candidates are:
  - CDE source staging and reduction batching for broad Singlet CDE probes,
    building on backend-safe loop-momentum index lowering and termwise native
    CDE aggregate staging now in place;
  - target-local EOM/IBP reductions for Higgs/gauge Wilson structures such as
    `cHBox`, `cHD`, `cHW`, `cHB`, and `cHWB`;
  - source staging for heavy-scalar-substituted Wilson projection so projection
    cost scales with target-compatible field content;
  - additional idenso/spenso-backed group/CG contractions exposed by E_VLL or
    S1S3LQs fixture differences;
  - bounded Dirac/NCM simplification for fermionic current coefficients.
- Add focused regression tests for the selected feature, update these notes,
  run targeted gates, then commit and push a green milestone.
