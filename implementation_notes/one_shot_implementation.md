# One-Shot Port Implementation Notes

## Active Plan And Non-Negotiable Guidelines

- Continue the Matchete-style one-shot one-loop matching port on branch
  `one-shot-port`. The first full nontrivial integration target remains the
  Singlet Scalar Extension matched to SMEFT Warsaw, then broaden to
  `VLF_toy_model`, `E_VLL`, `S1S3LQs`, and the remaining mappable Matchete
  validation assets.
- The forward architecture is explicit Wilson-line trace matching. CDE is a
  legacy diagnostic/cross-check path only.
- Runtime pychete and pytest must remain Mathematica- and
  Matchete-independent. Wolfram scripts are optional debug and fixture
  generation tools; committed pytest fixtures must be pychete-owned data.
- Use Symbolica-native primitives first. Use idenso for gamma/colour/metric
  algebra, spenso for tensor-network work, vakint for topology-independent
  tensor reduction and optional single-scale analytic checks, and pychete's
  own analytic one-loop vacuum-integral evaluator for mixed/zero-mass cases.
- Do not use or import sympy/scipy.
- For every Matchete/pychete mismatch, refresh focused Matchete
  WolframScript dumps, compare them against bounded pychete probes at the
  same trace/target/order/stage boundary, and patch only the first generic
  semantic divergence. Never tune a final Wilson coefficient directly.
- Use Matchete to guide algorithmic stage boundaries while implementing the
  pychete side with Symbolica/idenso/spenso/vakint-native mechanisms instead
  of copying Mathematica-specific mechanics.
- Treat performance parity as part of semantic parity. Prefer selected
  trace/source probes, entry-local projection, target filtering, staged
  sources, and small source-class diagnostics over global full-expression
  expansion.
- Run memory-risk tests and matching probes through
  `scripts/run_with_memory_watch.py --limit-gb 30 -- ...`.
- Never request sandbox permission escalation. Use the user-started
  `listener.py` `run.order` / `run.output` route for `.git` metadata writes
  and for retries after `Operation not permitted`.
- Keep this live file compact. The previous live log is archived unchanged as
  `implementation_notes/one_shot_implementation_part_I.md`. Earlier history
  is in `one_shot_implementation_B.md` and
  `one_shot_implementation_part_A.md` through
  `one_shot_implementation_part_H.md`.

## Current State

The Singlet converted Matchete on-shell effective-coupling boundary is now
green:

- UV theory: `Singlet_Scalar_Extension`.
- Effective theory/basis: SMEFT Warsaw.
- Nonzero Wilson conditions in the committed Matchete fixture: 25.
- pychete matches all 25 at the converted on-shell
  `MapEffectiveCouplings` boundary:
  `cH`, `cHB`, `cHBox`, `cHD`, `cHW`, `cHWB`, `cHd`, `cHe`, `cHl1`, `cHl3`,
  `cHq1`, `cHq3`, `cHu`, `cHud`, `cdH`, `ceH`, `cle`, `cledq`, `clequ1`,
  `cqd1`, `cqd8`, `cqu1`, `cqu8`, `cquqd1`, and `cuH`.

This is not yet full public one-loop generation parity. It proves that once a
Matchete-equivalent on-shell source is available, pychete can decompose it
into the full Singlet SMEFT Wilson set. The remaining work is to move that
coverage upstream into public Wilson-line source generation, on-shell
reduction, staged projection/effective-coupling mapping, and performance-safe
trace composition directly from the UV Lagrangian.

Current public Wilson-line accepted subset:

- Selected `hScalar-lScalar -> cHW/cHB/cHWB` Higgs-gauge routes match the
  committed Matchete fixture through `one_loop_preview_gap_report(...)`.
- The selected two-trace public `Theory.match(...)` route for `cHD` matches
  through finite/full staged checks using `hScalar-lScalar` orders `{0,2,4}`
  and `hScalar-lScalar-lVector-lScalar` orders `{0,1,2}` with Matchete-style
  fluctuation-DOF weighting, staged Wilson-line projection sources, scalar/EOM
  exposure, and selected-only trace composition.
- The broad default public Singlet report is still not green. It does not yet
  assemble the validated selected Wilson-line pieces and the
  effective-coupling map efficiently enough to reproduce all 25 conditions
  directly from the UV Lagrangian.
- Source-stage scalar-sector progress for `cHBox` is now pinned separately:
  selected `hScalar-hScalar` contributes
  `-hbar*kappa^2/(24 M^2)` at
  `interaction_wilson_line_normalized_internal_integral_finite_part`. This is
  not yet a final public `on_shell_eft_lagrangian` `cHBox` condition.

