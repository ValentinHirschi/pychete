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
- Treat performance parity as part of semantic parity. Intermediate pychete
  probes should be at least as performant as the corresponding Matchete stage;
  if not, first look for a broader-than-Matchete staging, missing pruning, or
  wrong algorithm boundary before increasing caps.
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
Matchete `EOMDevs[_Vector]`.

Current runtime ordering now mirrors the producer/consumer shape of Matchete's
`InternalSimplify` followed by `PerformSystematicFieldRedefs`: after
Wilson-line scalar commutator exposure, pychete can immediately rerun the
bounded on-shell EOM replacement and Abelian vector field-redefinition
companion on the scalar-exposed expression. This is implemented in both
`Theory.match(...)` and `ValidationFixture.one_loop_preview(...)`, with
separate supertraces for the raw scalar-exposed checkpoint and the
post-vector-EOM checkpoint. The remaining generic work is still the deeper
`InternalSimplify` producer that exposes the formal B/W vector-EOM terms from
the selected Singlet source itself; the current exact current-current bridge
still finds no vector divergence in the selected pychete probe.

## Current Implementation Slice

- Added `_apply_on_shell_eom_reduction_to_expression(...)` as a shared
  bounded helper in `src/pychete/wilson_line_eom.py`.
- Updated public one-loop matching and validation-preview Wilson-line
  finalization so scalar commutator exposure can be followed by a second
  vector-EOM/on-shell reduction pass when the Abelian vector
  field-redefinition option is enabled.
- Added focused regressions for the public `Theory.match(...)` route and the
  direct `ValidationFixture.one_loop_preview(...)` route. Both tests use a
  bounded scalar derivative source that reveals a vector-current divergence
  only after scalar commutator exposure.
- Kept the change performance-local: the second pass runs only on the already
  scalar-exposed expression and only when the existing on-shell/vector options
  request it. It does not globally expand or reclassify the full one-loop
  source.
- Focused validation currently passed for the four vector-EOM regression tests,
  py_compile on changed files, and targeted mypy on the changed source
  modules.

## Focused Tests For This Slice

Run after completing the slice:

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python -m pytest \
  tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_generates_abelian_vector_eom_replacements \
  tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_applies_vector_eom_after_scalar_commutator_exposure \
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_applies_abelian_vector_eom_field_redefinition \
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_applies_vector_eom_after_scalar_commutator_exposure -q
dependencies/.venv/bin/python -m py_compile \
  src/pychete/wilson_line_eom.py src/pychete/matching.py src/pychete/validation_fixtures.py \
  tests/integration/matching/test_heavy_scalar_tree.py \
  tests/integration/validation/test_validation_fixtures.py
dependencies/.venv/bin/python -m mypy \
  src/pychete/wilson_line_eom.py src/pychete/matching.py src/pychete/validation_fixtures.py
git diff --check
```
