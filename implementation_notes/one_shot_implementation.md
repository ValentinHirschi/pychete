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

## Current Field-Strength Metric Simplification Slice

- Probed the Singlet scalar CDE/tensor-reduced public path after vakint wrapper
  decoding. The output did contain pychete `FieldStrength(...)`, but the
  immediate order-2 CDE terms were single field strengths whose two Lorentz
  slots were contracted by `Metric(b, c)`. These terms are zero by
  field-strength antisymmetry, and keeping them alive obscures later
  basis-projection diagnostics.
- Added `pychete.backends.idenso.simplify_pychete_field_strength_metrics(...)`.
  It uses Symbolica `Replacement` rules to contract pychete `Metric`/`Delta`
  factors into `FieldStrength(...)` Lorentz slots, drop traced
  `Metric(mu, nu) * FieldStrength(... {mu, nu} ...)` terms, and canonicalize
  the antisymmetric Lorentz-slot ordering. The helper is wired into
  `simplify_index_algebra(..., metrics=True)`.
- Public `match_one_loop(...)` now applies this field-strength metric cleanup
  to the generated result before heavy-scalar substitution, on-shell
  reduction, EFT truncation, and matching-condition projection. Low-level CDE
  diagnostic builders remain raw so generated kernels and backend output can
  still be inspected.
- Added focused backend tests for metric-slot contraction, traced
  field-strength cancellation, Lorentz antisymmetry, and the idenso pipeline.
  Added an integration regression showing public CDE/tensor-reduced matching
  removes the spurious metric-traced field strengths while preserving the raw
  diagnostic coverage from the previous vakint decode slice.
- Validation for this slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_idenso_backend.py -q'`
    passed with 25 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "vakint_tensors or metric_traced_field_strengths" -q'`
    passed with 2 tests and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

## Current Vakint Covariant-Derivative Decode Slice

- Probed the small heavy-scalar/Higgs/SU(2) CDE path at total derivative order
  4. After tensor reduction and field-strength metric cleanup, the public
  result still contained `vakint::CD(...)` wrappers around products with nested
  vakint namespace heads. That blocks pychete's existing
  `expand_cd_operators(...)` and matching-condition projection normalizers,
  which deliberately operate on the central `CD(...)` head.
- Extended `pychete.backends.vakint.decode_pychete_namespace(...)` with a
  two-phase decode. The first phase decodes ordinary nested vakint heads such
  as `Field`, `FieldStrength`, `Coupling`, `Index`, `CG`, and `g`; the second
  phase wraps already-decoded derivative bodies as pychete `CD(...)`. This
  avoids returning `CD(...)` nodes whose bodies still contain native vakint
  namespace payloads.
- Added a direct vakint backend unit test for `vakint::CD(vakint::List(...),
  vakint::Field(...))` and an integration regression for public order-4 CDE
  matching. The public order-4 CDE result now has pychete `CD(...)` and
  `FieldStrength(...)` structures without `vakint::CD` or `vakint::List`.
- Validation for this slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_vakint_backend.py -q'`
    passed with 30 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "vakint_tensors or metric_traced_field_strengths or order_four_covariant_derivatives" -q'`
    passed with 3 tests and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

## Current Native Colour Chain Decode Slice

- Probed the order-4 CDE colour/basis frontier after `vakint::CD` decoding.
  Registered Wilson projections for `cHW`, `cHBox`, `cHD`, and `cH` remained
  zero even though the public source now contains pychete `FieldStrength(...)`
  and `CD(...)` atoms. A direct result-level
  `simplify_pychete_color_algebra(...)` attempt was not viable: the existing
  bridge could hang on native `spenso::chain(...)` wrappers produced by
  idenso/spenso for generator products multiplied by pychete field-strength
  payloads.
- Bounded probes showed that native idenso/spenso stages were not the slow
  part: `simplify_color(...)` and `simplify_metrics(...)` returned quickly.
  The hang started in pychete's decode layer because `_decode_native_color_tensors`
  used repeating Symbolica replacements while returning the original expression
  for an undecodable multi-generator native chain.
- Updated `pychete.backends.idenso` so native colour metric and tensor decoders
  use non-repeating decode-only replacements. Added bounded decoding for
  native `spenso::chain(left, right, t(...), ...)` generator products up to the
  same kind of fixed arity cap used elsewhere in the backend adapters. Decoded
  multi-generator chains become ordered products of registered pychete
  `CG(gen_..._fund, ...)` atoms with generated theory-owned internal index
  labels; this is representation decoding only, not a handwritten SU(N)
  simplification rule.
