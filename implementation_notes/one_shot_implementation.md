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

Pychete now has a bounded producer and consumer for formal Abelian vector EOM
atoms:
`EOM(Field(B, Vector(...), {mu}, {}))` is routed through the same scalar-current
replacement and Abelian vector field-redefinition companion as the
`FieldStrength(B, {nu, mu}, {}, {nu})` standard form. A new standard-form pass
also converts already-created Abelian `D.F` divergences into formal vector EOM
atoms using Symbolica `replace_multiple`, without rerunning the full Green-basis
solver. The derivative selector has also been corrected to count vector formal
EOMs as two derivatives, matching Matchete `EOMDevs[_Vector]`.

Current runtime ordering now mirrors more of the producer/consumer shape of
Matchete's `InternalSimplify` followed by `PerformSystematicFieldRedefs`: after
Wilson-line scalar commutator and explicit `CD(...)` exposure, pychete rewrites
Abelian `D.F` into formal B-vector EOM atoms, then the bounded on-shell EOM
replacement and Abelian vector field-redefinition companion can run on the
scalar-exposed expression. This is implemented in both `Theory.match(...)` and
`ValidationFixture.one_loop_preview(...)`, with separate supertraces for the
raw scalar-exposed checkpoint and the post-vector-EOM checkpoint. The remaining
generic work is still the deeper `InternalSimplify` producer that exposes the
full set of formal B/W vector-EOM terms from the selected Singlet source; the
exact current-current bridge still finds no useful dim6/dev3 B/W vector-EOM
structure in the raw selected pychete source.

Latest bounded probes:

- Selected total orders 0 and 1 still have no B field-strength divergence
  after scalar commutator exposure.
- In total order 2, `wilson13_o1_1_0_0` used to leave one B field-strength
  divergence after scalar exposure. The current bounded probe now reports
  `scalar_eom_exposed_formal_vector_eom_count = 1`,
  `scalar_eom_exposed_vector_field_strength_divergence_count = 0`, and one
  nonzero post-exposure Abelian vector field-redefinition delta for that entry.
  This confirms the formal B-EOM producer/consumer chain is active at the
  selected-trace boundary.
- The `wilson13_o1_1_0_0` contribution still has four-Higgs/heavy-solution
  field content and projects to zero for both `cHD` and the simple Matchete
  dim6/dev3
  `Bar[D_mu H] H D_nu F_B^{mu nu}` / `Bar[H] D_mu H D_nu F_B^{mu nu}`
  intermediate operators.
- A refreshed projection probe now records the post-exposure vector-shift
  projection explicitly. The raw scalar-exposed B-vector field-redefinition
  delta and the heavy-substituted version are both nonzero for
  `wilson13_o1_1_0_0`, but both project to zero for `cHD`. This eliminates
  heavy-substitution ordering as the reason for the current zero.
- Filtered and unfiltered Wilson-line generation have identical selected term
  counts through total order 2: 8 terms at order 0, 24 at order 1, and 72 at
  order 2. The current cHD gap is therefore not caused by target-local
  Wilson-line term filtering.
- The cHD target-local Abelian EOM projection aliases do exist and have
  nonzero weights for the B-current/divergence preimages, so the latest zero
  is not simply a missing projection alias. The source content produced by
  pychete is still not the Matchete dim6/dev3 B/W vector-EOM source content.
- `wilson14_o2_0_0_0` creates many field-strength atoms after scalar exposure
  but no B divergence and no vector-EOM rule.
- The exact `expose_abelian_vector_eom_currents(...)` bridge can see too many
  absent current-pair candidates on scalar-exposed expressions; it now returns
  the accumulated expression when its budget is exhausted instead of raising.
  This keeps the debug/performance boundary conservative and confirms that the
  remaining `cHD` gap is not solved by broadening this exact bridge.
- Refreshed Matchete dissection with
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls --sample-terms 20`
  now records all 12 selected dim6/dev3 B/W vector-EOM terms at
  `after_shift_dim6_dev3`. The terms are two-Higgs formal vector-EOM sources
  proportional to `hbar A^2 / M^4`, not four-Higgs sources.
- The Matchete script now also replays the dim6/dev3 vector shift field by
  field. The B-only replay selects six terms and produces the full cHD
  on-shell delta
  `-hbar A^2 gY^2 (6 + 17 eps + 6 eps log(mubar2/M^2))/(36 eps M^4)`;
  the W-only replay also selects six terms but projects zero to cHD. This
  keeps the first parity milestone B-focused and avoids a broader W-vector
  field-redefinition implementation until a target needs it.
- A bounded pychete hScalar-lScalar source-trace probe was added to
  `scripts/debug_pychete_singlet_eom_boundary.py` and refreshed in
  `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`. With
  the cHD target-local filter, it evaluates only three hScalar-lScalar entries
  (`o0_0`, `o2_0`, and `o4_0`). The nonzero vector-shift projection comes only
  from `hScalar-lScalar#wilson14_o4_0`, with four formal B-vector EOM source
  atoms and a nonzero cHD projection.