## Latest Milestone

Commit `36647fc` (`Recover Singlet Q_HBox Higgs-sector mapping parity`) added
the final converted-boundary bridge:

- Matchete evidence: `CouplingManipulations.m` applies
  `MapEffectiveCouplings` followed by `ShiftRenCouplingsInMC`, and
  `assets/validation/matchete/debug/singlet_eom_cHBox.debug.json` shows that
  `Q_HBox` maps through an EOM-reduced effective-projection representative.
- pychete patch: `MatchingResult.map_effective_couplings(...)` applies a
  tightly gated on-shell SMEFT `Q_HBox` bridge for `cH`, `cdH`, `ceH`, and
  `cuH`, obtains `cHBox` through the same Symbolica-backed map, uses
  registered `lambda/Yd/Ye/Yu` coupling metadata, removes loop-counting
  symbols only to read tree weights, and uses `series_eft(coefficient *
  operator, eft_order=dim)` for the renormalizable shift.
- Focused validation passed under the 30 GiB watchdog: the new
  `cH/cdH/ceH/cuH` fixture regressions, the full
  `test_validation_fixtures.py -k effective_coupling_map_recovers` subset,
  targeted mypy on `src/pychete/matching_results.py`, `git diff --check`,
  and a compact all-nonzero Singlet probe reporting `25 ok, 0 bad`.

## Current Continuation Notes

- The first probe after `36647fc` attempted to run an effective-coupling map
  sweep over the selected two-trace public Wilson-line source. It was stopped
  with the watchdog `stop.order` mechanism after several minutes because the
  all-source solve was too coarse for iteration. This supports the next design
  direction: expose smaller public mapping boundaries and avoid global
  effective-coupling solves on large selected Wilson-line expressions.
- The live implementation note was archived to
  `one_shot_implementation_part_I.md` because it had grown beyond 1.5k lines.
- New public mapping boundary: `MatchingResult.with_mapped_effective_couplings(...)`
  now stores effective-coupling-map solutions back into a structured
  `MatchingResult` with metadata. `Theory.match(..., loop_order=1)` and
  `ValidationFixture.one_loop_preview_gap_report(...)` expose this through the
  opt-in flags `matching_condition_effective_coupling_map` and
  `matching_condition_effective_coupling_allow_incomplete_target`.
- Defaults still use direct Symbolica coefficient projection. The new mapping
  route is intentionally target-local and should be used for selected Wilson
  subsets, not global all-Wilson solves on unreduced Wilson-line sources.
- Validation for this slice passed under the 30 GiB watchdog:
  the new structured-result and gap-report forwarding tests, the existing
  `test_validation_fixtures.py -k effective_coupling_map_recovers` group
  (`20 passed`), targeted mypy on `matching.py`, `matching_results.py`,
  `theory.py`, and `validation_fixtures.py`, plus the selected public Singlet
  `cHW/cHB/cHWB` and `cHD` regressions (`2 passed`, including the known slow
  `cHD` route).
- Follow-up public mapping slice: the first real selected `cHD` public
  effective-map probe failed after source generation with
  `Green-basis reduction discovered more than 128 basis terms`. This
  identified the next boundary as map-time source size rather than Wilson-line
  generation or a final-coefficient convention.
- Implemented staged effective-coupling mapping:
  `MatchingResult.map_effective_couplings_from_sources(...)` and
  `with_mapped_effective_couplings_from_sources(...)` solve each selected
  projection source independently and sum the coefficients. Public
  `Theory.match(..., loop_order=1)` and direct fixture previews now choose
  this staged path automatically when effective-coupling mapping is requested
  and `MatchingResult.staged_projection_sources(...)` exposes selected
  Wilson-line sources.
- Added target-local source filtering before incomplete effective-coupling
  maps, reusing the existing Symbolica-pattern projection atom requirements.
  The filter is disabled for the registered SMEFT `Q_HBox` bridge targets
  `cH`, `cdH`, `ceH`, and `cuH`, because those Matchete effective-map
  conditions require the `Q_HBox` EOM image and renormalizable shifts outside
  the raw target-operator atom family.
- New/updated regressions:
  `test_matching_result_maps_effective_couplings_from_staged_sources`,
  `test_public_match_selected_higgs_gauge_effective_map_subset_matches_matchete_fixture`,
  and the parameterized slow
  `test_singlet_wilson_line_gap_report_accepts_selected_chd_against_matchete_fixture`
  now cover both direct projection and staged effective mapping.
