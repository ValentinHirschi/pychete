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
  probes must be at least as targeted as the corresponding Matchete stage. If
  a pychete comparison is slower or broader, first look for missing classing,
  scoring, pruning, or staging before raising caps or expanding more input.
- Run memory-risk tests and matching probes through
  `scripts/run_with_memory_watch.py --limit-gb 30 -- ...`.
- Never request sandbox permission escalation. Use the user-started
  `listener.py` `run.order` / `run.output` route for `.git` metadata writes
  and for retries after `Operation not permitted`.
- Keep this live file compact. The previous live log from this slice was
  archived as `implementation_notes/one_shot_implementation_part_G.md`; earlier
  history lives in `one_shot_implementation_B.md` and
  `one_shot_implementation_part_A.md` through
  `one_shot_implementation_part_F.md`.

## Current First-Parity Target

The first realistic full one-loop matching integration test remains the
Singlet Scalar Extension to SMEFT, with `cHD` as the hard coefficient. The
selected `hScalar-lScalar-lVector-lScalar -> cHD` Wilson-line
trace/integral/projection path matches Matchete's off-shell checkpoint through
propagation orders 0, 1, and 2. The remaining blocker is the on-shell
operator-simplification and field-redefinition source feeding the cHD shift.

The active evidence points away from scalar-Higgs EOM replacement as the first
source of the mismatch. Matchete's first nonzero `cHD` delta appears at
`PerformSystematicFieldRedefs` stage `after_shift_dim6_dev3`, where the
selected pre-shift terms contain formal vector-EOM sources over `{B, W}` and
no selected Higgs-EOM terms. The B-only replay carries the full cHD shift; the
W-only replay is selected but currently projects zero to `cHD`.

Estimated remaining work for the first full nontrivial parity test is still a
few coherent slices:

- Port Matchete's class-wise `InternalSimplify` / `IBPSimplify`
  vector-EOM-producing semantics deeply enough for the selected Singlet `cHD`
  source.
- Feed the resulting formal Abelian `B` EOM source into pychete's bounded
  vector field-redefinition consumer and keep W-vector semantics staged until
  a target requires them.
- Verify public route composition: selected Wilson-line replacement,
  unselected supertrace remainder, heavy-scalar substitution, on-shell
  ordering, and registered `cHD` projection.
- Lock a full Singlet `cHD` regression, then broaden within the Singlet model.
- Defer fermion/gamma/Fierz/colour-heavy model parity until the scalar Singlet
  path is green.

## Active Checkpoints

Matchete checkpoint:

- `helper_mathematica_scripts/debug_singlet_eom_simplify.wls`
- `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`

Pychete checkpoint:

- `scripts/debug_pychete_singlet_eom_boundary.py`
- `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`

Additional hScalar-lScalar/cHD trace checkpoint:

- `helper_mathematica_scripts/debug_singlet_wilson_trace.wls`
- `assets/validation/matchete/debug/singlet_hScalar_lScalar_cHD.prop4.debug.json`

Latest narrowed mismatch:

- Matchete inert-`SymGammaFactor` replay selects the normalized B-source
  coefficient
  `-(1 + eps + eps log)/eps * (SG[1,4] - 8 SG[2,4])` multiplying
  `i hbar A^2 Bar[H] EOM[B] D H / M^4`.
- pychete now mirrors Matchete's local scalar/vector `OpScore` scale in the
  bounded scalar Green-basis scorer: kinetic scalar representatives score near
  `20000`, formal EOM representatives near `10000`, field-strength
  representatives near `1`, and repeated-derivative penalties are small
  `0.1` corrections rather than dominant terms.
- With that Matchete-scale score, the paired target-filtered raw-topology
  source probe records the expected formal source polynomial
  `-8*pi^2*SG[1,4] + 64*pi^2*SG[2,4]` for `Bar[H] EOM[B] D H` and the
  opposite for `D Bar[H] EOM[B] H`, with the previous spurious constant term
  removed. This closes the evanescent finite `cHD` source mismatch at this
  local stage without increasing Green-basis caps or using the slower
  heavy-first expansion route.
- The topology evaluation, cHD projection aliases, metric contraction order,
  closed metric-trace convention, B-source orientation preference, simple
  Green-basis round increases, and pre-expanded commutator identities have
  been ruled out as fixes for the earlier mismatch.
- The next frontier is to run the public route against this corrected local
  source: selected Wilson-line replacement, unselected supertrace remainder,
  heavy-scalar substitution, on-shell field redefinition, and registered
  `cHD` projection must compose to the Matchete full integration coefficient.