- This corrects the previous four-slot-only diagnosis: the cHD on-shell shift
  is fed by the hScalar-lScalar order-four two-Higgs source generated by
  Matchete `InternalSimplify`, while the four-slot
  `hScalar-lScalar-lVector-lScalar` trace accounts for the off-shell cHD
  coefficient. Heavy-first expansion of the four-slot `wilson13` entry reached
  about 79 MB for one entry before producing useful information, so that route
  is not performance-competitive and should not be used as the main parity
  strategy.
- Current first differing source boundary: pychete exposes the bounded
  hScalar-lScalar B-vector EOM source and obtains a nonzero Abelian vector
  field-redefinition projection, but the coefficient is still short of
  Matchete's `after_shift_dim6_dev3` delta. The next algorithmic target is
  scalar Green / `EoMSplitter` coefficient parity for the two-Higgs
  hScalar-lScalar source, with non-Abelian W-vector EOM treatment tracked as a
  later generic boundary if needed.
- Refreshed pychete source-operator projections now isolate that boundary more
  sharply. The target-filtered `hScalar-lScalar#wilson14_o4_0` source projects
  onto `Bar[H] EOM[B_mu] D_mu H` with the same pole and log structure as the
  Matchete B-only replay, but pychete's finite source coefficient is
  `7 i/36 * hbar A^2/M^4` where Matchete's selected B terms require
  `17 i/72 * hbar A^2/M^4`. The conjugate
  `D_mu Bar[H] EOM[B_mu] H` projection is currently zero in this pychete
  source probe. This confirms the next runtime patch must target the generic
  tensor/source producer before vector current insertion or cHD projection.
- A performance check on the same boundary reinforces the staging choice:
  per-term Green splitting can hit the local basis cap, while the aggregate
  target-filtered source probe stays bounded and mirrors the Matchete class
  boundary. Future cHD parity slices should improve this source-stage
  algorithm, not raise caps or switch back to heavy-first four-slot expansion.
- A Matchete inert-`SymGammaFactor` replay of the same dim6/dev3 B selection
  shows the source-level evanescent difference explicitly. Matchete selects
  `(-G1 + 8 G2) * (1/eps + log(mubar2/M^2) + 1)` multiplying
  `i hbar A^2 Bar[H] EOM[B] D H / M^4`. Pychete's raw topology/source probe
  gives `(2 G1 - 4 G2 - 1/4)` multiplying the same single
  `Prop[0]^3 Prop[M]` topology. These are equal at epsilon^0 but differ by
  `epsilon/24`; after the topology pole this is exactly the missing finite
  `+ i hbar A^2/(24 M^4)`. The one-loop topology formula itself was checked
  against Matchete's `LoopIntegrate[Prop[0]^3 Prop[M]]` and agrees.
- Ruled-out fixes for this boundary: moving `ContractMetric` before
  `WilsonExpand` in pychete's pre-Wilson path leaves the source coefficient
  unchanged; replacing closed Lorentz metric traces by strict `4` leaves it
  unchanged; explicitly preferring the Matchete B-source orientations in the
  Green-basis solve leaves it unchanged. The remaining semantic gap is
  therefore the d-dimensional `InternalSimplify` / identity-set semantics that
  produce Matchete's evanescent representative, not projection, vector-current
  insertion, or scalar topology evaluation.

## Current Implementation Slice

- Added `vector_eom_identities(...)` as the formal vector-EOM identity source
  for Abelian `D.F` representatives inside the existing Symbolica-backed
  Green-basis solver.
- Added `vector_formal_eom_ibp_identities(...)` for the vector branch of
  Matchete `IdentitiesIBP` / `EoMSplitter`, mapping formal vector EOM atoms to
  `FieldStrength(mu, nu)` splitters and applying `apply_cd([mu], ...)` before
  the Symbolica-backed Green-basis solver combines that total-derivative
  identity with `vector_eom_identities(...)`. Focused unit tests cover both
  the raw identity and the normal-form use. The refreshed cHD probe is
  unchanged, so this was necessary generic coverage but not the source of the
  short Singlet B coefficient.