- Added `decode_native_color_wrappers(...)` as a decode-only public backend
  helper for post-result matching expressions. Full native
  `simplify_pychete_color_algebra(...)` remains available for controlled
  colour-bearing kernels/subexpressions, but public post-result CDE cleanup now
  decodes already-native colour wrappers without running idenso's global colour
  simplifier across generated pychete CDE/Lorentz structures. This avoids the
  native `d1` abstract-index conversion failure seen in result-level probes.
- Added unit coverage for the previously hanging shape:
  `Bar(H) H gen(A) gen(B) FieldStrength(A) FieldStrength(B)`. The simplified
  expression now returns immediately, preserves the pychete field-strength
  payload, emits two registered pychete generator CG atoms, and leaks no
  `spenso::` wrappers.
- Updated `AGENTS.md` to require native generator-chain wrappers to decode back
  to pychete CG products before public matching output is exposed, while still
  forbidding handwritten Python SU(N) identities.
- Validation for this slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_idenso_backend.py -q'`
    passed with 26 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_option_simplifies_pychete_color_algebra -q'`
    passed with 1 test.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "vakint_tensors or metric_traced_field_strengths or order_four_covariant_derivatives" -q'`
    passed with 3 tests and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

## Current Vakint Constant Decode Slice

- Continued probing the order-4 CDE Wilson projection failure. The public CDE
  source contains pychete `FieldStrength(...)` and `CD(...)` atoms, but direct
  Wilson projection for `cHW`, `cHBox`, `cHD`, and `cH` still returns zero.
  The immediate actionable backend-boundary issue found in this probe was a
  public-output leak of `vakint::𝑖` from both native vakint evaluation results
  and pychete's internal analytic vacuum-integral normalization.
- Extended `pychete.backends.vakint.decode_pychete_namespace(...)` so native
  vakint imaginary-unit and pi symbols (`vakint::𝑖`, `vakint::I`,
  `vakint::𝜋`, `vakint::π`) decode to Symbolica's `Expression.I` and
  `Expression.PI` through Symbolica replacement rules. The direct backend unit
  test now verifies that those constants normalize canonically.
- Changed `pychete.backends.vacuum_integrals.imaginary_unit_symbol()` to return
  native `Expression.I` directly. This keeps pychete-owned analytic
  one-loop-evaluation output in Symbolica form instead of reusing vakint's
  namespace convention.
- Updated the vakint/internal cross-check tests so raw native vakint results
  are decoded before comparing against pychete's internal analytic evaluator.
  The equality check still validates agreement with vakint, but now at the
  pychete backend boundary representation.
- Added an order-4 public CDE regression assertion that `vakint::𝑖` does not
  leak into matching output.
- Validation for this slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_vakint_backend.py tests/unit/backends/test_vacuum_integrals_backend.py -q'`
    passed with 68 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "vakint_tensors or metric_traced_field_strengths or order_four_covariant_derivatives" -q'`
    passed with 3 tests and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

## Current SU(2) Field-Strength Projection Slice

- Followed the next order-4 CDE blocker after backend wrapper/constant cleanup:
  the generated source had pychete `FieldStrength(...)` atoms and decoded
  generator CG tensors, but the `cHW` registered Wilson projection stayed zero.
  The immediate cause was twofold. First, barred non-Abelian generator
  insertions used the same output/input-dual orientation as unbarred fields,
  producing duplicate dual slots that native idenso/spenso could not contract.
  Second, the Wilson target is conventionally normalized as
  `Hbar H W^A W^A / gL^2`, while the projection extractor only tried direct
  coefficient extraction on that negative-power target.
- Corrected `Theory.non_abelian_gauge_generator_insertion(...)` and the
  commutator field/field-strength insertion paths so barred/conjugate fields
  use `CG(gen, adjoint, input, output_dual) * Bar(field(output))`. This keeps
  generated fund/dual contractions explicit for native backend algebra.
- Added `pychete.backends.idenso.simplify_su2_field_strength_generator_bilinears(...)`.
  It matches the symmetric SU(2) CDE structure
  `Bar(H_j) H_i T^A_{i k} T^B_{k j} W^A W^B` with Symbolica replacement rules,
  computes the singlet coefficient from an idenso-simplified contracted
  generator trace, and rewrites the term to the Warsaw-like
  `Bar(H_i) H_i W^A W^A` structure. This remains in the idenso backend path and
  avoids a Wilson-specific projection special case.
