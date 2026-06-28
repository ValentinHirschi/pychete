# One-Shot Port Implementation Notes

## Active Plan And Non-Negotiable Guidelines

- Continue the Matchete-style one-shot one-loop matching port on branch
  `one-shot-port`, targeting the first full nontrivial integration parity on
  the Singlet Scalar Extension to SMEFT before broadening to `E_VLL` and
  `S1S3LQs`.
- The forward architecture is explicit Wilson-line trace matching. CDE remains
  legacy/diagnostic only.
- Runtime pychete and pytest remain Mathematica- and Matchete-independent.
  Wolfram scripts are optional debug/fixture-generation tools.
- Use Symbolica-native primitives first, with idenso for gamma/colour/metric
  algebra, spenso for tensor-network work, vakint for topology-independent
  tensor reduction and optional single-scale analytic checks, and pychete's
  own analytic one-loop vacuum-integral evaluator for mixed/zero-mass cases.
- Do not use or import sympy/scipy.
- For every Matchete/pychete mismatch, run or refresh focused Matchete
  WolframScript dumps, compare them against bounded pychete probes at the
  same trace/target/order/stage boundary, and patch only the first generic
  semantic divergence. Never tune a final Wilson coefficient directly.
- Run memory-risk tests and matching probes through
  `scripts/run_with_memory_watch.py --limit-gb 30 -- ...`.
- Never request sandbox permission escalation. Use the user-started
  `listener.py` `run.order` / `run.output` route for `.git` metadata writes
  and for retries after `Operation not permitted`.
- Keep this live file compact. The previous long live log was archived as
  `implementation_notes/one_shot_implementation_B.md`; earlier history also
  lives in `one_shot_implementation_part_A.md` through
  `one_shot_implementation_part_F.md`.

## Current First-Parity Estimate

The first realistic full one-loop matching integration test is still the
Singlet Scalar Extension to SMEFT, with `cHD` as the hard coefficient. The
selected `hScalar-lScalar-lVector-lScalar -> cHD` Wilson-line
trace/integral/projection path now matches Matchete's off-shell checkpoint
through propagation orders 0, 1, and 2. The remaining blocker is on-shell
operator simplification and field redefinition.

Estimated missing work for the first full nontrivial parity test is roughly
3-5 coherent slices:

- Port Matchete's class-wise `InternalSimplify` / `IBPSimplify` vector-EOM
  producer deeply enough for the selected Singlet `cHD` source. The refreshed
  Matchete replay shows the first nonzero on-shell delta at
  `after_shift_dim6_dev3`, where the pre-shift selection contains 12 formal
  vector-EOM terms over `{B, W}` and no Higgs EOM terms.
- Feed the resulting formal Abelian `B` EOM terms into pychete's bounded
  Abelian vector field-redefinition consumer, then extend the vector shift
  semantics toward the non-Abelian `W` side when needed.
- Verify the full public Singlet route composition: selected Wilson-line
  replacement, unselected supertrace remainder, heavy-scalar substitution,
  on-shell ordering, and registered `cHD` projection.
- Lock a full Singlet `cHD` regression, then broaden within the Singlet model.
- Defer fermion/gamma/Fierz/colour-heavy model parity until the scalar Singlet
  path is green.

The previous scalar-EOM route is no longer the leading explanation for the
first `cHD` delta: pychete's current scalar field-redefinition deltas project
to zero for `cHD`, and the six high-order scalar formal EOM terms are above
the dim6 selection boundary after heavy-scalar replacement. The current
Matchete evidence points instead to the formal vector-EOM route at dim6/dev3.

## Current Frontier

Active Matchete checkpoint:
`helper_mathematica_scripts/debug_singlet_eom_simplify.wls` and
`assets/validation/matchete/debug/singlet_eom_cHD.debug.json`.

Active pychete checkpoint:
`scripts/debug_pychete_singlet_eom_boundary.py` and
`assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`.

