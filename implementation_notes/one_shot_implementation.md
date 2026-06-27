# One-Shot Port Implementation Notes

## Active Plan And Guidelines

- Continue the one-shot Matchete-style one-loop matching port on branch
  `one-shot-port`, targeting the default SMEFT-oriented Matchete models first:
  `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Incorporate Matchete author feedback from the current slice: CDE was the
  early v0.1/paper route and must not become pychete's forward core matching
  architecture. Keep existing CDE machinery as opt-in legacy diagnostics and
  validation support, and steer new one-loop core work toward explicit
  Wilson-line trace handling that can generalize beyond one loop.
- Keep operator-basis handling generic. SMEFT Warsaw is an optional built-in
  basis provider used for validation and convenience, not a special core
  matching assumption. The implementation lives under
  `pychete.bases.smeft_warsaw`; `pychete.smeft` remains only as a
  compatibility shim. Do not expose SMEFT-specific helpers from the package
  root; the root API stays generic and basis providers live under
  `pychete.bases`. Generic code should consume `OperatorBasis` metadata and the
  operator-basis registry, not Warsaw-specific modules or names.
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
  `pychete` for generic pychete objects. Optional basis providers such as SMEFT
  Warsaw are discoverable through `pychete.bases`, not the root API. Public
  objects and user-facing methods need docstrings and Jupyter-friendly repr
  methods where relevant.
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
- Tests or exploratory workloads that may exceed local memory must be run
  through `scripts/run_with_memory_watch.py --limit-gb 30`. The wrapper now
  polls `stop.order` in the current working directory by default; remove stale
  `stop.order` before launching long work, and create/touch it to terminate the
  wrapped process group without relying on sandboxed process-management
  permissions.
- Sandbox-sensitive shell commands must not stall on approval prompts. This is
  the first shell-operating rule for the one-shot branch: never leave the
  thread waiting for sandbox approval. The `exec_command` parameter
  `sandbox_permissions: "require_escalated"` is banned for this repository.
  Do not set it, do not request escalation, and do not ask the user for
  permission through the tool approval path. Use the user-started `listener.py`
  route immediately for known restricted operations, especially `.git`
  metadata writes such as commits, rebases, merges, lock cleanup, or similar
  repository-maintenance commands. Queue exactly one command through
  `run.order` and read `run.output`. For ordinary direct commands, if one
  unexpectedly fails with `Operation not permitted`, a sandbox write
  restriction, or the known read-only `.git` metadata failure, immediately
  retry through the listener rather than waiting for approval. The listener is
  the sandbox-dispatch fallback; keep using the 30 GiB watchdog for long or
  memory-sensitive Python/test/matching workloads.
- Mechanical fail-closed guard for shell tool calls: the `sandbox_permissions`
  key must be absent from every `exec_command` payload, including the value
  `use_default`. Before sending any shell command, inspect the intended payload;
  if the key is present, remove it and re-plan. If the command might require
  approval, dispatch it through `listener.py` instead of escalation. Approval
  escalation is not an available path on this branch.

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

- Recent pushed milestones include `75e20f6 Stage native vakint CDE aggregates
  termwise` and `0f02dc9 Expose index canonization in fixture reports`.
- Recent milestones since the Part E summary added public
  `infer_coupling_mass_dimensions(theory, lagrangian)`, exposed Symbolica
  tensor-index canonicalization diagnostics, made vakint loop-momentum index
  lowering backend-safe, and staged selected native CDE/vakint aggregate
  canonicalization/reduction/evaluation term-by-term.
- Matchete author feedback has been promoted to an active architectural
  constraint for the current slice: CDE remains legacy/diagnostic support,
  while forward matching work should expose explicit Wilson-line trace
  machinery. This slice adds `WilsonLineTraceExpansionTerm` and
  `WilsonLineTracePath.propagator_expansion_terms(...)` so termwise propagator
  expansion can be requested through Wilson-line-named APIs rather than only
  through `BosonicCDETraceExpansionTerm`.
- `OneLoopSetup.interaction_wilson_line_expansion_terms_by_trace(...)`,
  `interaction_wilson_line_expansion_terms(...)`,
  `interaction_wilson_line_expansion_kernel_expression_map(...)`, and
  `interaction_wilson_line_expansion_vakint_integral_expression_map(...)` are
  the new structured diagnostic hooks for the current Matchete Wilson-line
  route. They reuse the tested covariant propagator expansion primitive
  internally but keep the public architecture Wilson-line-first.
- `apply_cd` now treats `WilsonTerm(field, links, derivatives)` as the
  derivative-carrying Wilson-line object. Open covariant derivatives append to
  the derivative slot through Symbolica replacement rules before
  `expand_wilson_terms(...)` lowers supported identity/field-strength cases.
- The current hybrid follow-up makes the public Wilson-line matcher preserve
  the unselected interaction-power remainder. The pure selected-trace
  `interaction_wilson_line_*_matching_result(...)` methods remain available for
  diagnostics, but `Theory.match(..., loop_order=1,
  one_loop_options=OneLoopMatchOptions(wilson_line_expansion_indices_by_trace=...))`
  now routes through `interaction_wilson_line_hybrid_*` variants for all four
  backend modes. This mirrors the useful selected-trace replacement behavior
  from the legacy CDE path without using CDE-named public controls.
- CDE and Wilson-line expansion options are mutually exclusive in the public
  matcher and validation preview helpers so the old v0.1-style path and
  current Wilson-line path cannot be accidentally mixed without an explicit
  future policy.
- The latest author-feedback API adjustment removes SMEFT Warsaw helpers from
  `pychete.api` and package-root `pychete`. The optional provider remains
  available through `pychete.bases.smeft_warsaw` and the legacy
  `pychete.smeft` shim, while the generic root keeps `OperatorBasis` and
  `define_wilson_coefficient_from_basis(...)` as the intended basis mechanism.
  The package-root public API test now guards this explicitly, and tests that
  exercise SMEFT Warsaw fixtures import the optional provider directly.
- The latest Matchete-author feedback pass adds a generic operator-basis
  registry:
  `register_operator_basis(...)`, `registered_operator_basis(...)`,
  `operator_basis_names()`, and
  `define_wilson_coefficient_from_registered_basis(...)`. The bundled Warsaw
  provider registers through this boundary when `pychete.bases` is imported,
  but package-root exports remain provider-agnostic. This makes the intended
  structure explicit: SMEFT Warsaw is optional provider data, not the matching
  engine's model for operator-basis support.
- Focused validation for the author-feedback API adjustment used the 30 GiB
  watchdog wrapper: `pytest tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_theory_definitions.py::test_generic_operator_basis_defines_wilson_operator_metadata
  tests/unit/definitions/test_theory_definitions.py::test_smeft_warsaw_operator_builders_attach_wilson_operator_metadata
  -q` passed with `9 passed`; `pytest --collect-only
  tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_numeric_probes.py
  tests/integration/validation/test_validation_fixtures.py -q` collected
  `188 tests`; and `python -m mypy` reported no issues.
- The current Wilson-line fermion-loop slice re-read Matchete's
  `CloseFermionLoop`/`FermionTrace` path and the local idenso/spenso Python
  stubs. The native `idenso.simplify_gamma(...)` stub explicitly supports
  trace identities such as `Tr(gamma(mu) gamma(nu))`, so pychete now has
  `pychete.backends.idenso.trace_pychete_closed_dirac_chains(...)` for pure
  compact pychete `NCM(...)` gamma/projector words. The helper lowers closed
  spinor-index chains to native spenso tensors, delegates the trace to idenso,
  and decodes native Lorentz `spenso::g(mink(...), mink(...))` wrappers back
  to `pychete::Metric(...)`.
- `WilsonLineTracePath.propagator_expansion_terms(...)` now asks the
  Wilson-line numerator postprocessor to close a fermion loop when the first
  propagator slot is fermionic, mirroring Matchete's `CloseFermionLoop`
  dispatch. The closure is intentionally conservative: pure gamma words are
  traced through idenso, scalar fermion-loop numerators with no compact Dirac
  factors and no registered fermion fields receive the Dirac identity trace
  factor, and open chains with registered fermion endpoints stay open. Native
  idenso does not currently reduce a lone closed projector trace through this
  bridge, so projector-only closed words remain formal rather than being
  replaced by Python-side gamma-trace identities.
- The latest Wilson-line backend-algebra slice threads the existing
  `simplify_pychete_color_algebra` option into generated Wilson-line terms.
  Setup-level colour simplification happens before generated
  `WilsonTerm`/field-strength CG structures exist, so
  `WilsonLineTracePath.propagator_expansion_terms(...)` now delegates each
  generated numerator to `idenso.simplify_pychete_color_algebra(...)` after
  Wilson-term expansion and Dirac/NCM postprocessing when the option is
  enabled. Default diagnostic Wilson-line output remains raw unless the caller
  explicitly opts in.
- The validation fixture direct preview path now forwards the same
  `simplify_pychete_color_algebra` option into Wilson-line hybrid result
  methods. This keeps `ValidationFixture.one_loop_preview(...)` aligned with
  public `Theory.match(...)` for current-Matchete Wilson-line probes, instead
  of only simplifying the pre-expansion setup and leaving generated
  Wilson-line CG structures raw.
- The current Wilson-line fixture-filtering slice extends that alignment to
  target-local term filtering. Direct `ValidationFixture.one_loop_preview(...)`
  and non-public `one_loop_preview_gap_report(...)` runs can now accept
  projected matching targets, compute the same Symbolica-pattern atom
  requirements as `Theory.match(...)`, and pass them into Wilson-line hybrid
  setup methods. This intentionally improves the current-Matchete Wilson-line
  fixture path without adding a new legacy CDE-first surface.
- The current Wilson-line backend-boundary cleanup makes generated
  Wilson-line numerator postprocessing contract pychete loop-momentum metrics
  and field-strength metric/antisymmetry structures through the idenso adapter
  after Dirac/NCM simplification. This addresses closed-fermion-loop cases
  where native Dirac tracing emits `Metric(mu,nu)` factors that should reduce
  `LoopMomentum(mu) LoopMomentum(nu)` to `LoopMomentumSquared` before
  vakint/internal vacuum-integral evaluation.
- Focused validation for the Wilson-line backend-boundary cleanup used the
  30 GiB watchdog wrapper: the exact postprocess regression
  `test_wilson_line_postprocess_closes_pure_fermion_loop_dirac_traces`
  passed; `pytest tests/unit/backends/test_idenso_backend.py
  tests/integration/matching/test_fluctuation_operator.py -k "wilson_line or
  dirac or loop_momentum_metrics or field_strength_metrics" -q` passed with
  `21 passed, 103 deselected`; the broader Wilson-line gate `pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_validation_fixtures.py -k "wilson_line"
  -q` passed with `14 passed, 122 deselected`; the full idenso backend file
  passed with `29 passed`; `python -m mypy` reported no issues; and
  `git diff --check` passed.