- Wired that helper into the opt-in public colour cleanup path after native
  colour wrapper decoding. Public result metadata now records
  `su2_field_strength_generator_bilinears_simplified` when this cleanup path is
  active.
- Extended matching-condition coefficient extraction so negative-power target
  normalizations are handled generically. If exact extraction of a target such
  as `operator / g^2` vanishes, pychete extracts the numerator monomial and
  multiplies the denominator factor back into the coefficient. EFT truncation
  now uses the same extractor so registered Wilson projection and
  target-selective truncation agree.
- Updated the order-4 public CDE regression to register `cHW`, project
  `registered_wilsons`, and assert the projected coefficient is nonzero.
- Validation for this slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_idenso_backend.py::test_idenso_bridge_projects_su2_field_strength_generator_bilinear_to_singlet tests/unit/definitions/test_theory_definitions.py -k "non_abelian or covariant_derivative_commutator" -q'`
    passed with 19 tests and 29 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_spenso_backend.py::test_spenso_backend_lowers_generated_non_abelian_derivative_cg_tensors tests/unit/backends/test_idenso_backend.py::test_idenso_bridge_decodes_native_generator_chain_with_pychete_payload -q'`
    passed with 2 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_decodes_order_four_covariant_derivatives -q'`
    passed with 1 test.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_negative_power_normalized_wilson_targets tests/unit/backends/test_idenso_backend.py::test_idenso_bridge_projects_su2_field_strength_generator_bilinear_to_singlet tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_decodes_order_four_covariant_derivatives -q'`
    passed with 3 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_idenso_backend.py tests/unit/definitions/test_theory_definitions.py tests/integration/validation/test_numeric_probes.py -q'`
    passed with 108 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

## Current Mixed SU(2)-U(1) Field-Strength Projection Slice

- Probed the next gauge/Higgs CDE frontier by adding U(1) hypercharge to the
  small heavy-scalar/Higgs/SU(2) order-4 CDE smoke model. The existing source
  already projected nonzero `cHB` once the Higgs carried `Y=1/2`, but `cHWB`
  remained zero even though mixed `B_{\mu\nu} W^A_{\mu\nu}` structures and
  registered SU(2) generator CG tensors were present.
- Added
  `pychete.backends.idenso.simplify_su2_u1_field_strength_generator_bilinears(...)`.
  It uses Symbolica replacement rules over theory-owned field, group, and CG
  metadata to rewrite generated `H_i Bar(H_j) T^A_{i j} W^A B` CDE source
  structures into the registered Warsaw mixed-field-strength orientation. The
  U(1) charge, `gY`, and `gL` remain in the ordinary symbolic coefficient; the
  helper is only an index-orientation normalization and not a Wilson-specific
  coefficient rule.
- Wired the mixed helper into the same opt-in native-colour cleanup path as
  the SU(2) singlet helper. Public result metadata now records
  `su2_u1_field_strength_generator_bilinears_simplified` when that path is
  active.
- Extended `MatchingResult` coefficient extraction in two generic ways:
  numeric prefactors in target monomials are factored out before projection,
  and the final indexed-target fallback now asks Symbolica
  `Expression.canonize_tensors(...)` for the canonical target expression plus
  returned external/dummy index lists before replacing those canonical target
  indices by linked wildcards. Matched monomials are replaced by a temporary
  marker and its coefficient is extracted natively. This covers
  conjugate-representation label pairs such as the `cHWB` generator slot
  without a Python tree matcher or a separate pychete dummy-index canonicalizer.
- Updated the order-4 public CDE regression to include both `SU2L` and `U1Y`,
  register `cHW`, `cHB`, and `cHWB`, and assert all three projected Wilson
  conditions are nonzero.
- Validation for this slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_numeric_prefactor_normalized_targets tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_alpha_equivalent_conjugate_representation_indices tests/unit/backends/test_idenso_backend.py::test_idenso_bridge_canonicalizes_mixed_su2_u1_field_strength_generator_bilinear tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_decodes_order_four_covariant_derivatives -q'`
    passed with 4 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_idenso_backend.py tests/integration/validation/test_numeric_probes.py -q'`
    passed with 64 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "order_four_covariant_derivatives or metric_traced_field_strengths or vakint_tensors" -q'`
    passed with 3 tests and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

### Canonical Tensor-Index Follow-Up