- The Matchete fixture now also records the exact identity neighborhood for
  that B source. The selected inert B terms match two AtomicOps in class
  `{{H, Conj[H]}, 4}`: ID 13 is `D Bar[H] EOM[B] H`, ID 14 is
  `Bar[H] EOM[B] D H`. Both have score `10000.` and EOM subclasses over
  `{B}`. `ConstructOperatorIdentities[class, dDimensional]` gives 27 rules,
  of which only two touch IDs 13/14; both express the two source orientations
  through the same Hermitian/anti-Hermitian field-strength-divergence
  representative. This is now the concrete Matchete class boundary to port,
  not a reason to broaden the pychete Green-basis universe.
- pychete now has a bounded Abelian implementation of that two-orientation
  representative in `matchete_vector_eom_scalar_bilinear_normal_form(...)`.
  It runs after Abelian `D.F` terms are exposed as formal vector EOMs and
  rewrites `D Bar[phi] EOM[B] phi` / `Bar[phi] EOM[B] D phi` into Matchete's
  antisymmetric pair using Symbolica matches and native coefficient
  extraction. The refreshed pychete fixture now records nonzero paired
  `barH_EOMB_DH` and `DbarH_EOMB_H` projections. The remaining cHD gap is
  therefore the d-dimensional SymGamma/source coefficient, not loss of the
  conjugate orientation.
- The latest Matchete debug refresh records the same source boundary before
  and after `InternalSimplify[..., ReductionIdentities -> dDimensional]` with
  `EvaluateGammaFactor` left inert. Before `InternalSimplify`, the selected
  B/W vector-EOM source counts are both zero. After `InternalSimplify`, the
  selected source contains 12 B terms and 12 W terms, with the B orientations
  carrying the normalized coefficients
  `-/+ (1 + eps + eps log) (SG[1,4] - 8 SG[2,4]) / eps`. This confirms that
  Matchete creates the relevant vector-EOM source through its d-dimensional
  operator-identity stage; pychete should not keep looking for this gap in
  topology evaluation or contraction order.
- The latest pychete debug refresh adds a per-stage probe for the single
  selected `hScalar-lScalar#wilson14_o4_0` entry. The expression is roughly
  324 KB at formal SymGamma, 74 KB after postprocessing, and 99 KB after
  topology lowering. Current pychete order and a diagnostic Matchete-style
  `ContractMetric`-before-`WilsonExpand` order give identical topology-lowered
  source projections. The contraction-order hypothesis is therefore ruled out
  for the present cHD finite mismatch, and the next fix must target the
  d-dimensional operator-identity/Green-basis normal form.
- Refreshed Matchete's `hScalar-lScalar -> cHD` prop-order-4 trace dump. This
  stage contains two Matchete insertions: derivative-on-H and
  derivative-on-Bar[H] four-derivative bilinears. A later direct fixture/probe
  review showed that the apparent finite Higgs-bilinear disagreement was a
  stage/convention comparison issue: Matchete's `LF` replay carries the
  finite `+1` term, and pychete's bounded formal-SymGamma source now has the
  same `-/+ (SG[1,4] - 8 SG[2,4])` orientation polynomial after the
  Matchete-scale `OpScore` fix. Do not patch tensor reduction or integral
  evaluation from the older finite-bilinear note. The active mismatch is now
  public-route/full-coefficient composition from the corrected selected
  source: selected Wilson-line replacement, unselected remainder,
  heavy-scalar substitution, vector field redefinition, and registered `cHD`
  projection.
- A naive canonical fluctuation-basis prototype reduced the Singlet setup from
  26 discovered modes to 16 and the selected four-slot cHD path map from eight
  duplicated nonzero checkpoint paths to four canonical paths, but it was not
  retained because it lost Matchete's component/field-degree multiplicity and
  halved the four-slot cHD checkpoint. The performance direction is still
  correct, but the implementation must carry explicit multiplicity weights or
  Matchete-style field-degree factors before collapsing dummy-label-equivalent
  modes.

## Current Implementation Slice

1. Keep the refactor/context cleanup small and semantic: archive the long live
   notes, then split a coherent helper family out of the oversized
   `src/pychete/matching.py` without changing behavior.
2. Refresh a narrow Matchete `ConstructOperatorIdentities` dump for the
   two-Higgs/four-derivative class and the AtomicOp IDs that correspond to
   `Bar[H] EOM[B] D H` and `D Bar[H] EOM[B] H`.
3. Use the refreshed dump to design a bounded, generic pychete class-representative
   improvement. The implementation must use Symbolica pattern/coefficient/
   solve primitives and must not broaden the source more than Matchete's
   operator class.
4. Add focused tests that assert the paired Matchete/pychete checkpoint and
   include enough performance metadata to catch accidental broadening.
5. Run only targeted checks for the touched slice, then stage, commit, and push
   through `listener.py` once the slice is coherent.

Current slice progress:

- Completed the notes archive repair: the prior `one_shot_implementation_B.md`
  archive is preserved, while this slice's previous live note snapshot is in
  `one_shot_implementation_part_G.md`.
- Extracted generated CDE/Wilson-line expansion-plan data classes and helpers
  from `src/pychete/matching.py` into
  `src/pychete/matching_expansion_plans.py`, preserving public class identity
  through `pychete` and `pychete.matching`.
- Refreshed the Matchete cHD fixture with the bounded AtomicOp identity
  neighborhood for the selected inert B source.
- Implemented and unit-tested the Abelian vector-EOM scalar-bilinear
  orientation normal form, and refreshed the pychete cHD fixture to record the
  new paired orientation frontier.
- Added bounded pychete stage diagnostics for the selected source entry and
  refreshed the Matchete cHD debug fixture with raw-before-`InternalSimplify`
  inert-`SymGammaFactor` source counts. The new evidence points directly to a
  d-dimensional `InternalSimplify`/Green-basis identity gap.
- Updated the scalar Green-basis preferred-representative score to the
  Matchete `OpScore` scale. The refreshed pychete fixture now has the
  Matchete-aligned evanescent SymGamma source polynomial and finite
  vector-field-redefinition projection at the bounded hScalar-lScalar source
  checkpoint.
- Tested a canonical fluctuation-basis normalization prototype, then discarded
  it after it failed the selected four-slot cHD aggregate by losing a factor of
  two. This identifies a future performance refactor, not a current runtime
  change: canonical field-space modes need explicit multiplicity/DOf weights
  before path enumeration or tensor reduction can safely collapse duplicates.
- Generated the Matchete `hScalar-lScalar/cHD` prop-order-4 dump for direct
  finite Higgs-bilinear comparison against pychete's selected
  `wilson14_o4_0` entry, then reinterpreted it after checking the Matchete
  `LF`/finite-`+1` convention against the refreshed pychete formal-SymGamma
  source projections.
- Extracted the target-filtered CDE/Wilson-line projection-filter policy out
  of `src/pychete/matching.py` into
  `src/pychete/matching_projection_filters.py`. Existing private imports from
  `pychete.matching` remain compatibility aliases, while the performance
  policy now has a dedicated semantic home. This reduced `matching.py` from
  9,544 to 9,164 lines without changing the bounded cHD route.

## Performance Budget For This Slice

- Keep pychete probes target-filtered to the same hScalar-lScalar source and
  two-Higgs/four-derivative operator class used by the Matchete dump.
- Do not use per-term heavy-first expansion for this frontier; previous probes
  reached roughly 79 MB on a single entry and were not competitive with the
  Matchete class boundary.
- Do not increase Green-basis caps to hide missing Matchete class semantics.
  The current relevant pychete class is small enough to inspect directly
  before post-commutator expansion; if the implementation wants more terms, it
  needs a better classing/scoring boundary, not a larger global universe.
- Use `Expression.coefficient`, `Expression.match`, `Expression.matches`,
  `Expression.replace_multiple`, and `Expression.solve_linear_system` for the
  symbolic work. Python may orchestrate class buckets and bounded metadata,
  but not reimplement symbolic algebra.
- The score fix is deliberately a scoring/classing alignment rather than a
  broader search: it keeps the same target-filtered source probe and lowers
  the refreshed fixture byte counts in several expensive post-EOM summaries,
  so this stage remains at least as targeted as the Matchete intermediate
  checkpoint.
- A multiplicity-preserving canonical-basis pass remains the next performance
  guard for setup and Wilson-line path generation. The rejected prototype shows
  where the duplicate work lives, but current parity probes must continue to
  use the existing eight path IDs until the replacement carries explicit
  component/DOf weights and preserves the selected cHD aggregate.
- Projection filtering is now isolated in
  `src/pychete/matching_projection_filters.py`; keep future performance work
  there when it is about target-local Wilson-line/CDE pruning rather than
  supertrace construction itself. The focused extraction gate was:
  `test_wilson_line_target_filter_skips_impossible_entries_before_generation`,
  `test_singlet_wilson_line_target_prefilter_matches_matchete_order_four_insertions`,
  and `test_registered_chd_filter_requirements_keep_vector_eom_alias_candidates`,
  all under the 30 GiB watchdog.

## Targeted Commands

```sh
source "$HOME/.bashrc"
PYTHONPATH=src dependencies/.venv/bin/python -m pytest \
  tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_selected_chd_pychete_boundary_fixture_records_pre_eom_gap \
  tests/integration/validation/test_validation_fixtures.py::test_singlet_reference_chd_debug_records_inert_gamma_vector_source_split \
  -q
```

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- \
  dependencies/.venv/bin/python scripts/debug_pychete_singlet_eom_boundary.py \
  --out /tmp/singlet_eom_cHD.pychete.debug.json
```