- Status clarification for the current user check: no complete Matchete
  one-loop SMEFT integration model has been reproduced end-to-end yet.
  Successful coverage so far is narrower integration plumbing: fixture loading
  without Mathematica, one-loop preview/gap-report routes, selected
  Wilson-line trace smoke paths, internal/vakint single-scale integral
  cross-checks, projection/canonicalization behavior, and pieces of
  Singlet-style Wilson projection. The broad remaining blockers are the full
  explicit Wilson-line trace engine, robust non-Abelian/group and Dirac algebra
  through idenso/spenso for realistic models, mixed/zero-mass analytic vacuum
  integral backend through the full default-model matching path, complete
  converted model fixtures, and generic operator-basis projection without
  Warsaw-specific engine assumptions. Backend-level tests already cover
  internal two-mass, massless-plus-massive, scaleless massless, and
  Matchete-style loop-function simplification cases; those are necessary
  backend pieces, not full model-level Matchete parity.
- The current conjugate-WilsonTerm regression slice adds focused coverage for
  barred non-Abelian field Wilson-term lowering. The test verifies that
  `expand_wilson_terms(...)` uses the conjugate generator orientation
  `CG(gen, adjoint, input, output_dual)` and the conjugate endpoint
  transporter generated from theory-owned Symbolica representation metadata.
  This preserves the earlier structural requirement for barred/conjugate
  non-Abelian fields without adding Python-side tensor identities.
- Focused validation for this slice used the 30 GiB watchdog wrapper: the
  exact regression
  `test_expand_wilson_terms_lowers_conjugate_non_abelian_two_derivative_term`
  passed, and
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "expand_wilson_terms or symmetry_vanishing_wilson_terms or wilson_line" -q`
  passed with `22 passed, 74 deselected`.
- Focused validation for the direct Wilson-line fixture-filtering slice used
  the 30 GiB watchdog wrapper: `pytest
  tests/integration/validation/test_validation_fixtures.py -k "wilson_line"
  -q` passed with `3 passed, 38 deselected`; the broader Wilson-line gate
  `pytest tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_validation_fixtures.py -k "wilson_line"
  -q` passed with `14 passed, 122 deselected`; `python -m mypy` reported no
  issues; and `git diff --check` passed.
- Focused validation for the current fermion-loop trace slice has so far used
  the 30 GiB watchdog wrapper: exact new/affected tests
  `test_idenso_bridge_traces_closed_pychete_dirac_chains_through_native_gamma`,
  `test_wilson_line_postprocess_closes_pure_fermion_loop_dirac_traces`, and
  `test_wilson_line_fermion_slots_preserve_even_slash_numerators` passed with
  `3 passed`; the broader focused gate
  `pytest tests/unit/backends/test_idenso_backend.py
  tests/integration/matching/test_fluctuation_operator.py -k "wilson_line or
  dirac" -q` passed with `16 passed, 107 deselected`; the full idenso backend
  file `pytest tests/unit/backends/test_idenso_backend.py -q` passed with
  `29 passed`; and `python -m mypy` reported no issues.
- The current validation course-correction slice exposes the same
  `wilson_line_expansion_indices_by_trace`,
  `wilson_line_act_open_derivatives`, and
  `wilson_line_max_derivative_order` controls through
  `ValidationFixture.one_loop_preview(...)` and
  `one_loop_preview_gap_report(...)`. This lets Matchete-independent fixture
  probes exercise the Wilson-line hybrid route directly instead of continuing
  to make new frontier checks CDE-shaped.
- The current Wilson-line planning slice adds `WilsonLineExpansionPlanEntry`
  and `WilsonLineExpansionPlan`, plus
  `OneLoopSetup.interaction_wilson_line_expansion_plan(...)`. Public
  `OneLoopMatchOptions` and validation fixture helpers now accept
  `wilson_line_trace_names`, `wilson_line_max_total_order`,
  `wilson_line_max_slot_order`, and `wilson_line_index_prefix` so selected
  derivative-order frontier probes no longer need the legacy CDE planner.
  Generated plans still enter the existing Symbolica-backed Wilson-line
  expansion path; Python only enumerates the requested slot orders and creates
  theory-owned Lorentz index symbols with Wilson-line plan tags.
- The current author-feedback adjustment adds
  `OneLoopMatchOptions.wilson_line_filter_terms_by_matching_targets` and the
  matching validation-fixture option. This gives the preferred Wilson-line
  route the same target-local performance guard previously added for legacy
  CDE probes: selected Wilson-line expansion terms whose numerators cannot
  contain any requested field/field-strength target are skipped before tensor
  reduction/evaluation, and final coefficient extraction remains generic and
  Symbolica-backed.
- Validation for this slice used the 30 GiB watchdog wrapper:
  `pytest tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_validation_fixtures.py -k wilson_line -q`
  passed with `9 passed, 117 deselected`, and `python -m mypy` reported no
  issues.
- The current WilsonTerm vector-support slice removes the previous blanket
  formal fallback for vector Wilson terms. Non-Abelian vector fields now carry
  an implicit adjoint endpoint representation derived from the registered
  gauge-group symbol data, so zero-derivative vector Wilson terms expand to
  the Lorentz endpoint metric times the adjoint transporter delta, and
  two-or-more-derivative terms can lower to field-strength/generator-chain
  structures through the existing Symbolica replacement callbacks. Abelian
  vector derivative terms with no field charges lower to zero. Focused
  validation under the 30 GiB watchdog:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line or expand_wilson_terms or periodic_cyclic_trace_factor" -q`
  passed with `16 passed, 72 deselected`, and `python -m mypy` reported no
  issues. While checking the broader affected file, two older setup assertions
  were updated to the already-established periodic cyclic prefactor convention
  (`hScalar-hScalar` carries `-1/4`, not a universal `-1/2`); rerunning those
  two setup tests passed.
- The current Matchete-author-feedback slice continues the Wilson-line-first
  correction by adding a pychete `SymmetricLorentzInds(...)` marker and a
  public `remove_symmetry_vanishing_wilson_terms(...)` helper. The helper uses
  Symbolica pattern matches over `SymmetricLorentzInds(...)` and
  `WilsonTerm(...)` to remove additive terms whose Wilson derivative pair is
  repeated or whose derivative-index list contains the loop-integration
  symmetric Lorentz group. `expand_wilson_terms(...)` now runs this cleanup
  before lowering supported Wilson terms, matching the current Matchete
  Wilson-line pipeline more closely without adding new CDE machinery.
- The same slice removes the implicit `"SMEFT"` basis default from raw
  `Theory.define_wilson_coefficient(...)`. Unbased Wilson coefficients remain
  basis-unassigned unless a caller explicitly uses `OperatorBasis`,
  `define_wilson_coefficient_from_basis(...)`, or the optional
  `define_smeft_wilson_coefficient(...)` convenience route. This keeps the
  bundled SMEFT Warsaw provider as validation/convenience metadata rather than
  a core matching assumption.
- Focused validation for this slice used the 30 GiB watchdog wrapper:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "symmetry_vanishing_wilson_terms or expand_wilson_terms" -q` passed with
  `10 passed, 79 deselected`; `pytest
  tests/unit/definitions/test_pretty_printing.py -k
  "supertrace_denominator_heads or builtin_pychete_symbols" -q` passed with
  `2 passed, 8 deselected`; `pytest tests/unit/definitions/test_public_api.py
  -q` passed with `5 passed`; `pytest
  tests/unit/definitions/test_theory_definitions.py -k
  "wilson_coefficients_are_unbased_by_default or wilson_coefficients_store_basis
  or generic_operator_basis or smeft_warsaw_operator" -q` passed with
  `4 passed, 46 deselected`; `pytest
  tests/integration/validation/test_validation_fixtures.py -k
  "wilson_line or cde_filter or projected_targets or
  matching_condition_projection_names" -q` passed with
  `4 passed, 37 deselected`; `pytest
  tests/integration/matching/test_heavy_scalar_tree.py -k
  "matching_condition or wilson or cPhi" -q` passed with
  `2 passed, 18 deselected`; and `python -m mypy` reported no issues.
  A broader follow-up ran `pytest tests/unit/definitions/test_theory_definitions.py
  -q` with `50 passed` and `pytest
  tests/integration/validation/test_numeric_probes.py -k
  "wilson or basis or matching_condition" -q` with
  `9 passed, 45 deselected`.
- The current Wilson-line symmetry follow-up makes that cleanup effective for
  generated propagator-expanded Wilson-line terms. `BosonicCovariantPropagatorExpansionTerm`
  now stores the explicit `loop_momentum_indices` used to build its numerator,
  avoiding loss of multiplicity when Symbolica simplifies repeated
  `LoopMomentum(...)` factors into powers. `WilsonLineTracePath.propagator_expansion_terms(...)`
  passes the accumulated index metadata through
  `remove_loop_momentum_symmetry_vanishing_wilson_terms(...)` after open
  derivatives act and before supported Wilson-term expansion. The helper
  temporarily inserts `SymmetricLorentzInds(...)`, removes vanishing Wilson
  terms with Symbolica pattern matches, then strips the marker so public
  numerators still carry the original loop-momentum factors for vakint/idenso
  tensor reduction.