- After the green mixed-field-strength commit, tightened the indexed-target
  fallback to explicitly use Symbolica's `canonize_tensors` return values. The
  previous implementation already ran after projection-source/target
  canonicalization, but it built wildcards from every target index by scanning
  the expression. The refined path now builds its pattern from the canonical
  target and the canonical external/dummy index lists returned by Symbolica,
  falling back to the scan only when native tensor canonicalization raises.
- Focused validation for the follow-up:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_alpha_equivalent_conjugate_representation_indices tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_alpha_equivalent_index_contractions tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_canonicalizes_higgs_derivative_current_to_chd tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_numeric_prefactor_normalized_targets -q'`
    passed with 4 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_decodes_order_four_covariant_derivatives -q'`
    passed with 1 test.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_idenso_backend.py tests/integration/validation/test_numeric_probes.py -q'`
    passed with 64 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "order_four_covariant_derivatives or metric_traced_field_strengths or vakint_tensors" -q'`
    passed with 3 tests and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

### Registered Wilson IBP Projection Follow-Up

- Started by probing a broader order-4/order-6 CDE source for the small
  heavy-scalar/Higgs/SU(2)xU(1) regression, but the broad probe was too slow
  for the slice and was stopped. The slice was narrowed to a projection
  improvement that directly affects the known `cHBox` frontier.
- Updated `MatchingResult.project_matching_conditions(...)` so registered
  Wilson-coefficient targets with stored operator metadata use target-local
  scalar-bilinear IBP aliases automatically. Raw expression targets remain
  exact by default and still require `normalize_ibp_scalar_bilinears=True`.
- Tightened alias canonicalization: whenever any IBP alias exists, the source,
  projection target, and alias expressions are sent through the same
  Symbolica-native tensor-index canonicalization path before wildcard-index
  projection fallback. This keeps the latest `canonize_tensors(...)` index
  alignment behavior active for automatically generated registered-Wilson
  aliases too.
- Added a focused `cHBox` regression using the registered SMEFT Wilson target
  from the Singlet validation fixture. The same source still projects zero
  against the raw Warsaw operator target by default, while the registered
  Wilson target now projects the expected coefficient through its stored
  operator metadata.
- Focused validation for this follow-up:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_uses_registered_wilson_ibp_aliases tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_handles_indexed_smeft_hbox_ibp_alias tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_canonicalizes_higgs_derivative_current_to_chd -q'`
    passed with 3 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -q'`
    passed with 37 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

### Termwise CDE Evaluation And Target-Filtered Projection

- Probed the next Higgs-sector CDE frontier after the `cHW/cHB/cHWB` and
  registered-IBP projection slices. The one-insertion `hScalar` CDE source
  contains two-Higgs derivative terms and field-strength structures, but it
  cannot project quartic Higgs derivative Warsaw targets. The relevant source
  for those terms is the two-insertion `hScalar-hScalar` trace at total CDE
  derivative order 2.
- A public `hScalar-hScalar` CDE run with tensor reduction and registered
  Wilson projection initially hung. Lower-level inspection showed CDE term
  generation was fast and the generated numerators contained the expected
  quartic Higgs derivative structures. Tensor-reducing/evaluating the five
  generated CDE terms independently returned quickly, while tensor-reducing
  the monolithic summed topology did not.
- Updated `OneLoopSetup.interaction_bosonic_cde_internal_integral_sum(...)` to
  use generated `BosonicCDETraceExpansionTerm` objects as the backend boundary:
  build each term's topology, optionally tensor-reduce it with vakint, decode
  pychete namespaces, evaluate the scalar vacuum topology with pychete's
  analytic backend, and only then sum all evaluated terms. Public result
  metadata now records
  `interaction_bosonic_cde_internal_termwise_evaluation=True`.
- The next hotspot was registered Wilson projection on large composite targets.
  Added a conservative source prefilter inside `_ProjectionCoefficientExtractor`
  before native `Expression.coefficient(...)`: for each additive target term,
  collect registered field and field-strength label requirements with
  Symbolica patterns, keep source terms whose dynamical-label content can match
  that target term, reject terms with extra field/field-strength labels, and
  then delegate coefficient extraction to Symbolica. The filter is conservative
  around powered field monomials, where pattern multiplicities do not directly
  encode powers.
- Added a public CDE regression for the two-insertion heavy-scalar/Higgs trace.
  With `hScalar-hScalar`, total CDE order 2, tensor reduction, internal
  analytic integral evaluation, and registered Wilson projection, pychete now
  projects a nonzero `cHD` coefficient from the small model in about one
  second. `cHBox` remains a broader Higgs-sector reduction frontier item.