- Latest validation passed under the 30 GiB watchdog: the new staged unit and
  Higgs-gauge effective-map tests, the converted effective-map group (`20
  passed`), targeted mypy on `matching.py`, `matching_results.py`, and
  `validation_fixtures.py`, and the selected `cHD` direct/effective-map slow
  regression (`2 passed` in about six minutes).
- Current slice: `cHBox` public staged effective-map debugging found a
  generic incomplete-map boundary, not a final-coefficient issue. Matchete
  evidence remains the committed `Q_HBox` EOM/projection dump
  `assets/validation/matchete/debug/singlet_eom_cHBox.debug.json`, while the
  paired pychete probes were target-local public `cHBox` runs through
  `Theory.match(...)` and a cheap Singlet tree-only map. Before the patch,
  every staged selected public `cHBox` source, including
  `tree_level_on_shell_projection_source`, mapped to zero in incomplete
  effective-map mode even though direct projection recovered the tree
  coefficient. The first differing boundary was therefore
  `MapEffectiveCouplings` on a target-local source containing a registered
  projection alias of the Wilson operator rather than the exact target
  representative.
- Implementation: `MatchingResult.map_effective_couplings(...)` now keeps the
  lower-level Symbolica linear solve authoritative when it returns a nonzero
  answer, but for incomplete target-local maps whose solve returns zero it
  falls back to the existing direct Symbolica coefficient/projection-alias
  machinery for registered Wilson targets on the same source stage. The
  SMEFT `Q_HBox` bridge now passes the actual source-stage name into its
  internal `cHBox` lookup so alias gating remains stage-aware. This is a
  generic projection-boundary fallback for partial effective maps, not a
  hard-coded `cHBox` coefficient.
- Validation for the slice: focused effective-coupling unit tests and the new
  Singlet tree regression passed (`18 passed` for the selected group), the
  converted effective-map fixture group passed under the 30 GiB watchdog
  (`20 passed`), targeted mypy passed on `matching_results.py` and
  `effective_couplings.py`, and the public selected Higgs-gauge staged
  effective-map regression still passed.
- Updated `cHBox` public frontier: the selected two-trace public route now
  maps the tree `-A^2/(2 M^4)` contribution correctly but still differs from
  the full Matchete `cHBox` condition because the selected
  `hScalar-lScalar` / `hScalar-lScalar-lVector-lScalar` families do not
  generate the missing one-loop scalar-sector terms. A focused Matchete dump
  for `hScalar -> cHBox`
  (`assets/validation/matchete/debug/singlet_hScalar_cHBox.debug.json`)
  shows a zero selected prop-order-4 Wilson-line insertion sum but nonzero
  full power-type and previous validation traces, so the next `hScalar` issue
  is full power-trace composition rather than a selected-order coefficient
  mismatch. A bounded public pychete probe now has a regression showing that
  `hScalar-hScalar` contributes the reference `-hbar*kappa^2/(24 M^2)` term
  at the normalized Wilson-line finite stage. Broader
  `hScalar-hScalar-hScalar` probing was stopped with `stop.order` because the
  unrestricted derivative-order plan was too slow. The next `cHBox` work
  should use narrower total-order plans for pure-heavy scalar traces before
  broadening further.
- Validation for the latest scalar-stage regression:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_public_match_selected_hscalar_hscalar_chbox_stage_records_scalar_loop_contribution`
  passed under the 30 GiB watchdog (`1 passed` in about 16 seconds).

## Next Implementation Slices

1. Selected Singlet broadening:
   use the staged public map boundary to broaden beyond the currently green
   selected `cHW/cHB/cHWB/cHD` families. The immediate `cHBox` sub-frontier is
   pure-heavy scalar trace coverage: keep `hScalar-hScalar` as the first
   committed partial loop contribution and probe `hScalar-hScalar-hScalar`
   only with narrow total-order plans. Record whether each failure is source
   generation, on-shell reduction, effective-coupling decomposition, or
   performance.

2. Trace/source generation parity:
   broaden beyond the selected `cHW/cHB/cHWB/cHD` families by following
   Matchete's `GenericPropagatorExpansion -> DeterminePowerInsertions ->
   EvaluateSTr -> InternalSimplify -> EOMSimplify -> MapEffectiveCouplings`
   stage order. Use focused Wolfram dumps and bounded pychete probes for each
   new mismatch.

3. Performance:
   keep Wilson-line work entry-local and target-filtered. Do not repeat the
   stopped global selected-source solve pattern unless the source has first
   been reduced to a small target-local subset.

4. Validation and commits:
   add focused tests for each new public boundary, run only relevant pytest
   subsets during development, then a broader targeted gate before committing.
   Commit and push only coherent green milestones to `one-shot-port`.