- The next Wilson-line gather-stage adjustment tightens that helper further:
  odd-rank generated loop-momentum numerator terms now vanish immediately,
  matching Matchete's `LoopMoms[...]` rule before `WilsonExpand`. This keeps
  odd terms from being expanded only to be killed later by vakint tensor
  reduction, while even-rank survivors still preserve their explicit
  `LoopMomentum(...)` factors for the backend path.
- The current author-feedback follow-up moves the SMEFT Warsaw provider out of
  the top-level implementation module and into `pychete.bases.smeft_warsaw`.
  `pychete.smeft` now re-exports the same helpers as a compatibility shim, and
  `pychete.api` exposes only generic operator-basis registry helpers. This
  keeps Warsaw support as optional validation/convenience metadata rather than
  a core matching-engine module.
- The same follow-up makes Wilson-line propagator expansion slot-statistics
  aware. `fermionic_covariant_propagator_expansion_terms(...)` implements the
  Matchete `PropFermionExpand`-style `(slash(k)+M) Helper[n] +
  i gamma(mu) OpenCD(mu) Helper[n-1]` structure with theory-owned generated
  Lorentz indices, and `WilsonLineTracePath.propagator_expansion_terms(...)`
  now dispatches between bosonic and fermionic covariant propagator expansions
  from the actual fluctuation mode metadata. The shared term type is now
  `CovariantPropagatorExpansionTerm`, with the old bosonic name kept as a
  compatibility alias.
- The current vector-slot parity slice implements Matchete's
  `PropExpand[Vector] = -PropBosonExpand[...]` rule in the Wilson-line
  propagator dispatch. The check uses `FluctuationMode.field_type` and the
  registered vector field type, not `hVector` trace-name strings. The sign is
  stored on the covariant propagator term prefactor, so the existing
  Wilson-line term construction, vakint topology lowering, and internal
  evaluation paths see the same denominator powers and loop-momentum metadata
  as scalar slots with only the Matchete vector sign flipped.
- The current Wilson-line noncommutative cleanup slice adds
  `normalize_ncm_chains(...)`, a bounded Symbolica-replacement pass that
  flattens nested pychete `NCM(...)` operands and hoists only commutative
  scalar coefficients. Generated Wilson-line numerators now pass through this
  normalization, then through idenso-backed
  `simplify_pychete_dirac_algebra(...)`, before final commutative
  scalarization. This removes Matchete-incompatible nested `NCM(...,
  NCM(...), ...)` structures from fermion Wilson-line paths and gives native
  gamma/projector simplification the expected flat word boundary.
- The same slice fixes manual order-zero `SupertraceBlockTrace` diagnostics:
  `power_type_log_prefactor` now returns 1 for order-zero traces instead of
  constructing an infinite prefactor. Generated physical power traces are
  nonzero order and keep the existing cyclic-orbit prefactor convention.
- Focused validation for the noncommutative Wilson-line cleanup used the
  30 GiB watchdog wrapper: `pytest tests/unit/functional/test_noncommutative.py
  tests/integration/matching/test_fluctuation_operator.py -k
  "normalize_ncm or nested_fermion_ncm or projector_words_before_vakint or
  mixed_ncm_dirac" -q` passed with `4 passed, 91 deselected`; the broader
  affected gate `pytest tests/unit/definitions/test_public_api.py
  tests/unit/functional/test_noncommutative.py
  tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_validation_fixtures.py -k
  "public_api or noncommutative or wilson_line or
  projector_words_before_vakint or mixed_ncm_dirac" -q` passed with
  `22 passed, 119 deselected`; `python -m
  mypy` reported no issues; and `git diff --check` passed.
- Focused validation for the odd-rank Wilson-line gather adjustment used the
  30 GiB watchdog wrapper: `pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "loop_momentum_symmetry_cleanup or wilson_line_expansion_drops_odd_loop_rank
  or interaction_wilson_line_expansion or
  one_loop_match_can_use_selected_wilson_line_expansion" -q` passed with
  `3 passed, 87 deselected`; the broader Wilson-line/validation gate `pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_validation_fixtures.py -k "wilson_line"
  -q` passed with `9 passed, 122 deselected`; `python -m mypy` reported no
  issues; and `git diff --check` passed.
- Focused validation for this follow-up used the 30 GiB watchdog wrapper:
  `pytest tests/unit/functional/test_cde.py -q` passed with `10 passed`;
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "loop_momentum_symmetry_cleanup or symmetry_vanishing_wilson_terms or
  wilson_line_expansion_lets_open_derivatives or interaction_wilson_line_expansion"
  -q` passed with `3 passed, 87 deselected`; the broader Wilson-line gate
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line or expand_wilson_terms" -q` passed with
  `15 passed, 75 deselected`; `pytest tests/unit/definitions/test_public_api.py
  -q` passed with `5 passed`; and `python -m mypy` reported no issues.
- The generic-basis rule was tightened: SMEFT Warsaw stays an optional
  `OperatorBasis` convenience provider and validation asset. New engine code
  should consume generic Wilson/operator metadata and must not branch on Warsaw
  names or import `pychete.smeft` for core matching behavior.
- Validation fixture gap reports now expose `comparison_canonize_indices`
  and pass it through to `MatchingResult.compare_to(...)`, so common
  supertrace and matching-condition comparisons use Symbolica
  `Expression.canonize_tensors(...)` by default instead of reporting
  alpha-equivalent dummy-index relabelings as false gaps.
- The current slice fixes target-local tree/projection recovery for the
  Singlet `cHBox` derivative operator: explicit list-form `CD({mu, mu}, ...)`
  now counts one EFT derivative per listed index, additive projection targets
  can extract coefficient terms common to every additive component, and
  over-contracted scalar derivative bilinears are split with Symbolica
  replacement rules before tensor canonization.
- The current staged-projection slice adds loop/tree source staging for full
  one-loop matching conditions. `MatchingResult` can now project matching
  conditions independently from multiple source stages and sum the coefficients,
  and public one-loop matching uses this automatically when
  `include_tree_level_matching=True` created loop-only and tree-level projection
  sources. Those staged sources are carried through on-shell replacement rules
  and EFT truncation.
- The current CDE/projection performance slice adds an opt-in
  `OneLoopMatchOptions.bosonic_cde_filter_terms_by_matching_targets` guard. It
  computes target atom requirements with Symbolica field/field-strength pattern
  matches and skips generated CDE terms that cannot contain any requested
  target before tensor reduction/evaluation. The filter deliberately stays
  label-level and leaves all dummy-index alignment to the existing
  `Expression.canonize_tensors(...)` projection/comparison path.
- The fixture-report path now exposes the same CDE target filter for
  Matchete-independent validation frontier work:
  `ValidationFixture.one_loop_preview_gap_report(...,
  bosonic_cde_filter_terms_by_matching_targets=True)` forwards the option to
  public `Theory.match(...)` when `use_public_match_api=True` and
  `project_reference_matching_conditions=True`.
- Fixture gap reports now also support
  `matching_condition_projection_names=...`, accepting canonical condition
  names, external Wilson names such as `cHW`, or `"wilson"` for all Wilson
  targets. This keeps target-local CDE/EOM/IBP investigations from projecting
  and comparing all 72 default SMEFT matching conditions on every smoke run.
- The current projection-filter follow-up tightens the target atom-count
  prefilter for powered field-strength atoms. Operators such as `cHW`, whose
  registered target contains `FieldStrength(W)^2`, now require two compatible
  `W` field-strength atoms before a generated CDE/source term survives the
  label-level filter. Dummy-index alignment still remains delegated to
  Symbolica `Expression.canonize_tensors(...)` and its returned canonical
  external/dummy index payload.
- Matchete author feedback triggered a course correction: existing CDE support
  remains useful as a diagnostic/validation path, but it is no longer treated
  as the architectural route for completing the one-loop port. New core work
  should investigate explicit Wilson-line style trace handling, while keeping
  current CDE paths optional and bounded.
- The current structural slice introduces generic operator-basis registration
  via `OperatorBasis` and `define_wilson_coefficient_from_basis(...)`.
  `pychete.bases.smeft_warsaw` now exposes SMEFT Warsaw as an optional
  built-in basis using that generic mechanism instead of making SMEFT-specific
  operator maps the conceptual source for all matching code.
- A dependency-free memory watchdog now lives at
  `scripts/run_with_memory_watch.py` and is documented for 30 GiB capped test
  and matching workloads.
- The converter path now preserves the structural invariant that Symbolica
  symbol data is attached before fixture expressions are parsed. Do not mutate
  coupling symbol data after final symbols exist.
- The current Wilson-line structural slice adds explicit pychete
  `WilsonLine`/`WilsonTerm` symbols and a public `WilsonLineTracePath` object
  built from ordered supertrace entry paths before the trace is summed. This is
  a first bridge toward current Matchete-style Wilson-line traces: it preserves
  the ordered interaction insertions, the next-mode propagator mass slots, the
  closing field label, and a placeholder Wilson line/term without changing the
  existing power-type or legacy CDE result pipeline.
- `OneLoopSetup` now exposes interaction Wilson-line paths and named kernel
  expressions through `interaction_wilson_line_trace_paths(...)`,
  `interaction_wilson_line_trace_paths_by_trace(...)`, and
  `interaction_wilson_line_kernel_expression_map(...)`. These are structural
  diagnostics and future expansion inputs, not yet a full Wilson-line
  functional-trace evaluator.