Latest finding: the Matchete debug script now dumps `selection_before_shift`
for every replayed `PerformSystematicFieldRedefs` stage. The first nonzero
`cHD` delta is `after_shift_dim6_dev3`, with 12 selected formal vector-EOM
terms over `{B, W}`. `after_shift_dim6_dev4` has one Higgs-EOM selection but
zero `cHD` delta; `after_shift_dim6_dev2` contains many Higgs-EOM terms but
does not change the already-created vector-shift delta.

Pychete now has a bounded consumer for formal Abelian vector EOM atoms:
`EOM(Field(B, Vector(...), {mu}, {}))` is routed through the same scalar-current
replacement and Abelian vector field-redefinition companion as the
`FieldStrength(B, {nu, mu}, {}, {nu})` standard form. The derivative selector
has also been corrected to count vector formal EOMs as two derivatives, matching
Matchete `EOMDevs[_Vector]`. The remaining generic work is the
`InternalSimplify` producer that exposes those formal B/W vector-EOM terms from
the selected Wilson-line source; the current exact current-current bridge still
finds no vector divergence in the selected pychete probe.

## Current Implementation Slice

- Added `scalar_derivative_green_normal_form_by_operator_class(...)`, which
  applies the existing Symbolica-backed scalar Green solver per
  Matchete-style operator class instead of one global local basis.
- Wired Wilson-line formal scalar EOM exposure to that class-wise helper.
- Refactored Wilson-line scalar EOM postprocessing out of
  `matching.py` into `src/pychete/wilson_line_eom.py`.
- Refreshed the Singlet `cHD` pychete boundary fixture. The class-wise pass
  plus `EoMStandardForm`-only exposure now exposes formal scalar EOM terms and
  nonzero scalar field-redefinition deltas for four lower-order selected
  entries. The hybrid finite operator-basis path now also exposes formal
  scalar EOM terms for the six high-order selected entries without recursive
  Green-basis cap failures, but those high-order exposed terms still produce
  zero scalar field-redefinition deltas.
- Refreshed the Matchete `singlet_eom_cHD.debug.json` fixture with
  `selection_before_shift` data. This narrowed the first on-shell mismatch to
  dim6/dev3 vector EOM terms rather than scalar EOM deltas.
- Added a bounded pychete consumer for formal Abelian vector EOM atoms and
  fixed `operator_derivative_count(...)` so vector formal EOMs count as two
  derivatives.
- Focused validation passed for the scalar Green/operator-basis tests, the
  Wilson-line scalar EOM hook tests, the Singlet `cHD` debug-fixture
  regression, py_compile on changed files, targeted mypy, and
  `git diff --check`.

## Focused Tests For This Slice

Run after completing the slice:

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python -m pytest \
  tests/unit/functional/test_scalar_eom.py::test_eom_replacement_rules_collect_formal_abelian_vector_eom_targets \
  tests/unit/functional/test_scalar_eom.py::test_formal_vector_eom_terms_use_matchete_dimension_and_derivative_count \
  tests/unit/functional/test_scalar_green_bilinears.py::test_scalar_derivative_green_standard_form_eom_ignores_interaction_terms \
  tests/unit/functional/test_scalar_green_bilinears.py::test_scalar_derivative_green_normal_form_by_operator_class_keeps_basis_local \
  tests/unit/functional/test_scalar_green_bilinears.py::test_wilson_line_scalar_green_hook_closes_four_derivative_formal_eom_neighborhood \
  tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_selected_chd_pychete_boundary_fixture_records_pre_eom_gap -q
dependencies/.venv/bin/python -m py_compile \
  src/pychete/functional.py src/pychete/matching.py src/pychete/wilson_line_eom.py \
  scripts/debug_pychete_singlet_eom_boundary.py \
  tests/unit/functional/test_scalar_green_bilinears.py \
  tests/integration/matching/test_singlet_selected_wilson_coefficients.py
dependencies/.venv/bin/python -m mypy \
  src/pychete/functional.py src/pychete/matching.py src/pychete/wilson_line_eom.py \
  scripts/debug_pychete_singlet_eom_boundary.py \
  tests/unit/functional/test_scalar_green_bilinears.py \
  tests/integration/matching/test_singlet_selected_wilson_coefficients.py
git diff --check
```