- Probed the three-insertion `hScalar-hScalar-hScalar` CDE source for the Higgs
  potential operator `cH`. The source existed but reused the same portal dummy
  Higgs index in every trace entry, producing an over-contracted expression
  like `H[d1]^3 Bar(H[d1])^3` that could not canonically project to the
  registered SMEFT target. Each ordered CDE trace-entry operand now freshens
  its local dummy contractions with `relabel_dummy_indices(...)` before the NCM
  chain is multiplied. The public regression verifies that the generated
  numerator has three independent dummy contractions and that the registered
  `cH` Wilson coefficient projects nonzero through Symbolica's
  `Expression.canonize_tensors(...)`-enabled projection path.
- Focused validation for this slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_projects_three_insertion_higgs_potential_operator -q'`
    passed with 1 test.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_projects_two_insertion_higgs_derivative_operator -q'`
    passed with 1 test.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "order_four_covariant_derivatives or two_insertion_higgs_derivative_operator or three_insertion_higgs_potential_operator or bosonic_cde_internal_tensor_reduction or metric_traced_field_strengths" -q'`
    passed with 5 tests and 62 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -q'`
    passed with 37 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

### Projection Performance Follow-Up For Substituted Singlet Probes

- Reran the default projected-condition frontier test after the CDE `cH`
  source fix. The tracked `max_trace_order=1` frontier remains unchanged:
  Singlet stays at `42/72` accepted matching conditions and `39/64` accepted
  Wilson targets; `E_VLL` and `S1S3LQs` remain at the previous `27/72` and
  `12/72` accepted counts. This confirms the focused CDE fixes do not affect
  the old order-1 interaction-power report by themselves.
- Probed Singlet with selected CDE traces
  `hScalar`, `hScalar-hScalar`, and `hScalar-hScalar-hScalar` through total CDE
  order 0. The report still remained at `42/72` and `39/64` accepted Wilsons.
  Inspecting selected coefficients showed the new `cH` source is present in
  the candidate as the pure `kappa^3/M^2` term, while the Matchete reference
  `cH` includes the larger `hbar`, logarithmic, and trilinear-`A` dependent
  tree/one-loop structure. The next Singlet improvement therefore needs the
  heavy-scalar substitution/on-shell reduction path, not only CDE projection.
- Attempted the public-match Singlet gap report with
  `substitute_heavy_scalar_solutions=True`. With global EFT truncation enabled,
  the run hung in global `series_eft(...)` expansion. Added a
  `ValidationFixture.one_loop_preview_gap_report(..., truncate_eft_result=...)`
  pass-through so `use_public_match_api=True` can set
  `OneLoopMatchOptions.truncate_eft_result=False` while keeping
  `matching_condition_projection_truncate_eft=True` for target-local Wilson
  truncation. This exposes the intended performance mode to fixture probes.
- With global truncation disabled, the broad substituted Singlet projection
  still remained too slow. Stack traces showed two projection hotspots:
  duplicate full-source tensor canonicalization for target-local IBP aliases,
  and repeated field/field-strength label counting plus expansion of filtered
  source subsets in `_ProjectionCoefficientExtractor`.
- Updated projection internals so the source, projection targets, and flat IBP
  aliases are canonicalized through one shared
  `Expression.canonize_tensors(...)` index-spec path, avoiding a second
  full-source canonicalization pass. The projection extractor now caches the
  source term tuple and each term's field/field-strength label counts, and it
  returns the filtered source sum without expanding it before native Symbolica
  coefficient/collect/factor fallbacks. Focused regressions verify one source
  canonicalization when aliases exist and one source-term label scan reused
  across multiple projection targets.
- Follow-up target-local projection work replaced the remaining global
  projection canonicalization with an exact-first path plus filtered
  target-local canonicalization. For each target, pychete first asks native
  Symbolica `Expression.coefficient(...)` for the raw exact coefficient with
  wildcard dummy-index fallback disabled. That result is accepted without
  `canonize_tensors(...)` only if `coefficient * target` exhausts the
  conservatively filtered target-local source; otherwise the target, its IBP
  aliases, and only the filtered source subset are canonicalized together with
  Symbolica `Expression.canonize_tensors(...)`. This keeps exact isolated
  indexed projections cheap while preserving contributions from
  alpha-equivalent dummy-index terms. The implementation treats Symbolica's
  `canonize_tensors(...)` result as the native dummy-index canonicalization
  authority; no Python dummy-index canonicalizer was added.