- The current Wilson-term expansion slice adds `expand_wilson_terms(theory,
  expr)` and `wilson_term_expansion(...)` as the reusable expansion boundary.
  The supported cases are deliberately bounded and native-pattern based:
  identity transport for zero derivatives, zero for one derivative, and
  Matchete-style derivative-sublist field-strength insertions for
  scalar/fermion representations up to `max_derivative_order` (default four)
  using theory-owned Abelian/non-Abelian gauge metadata. `WilsonTerm` atoms
  above the requested order and vector derivative terms remain formal for a
  later tensor/generator-chain validation slice.
- `WilsonLineTracePath` now exposes
  `wilson_term_expanded_template_expression(...)` and
  `wilson_term_expanded_kernel_expression(...)`, allowing future matching code
  to inspect Wilson-term-expanded path numerators/kernels without changing the
  default power-type or CDE result pipelines.
- `AGENTS.md` now makes the Matchete-author course correction explicit:
  new core matching work should use ordered Wilson-line path metadata, not a
  CDE-first architecture, and SMEFT Warsaw must remain an optional
  `OperatorBasis` provider rather than a bespoke matching core assumption.
- Projection and comparison paths already use Symbolica
  `Expression.canonize_tensors(...)` through `tensor_index_specs(...)` and
  `canonize_tensor_indices(...)`, preserving the canonical expression,
  external-index list, and ordered dummy-index list for alpha-equivalent
  contractions.
- The current projection/comparison route was rechecked against the Symbolica
  stub contract: `Expression.canonize_tensors(...)` returns the canonical
  expression plus the canonical external and ordered dummy indices. pychete
  treats that returned payload as the native replacement/alignment information
  for dummy-index comparisons instead of inferring an index map by rescanning
  expression strings.
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

- Wilson-line generated-colour simplification gate, under the 30 GiB watchdog
  wrapper: `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line_expansion_can_simplify_generated_color_algebra or
  one_loop_match_can_use_selected_wilson_line_expansion or
  wilson_line_path_expands_propagator_terms" -q` passed with `3 passed, 92
  deselected`.
- `python -m mypy`, under the 30 GiB watchdog wrapper, reported no issues in
  40 source files after the Wilson-line generated-colour simplification slice.
- Validation-fixture Wilson-line colour follow-through gate, under the 30 GiB
  watchdog wrapper: `pytest tests/integration/validation/test_validation_fixtures.py
  -k "validation_fixture_preview_can_use_wilson_line_expansion_without_mathematica
  or preview_can_simplify_pychete_color_algebra or
  gap_report_forwards_pychete_color" -q` passed with `3 passed, 38 deselected`.
- `python -m mypy`, under the 30 GiB watchdog wrapper, reported no issues in
  40 source files after the validation-fixture Wilson-line colour follow-through.
- Author-feedback generic-basis registry gate, under the 30 GiB watchdog
  wrapper: `pytest tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_theory_definitions.py -k "public_api or
  operator_basis or smeft_warsaw_operator" -q` passed with `11 passed, 48
  deselected`.
- `python -m mypy`, under the 30 GiB watchdog wrapper, reported no issues in
  40 source files after the generic registry/course-correction slice.
- `git diff --check` passed after the generic registry/course-correction
  slice.
- Vector-slot Wilson-line parity gate, under the 30 GiB watchdog wrapper:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line_vector_slots_use_matchete_propagator_sign or
  wilson_line_path_expands_propagator_terms_without_cde_result_object or
  fermion_slots_preserve_even_slash or normalizes_nested_fermion_ncm or
  one_loop_match_can_use_selected_wilson_line_expansion" -q` passed with
  `5 passed, 88 deselected`.
- Broader vector/Wilson-line affected gate, under the 30 GiB watchdog wrapper:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line or vector" -q` passed with `19 passed, 74 deselected`.
- `python -m mypy`, under the 30 GiB watchdog wrapper, reported no issues in
  40 source files after the vector-slot sign change.
- `git diff --check` passed after the vector-slot sign change.
- Author-feedback Wilson-line/provider follow-up gate, under the 30 GiB
  watchdog wrapper: `pytest tests/unit/functional/test_cde.py
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_theory_definitions.py -k "fermionic_covariant or
  bosonic_covariant or nested_fermion_ncm or even_slash or wilson_line or
  public_api or compatibility_shim or generic_operator_basis or
  smeft_warsaw_operator" -q` passed with `22 passed, 138 deselected`.
- `python -m mypy`, also under the 30 GiB watchdog wrapper, reported no issues
  in 40 source files.
- `git diff --check` passed after the provider-layout and fermion-slot
  Wilson-line expansion changes.
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
- Focused validation-report tensor-canonization regression:
  `pytest tests/integration/validation/test_numeric_probes.py::test_fixture_gap_report_canonizes_alpha_equivalent_matching_conditions -q`
  passed.
- Full numeric-probe/validation-report file after exposing
  `comparison_canonize_indices`:
  `pytest tests/integration/validation/test_numeric_probes.py -q` passed with
  53 tests.
- 30 GiB memory-watch Wilson-line structural/API gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_exposes_explicit_wilson_line_trace_paths tests/unit/definitions/test_public_api.py::test_public_api_exports_have_docstrings tests/unit/definitions/test_public_api.py::test_public_api_methods_have_docstrings -q`
  passed with 3 tests.
- 30 GiB memory-watch typing gate after the Wilson-line structural slice:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `git diff --check` passed after the Wilson-line structural slice.
- 30 GiB memory-watch Wilson-term expansion focused gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "wilson" -q`
  passed with 7 tests selected and 73 deselected, covering identity,
  one-derivative zero, Abelian two-derivative field-strength insertion,
  Abelian three-derivative derivative-sublist insertion, Abelian
  four-derivative multi-block partitions, non-Abelian generator/field-strength
  insertion, explicit derivative-order cap behavior, and the
  `WilsonLineTracePath` expansion bridge.
- 30 GiB memory-watch public API gate after exporting Wilson expansion helpers:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/unit/definitions/test_public_api.py -q`
  passed with 5 tests.
- 30 GiB memory-watch typing gate after the Wilson-term expansion slice:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `git diff --check` passed after the Wilson-term expansion slice.
- 30 GiB memory-watch Wilson-line public matcher/API gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "wilson" tests/unit/definitions/test_public_api.py -q`
  passed with 11 tests selected and 78 deselected. This covers direct
  Wilson-line expansion terms, `Theory.match(..., loop_order=1)` routing
  through `OneLoopMatchOptions.wilson_line_expansion_indices_by_trace`, and
  rejection of simultaneous Wilson-line/CDE expansion options.
- 30 GiB memory-watch typing gate after the Wilson-line public matcher bridge:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `git diff --check` passed after the Wilson-line public matcher bridge.
- 30 GiB memory-watch Wilson-line hybrid matcher/API gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "wilson" tests/unit/definitions/test_public_api.py -q`
  passed with 11 tests selected and 78 deselected. This now verifies that
  public `Theory.match(...)` Wilson-line expansion uses the hybrid stage and
  keeps unselected interaction-power remainder terms.
- 30 GiB memory-watch typing gate after the Wilson-line hybrid matcher slice:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `python -m mypy` passed after the validation-report canonization slice.
- `git diff --check` passed after the validation-report canonization slice.
- Focused Singlet tree projection regression:
  `pytest tests/integration/validation/test_numeric_probes.py::test_singlet_tree_matching_projects_ch_and_hbox_terms -q`
  passed and verifies the tree-level `cH` term plus `cHBox = -A^2/(2*M^4)`.
- EFT counting gate:
  `pytest tests/unit/eft/test_eft_counting.py -q` passed with 7 tests,
  including direct coverage that `CD({mu, mu}, heavy)` has two derivative
  dimensions.
- Heavy-scalar tree matching gate:
  `pytest tests/integration/matching/test_heavy_scalar_tree.py -q` passed with
  20 tests.
- Focused HBox/CD/IBP projection subset:
  `pytest tests/integration/validation/test_numeric_probes.py -k "hbox or cd_targets or ibp or singlet_tree" -q`
  passed with 8 tests and 45 deselected.
- Full numeric-probe/projection file:
  `pytest tests/integration/validation/test_numeric_probes.py -q` passed with
  53 tests after the additive projection and CD-counting fixes.
- `python -m mypy` passed after the target-local HBox projection slice.
- `git diff --check` passed after the target-local HBox projection slice.
- Staged projection regression gate:
  `pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_staged_projection_preserves_hbox_tree_alias_with_direct_loop_term tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_can_include_tree_level_matching_source tests/unit/definitions/test_public_api.py::test_public_api_methods_have_docstrings -q`
  passed with 3 tests.
- A real Singlet public-match smoke with `max_trace_order=1`, internal minimal
  subtraction, `include_tree_level_matching=True`,
  `substitute_heavy_scalar_solutions=True`, target-local EFT truncation, and
  only the `cHBox` target now reports
  `matching_condition_projection_source=staged` and includes the tree piece
  `-A^2/(2*M^4)` in the projected coefficient:
  `-A^2/(2*M^4) - i*log(mursq)*A^2*lambdaphi/(32*pi^2*M^4)
  + i*log(M)*A^2*lambdaphi/(16*pi^2*M^4)
  - i*A^2*lambdaphi/(32*pi^2*M^4)`.
- Focused touched-file gate:
  `pytest tests/integration/matching/test_heavy_scalar_tree.py tests/unit/definitions/test_public_api.py -q`
  passed with 25 tests.
- Focused HBox/staged-projection gate:
  `pytest tests/integration/validation/test_numeric_probes.py -k "hbox or staged_projection or projection_source" -q`
  passed with 4 tests and 50 deselected.
- `python -m mypy` passed after the staged projection slice.
- `git diff --check` passed after the staged projection slice.
- Focused target-local CDE filter regression:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k "filter_terms_by_matching_targets"`
  passed. In the synthetic `cHW` order-four CDE case, the opt-in filter reduces
  evaluated generated terms from 12 to 8 while keeping the projected Wilson
  coefficient nonzero.
