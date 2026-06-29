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

## Next Implementation Slices

1. Selected Singlet broadening:
   use the public map boundary on already validated selected Wilson-line
   source families, starting with `cHD` and then Higgs-gauge/Higgs-sector
   subsets. Record whether each failure is source generation, on-shell
   reduction, effective-coupling decomposition, or performance.

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