- Added projection regressions for the exact-index fast path and for mixed
  exact plus alpha-equivalent source terms. The first test fails if tensor
  canonicalization is called for a source that is exactly `coefficient *
  target`; the second verifies that exact-first projection does not drop the
  dummy-renamed contribution.
- The broad substituted Singlet public-match report with
  `substitute_heavy_scalar_solutions=True`, global EFT truncation disabled,
  target-local projection truncation enabled, and reference-condition
  projection enabled now completes as a smoke probe in about 10.6 seconds.
  The frontier did not improve yet: it remains `42/72` accepted common
  matching conditions and `39/64` accepted common Wilson conditions. The next
  slices should therefore focus less on projection throughput and more on the
  missing physics/content: full heavy-scalar substitution/on-shell terms,
  higher CDE trace coverage, basis reduction, and remaining Matchete parity
  pieces.
- Focused validation for this follow-up:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_skips_tensor_canonization_for_exact_index_match tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_adds_exact_and_alpha_equivalent_index_matches tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_canonizes_source_once_for_ibp_aliases tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_reuses_source_term_atom_counts tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_alpha_equivalent_index_contractions tests/integration/validation/test_numeric_probes.py::test_matching_result_projects_alpha_equivalent_conjugate_representation_indices tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_canonicalizes_higgs_derivative_current_to_chd -q'`
    passed with 7 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -q'`
    passed with 41 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_forwards_pychete_color_to_public_match_api tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_projected_matching_condition_frontier_without_mathematica -q'`
    passed with 2 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.
  - Smoke probe only, not yet a committed test gate:
    `fixture.one_loop_preview_gap_report(... use_public_match_api=True,
    substitute_heavy_scalar_solutions=True, truncate_eft_result=False,
    matching_condition_projection_expand_source=False,
    matching_condition_projection_truncate_eft=True,
    matching_condition_projection_normalize_ibp_scalar_bilinears=True,
    project_reference_matching_conditions=True)` for
    `Singlet_Scalar_Extension` completed in about 10.6 seconds and reported
    `42/72` accepted common matching conditions and `39/64` accepted common
    Wilson conditions.

### Simple-Coupling Projection Prefilter Follow-Up

- Probed selected Singlet renormalizable matching conditions after the
  target-local projection slice. Direct public matching for only `mu2` and
  `lambda`, with heavy-scalar solution substitution enabled and global EFT
  truncation disabled, now completes in about 13 seconds. The candidate still
  returns only the tree-level identities `mu2` and `lambda`, while the Matchete
  reference includes large one-loop threshold corrections with `hbar`, pole,
  logarithmic, portal-coupling, trilinear-`A`, and gauge-dependent terms. This
  confirms that the renormalizable-condition gap is missing matching content,
  not merely projection shape.
- Added a conservative simple-coupling projection prefilter to
  `_ProjectionCoefficientExtractor`. For exact registered
  `Coupling(label, indices, order)` projection targets, pychete now filters the
  source term tuple with a native Symbolica `Coupling(label, _, _)` pattern and
  then delegates the actual coefficient extraction to Symbolica's
  `Expression.coefficient(...)`, `collect_factors(...)`, and `factor(...)`
  fallbacks. No Python-side coupling algebra or polynomial reasoning was
  added.
- Added a focused regression proving that unrelated source terms are excluded
  from the simple-coupling filtered source while public projection still
  returns the native Symbolica coefficient.
- A direct single-target `cH` public projection over the heavy-scalar
  substituted Singlet source still did not return inside the interactive
  diagnostic window and was stopped. The next Wilson-focused performance slice
  should reduce the substituted Wilson source before projection, likely by
  splitting the post-substitution source into field-label-compatible pieces or
  by applying basis/on-shell reductions before target projection.

### Large-Source Projection Factor-Gate Follow-Up

- Profiled direct `cH` projection over a heavy-scalar-substituted Singlet
  result by splitting source generation from projection. Source generation
  completed in about 13.1 seconds, then projection stalled in
  `_ProjectionCoefficientExtractor._factored_source(...)`, i.e. native
  `Expression.factor()` on the filtered Higgs-only source. The filtered `cH`
  source had only six terms but about 31 KB of Symbolica expression data, so
  term count alone was not a sufficient complexity guard.