- Focused order-four/filter CDE gate:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k "filter_terms_by_matching_targets or order_four_covariant_derivatives"`
  passed with 2 tests and 69 deselected.
- Broader non-heavy-solution CDE gate:
  `pytest tests/integration/matching/test_fluctuation_operator.py -k "bosonic_cde and not heavy_solution"`
  passed with 12 tests and 59 deselected.
- `python -m mypy` passed after the target-local CDE filter slice.
- `git diff --check` passed after the target-local CDE filter slice.
- Validation-fixture public CDE filter forwarding gate:
  `pytest tests/integration/validation/test_validation_fixtures.py -k "public_match_api or public_cde_filter or registered_wilsons_before_reference_targets" -q`
  passed with 3 tests and 35 deselected.
- `python -m mypy` passed after exposing CDE target filtering in fixture gap
  reports.
- `git diff --check` passed after exposing CDE target filtering in fixture gap
  reports.
- Focused target-subset fixture report smoke:
  a real Singlet public-match report with
  `matching_condition_projection_names=("cHBox",)`, internal minimal
  subtraction, heavy-scalar substitution, and tree-level matching completed in
  about 15 seconds and exposed exactly one candidate/reference matching
  condition.
- Focused raw CDE fixture report smoke:
  a real Singlet public-match report with
  `matching_condition_projection_names=("cHW",)`, raw CDE `hScalar` expansion
  through order 4, target filtering, and pychete colour simplification
  completed in about 14 seconds and exposed exactly one candidate/reference
  condition. The condition remains different from Matchete, so this is
  tractable frontier evidence rather than parity.
- Target-subset fixture projection gate:
  `pytest tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_projects_registered_wilsons_before_reference_targets tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_can_filter_public_cde_terms_by_projected_targets -q`
  passed.
- Broader public-match fixture projection subset:
  `pytest tests/integration/validation/test_validation_fixtures.py -k "public_cde_filter or registered_wilsons_before_reference_targets or public_match_api" -q`
  passed with 3 tests and 35 deselected.
- `python -m mypy` passed after adding target-subset fixture projection.
- `git diff --check` passed after adding target-subset fixture projection.
- Focused powered-field-strength target-filter regression:
  `pytest tests/integration/matching/test_fluctuation_operator.py::test_projection_atom_filter_counts_powered_field_strength_targets -q`
  passed and verifies a `cHW`-style `FieldStrength(W)^2` target requires two
  `W` field strengths before a source term survives projection filtering.
- Direct structured Singlet target smoke through the real
  `registered_wilsons` CDE requirement path now reports
  `(('field', 'Singlet_Scalar_Extension::field_H', 2),
  ('field_strength', 'Singlet_Scalar_Extension::field_W', 2))` for the `cHW`
  family, confirming the filter uses the stored Wilson operator metadata rather
  than the coefficient symbol alone.
- `python -m mypy` passed after the powered-field-strength filter fix.
- `git diff --check` passed after the powered-field-strength filter fix.
- A broader public CDE subset and the public order-four CDE test were started
  during this slice, but stopped after they entered slow native CDE paths. They
  are not counted as validation gates for this small projection-filter fix.
- 30 GiB memory-watch focused public API/operator-basis gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/unit/definitions/test_theory_definitions.py::test_generic_operator_basis_defines_wilson_operator_metadata tests/unit/definitions/test_theory_definitions.py::test_smeft_warsaw_operator_builders_attach_wilson_operator_metadata tests/unit/definitions/test_public_api.py -q`
  passed with 7 tests. An initial run found that the new SMEFT basis exposed
  builder insertion order rather than the published
  `SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES` order; the basis constructor now
  preserves the published order.
- 30 GiB memory-watch compact field-strength projection gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_projection_atom_filter_counts_powered_field_strength_targets tests/integration/matching/test_fluctuation_operator.py::test_matching_projection_handles_compact_alpha_equivalent_field_strength_powers -q`
  passed with 2 tests.
- 30 GiB memory-watch typing gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `git diff --check` passed after the Matchete-author-feedback course
  correction, generic operator-basis refactor, memory-watch wrapper, and
  compact field-strength projection fast path.
- 30 GiB memory-watch validation-fixture Wilson-line course-correction gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py -k "wilson_line or bosonic_cde_expansion or forwards_pychete_color_to_public_match_api" -q`
  passed with 4 tests and 36 deselected. This covers direct fixture
  `one_loop_preview(...)` routing through the Wilson-line hybrid stage,
  mutual exclusion with legacy CDE expansion, public gap-report forwarding of
  `wilson_line_*` options, and preservation of the existing CDE forwarding
  path.
- 30 GiB memory-watch typing gate after exposing Wilson-line validation
  controls:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `git diff --check` passed after exposing Wilson-line validation controls.
- 30 GiB memory-watch Wilson-line generated-plan gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_wilson_line_path_expands_propagator_terms_without_cde_result_object tests/integration/matching/test_fluctuation_operator.py::test_one_loop_match_can_use_selected_wilson_line_expansion_route tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_wilson_line_expansion_without_mathematica tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_forwards_wilson_line_to_public_match_api tests/unit/definitions/test_public_api.py -q`
  passed with 9 tests. This covers setup-level
  `interaction_wilson_line_expansion_plan(...)`, public
  `OneLoopMatchOptions(wilson_line_max_total_order=...)`, validation fixture
  generated previews, gap-report forwarding of generated-plan controls, and
  public API docstring/export coverage.
- 30 GiB memory-watch typing gate after the Wilson-line generated-plan slice:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `git diff --check` passed after the Wilson-line generated-plan slice.
- Current Wilson-line commutator/colour-fallback slice:
  - `OneLoopMatchOptions` now exposes
    `wilson_line_emit_covariant_derivative_commutators`,
    `wilson_line_emit_covariant_derivative_commutator_passes`, and
    `wilson_line_expand_covariant_derivative_commutators`, matching the
    existing CDE diagnostic controls but routing through explicit Wilson-line
    trace expansion.
  - Setup-level Wilson-line expansion methods thread these flags into the
    native Symbolica replacement-rule commutator emission/lowering pipeline
    before the existing Wilson-line numerator post-processing.
  - The loop-momentum symmetry cleanup now only drops a `WilsonTerm` whose
    derivative group has exactly two indices contained in a symmetric
    loop-integration marker. Four-derivative Wilson terms must survive this
    early cleanup because their later derivative-sublist expansion can produce
    field-strength bilinears.
  - `spenso.lower_native_hep_cg_tensors_to_spenso(...)` now conservatively
    keeps a theory-owned pychete `CG(...)` atom when native spenso cannot cook
    a generated dummy-index label into an `AbstractIndex`. This keeps native
    colour simplification available for supported terms while preventing
    callback failures from erasing Wilson-line field-strength terms.
  - A direct Singlet Scalar Extension target-local probe for `hScalar` order
    four and `cHW` requirements now keeps six field-strength-bearing
    Wilson-line terms even with `simplify_pychete_color_algebra=True`. A full
    projected public `cHW` coefficient probe entered expensive
    projection/evaluation and was stopped; exact Singlet `cHW` parity remains a
    later, larger projection-performance slice rather than a gate for this
    backend/term-generation fix.
  - The memory wrapper now supports file-based termination through `stop.order`
    and has a unit regression for that stop-file path, avoiding future stalls
    on sandboxed permission requests for process management.
- The current Wilson-line projection-performance follow-up found that native
  vakint can return `vakint::NCM(...)` wrappers around decoded pychete atoms.
  Leaving those wrappers formal hides field/field-strength atoms from the
  target-local projection filter, so `decode_pychete_namespace(...)` now
  decodes bounded-arity native `NCM` wrappers recursively and then scalarizes
  fully commutative pychete `NCM(...)` chains, including one-operand chains.
- After that decode fix, Singlet `hScalar` order-four Wilson-line probes expose
  target-compatible `cHW` source terms to the projection filter. The remaining
  stall moved to the final generic coefficient fallback after raw exact,
  wildcard-index, and tensor-canonicalized target-local projections had already
  failed. Projection now treats `Expression.collect_factors()` like
  `Expression.factor()` and `Expression.expand()`: still native Symbolica, but
  only attempted on target-local filtered sources below explicit term/byte
  thresholds. Oversized sources fall through to the existing wildcard/normalized
  fallback path instead of spending unbounded time in global collection.
- The same slice adds a stricter threshold for the final generic fallback after
  target-local tensor canonicalization. In the real Singlet `cHW` Wilson-line
  probe, the filtered/canonized source has 21 terms and roughly 14 KiB of
  Symbolica payload; this was still small enough for the older collect/factor
  guard but large enough to enter an expensive full-source coefficient path.
  The stricter guard makes the public `project_matching_conditions(...,
  eft_order=6)` probe return in about 0.07 seconds after the Wilson-line source
  is built. The coefficient is still zero in this bounded path, so this is a
  projection-performance safety fix, not a completed `cHW` parity result.
- 30 GiB memory-watch stop-file wrapper gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/unit/dependencies/test_memory_watch.py -q`
  passed.
- 30 GiB memory-watch Wilson-line commutator/color fallback gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "expand_wilson_terms or symmetry_vanishing_wilson_terms or wilson_line" -q`
  passed with 23 tests and 74 deselected.
- 30 GiB memory-watch validation-fixture Wilson-line forwarding gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py -k "wilson_line or forwards_pychete_color_to_public_match_api" -q`
  passed with 4 tests and 37 deselected.
- 30 GiB memory-watch typing gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.
- `git diff --check` passed after the Wilson-line commutator/color-fallback
  and stop-file wrapper slice.
- 30 GiB memory-watch NCM/projection guard gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/unit/functional/test_noncommutative.py tests/unit/backends/test_vakint_backend.py tests/integration/validation/test_numeric_probes.py -k "projection" -q`
  passed with 21 tests and 74 deselected.
- 30 GiB memory-watch Wilson-line guard gate:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py tests/integration/validation/test_validation_fixtures.py -k "wilson_line or forwards_pychete_color_to_public_match_api" -q`
  passed with 16 tests and 122 deselected.
