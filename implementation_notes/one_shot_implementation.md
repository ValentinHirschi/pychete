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

- Port Matchete's class-wise `InternalSimplify` / `IBPSimplify` scalar
  operator grouping deeply enough for the selected Singlet `cHD` source.
- Feed the resulting formal Higgs `EOM(...)` terms into the existing scalar
  `PerformSystematicFieldRedefs` consumer.
- Verify the full public Singlet route composition: selected Wilson-line
  replacement, unselected supertrace remainder, heavy-scalar substitution,
  on-shell ordering, and registered `cHD` projection.
- Lock a full Singlet `cHD` regression, then broaden within the Singlet model.
- Defer fermion/gamma/Fierz/colour-heavy model parity until the scalar Singlet
  path is green.

The main unknown is whether scalar class-wise Green/EOM identities are enough
for this coefficient or whether 4D/evanescent identities also contribute. The
current Matchete evidence points to the scalar class-wise route:
`InternalSimplify` exposes 105 Higgs formal-EOM terms, and
`after_shift_dim6_dev3` is the first nonzero scalar field-redefinition stage.

## Current Frontier

Active Matchete checkpoint:
`helper_mathematica_scripts/debug_singlet_eom_simplify.wls` and
`assets/validation/matchete/debug/singlet_eom_cHD.debug.json`.

Active pychete checkpoint:
`scripts/debug_pychete_singlet_eom_boundary.py` and
`assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`.

Latest finding: pychete now records scalar-EOM exposure attempts for each of
the 10 nonzero selected `hScalar-lScalar-lVector-lScalar` Wilson-line entries.
After switching Wilson-line exposure to Matchete `EoMStandardForm` semantics,
four lower-order entries expose 20 formal scalar `EOM(...)` atoms total and
produce nonzero scalar field-redefinition deltas. Six high-order entries still
fail before formal scalar `EOM(...)` atoms are generated. Those failures are
split between:

- `Green-basis reduction discovered more than 256 basis terms`
- `scalar Green-basis reduction generated more than 512 identities`

The next generic algorithm work is still Matchete `InternalSimplify`
operator-class / identity-neighborhood control for the high-order entries, not
final `cHD` coefficient tuning.

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
  entries, but six high-order selected entries still exceed bounded scalar
  Green-basis exposure limits before formal scalar EOM terms appear.
- Focused validation passed for the two scalar Green tests, the Singlet `cHD`
  debug-fixture regression, py_compile on changed files, targeted mypy, and
  `git diff --check`.

## Focused Tests For This Slice

Run after completing the slice:

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python -m pytest \
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