- Added `expose_vector_field_strength_divergences_as_formal_eom(...)` as the
  cheap standard-form pass for already-created Abelian field-strength
  divergences. This uses Symbolica `replace_multiple` over tag-restricted
  field-strength matches, with the Matchete orientation signs, and is gated by
  registered Abelian gauge-vector metadata.
- Wired the direct standard-form pass into the Wilson-line post-integral hook
  immediately after explicit `CD(...)` and scalar-commutator exposure when
  `wilson_line_expose_scalar_eom_terms` is enabled. This avoids rerunning a
  broad Green-basis closure just to standardize `D.F` leftovers.
- Extended Green class grouping so formal vector EOM atoms are classed with
  their owning field and Matchete's two-derivative EOM bonus.
- Extended the Singlet cHD debug script with vector-specific post-exposure
  counters for formal vector EOMs, residual B divergences, and the Abelian
  vector field-redefinition delta after scalar-EOM exposure.
- Extended the same debug script again with cHD projections of the raw and
  heavy-substituted post-exposure Abelian vector field-redefinition deltas,
  and embedded the Matchete `after_shift_dim6_dev3` delta/selection summary in
  the pychete JSON payload for side-by-side inspection.
- Extended the pychete cHD boundary script with a target-filtered
  hScalar-lScalar source-trace vector-EOM probe. This records the
  Matchete-relevant two-Higgs B-vector EOM source separately from the
  four-slot off-shell trace probe, and keeps the parity comparison bounded
  enough to stay useful.
- Extended the same source-trace probe with formal B-vector EOM source-operator
  projections for `Bar[H] EOM[B] D H`, `D Bar[H] EOM[B] H`, and the unbarred
  diagnostic orientations. These projections use the off-shell source in
  `MatchingResult.project_matching_conditions(...)`, so they avoid registered
  Wilson vector-EOM aliases and isolate the source coefficient directly.
- The latest script-only diagnostic run shows:
  pychete has one nonzero four-slot post-exposure B-vector field-redefinition
  delta with zero cHD projection, and separately one nonzero hScalar-lScalar
  order-four B-vector field-redefinition projection. The latter is the first
  relevant source for Matchete `after_shift_dim6_dev3`. Its `Bar[H] EOM[B] D H`
  finite source coefficient is now recorded as `7 i/36`, short of Matchete's
  `17 i/72`, while the pole/log terms align.
- Additional bounded probes compared the raw pychete topology coefficient and
  a Matchete run with inert `EvaluateGammaFactor`. The first mismatch is now
  localized to the evanescent symmetric-tensor representative:
  Matchete `-G1 + 8 G2` versus pychete `2 G1 - 4 G2 - 1/4` for the same
  `Bar[H] EOM[B] D H` source. Per-term splitting is still not
  performance-competitive and hits the Green-basis cap, so the next runtime
  slice should port the missing class-wise d-dimensional identity semantics in
  the aggregate source path.
- Focused validation passed for scalar Green/vector EOM units, scalar EOM
  units, the two public vector-EOM replay integration regressions, py_compile
  on changed files, static typing, and the bounded Singlet cHD debug probe.

## Focused Tests For This Slice

Run after completing the slice:

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python -m pytest \
  tests/unit/functional/test_scalar_green_bilinears.py \
  tests/unit/functional/test_scalar_eom.py \
  tests/unit/functional/test_scalar_eom.py::test_expose_abelian_vector_eom_currents_rewrites_exact_current_product \
  tests/unit/functional/test_scalar_eom.py::test_expose_abelian_vector_eom_currents_returns_bounded_source_when_candidate_budget_is_exhausted \
  tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_generates_abelian_vector_eom_replacements \
  tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_applies_vector_eom_after_scalar_commutator_exposure \
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_applies_abelian_vector_eom_field_redefinition \
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_applies_vector_eom_after_scalar_commutator_exposure -q
dependencies/.venv/bin/python -m py_compile \
  src/pychete/functional.py src/pychete/wilson_line_eom.py scripts/debug_pychete_singlet_eom_boundary.py \
  tests/unit/functional/test_scalar_green_bilinears.py tests/unit/functional/test_scalar_eom.py \
  tests/integration/matching/test_heavy_scalar_tree.py \
  tests/integration/validation/test_validation_fixtures.py
dependencies/.venv/bin/python -m pytest tests/test_static_typing.py -q
dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 --stop-file /tmp/pychete_singlet_probe.stop -- \
  dependencies/.venv/bin/python scripts/debug_pychete_singlet_eom_boundary.py --out /tmp/singlet_eom_cHD.pychete.debug.json
git diff --check
```