- 30 GiB memory-watch real Singlet `cHW` projection probe:
  building the selected `hScalar` order-four Wilson-line hybrid internal
  minimal-subtraction result produced a 556-node, 243407-byte source, and
  projecting the selected `cHW` target with `expand_source=False` and
  `eft_order=6` returned in about 0.07 seconds with a zero coefficient.
  This confirms the performance guard prevents the previous memory-limit kill,
  while leaving exact `cHW` parity as future work.
- The current Singlet `cHW` backend-normalization follow-up found the concrete
  reason the order-four `hScalar` source stayed trapped behind CG tensors:
  native tensor reduction emitted field-strength Lorentz slots as
  `vakint::wilson_line_*`, while metric tensors carried theory-owned
  `index_wilson_line_*` aliases. `decode_pychete_namespace(...)` and
  `idenso.simplify_pychete_field_strength_metrics(...)` now normalize generated
  Wilson-line/CDE Lorentz labels to a pychete-generated namespace before
  idenso metric contractions. This is a backend-boundary rule, not a
  Wilson-specific projection workaround.
- After that alias normalization, the selected Singlet `hScalar` order-four
  Wilson-line probe shrank from 556 source nodes / 263 CG-bearing terms to 373
  source nodes / 127 CG-bearing terms, and projected `cHW` became nonzero:
  `-I*gL^4*kappa/(64*pi^2*M^2) - I*gL^4*kappa/(48*pi^2*(-2+epsilon)*M^2)`.
  This is still not the Matchete reference
  `hbar*A^2*gL^2/(12*M^4)`; it is only a partial `hScalar` contribution and
  exposes the next source-coverage/evaluation gap. A combined exploratory
  probe over `hScalar-lScalar`, `hScalar-hScalar`, and `hScalar` was stopped
  after roughly two minutes without first-trace output, so mixed-trace probes
  must be split and made more target-local before they become routine
  validation checks.
- The current Wilson-line mixed-trace performance slice refactored selected
  Wilson-line result assembly so generated terms are built once and then reused
  for kernel maps, raw vakint topologies, evaluated internal sums, and result
  metadata. It also adds a pre-generation requirement check: if a trace path
  and derivative-order entry cannot generate enough field-strength atoms for
  the projected target, the term generator is skipped before expensive
  Wilson-term lowering. For the real Singlet `hScalar-lScalar`/`cHW` probe,
  this keeps only the five total-order-four entries and generates 40 terms in
  about 22 seconds.
- `vakint.epsilon_coefficient(...)` now uses Symbolica's native
  `Expression.series(...)[power]` Laurent coefficient extraction before
  falling back to `coefficient_list(...)`. This handles epsilon-rational
  internal-evaluator outputs such as `1/(epsilon*(epsilon-2))` without forcing
  a full coefficient-list enumeration. In the staged Singlet `hScalar-lScalar`
  probe, the 40 termwise tensor reductions/evaluations completed in about
  31 seconds, finite extraction in about 21 seconds, and final target-local
  projection in about 38 seconds.
- Wilson-line hybrid internal pole/finite assembly now reuses the component
  interaction-power and selected Wilson-line pole/finite expressions instead
  of recomputing Laurent coefficients from the full hybrid aggregate. The real
  fixture-level Singlet `hScalar-lScalar`/`cHW` gap-report probe now returns
  under the 30 GiB watchdog in about 153 seconds with one projected candidate
  and one reference condition. They are still different, and a direct selected
  finite-source probe gives `cHW = 0` for `hScalar-lScalar` alone. This makes
  the mixed-trace path bounded but confirms that exact Matchete parity still
  needs the missing source/convention/basis reductions rather than only a
  performance fix.
- 30 GiB memory-watch typing gate after the NCM/projection guard slice:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m mypy`
  passed.

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
- With tree-level matching included, staged loop/tree matching-condition
  projection now preserves the tree-only Singlet `cHBox = -A^2/(2*M^4)` piece
  even when loop-only derivative pieces also project directly onto the same
  additive HBox target. Full default Singlet parity still needs broader
  basis/on-shell/IBP reductions and loop-source coverage beyond this HBox
  source-staging fix.
- A broad real Singlet CDE probe with `hScalar`, `hScalar-hScalar`, and
  `hScalar-hScalar-hScalar` selected at trace order 3 remains too heavy for
  routine slice validation. The latest 30 GiB watchdog run also showed that a
  public order-four CDE projection can still exceed the memory cap after the
  focused powered-field-strength fixes. Treat this as a legacy CDE performance
  frontier, not as the next core architecture blocker. Existing CDE controls
  and tests should remain bounded and useful for diagnostics, while full
  matching progress should pivot toward explicit Wilson-line trace handling,
  generic basis/on-shell reductions, and backend algebra coverage.
- Explicit Wilson-line order-four `hScalar` generation now produces
  field-strength-bearing terms for the Singlet `cHW` target subset, but the
  final projected public `cHW` coefficient comparison is not yet reproduced.
  Backend normalization now exposes a nonzero partial `hScalar` contribution,
  and the selected `hScalar-lScalar` route is bounded enough to measure, but
  before the conjugate-propagator correction its selected finite projection
  was zero because the explicit entry paths produced same-orientation
  `H H`/`Bar(H) Bar(H)` source factors. The Wilson-line and matrix trace path
  builders now insert the free-propagator field-space pairing between
  interaction entries, so complex scalar and fermion paths close through the
  conjugate mode. A Singlet fixture zero-order source probe now produces
  indexed mixed `H_i Bar(H_j)` bilinears with the expected `A^2` pieces. The
  full `cHW = hbar*A^2*gL^2/(12*M^4)` comparison is still not reproduced: the
  next blockers are the order-four finite/pole convention through the full
  hybrid result, generic basis/on-shell/IBP reductions, and idenso/spenso
  group/CG simplifications.
- Validation for the conjugate-propagator slice:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "supertrace_plan or one_loop_setup_prepares or wilson_line or projector or hFermion" -q`
  passed with 22 selected tests; `dependencies/.venv/bin/python
  scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python
  -m mypy` passed; `git diff --check` passed. The follow-up CDE/projection
  slice moved the canonized target-local exact extraction before the generic
  projection size guard, so registered Wilson projection can recover focused
  complex-Higgs CDE coefficients such as `cHD` and heavy-solution `cH` without
  opening the expensive collect/factor fallback on large sources. The
  conjugate charged-field commutator primitive is now tested directly, while
  the full CDE commutator route no longer asserts that antisymmetric
  field-strength pieces survive after loop-momentum symmetry cleanup.
- Additional validation after the CDE/projection follow-up:
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -q`
  passed with 99 tests; the targeted validation-fixture gate
  `dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py -k "one_loop_preview or bosonic_cde or wilson_line or projected_condition or matching_condition" -q`
  passed with 8 selected tests. The validation auto-probe builder now gathers
  numeric evaluator parameters from the same tensor-canonized expressions that
  `MatchingResult.compare_to(...)` probes, so canonized dummy labels inside
  function atoms such as `Yd[d2, index_i2]` are included in the Symbolica
  evaluator parameter map.
- Current Wilson-line/CDE generated-numerator cleanup: commutator-enabled
  Singlet `cHW` order-four Wilson-line source generation now produces 25
  filtered field-strength-bearing terms for the selected `hScalar` and
  `hScalar-hScalar` plan. The diagnostic also exposed large intermediate
  `CD(..., 0)` wrappers after commutator expansion. Added
  `simplify_trivial_cd_operators(...)`, implemented as a Symbolica replacement
  over the central `CD` pattern, and call it at the generated-numerator
  postprocessing boundary before idenso/vakint work. This does not solve the
  final `cHW = hbar*A^2*gL^2/(12*M^4)` parity yet, but it removes a real
  expression-size/performance obstacle and prevents zero-derivative clutter
  from influencing target-local filtering/projection.
- Focused validation for this cleanup used the 30 GiB watchdog wrapper:
  `pytest tests/unit/functional/test_cde.py::test_simplify_trivial_cd_operators_removes_derivatives_of_zero tests/integration/matching/test_fluctuation_operator.py::test_wilson_line_commutator_terms_survive_color_simplification_with_dummy_indices -q`
  passed with `2 passed`; the broader affected gate
  `pytest tests/unit/functional/test_cde.py tests/integration/matching/test_fluctuation_operator.py -k "trivial_cd_cleanup or wilson_line_commutator or symmetry_vanishing_wilson_terms or expand_wilson_terms or wilson_line_postprocess" -q`
  passed with `13 passed, 99 deselected`; `python -m mypy` reported no issues.
  A term-level Singlet diagnostic confirmed `filtered_terms=25`,
  `zero_cd_terms=0`, and `field_strength_terms=25` for the commutator-enabled
  `cHW` Wilson-line plan.
- Current idenso backend-boundary cleanup: the native-color decode plus
  field-strength/group simplification sequence is now centralized in
  `idenso.decode_native_color_wrappers_and_simplify_field_strengths(...)` and
  `idenso.simplify_pychete_field_strength_group_algebra(...)`. Public
  `Theory.match(...)` reuses that shared helper, and direct
  `ValidationFixture.one_loop_preview(...)` now applies the same post-result
  simplification when `simplify_pychete_color_algebra=True`. This keeps
  direct fixture probes aligned with the public match path for SU(2) and
  mixed SU(2)-U(1) field-strength generator bilinears instead of relying on a
  public-match-only cleanup. A targeted generated Singlet term diagnostic
  showed the helper is not supposed to project pre-tensor-reduction monomials
  with different Lorentz field-strength pairs; the shared boundary is for
  decoded/reduced pychete field-strength structures where Lorentz identities
  have already been exposed.
- Focused validation for the idenso boundary cleanup used the 30 GiB watchdog
  wrapper: `pytest tests/unit/backends/test_idenso_backend.py::test_idenso_bridge_shared_field_strength_group_helper_projects_su2_bilinear tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_wilson_line_expansion_without_mathematica -q`
  passed with `2 passed`; the broader affected gate
  `pytest tests/unit/backends/test_idenso_backend.py tests/integration/validation/test_validation_fixtures.py -k "field_strength or wilson_line" -q`
  passed with `11 passed, 62 deselected`; `python -m mypy` reported no issues;
  `git diff --check` passed.
- Current Wilson-line target-prefilter slice: the selected Wilson-line
  pre-generation filter is now label-aware for requested field-strength
  targets. It uses theory-owned Symbolica metadata for field charges,
  representation indices, gauge groups, and vector-field labels to prove when
  no registered field in an ordered Wilson-line path can generate a requested
  gauge `FieldStrength(...)` through covariant-derivative commutators. It also
  treats required ordinary field atoms as static path requirements, because
  Wilson-term expansion can add field strengths but cannot invent missing
  light-field operator content. This keeps the filter conservative: possible
  paths still go through generated-term Symbolica pattern filtering, while
  impossible plan entries are skipped before expensive Wilson-term lowering,
  commutator expansion, tensor reduction, or integral evaluation. This is
  aimed at making real Singlet `cHW` and broader Wilson-line fixture probes
  scale better; it is not yet a full `cHW = hbar*A^2*gL^2/(12*M^4)` parity
  result.
- Focused validation for this slice used the 30 GiB watchdog wrapper:
  `pytest tests/integration/matching/test_fluctuation_operator.py::test_wilson_line_target_filter_skips_impossible_entries_before_generation -q`
  passed with `1 passed`; `pytest
  tests/integration/matching/test_fluctuation_operator.py -k "wilson_line and
  filter" -q` passed with `2 passed, 98 deselected`; the broader matching gate
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line or projection_atom_filter or field_strength_powers" -q` passed
  with `17 passed, 83 deselected`; and `python -m mypy` reported no issues.
