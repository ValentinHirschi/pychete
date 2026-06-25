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
  `collect`, `derivative`, `Transformer`, polynomial/rational tools, and
  evaluators. Avoid Python tree walkers and handwritten simplifiers unless the
  native APIs are proven insufficient for that exact operation.
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
- `implementation_notes/one_shot_implementation_part_D.md` keeps the fourth
  long implementation log unchanged. It records non-Abelian infrastructure,
  pychete colour/idenso/spenso bridges, vakint namespace decoding, projection
  canonicalization, heavy-scalar dummy freshening, derivative/IBP projection
  improvements, covariant-commutator emission/lowering, CDE expansion planning,
  scalar CDE NCM projection, and cyclic closed-trace OpenCD action through
  commit `36755c2`.

## Current CDE Hybrid Source Slice

- Found that public CDE matching and validation fixture preview still used a
  pure selected-CDE aggregate whenever a CDE request was present. This was a
  structural problem for partial CDE plans: selecting one trace family could
  discard every unselected interaction-power trace.
- Added optional `exclude_trace_names` filtering to the interaction-power
  contribution, expression-map, vakint aggregate, internal aggregate, and result
  builders. This keeps filtering at the contribution boundary instead of
  rewriting backend expressions after the fact.
- Added public diagnostic setup methods:
  `interaction_bosonic_cde_hybrid_matching_result(...)`,
  `interaction_bosonic_cde_hybrid_internal_matching_result(...)`,
  `interaction_bosonic_cde_hybrid_internal_minimal_subtraction_result(...)`,
  and `interaction_bosonic_cde_hybrid_minimal_subtraction_result(...)`.
  These compose the filtered interaction-power remainder with the selected CDE
  aggregate while preserving both component supertrace maps.
- Switched public `match_one_loop(...)`, `Theory.match(..., loop_order=1)`, and
  validation fixture preview CDE branches to use the hybrid methods. The
  lower-level `interaction_bosonic_cde_*` methods remain pure selected-CDE
  diagnostics for inspecting generated terms, kernels, and backend expressions.
- Updated `OneLoopMatchOptions` docs and `AGENTS.md` to make the invariant
  explicit: public CDE requests replace only selected interaction-supertrace
  families and keep unselected interaction-power families in the one-loop
  source.
- Added regression coverage with a nonzero unselected heavy self-interaction
  trace. Public CDE matching now returns
  `interaction_power_remainder + selected_cde_replacement`, and result metadata
  records `interaction_bosonic_cde_hybrid`, selected trace names, component
  stages, and the interaction-power remainder contribution count.
- Validation for this slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "bosonic_cde" -q'`
    passed with 5 tests and 57 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_bosonic_cde_expansion_without_mathematica tests/unit/definitions/test_public_api.py -q'`
    passed with 6 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed before note rotation; rerun after this note edit
    before committing.

## Current Vakint Tensor Decode Slice

- Diagnosed the next CDE/basis obstacle after the hybrid-source fix: native
  vakint tensor reduction can preserve pychete fields and field strengths but
  return metric and Clebsch-Gordan structures as `vakint::g(...)` and
  `vakint::CG(...)`. Those native wrappers are backend implementation details;
  if they survive into public EFT expressions, pychete's projection,
  idenso/spenso simplification, and registered-SMEFT target matching do not see
  ordinary `Metric(...)` and `CG(...)` heads.
- Extended `pychete.backends.vakint.decode_pychete_namespace(...)` with
  Symbolica replacement rules for recognized native metric and CG wrappers.
  Registered CG tensor labels are resolved through theory-owned names and safe
  names, then rebuilt as central pychete `CG(...)` atoms with decoded index
  metadata. Unknown CG wrappers are intentionally left in the vakint namespace
  rather than guessed.
- Added focused unit coverage for direct wrapper decoding and for a tensor
  reduction path that produces native metric/CG wrappers. Added an integration
  regression showing the internal CDE tensor-reduction path now emits public
  pychete `Metric(...)`, `CG(...)`, and `FieldStrength(...)` structures without
  leaking `vakint::g` or `vakint::CG`.
- Validation for this slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_vakint_backend.py -q'`
    passed with 29 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "vakint_tensors or bosonic_cde_internal_tensor_reduction" -q'`
    passed with 1 test and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

## Current Validation Frontier

- Latest focused projected-condition probe for default models with
  `max_trace_order=1`, internal minimal subtraction, public `Theory.match(...)`,
  registered Wilson projection:
  - `Singlet_Scalar_Extension`: 72/72 projected targets, 42 accepted, 30
    different; 39/64 Wilson targets accepted.
  - `E_VLL`: 72/72 projected targets, 27 accepted, 45 different; 25/64 Wilson
    targets accepted.
  - `S1S3LQs`: 72/72 projected targets, 12 accepted, 60 different; 12/64
    Wilson targets accepted.
- Raising the Singlet trace order from 1 to 3 and enabling opt-in Abelian
  covariant-derivative expansion did not move the frontier.
- Selected Singlet `hScalar` CDE through order 2 now generates field-strength
  supertrace terms after cyclic OpenCD action and commutator lowering, but the
  CDE-only route previously dropped unselected traces and reported 41/72
  accepted versus the 42/72 default. The current hybrid source fix removes that
  aggregation bug; rerun targeted fixture probes only after the next feature
  slice materially changes basis/on-shell reduction or generated sources.

## Current Remaining Work

- Continue the CDE/basis-reduction feature family from the new hybrid source:
  use the cyclic derivative/field-strength CDE output together with the
  interaction-power remainder, then add the needed EOM/IBP/Warsaw-basis
  reductions before expecting gauge Wilson structures such as `cHB`, `cHW`,
  `cHWB`, `cHBox`, `cHD`, and fermionic Higgs-current coefficients to move.
- Extend idenso/spenso-backed group algebra beyond the current simple
  generator, Fierz, metric, and structure-constant cases as fixture probes
  expose missing contractions.
- Continue improving fermionic/Dirac NCM simplification through idenso-backed
  paths and Symbolica replacement rules. Conservative all-commutative scalar
  CDE `NCM(...)` scalarization is covered; arbitrary fermion/projector chains
  remain deliberately bounded.
- Broaden on-shell/EOM/IBP reduction beyond exact linear target isolation and
  target-local scalar-bilinear aliases. The remaining Singlet differences are
  dominated by gauge-dependent and Higgs-sector conditions.
- Optimize heavy-scalar solution substitution/projection so it can be enabled
  selectively for larger order-3 SMEFT projections without avoidable expression
  growth.