- Added a bounded factor fallback for matching-condition projection. The
  extractor still tries native `Expression.coefficient(...)` and
  `collect_factors()` first, but it now skips the global `factor()` fallback
  unless the filtered source is small by both Symbolica term count and
  `Expression.get_byte_size()`. The final wildcard-index projection fallback
  now uses the already filtered source rather than the full matching source.
  This keeps the operation native-Symbolica based while avoiding an expensive
  global factorization on large substituted sources.
- Added regressions showing that projection skips the factor fallback for both
  many-term filtered sources and few-term but large-byte filtered sources.
- Re-ran the separated direct `cH` probe after the factor gate. The substituted
  source still builds in about 13.2 seconds, but `cH` projection now returns in
  about 0.26 seconds with coefficient `0`. This turns the previous projection
  hang into an inspectable missing-source/reduction frontier: current
  max-trace-order-1 substituted Singlet output does not yet contain the
  Matchete `cH` contribution in a projectable form.
- Focused validation for this follow-up:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_skips_factor_fallback_for_large_filtered_sources tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_skips_factor_fallback_for_large_expression_sources tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_prefilters_simple_coupling_targets tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_adds_exact_and_alpha_equivalent_index_matches -q'`
    passed with 4 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -q'`
    passed with 44 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_projected_matching_condition_frontier_without_mathematica -q'`
    passed with 1 test.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.

### Selected CDE Trace Construction And Tensor-Index Comparison Follow-Up

- Probed the Singlet `cH` frontier through the selected bosonic CDE path
  `hScalar-hScalar-hScalar` at total derivative order zero. Before this slice,
  the selected CDE request still built the full interaction supertrace map and
  the diagnostic took roughly 33 seconds. After target-local selected trace
  construction, the same probe completes in about 15.7 seconds.
- The selected Singlet CDE candidate remains only the partial three-insertion
  source `i*kappa^3/(32*pi^2*M^2)`, while Matchete's `cH` reference contains
  additional threshold, tree/on-shell, and basis-reduction terms involving
  `A`, `muphi`, logs/poles, and lower powers of `M`. This confirms the current
  blocker is matching-content and reduction completeness, not the projection
  hang fixed in the previous slice.
- Added direct interaction category-block construction for selected CDE trace
  names. Explicit CDE maps and `bosonic_cde_trace_names` now validate requested
  trace names with the lightweight cyclic-unique trace-name enumerator, then
  build only those category chains. Repeated category-pair blocks inside a
  selected trace are cached.
- Added `MatchingResult.compare_to(..., canonize_indices=True)`, defaulting to
  native Symbolica tensor-index canonicalization before canonical string
  comparison. This uses `Expression.canonize_tensors(...)` through the existing
  projection index-spec helper so alpha-equivalent dummy-index contractions do
  not appear as false canonical differences. `canonize_indices=False` remains
  available for diagnostics.
- Updated `AGENTS.md` to explicitly require Symbolica
  `Expression.canonize_tensors(...)` for dummy-index alignment and to require
  selected CDE trace requests to avoid full interaction-supertrace plan
  construction.
- Focused validation for this follow-up:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_interaction_bosonic_cde_expansion_maps_selected_trace_to_kernel_and_vakint tests/integration/matching/test_fluctuation_operator.py::test_selected_bosonic_cde_builds_only_requested_interaction_category_blocks tests/integration/validation/test_numeric_probes.py::test_matching_result_comparison_canonizes_alpha_equivalent_index_contractions -q'`
    passed with 3 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_matching_preserves_unselected_interaction_traces tests/integration/matching/test_fluctuation_operator.py::test_public_bosonic_cde_matching_projects_scalar_ncm_chains -q'`
    passed with 2 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -k "comparison_canonizes or projects_alpha_equivalent_index_contractions or projection_canonizes_source_once or skips_tensor_canonization or adds_exact_and_alpha_equivalent" -q'`
    passed with 5 tests and 40 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m mypy'`
    passed.
  - `git diff --check` passed.
- A broader `pytest -k "bosonic_cde or selected_bosonic_cde"` run was stopped
  after several minutes to preserve the requested testing discipline; the
  directly impacted CDE and projection tests above passed.

### Indexed-Power Projection And Tree-Plus-Loop Source Follow-Up

- Diagnosed the next Singlet `cH` gap after the selected CDE slice. The
  tree-level heavy-scalar matched EFT already contains the expected
  `-A^2*kappa/(2*M^4) + A^3*muphi/(6*M^6)` Higgs-six terms, but pychete stored
  them as indexed-power shorthand such as `H[d1]^3*bar(H[d1])^3`. The
  registered SMEFT `cH` operator is written with three independent dummy
  contractions, so projection returned zero even though the source term was
  present.