- Current fixture-diagnostics follow-up: `MatchingFixtureGapReport` now carries
  JSON-safe snapshots of the candidate and reference `MatchingResult.metadata`.
  This exposes Wilson-line plan and target-filter metadata such as
  `interaction_wilson_line_plan_entry_count`,
  `interaction_wilson_line_term_count`,
  `interaction_wilson_line_terms_filtered_by_matching_targets`, backend stage,
  normalization, and fixture source directly in Python report objects and
  `to_json_obj()` output. The snapshot normalizes tuples/lists recursively and
  renders unexpected objects as strings, so report JSON remains stable without
  making validation tests depend on private result internals. This does not
  alter the physics result; it makes real Singlet `cHW` and other Wilson-line
  fixture probes easier to triage without rerunning separate ad hoc
  diagnostics.
- Focused validation for this diagnostic slice used the 30 GiB watchdog
  wrapper: `pytest tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_can_filter_direct_wilson_line_terms_by_projected_targets -q`
  passed with `1 passed`; `pytest
  tests/integration/validation/test_validation_fixtures.py -k "wilson_line or
  candidate_metadata or matching_condition_projection" -q` passed with
  `3 passed, 38 deselected`; and `python -m mypy` reported no issues.
- Current Wilson-line accounting follow-up: Wilson-line matching results now
  record generated term counts by expansion-plan entry, by original trace
  name, and by plan-entry/path index. Empty plan entries are preserved in the
  metadata, and nonzero plan labels are listed explicitly. The same data is
  available through validation fixture gap-report metadata snapshots and JSON.
  This does not change symbolic output; it makes the next Singlet `cHW`
  Wilson-line frontier probe actionable because a mismatch can be localized to
  the exact trace/order/path family that survived target filtering.
  While adding this accounting, the native-vakint Wilson-line minimal
  subtraction path was tightened to generate the grouped Wilson-line terms
  once and reuse them for evaluated sums, named integrals, kernel maps, and
  metadata instead of rebuilding the same expansion several times.
- Focused validation for this accounting follow-up used the 30 GiB watchdog
  wrapper: `pytest tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_wilson_line_expansion_without_mathematica tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_can_filter_direct_wilson_line_terms_by_projected_targets -q`
  passed with `2 passed`; `pytest
  tests/integration/validation/test_validation_fixtures.py -k "wilson_line or
  candidate_metadata" -q` passed with `3 passed, 38 deselected`; `python -m
  mypy` reported no issues; and `git diff --check` passed.
- Current sandbox-policy hardening: `AGENTS.md` and both live one-shot notes
  now explicitly ban the `exec_command` parameter
  `sandbox_permissions: "require_escalated"` for this repository. Direct
  sandboxed commands may still run when appropriate, but any `.git` metadata
  write or direct `Operation not permitted` failure must go through the
  user-started `listener.py` route instead of the tool approval path. This
  policy-only commit was pushed as `5679d04`.
- Current Singlet `cHW` frontier remeasurement: a bounded
  `ValidationFixture.one_loop_preview_gap_report(...)` using the Wilson-line
  route, internal minimal subtraction, Matchete evaluated-hbar normalization,
  target filtering, and only the projected `cHW` condition completed far
  enough to expose the new accounting. The candidate is still canonically
  different from the Matchete `cHW` reference. The target-filtered Wilson-line
  source contains 65 generated terms across 35 plan entries, with 24 empty
  entries and 11 nonzero entries. Surviving terms split as `hScalar: 5`,
  `hScalar-hScalar: 20`, and `hScalar-lScalar: 40`; the nonzero entries are
  exactly the total-derivative-order-four entries
  `hScalar#wilson4_o4`, `hScalar-hScalar#wilson15_o0_4` through
  `hScalar-hScalar#wilson19_o4_0`, and `hScalar-lScalar#wilson30_o0_4`
  through `hScalar-lScalar#wilson34_o4_0`. A follow-up monolithic direct value
  projection was stopped via `stop.order` because it produced no intermediate
  output after several minutes, confirming that smaller entrywise projection
  probes are needed before more physics changes.
- Current Wilson-line entrywise-backend slice: internal Wilson-line result
  paths now keep evaluated scalar-vacuum-integral terms grouped by expansion
  plan entry. `MatchingResult.supertraces` exposes
  `interaction_wilson_line_internal_integral_sum[<entry>]`,
  `interaction_wilson_line_internal_integral_pole_part[<entry>]`, and
  `interaction_wilson_line_internal_integral_finite_part[<entry>]` for nonzero
  generated entries, while aggregate sums remain unchanged. This is a
  diagnostic/performance boundary for the next Singlet `cHW` pass: project the
  smaller entry-level finite pieces to identify which trace/order family
  produces the mismatch instead of projecting one monolithic hybrid source.
- Focused validation for the entrywise-backend slice used the 30 GiB watchdog
  wrapper: `pytest tests/integration/matching/test_fluctuation_operator.py::test_wilson_line_internal_results_expose_entrywise_laurent_sums -q`
  passed with `1 passed`; `pytest
  tests/integration/matching/test_fluctuation_operator.py -k "wilson_line and
  internal" -q` passed with `2 passed, 99 deselected`; and `python -m mypy`
  reported no issues; and `git diff --check` passed before the milestone was
  committed as `a627d19`.
- Current projection-performance follow-up: registered powered
  field-strength targets with denominator factors, such as the Singlet
  `cHW` projection target `H^\dagger H W^2/gL^2`, now normalize numeric
  factors and negative powers before the generic coefficient path, then try
  the bounded indexed-field-strength wildcard projection before broad
  collect/factor fallbacks. This keeps target-local `cHW` projection on
  entrywise finite sources from entering unbounded global collection. The
  follow-up Singlet probe projected all 11 nonzero order-four entry-level
  finite parts exposed by the Wilson-line internal backend; every entry
  projected to zero, so the missing `hbar*A^2*gL^2/(12*M^4)` coefficient is
  now localized to Wilson-line source generation/simplification or group,
  Lorentz, and basis/on-shell reduction rather than to the coefficient-sum
  mechanism.
- Focused validation for the projection-performance follow-up: `pytest
  tests/integration/matching/test_fluctuation_operator.py::test_matching_projection_handles_compact_alpha_equivalent_field_strength_powers
  tests/integration/matching/test_fluctuation_operator.py::test_matching_projection_normalizes_field_strength_target_denominators_before_fallbacks
  -q` passed with `2 passed`; `pytest
  tests/integration/matching/test_fluctuation_operator.py -k "field_strength_power
  or field_strength_target_denominators or entrywise_laurent" -q` passed with
  `3 passed, 99 deselected`; `python -m mypy` reported no issues; and
  `git diff --check` passed.
- Current Wilson-line propagation/backend slice: explicit Wilson-line path
  expansion now records the fluctuation row mode reached after each propagator
  slot and inserts a slot-local field-space propagation `Delta(...)` between
  adjacent interaction entries. This fixes the previous disconnected
  heavy-light generator-chain shape in mixed Singlet `hScalar-lScalar`
  sources. The idenso bridge now contracts explicit pychete `Delta` heads into
  neighboring registered `CG(...)` tensors before native-backed colour and
  field-strength group simplification, and the vakint adapter now uses a
  tensor-reduction-only default engine (`evaluation_order=[]`) for
  `vakint.tensor_reduce(...)` so PySecDec is not required for
  topology-independent tensor reduction.
- Current projection-local cleanup: `_ProjectionCoefficientExtractor` now
  carries the active theory and, for bounded field-strength projection targets,
  applies `idenso.simplify_pychete_field_strength_group_algebra(...)` only to
  the conservatively filtered target-local source before native Symbolica
  coefficient extraction. A focused regression shows Wilson-line-shaped
  `Metric * Delta * CG * CG * F * F * H^\dagger H` sources project onto the
  generic `cHW` target with the expected SU(2) trace factor.
- Current Singlet `cHW` remeasurement after this slice: the representative
  mixed `hScalar-lScalar` `(2,2)` entry now visibly reduces local terms to
  compact `A^2*gL^2*H^\dagger H*W^2/M^4` structures, and individual isolated
  terms project correctly. However, the full simplified target-local
  `(2,2)` source cancels under the current generated entry sum, and the
  entrywise probe over all 11 nonzero order-four entries still returns only
  `-hbar*gL^4*kappa/(12*M^2)` from `hScalar#wilson4_o4`, with all
  `hScalar-hScalar` and `hScalar-lScalar` entries projecting to zero. No full
  Matchete one-loop integration test is reproduced yet. The first milestone
  remains Singlet `cHW`; the next blocker is no longer the missing propagation
  delta or vakint tensor-reduction constructor, but the remaining Wilson-line
  source/sign/combinatorics and basis/on-shell reduction needed to produce the
  Matchete `+hbar*A^2*gL^2/(12*M^4)` condition while eliminating the spurious
  pure-heavy `kappa*gL^4/M^2` projection.
- Focused validation for this slice: `pytest
  tests/unit/backends/test_idenso_backend.py::test_idenso_bridge_contracts_pychete_delta_head_into_cg_tensor
  tests/unit/backends/test_idenso_backend.py::test_idenso_bridge_projects_su2_field_strength_bilinear_with_pychete_delta
  tests/unit/backends/test_vakint_backend.py::test_vakint_tensor_reduce_uses_tensor_only_default_engine
  tests/integration/matching/test_fluctuation_operator.py::test_matching_projection_simplifies_target_local_field_strength_group_structures
  tests/integration/matching/test_fluctuation_operator.py::test_wilson_line_complex_scalar_paths_follow_conjugate_propagators
  tests/integration/matching/test_fluctuation_operator.py::test_wilson_line_path_expands_propagator_terms_without_cde_result_object
  -q` passed with `6 passed`; `python -m mypy` reported no issues; and
  `git diff --check` passed.
- Current Wilson-line coupling-convention follow-up: re-reading Matchete's
  current `WilsonTermExpand`/`GAction` route showed that Wilson-line-generated
  field-strength insertions are coupling-free at the derivative-commutator
  lowering boundary; the Warsaw/operator target normalization carries the
  explicit gauge-coupling factors separately. `Theory.expand_covariant_derivative_commutators(...)`
  now has an `include_gauge_coupling` flag, and generated CDE/Wilson-line
  numerator postprocessing sets it to `False`, while the public default remains
  `True` for ordinary covariant-derivative expansion semantics.
- First-milestone status after this pass: still no complete Matchete one-loop
  model integration test is green. The closest target remains
  `Singlet_Scalar_Extension` `cHW`. The current implementation can load the
  fixture, build selected explicit Wilson-line plans, filter target-compatible
  terms, reduce/evaluate entry-level finite pieces, and project bounded
  entrywise sources. The active gap is now the generated Wilson-line
  source/algebra/reduction path from those terms to the Matchete
  `+hbar*A^2*gL^2/(12*M^4)` condition. The long public cHW-only report still
  exceeded the quick-check budget and was stopped with `stop.order`, so the
  reliable measurement remains the entrywise probe: all currently selected
  mixed `hScalar-lScalar` order-four entries project to zero after the latest
  convention change.
- Current Wilson-line ordering correction: explicit Wilson-line
  `ActWithOpenCDs` semantics now use the right-acting Matchete rule instead of
  the cyclic closed-chain wrapping used by the legacy CDE helper. The closing
  `WilsonTerm(...)` already represents the trace closure, so generated
  Wilson-line open derivatives must not wrap back to earlier insertions. A
  focused Abelian mixed-trace regression now checks that pure one-slot
  `hScalar` order-four Wilson-line terms vanish, while `hScalar-lScalar`
  `(4,0)` terms still lower to coupling-free field-strength sources.
- Singlet `cHW` remeasurement after the right-acting change: target-filtered
  generation across the selected `hScalar`, `hScalar-hScalar`, and
  `hScalar-lScalar` order-four Wilson-line plan still has 35 plan entries, but
  nonzero entries are now restricted to
  `hScalar-hScalar#wilson5_o0_0`,
  `hScalar-hScalar#wilson10_o2_0`,
  `hScalar-hScalar#wilson19_o4_0`,
  `hScalar-lScalar#wilson20_o0_0`,
  `hScalar-lScalar#wilson25_o2_0`, and
  `hScalar-lScalar#wilson34_o4_0`, with 8 `hScalar-hScalar` terms and 16
  `hScalar-lScalar` terms. The two order-four finite projections still give
  `cHW = 0`, so this removes non-Matchete cyclic sources but does not yet
  complete the first Matchete parity milestone.
- Current Wilson-line symmetry correction: re-reading Matchete's
  `RemoveSymmetryVanishingWilsonTerms` showed that its
  `SubsetQ[symInds, wilsonInds]` rule is rank-agnostic. pychete's
  `remove_symmetry_vanishing_wilson_terms(...)` now drops any Wilson term whose
  derivative-index list contains the full symmetric loop-momentum index group,
  not only two-derivative Wilson terms. Focused validation passed with
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "loop_momentum_symmetry_cleanup or remove_symmetry_vanishing" -q`
  (`2 passed, 101 deselected`).
- Singlet `cHW` remeasurement after the rank-agnostic symmetry fix: unfiltered
  selected generation over `hScalar`, `hScalar-hScalar`, and `hScalar-lScalar`
  still has seven nonzero plan entries and 25 terms, but with Wilson-term
  field-strength artifacts removed it contains no field strengths unless
  Higgs-derivative commutators are explicitly emitted and lowered. With
  commutator emission/lowering enabled, the selected source has field-strength
  terms and target filtering keeps only `hScalar-hScalar#wilson19_o4_0` and
  `hScalar-lScalar#wilson34_o4_0`; however the projection atom counter still
  finds zero generated additive terms satisfying the exact `cHW` requirement
  `H^2 W^2` with no extra dynamical labels. The committed Matchete reference
  fixture projects `cHW` entirely from `hScalar-lScalar`, with one reference
  term satisfying that exact requirement. pychete's generated `hScalar-lScalar`
  near-misses currently carry extra background-heavy `phi` atoms or only one
  field-strength atom after power-aware counting. The first milestone remains
  incomplete; the next coherent slice should focus on Matchete-equivalent
  `hScalar-lScalar` Wilson-line source generation and the stage at which
  background-heavy scalar fields are eliminated before target-local Wilson
  projection.
- Current Wilson-line `NCM` linearity slice: generated ordered chains now run
  through `distribute_ncm_additions(...)` before and after explicit
  Wilson-line `ActWithOpenCDs`. This bounded Symbolica replacement-rule pass
  linearizes additive operands such as `NCM(A*H + kappa*phi*H, OpenCD(...),
  ...)` into separate ordered chains before Wilson-term symmetry pruning and
  target-local filtering. This matches Matchete's termwise `NCM` processing
  more closely and prevents aggregate additive entries from being treated as a
  single noncommutative object.
- Focused validation for the `NCM` linearity slice: `pytest
  tests/unit/functional/test_noncommutative.py -q` passed with `6 passed`;
  `pytest tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line and not slow" -q` passed with `16 passed, 87 deselected`.
- Current Singlet `cHW` diagnostic after `NCM` linearity: additive
  linearization is necessary but not sufficient. Direct term-level probes show
  that applying the existing heavy-scalar solution rules to generated
  `hScalar-lScalar` numerators turns `phi`-bearing near-misses into higher
  Higgs powers, not the reference `H^2 W^2` structure. The pure `A^2`
  `hScalar-lScalar` terms are present before commutator lowering as
  loop-momentum tensors multiplying four covariant derivatives on a charged
  Higgs. Running the current inversion-only commutator pass before tensor
  reduction, forcing it to commute adjacent canonical pairs, or tensor-reducing
  first and then applying that pass still produces at most one field-strength
  insertion. The remaining first-milestone blocker is therefore a genuine
  Matchete-style loop-symmetric multi-commutator lowering stage, tied to
  `EvaluateSymmetricLorentzInds`/`CommuteCDs` behavior, not target filtering,
  post-result heavy-scalar substitution, additive `NCM` linearization, or a
  simple tensor-reduction ordering change.

## Next Work

- Choose one coherent basis/projection/backend feature family from the
  remeasured frontier. Priority candidates are:
  - Wilson-line source/simplification work for Singlet `cHW`: inspect the
    11 nonzero entrywise finite sources that now project boundedly to zero and
    identify which generated structures fail to reduce to the registered
    `H^\dagger H W^A_{\mu\nu} W^{A\mu\nu}` target, prioritizing idenso-backed
    Lorentz/field-strength/group simplification and missing Wilson-term
    source generation over projection mechanics;
  - explicit Wilson-line style supertrace representation and metadata, using
    current Matchete behavior as the reference direction rather than expanding
    the legacy CDE route;
  - Wilson-line fixture-frontier remeasurement, using
    `ValidationFixture.one_loop_preview_gap_report(..., wilson_line_*)` and
    the new per-entry/per-trace term-count metadata instead of adding more
    legacy CDE-first validation knobs;
  - target-local EOM/IBP reductions for generic operator-basis projection,
    including Higgs/gauge structures such as `cHBox`, `cHD`, `cHW`, `cHB`, and
    `cHWB`, without making those reductions SMEFT-specific;
  - source staging for heavy-scalar-substituted Wilson projection so projection
    cost scales with target-compatible field content;
  - additional idenso/spenso-backed group/CG contractions exposed by E_VLL or
    S1S3LQs fixture differences;
  - bounded Dirac/NCM simplification for fermionic current coefficients.
- Add focused regression tests for the selected feature, update these notes,
  run targeted gates, then commit and push a green milestone.