- Added projection-local normalization for powers of indexed `Field(...)` and
  `Bar(Field(...))` atoms. It uses a Symbolica power-pattern replacement
  callback to expand powered indexed atoms into fresh-index products, then
  delegates dummy-index alignment to native `Expression.canonize_tensors(...)`.
  The same normalized shape is used for the projection atom prefilter, so
  powered indexed fields are counted with the correct multiplicity instead of
  being filtered away before canonicalization.
- Added `OneLoopMatchOptions.include_tree_level_matching`. When enabled,
  `match_one_loop(...)` computes pychete's tree-level heavy-scalar matched EFT
  source and adds it to the off/on-shell one-loop result after loop
  normalization and before final truncation/projection. The loop-only stages
  are preserved as `loop_only_off_shell_eft_lagrangian` and
  `loop_only_on_shell_eft_lagrangian`, and the tree source is exposed as
  `tree_level_eft_lagrangian`.
- Forwarded `include_tree_level_matching` through validation fixture public
  match gap reports so Matchete-style full matching-condition probes can opt
  into tree-plus-loop sources.
- Re-ran a focused Singlet `cH` public smoke with selected
  `hScalar-hScalar-hScalar` CDE and `include_tree_level_matching=True`. It
  completed in about 16.9 seconds and projected
  `-A^2*kappa/(2*M^4) + A^3*muphi/(6*M^6) + i*kappa^3/(32*pi^2*M^2)`. This
  closes the previously missing tree-level `cH` pieces for that route; the
  remaining difference to Matchete is still the broader one-loop threshold,
  pole/log, and on-shell/basis-reduction content.
- Focused validation for this follow-up:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py::test_matching_result_projection_expands_indexed_higgs_bilinear_powers_to_ch tests/integration/validation/test_numeric_probes.py::test_singlet_tree_matching_projects_ch_power_terms tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_can_include_tree_level_matching_source tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_forwards_pychete_color_to_public_match_api -q'`
    passed with 4 tests.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -k "projection_ or comparison_canonizes or singlet_tree" -q'`
    passed with 17 tests and 30 deselected.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_heavy_scalar_tree.py -q'`
    passed with 20 tests.
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
- Focused CDE regressions now produce nonzero projected `cHW`, `cHB`, `cHWB`,
  `cHD`, and `cH` coefficients for small heavy-scalar/Higgs models. The
  field-strength targets come from the one-insertion order-4 `hScalar` source,
  `cHD` comes from the two-insertion order-2 `hScalar-hScalar` source, and `cH`
  comes from the three-insertion order-0 `hScalar-hScalar-hScalar` source. The
  default fixture frontier above was rerun after the focused CDE slices and
  remains unchanged until heavy-scalar substitution/on-shell reduction becomes
  viable in the projected Singlet report.

## Current Remaining Work

- Continue the CDE/basis-reduction feature family from the new hybrid source:
  use the cyclic derivative/field-strength CDE output together with the
  interaction-power remainder, then add the needed EOM/IBP/Warsaw-basis
  reductions for remaining gauge/Higgs Wilson structures such as `cHBox` and
  fermionic Higgs-current coefficients. `cHW`, `cHB`, `cHWB`, `cHD`, and `cH`
  now have focused nonzero CDE projections, but default fixture parity has not
  yet been remeasured.
- Extend idenso/spenso-backed group algebra beyond the current simple
  generator, Fierz, metric, structure-constant, and native generator-chain
  decode cases as fixture probes expose missing contractions.
- Continue improving fermionic/Dirac NCM simplification through idenso-backed
  paths and Symbolica replacement rules. Conservative all-commutative scalar
  CDE `NCM(...)` scalarization is covered; arbitrary fermion/projector chains
  remain deliberately bounded.
- Broaden on-shell/EOM/IBP reduction beyond exact linear target isolation and
  target-local scalar-bilinear aliases. The remaining Singlet differences are
  dominated by gauge-dependent and Higgs-sector conditions.
- Continue reducing heavy-scalar-substituted Wilson projection cost. The broad
  substituted Singlet report now completes, and simple coupling targets are
  filtered cheaply. Direct `cH` projection over the substituted source is now
  fast and returns zero, so the next work is source/basis completeness rather
  than projection throughput for that target. Future slices should split
  substituted source stages by target-compatible field content and apply
  basis/on-shell reductions before projection.
