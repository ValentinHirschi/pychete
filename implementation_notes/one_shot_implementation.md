# One-Shot Port Implementation Notes

## Active Plan And Non-Negotiable Guidelines

- Continue the Matchete-style one-shot one-loop matching port on branch
  `one-shot-port`, targeting first full nontrivial integration parity on the
  Singlet Scalar Extension to SMEFT, with `cHD` as the active hard
  coefficient. Broaden only after this path is green.
- The forward architecture is explicit Wilson-line trace matching. CDE is a
  legacy diagnostic/cross-check path only.
- Runtime pychete and pytest must remain Mathematica- and
  Matchete-independent. Wolfram scripts are optional debug and fixture
  generation tools.
- Use Symbolica-native primitives first. Use idenso for gamma/colour/metric
  algebra, spenso for tensor-network work, vakint for topology-independent
  tensor reduction and optional single-scale analytic checks, and pychete's
  own analytic one-loop vacuum-integral evaluator for mixed/zero-mass cases.
- Do not use or import sympy/scipy.
- For every Matchete/pychete mismatch, refresh focused Matchete
  WolframScript dumps, compare them against bounded pychete probes at the
  same trace/target/order/stage boundary, and patch only the first generic
  semantic divergence. Never tune a final Wilson coefficient directly.
- Treat performance parity as part of semantic parity. Pychete probes should
  be at least as targeted as the corresponding Matchete stage.
- Run memory-risk tests and matching probes through
  `scripts/run_with_memory_watch.py --limit-gb 30 -- ...`.
- Never request sandbox permission escalation. Use the user-started
  `listener.py` `run.order` / `run.output` route for `.git` metadata writes
  and for retries after `Operation not permitted`.
- Keep this live file compact. The previous live log is archived unchanged as
  `implementation_notes/one_shot_implementation_part_H.md`. Earlier history
  is in `one_shot_implementation_B.md` and
  `one_shot_implementation_part_A.md` through
  `one_shot_implementation_part_G.md`.

## Current First-Parity Target

The first realistic full one-loop matching integration test remains the
Singlet Scalar Extension to SMEFT. Current accepted progress:

- The selected `hScalar-lScalar -> cHW/cHB/cHWB` Higgs-gauge subset is
  reproduced on the label-level Matchete-DOF weighted Wilson-line route.
- The selected `hScalar-lScalar -> cHD` B-vector EOM replay reaches
  Matchete's finite dim6/dev3 replay coefficient in staged probes.
- The selected four-slot `hScalar-lScalar-lVector-lScalar -> cHD` pole-through
  finite checkpoint can be reproduced when decomposed by bounded public
  Wilson-line order/entry filters, but a broad aggregate public projection is
  still too monolithic.
- The committed Singlet fixture has 64 external SMEFT/Wilson entries; 25 are
  nonzero. The broad default fixture report still has all 25 nonzero Wilson
  entries different, because public composition/projection is not yet using
  the validated staged Wilson-line pieces efficiently. Stage-local nonzero
  parity is now meaningful for 4 of the 25: selected-route
  `cHW`, `cHB`, `cHWB`, and staged selected `cHD` after explicit
  Matchete-fixture/vakint loop-convention conversion.

The active evidence points away from scalar-Higgs EOM replacement as the first
source of the remaining `cHD` mismatch. Matchete's first nonzero `cHD` delta
appears at `PerformSystematicFieldRedefs` stage `after_shift_dim6_dev3`, where
the selected pre-shift terms contain formal vector-EOM sources over `{B, W}`
and no selected Higgs-EOM terms. The B-only replay carries the `cHD` shift; W
is selected but currently projects zero to `cHD`.

Immediate next implementation direction:

- Mirror Matchete's class-local `InternalSimplify` / `IBPSimplify`
  vector-EOM-producing semantics deeply enough for the selected Singlet `cHD`
  source.
- Feed the resulting formal Abelian `B` EOM source into pychete's bounded
  vector field-redefinition consumer, preserving Matchete's
  `SelectOperatorDevsAndDim` order and derivative-count staging.
- Verify full public-route composition only after the stage-local source and
  replay match: selected Wilson-line replacement, unselected trace remainder,
  heavy-scalar solution policy, on-shell ordering, and registered `cHD`
  projection.

Performance follow-up on the two-trace public composition: a transient
Symbolica `is_linear=True` head prototype for pychete `FuncNCM` was tested
and rejected. It preserved the focused Wilson-line behavior but made the
heavy four-slot entries much slower (`o0_0_2_0` about 8.9s, `o0_2_0_0` about
20.9s, `o1_0_1_0` about 9.2s, `o1_1_0_0` about 15.2s, compared with the
previous roughly 2.4s/5.0s/2.5s/3.7s baseline). The next performance slice
must therefore port Matchete's actual staged
`GenericPropagatorExpansion -> DeterminePowerInsertions -> EvaluateSTr`
boundary, not only the distributive behavior of Mathematica `FuncNCM`.

Latest targeted regression: added
`test_selected_chd_staged_full_composition_matches_matchete_fixture_condition`.
It computes the selected pychete `cHD` coefficient from the already validated
four-slot off-shell source plus the `hScalar-lScalar` on-minus-off vector-EOM
piece, then compares it to the committed Matchete matching fixture after the
explicit convention bridge
`epsilon -> vakint::epsilon` and
`log(mubar2/M^2) -> log(vakint::mursq) - 2 log(M)`. This is a
Matchete-independent pytest regression for the first derivative-sector
nonzero coefficient, not yet full public-route parity.
Focused watchdog gate passed on 2026-06-29:
`test_selected_chd_staged_full_composition_matches_matchete_fixture_condition`,
the staged finite/full `cHD` composition checks, and the selected
`cHW/cHB/cHWB` public fixture check.

## Active Checkpoints

Matchete checkpoints:

- `helper_mathematica_scripts/debug_singlet_eom_simplify.wls`
- `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`
- `helper_mathematica_scripts/debug_singlet_wilson_trace.wls`
- `assets/validation/matchete/debug/singlet_hScalar_lScalar_cHD.prop4.debug.json`

Pychete checkpoints:

- `scripts/debug_pychete_singlet_eom_boundary.py`
- `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`

## Matchete One-Loop Top-Level Function Ledger

This ledger is source-derived from the local Matchete files read in this
slice: `Package/Matching.m`, `Package/SuperTrace.m`,
`Package/LoopIntegration.m`, `Package/EFTCounting.m`,
`Package/Simplifications.m`, `Package/FieldRedef.m`,
`Package/CouplingManipulations.m`, `Package/TreeLevelMatching.m`, and
`Package/DevTools/Validation.m`. Use this as the comparison order when a
pychete result disagrees with Matchete.

- `LoadModel[...]`: loads gauge groups, fields, masses, couplings,
  representations, basis operators, and model options. Pychete fixtures must
  construct theory metadata before any symbol is instantiated, so symbol data,
  custom print metadata, and dimensions are not lost.
- `Match[lag, EFTOrder -> 6, LoopOrder -> 1]`: public matching entry. It
  rejects unsupported heavy vectors at loop level, calls
  `SetCurrentLagrangian`, adds tree matching via `ReplaceHeavyEOM` when
  requested, adds one-loop matching via `LoopMatch`, applies
  `ContractCGs // MatchReduce`, and Hermitian-symmetrizes.
- `SetCurrentLagrangian[...]`: canonicalizes with `HcExpand`,
  `CanonizeFermionMassTerms`, `IntroduceEffectiveMasses`, `ContractCGs`,
  `RelabelIndices`, and `Contract`; adds gauge-fixing and ghost terms;
  refreshes current field/mass associations; solves heavy EOMs with
  `DetermineEOMs`; and builds loop substitutions with `SetSubstitutions`.
- `DetermineEOMs[...]` / `ReplaceHeavyEOM[...]`: tree/heavy-field solution
  boundary. `PowerTypeSTr` calls `ReplaceHeavyEOM` on matching-mode selected
  trace results, so pychete must keep heavy-field EOM substitution distinct
  from later on-shell `EOMSimplify` shifts.
- `SetSubstitutions[...]`: loop source-composition boundary. It builds
  `$XFieldDofs`, subtracts `KinOpLagrangian`, takes `FluctuationOperator`
  derivatives, removes ghost/vector background pieces from X terms, lowers
  `OpenCD[...]` to `OpenCD[mu] - I LoopMom[mu]`, decomposes by `SeriesEFT`,
  momentum order, and open-CD count, and stores `$Xsubs`, `$XOrders`,
  `$XOrdMin`, `$Msubs`, and `$Gsubs`.
- `ListPowerTypeTraces[...]`: enumerates heavy-seeded trace words, prunes with
  `$XOrdMin` and EFT order, bounds X-insertion count, and cyclically
  de-duplicates. Pychete Wilson-line plans must preserve cyclic factors and
  field-DOF/component weights here, before tensor reduction.
- `LoopMatch[...]`: selects log-type and power-type traces, applies
  `WhichTraces` filtering, evaluates charged log traces through `LogTypeSTr`,
  and evaluates cyclic words through `PowerTypeSTr`.
- `PowerTypeSTr[...]`: applies `-I*hbar/2` and statistics signs, determines
  propagator expansion order, builds `GenericPropagatorExpansion`, enumerates
  `DeterminePowerInsertions`, evaluates terms with `EvaluateSTr`, and applies
  `ReplaceHeavyEOM` to the matching-mode result before multiplying the
  prefactor into each term.
- `GenericPropagatorExpansion[...]`: builds the ordered noncommutative
  template `Xop, Prop, ..., Xop, Prop, WilsonLine`. Propagator mass slots are
  the post-insertion modes. `PropExpand` uses bosonic expansions for scalar
  slots, an extra minus sign for vector slots, and `PropFermionExpand` for
  fermion slots with slash numerator plus open-derivative term.
- `DeterminePowerInsertions[...]`: enumerates concrete field-DOF choices,
  enforces EFT-order admissibility, applies cyclic de-duplication and cyclic
  symmetry factors, assigns open-CD allocations, and returns replacement
  bundles for `Xterm`, `Mterm`, light-vector `GaugeCTerm`, and closing
  `WilsonTerm`.
- `LogTypeSTr[...]`, `DetermineLogInsertions[...]`, and
  `GenericLogExpansion[...]`: single-field log-trace route for charged/gauge
  fields. It still flows through `EvaluateSTr`, so it shares open-CD,
  Wilson-line, fermion-trace, tensor-reduction, and loop-integral boundaries.
- `EvaluateSTr[...]`: strict execution order:
  insertion replacements, `$Xsubs/$Msubs/$Gsubs`, `ActWithOpenCDs`,
  `FuncNCM -> NCM`, `GatherLoopMomenta`,
  `RemoveSymmetryVanishingWilsonTerms`, `CloseFermionLoop`,
  `EvaluateSymmetricLorentzInds`, `ContractMetric`, `WilsonExpand`,
  `LoopIntegrate`, `RelabelIndices`, `ExpandGenFSs`, `ContractDelta`,
  `ContractCGs`, `ContractDelta`, `RefineDiracProducts`, `EpsExpand`, final
  `RelabelIndices`.
- `ActWithOpenCDs[...]`: terminates open covariant derivatives to the right
  over the noncommutative chain and drops dangling open derivatives. Pychete
  must preserve derivative action before Wilson-term lowering.
- `RemoveSymmetryVanishingWilsonTerms[...]`: drops Wilson terms whose
  derivative indices vanish by symmetry, including overlap with symmetric
  loop-momentum Lorentz groups.
- `CloseFermionLoop[...]`: applies fermion traces for fermionic trace words,
  then canonicalizes spinor lines and contracts metrics. Pychete must keep
  this delegated to idenso rather than handwritten gamma identities.
- `WilsonExpand[...]` / `WilsonTermExpand[...]`: coincidence-limit Wilson-line
  expansion. Zero derivatives give identity transporters; one derivative
  vanishes; higher derivatives use derivative-sublist partitions and
  `FSWilsonFactor` / `DevTermOnWilson` to emit field strengths.
- `GatherLoopMomenta[...]`, `LoopMoms[...]`,
  `EvaluateSymmetricLorentzInds[...]`, `SymGammaFactor[...]`: tensor-reduce
  loop-momentum numerators into symmetric metric tensors and
  dimension-dependent gamma factors before scalar integration. This is the
  vakint tensor-reduction boundary in pychete.
- `LoopIntegrate[...]`: structurally collects `Prop[m]`, `Power[Prop[m], n]`,
  `Prop[0]`, and `Power[Prop[0], n]`, merging identical massive signatures by
  summing powers, then emits loop functions. Pychete must maintain this
  arbitrary-power collection invariant.
- `SingleScaleIntegral[...]`, `MultiScaleIntegral[...]`,
  `EvaluateLoopFunctions[...]`, `EpsExpand[...]`: analytic scalar-integral
  evaluation and epsilon expansion. Vakint may be used only for single-scale
  analytic checks/evaluation; mixed/zero-mass analytic evaluation is
  pychete-owned.
- `MatchReduce[...]`: final off-shell loop cleanup. It contracts CGs,
  rewrites field-strength representation indices, evaluates single-scale
  loop functions, converts trivial CG deltas, simplifies epsilon CG products,
  and removes redundant `FlavorSum`s.
- `SeriesEFT[...]` / `OperatorDimension[...]`: EFT truncation backbone used
  throughout. Pychete truncation must use stored field/coupling dimension
  metadata and Symbolica rational-polynomial inspection, not name heuristics.
- `CovariantLoop[...]`: selected-field diagnostic entry. It calls
  `SetCurrentLagrangian`, maps fields to Matchete field-type labels, evaluates
  selected log/power traces, then applies `ContractCGs // MatchReduce`. Use it
  as an oracle for trace-local dumps, not as a separate architecture.
- `GreensSimplify[...]`: public Green-basis simplification. It does
  `HcExpand`, `LagrangianExpand`, constants separation, `ContractDelta`,
  `ContractCGs`, `IBPSimplify`, `CollectCoefficients`, and
  `AtomicToNormalForm`.
- `InternalSimplify[...]`: internal normal-form boundary before field
  redefinitions. It runs `ContractDelta @ ContractCGs`, `IBPSimplify`,
  `CollectCoefficients`, then `AtomicToOperatorForm` unless internal operator
  representation is requested. The Singlet `cHD` fixture shows this stage
  creates the formal B/W vector-EOM source.
- `IBPSimplify[...]` / `ConstructOperatorIdentities[...]`: class-local
  operator identity solver. It builds operator classes, generates IBP,
  CD-commutator, Jacobi, spinor, Dirac, chirality, symmetry, group, Fierz,
  and Schouten identities, maps them to a vector space, row-reduces, and emits
  redundant-operator replacements.
- `IdentitiesIBP[...]` / `EoMSplitter[...]`: the EOM identity branch. Scalar
  EOMs map to `CD[mu, scalar]`, fermion EOMs to gamma insertions, and vector
  EOMs to field strengths. This is the immediate conceptual source for the
  current vector-EOM `cHD` bridge.
- `EOMSimplify[...]`: on-shell EFT reduction entry. It determines loop order
  from `hbar`, separates constants, calls `InternalSimplify`, optionally uses
  dummy coefficients, calls `PerformSystematicFieldRedefs`, then finishes with
  `GreensSimplify`.
- `PerformSystematicFieldRedefs[...]`: systematic field-redefinition loop. It
  runs `RenormalizeMatterFields`, computes `GaugeFieldNormalization`, then
  loops dimensions 5..max and derivative counts in descending order, calling
  `ShiftLagrangian` for each class.
- `ShiftLagrangian[...]`: one field-shift stage. It selects
  `SelectOperatorDevsAndDim[lag, devs, dim]`, extracts fields appearing in
  formal EOM atoms, calls `DetermineShifts`, splits the Lagrangian by the
  dimension that can still contribute, dummy-shifts selected fields, applies
  replacement rules, and runs `InternalSimplify` again.
- `VectorShift[...]`: real-vector shift rule. It extracts the coefficient of
  `EoM@f[mu,...]`, multiplies by minus inverse gauge normalization, applies
  `AdjustEOMShifts`, and replaces dummy shifted vectors by covariant
  derivatives of the shift. This is the Matchete boundary pychete must mirror
  for the active Abelian B replay.
- `SelectOperatorDevsAndDim[...]` / `OpDevsAndDim[...]`: class selector.
  Formal scalar/vector EOMs count as two derivatives, fermion EOMs as one,
  field strengths count as one plus derivative slots, and fields count by
  derivative slots.
- `SaveValidationResults[...]`: validation wrapper. It saves per-trace
  `ContractCGs // MatchReduce // GreensSimplify`, off-shell
  `GreensSimplify[LagrangianEFT]`, on-shell
  `EOMSimplify[LagrangianEFT]`, and SMEFT matching conditions from
  `MapEffectiveCouplings`.
- `MapEffectiveCouplings[...]`: final target-Lagrangian solver, not simple
  coefficient extraction. It may `EOMSimplify` input and target, handles
  tree-loop evanescence-free staging, delegates to
  `MapEffectiveCouplingsInternal`, optionally shifts renormalizable couplings,
  appends effective-coupling definitions, simplifies RHSs, and symmetrizes.
- `MapEffectiveCouplingsInternal[...]`: introduces temporary effective
  couplings into the input, computes `CollectOperators[input - target]`,
  extracts `CoefficientEqualities`, solves target couplings progressively with
  index-pattern rules, removes temporary couplings, truncates each RHS by EFT
  order, sorts, removes duplicates/trivial rules, and symmetrizes. Full
  Singlet parity ultimately needs this solve semantics, although pychete may
  keep native `Expression.coefficient(...)` as a fast target-local path.

## Current Slice Status

The source-audit checkpoint is committed as `77ebb72`, and this runtime slice
added `systematic_abelian_vector_eom_field_redefinition_delta(...)` as the
bounded Abelian-vector companion to the existing systematic scalar helper.
The helper:

- consumes already-exposed formal vector `EOM(Field(...))` terms only;
- loops over EFT dimension and descending derivative count like Matchete's
  `PerformSystematicFieldRedefs` / `ShiftLagrangian`;
- selects terms with `select_terms_by_dimension_and_derivatives(...)`; and
- delegates the actual current replacement to the existing Symbolica-pattern
  `abelian_vector_eom_field_redefinition_delta(...)` consumer.

Focused validation passed:

- `tests/unit/functional/test_scalar_eom.py`
- `tests/unit/definitions/test_public_api.py`
- `dependencies/.venv/bin/python -m mypy`

This follow-up slice wired the staged Abelian vector-EOM consumer into both
the public `Theory.match(..., loop_order=1)` Wilson-line/on-shell bridge and
the validation-fixture preview bridge. When
`wilson_line_expose_scalar_eom_terms=True`, pychete now:

- exposes formal vector EOM terms at the post-integral
  `InternalSimplify`-like boundary;
- applies ordinary EOM replacement rules to the exposed source;
- computes the Abelian vector field-redefinition companion through
  `systematic_abelian_vector_eom_field_redefinition_delta(...)`, selecting
  formal EOM terms by EFT dimension and descending derivative count; and
- records whether the vector companion was staged in result metadata.

The commutator-only bridge remains distinct: without
`wilson_line_expose_scalar_eom_terms=True`, it does not claim formal
vector-EOM replay. Tests now pin that inactive path separately from the staged
formal-EOM path.

Mismatch checklist for this slice:

- Matchete checkpoint: `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`
  with the `after_shift_dim6_dev3` vector-EOM replay boundary, plus
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls`.
- Pychete probes/tests:
  `tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_stages_vector_eom_redefinition_after_formal_eom_exposure`,
  `tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_stages_vector_eom_redefinition_after_formal_eom_exposure`,
  and the existing Singlet `cHD` public frontier tests.
- First generic boundary: Matchete `PerformSystematicFieldRedefs` /
  `ShiftLagrangian` selects formal vector EOM terms by
  `SelectOperatorDevsAndDim` before replaying the vector field shift. Pychete
  previously used the direct whole-expression Abelian vector companion at the
  Wilson-line scalar/EOM bridge.
- Generic port rationale: the runtime patch does not alter a Wilson
  coefficient. It reuses Symbolica-pattern EOM discovery and native
  coefficient extraction, but changes the consumer boundary to Matchete's
  dimension/derivative-staged field-redefinition loop for all already-exposed
  Abelian vector EOM terms.

Focused validation passed:

- `tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_commutator_exposure_without_formal_eom_keeps_vector_replay_inactive`
- `tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_stages_vector_eom_redefinition_after_formal_eom_exposure`
- `tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_commutator_exposure_without_formal_eom_keeps_vector_replay_inactive`
- `tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_stages_vector_eom_redefinition_after_formal_eom_exposure`
- `tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_public_match_selected_chd_hscalar_lscalar_eom_bridge_records_next_frontier`
- `tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_public_match_selected_chd_tree_staging_preserves_wilson_line_vector_delta`
- `dependencies/.venv/bin/python -m mypy`
- `git diff --check`

## Matchete Deep-Dive Refresh

This slice re-read the active one-loop call path directly in Matchete:
`Matching.m`, `SuperTrace.m`, `LoopIntegration.m`, `FunctionalTools.m`,
`EFTCounting.m`, `Simplifications.m`, `FieldRedef.m`,
`CouplingManipulations.m`, `TreeLevelMatching.m`, and
`DevTools/Validation.m`. The ledger above remains the authoritative local
summary of each top-level Mathematica function in the active route.

The practical conclusion for the Singlet `cHD` frontier is:

- Raw selected Wilson-line agreement is necessary but not sufficient. The
  Matchete integration test boundary is `SaveValidationResults[...]`, which
  compares per-trace simplified results, the off-shell `GreensSimplify`
  result, the on-shell `EOMSimplify` result, and the final
  `MapEffectiveCouplings` target-basis rules.
- `EvaluateSTr[...]` has a strict semantic order: insertion replacement,
  open-CD action, loop-momentum collection/tensor reduction, symmetry
  pruning, fermion trace closure, Wilson expansion, loop integration, and
  algebra cleanup. Pychete mismatch probes must keep comparing against this
  order instead of jumping directly to Wilson coefficients.
- `EOMSimplify[...]` is a staged field-redefinition algorithm, not just EOM
  replacement. The committed vector replay bridge now matches the
  `PerformSystematicFieldRedefs` / `ShiftLagrangian` consumer boundary for
  already-exposed Abelian vector EOM terms.
- The next unchecked generic boundary is still the producer side:
  Matchete's class-local `InternalSimplify` / `IBPSimplify` /
  `IdentitiesIBP` route that rewrites the selected `cHD` source into the
  formal scalar/vector EOM representatives consumed by `ShiftLagrangian`.
- Final matching-condition parity will need a closer
  `MapEffectiveCouplings` analogue than isolated coefficient lookup for the
  full model: introduce/track temporary effective couplings, collect the
  input-target operator difference, solve target couplings with index-aware
  rules, symmetrize, and truncate each RHS by EFT order. Native Symbolica
  coefficient extraction can remain the fast path for targeted probes.

Next code slice: use this staged boundary in the remaining Singlet `cHD`
gap analysis for full public-route composition, especially unselected trace
remainder and final `MapEffectiveCouplings`-equivalent projection semantics.

## Current Slice Update: Matchete Route Audit And Per-Trace Order Filters

This slice re-opened the live Matchete source bodies for the active route:
`Match`, `SetCurrentLagrangian`, `SetSubstitutions`, `LoopMatch`,
`PowerTypeSTr`, `GenericPropagatorExpansion`, `DeterminePowerInsertions`,
`EvaluateSTr`, `LoopIntegrate`, `InternalSimplify`, `GreensSimplify`,
`EOMSimplify`, `PerformSystematicFieldRedefs`, `ShiftLagrangian`,
`VectorShift`, `SaveValidationResults`, and `MapEffectiveCouplings`. The
ledger above remains correct: Matchete's one-loop validation boundary is a
composition of stage-local simplified trace results, off-shell Green-basis
cleanup, on-shell systematic field redefinitions, and final target-basis
coupling solving. The implementation should keep matching these boundaries in
order instead of tuning a final Wilson coefficient.

The concrete implementation change from this audit is a generated-plan filter
for per-trace Wilson-line total orders:
`OneLoopMatchOptions.wilson_line_total_orders_by_trace`. This mirrors the
Matchete structure more closely than a single global order filter when
different trace words require different bounded `DeterminePowerInsertions`
windows. The existing public four-slot Singlet `cHD` test now exercises this
per-trace filter and records it in result metadata.

A watchdog-wrapped two-trace public composition probe with
`hScalar-lScalar` orders `{0,2,4}` and
`hScalar-lScalar-lVector-lScalar` orders `{0,1,2}` was stopped after it
remained silent for roughly two minutes. That means the per-trace filter is a
needed diagnostic/control surface, but the full aggregate public composition
still needs a performance-aware stage-local composition path before it should
be promoted to a regression test.

Follow-up performance audit: Matchete's committed Singlet validation record
reports `Time (Match) -> 5.095216`, `Time (GreensSimplify) -> 0.30953`,
`Time (EOMSimplify) -> 4.203712`, and
`Time (MapEffectiveCouplings) -> 15.600245`, i.e. roughly 25 seconds for a
broader full-model validation boundary than pychete's selected two-trace
probe. A pychete profile of the selected public route showed the time is not
dominated by final coefficient projection; it is dominated by repeated
termwise Wilson-line cleanup: `replace_multiple`, idenso delta/field-strength
group simplification, NCM scalarization, open-CD action, and projection
prefilter label generation. Matchete's `EvaluateSTr` does insertion
replacement, open-CD action, loop-momentum gathering, Wilson expansion, loop
integration, and algebra cleanup in a collected staged expression flow rather
than repeatedly running every cleanup pass over every generated term. The
next performance slice should therefore reshape pychete toward a collected
stage-local Wilson-line evaluation path, while keeping termwise diagnostics
available for debugging.

This slice added conservative no-op guards around idenso colour/delta and
field-strength group simplification so expressions without `Delta`, `CG`,
`FieldStrength`, or native spenso colour wrappers skip those backend passes.
The bounded public four-slot `cHD` regression improved from about ten seconds
to about eight seconds, but the two-trace public composition remains much
slower than Matchete and should not yet be promoted to a slow regression.

This slice also fixed the public Wilson-line `INTERNAL` source ordering:
after loop normalization, `Theory.match(...)` now activates the
`interaction_wilson_line_*_internal_integral_through_finite_part` source as
the active off/on-shell EFT source for later Matchete-style EOM and projection
stages. Raw evaluated sums remain in named supertraces for diagnostics. This
matches Matchete's `EvaluateSTr -> EpsExpand` ordering and prevents positive
`epsilon` powers from leaking into public on-shell projections.

## Current Slice Update: Entrywise Internal Wilson-Line Evaluation

The follow-up performance slice added
`WilsonLineInternalEvaluationMode` with public
`OneLoopMatchOptions.wilson_line_internal_evaluation_mode`. Public internal
Wilson-line matching now defaults to `entrywise`, while the setup-level
diagnostic methods still default to `termwise`. The entrywise evaluator keeps
the existing per-entry diagnostics but evaluates each plan entry as a collected
sum. For the pre-Wilson tensor-reduction path it additionally groups terms by
identical propagator topology, sums their formal `WilsonTerm` numerators, and
then runs the Matchete-order tensor/Wilson/postprocess chain once per topology
instead of once per term. This is a step toward Matchete's collected
`EvaluateSTr` staging without removing the termwise debug route.

Focused checks:

- `tests/integration/matching/test_fluctuation_operator.py::test_wilson_line_internal_evaluation_can_tensor_reduce_before_wilson_expansion`
  now verifies entrywise and termwise pre-Wilson evaluation agree on the same
  formal Wilson-term input.
- The watchdog-wrapped public Singlet four-slot `cHD` order-one checkpoint
  still passes and records
  `interaction_wilson_line_internal_evaluation_mode == "entrywise"`.
- Public API export/docstring checks for the new enum passed.

Performance evidence:

- Setup and plan generation for the selected two-trace Singlet `cHD` public
  composition remain cheap: about 1.9 seconds for setup and 0.02 seconds for
  the 24-entry generated plan.
- Wilson-line term generation is still the main bottleneck: the same staged
  probe took about 38 seconds to build 68 kept terms across 13 non-empty plan
  entries before scalar integral evaluation or final projection.
- The slow entries are the four-slot
  `hScalar-lScalar-lVector-lScalar` total-order-two families, especially
  derivative allocations on earlier slots such as `o2_0_0_0`,
  `o0_2_0_0`, `o1_1_0_0`, `o1_0_1_0`, and `o0_0_2_0`.
- A conservative bosonic path-template cache was added for exact duplicate
  path templates, remapping Wilson-link symbols and preserving per-path
  component weights. It is intentionally strict and does not hit the active
  Singlet slow paths, because paths `0`, `1`, `6`, and `7` are different
  Higgs/bar-Higgs orientations rather than identical templates. This confirms
  that a naive path collapse would risk the multiplicity/charge-orientation
  problem already identified earlier.

Next performance direction:

- The remaining Matchete-vs-pychete speed gap is not solved by entrywise
  scalar integral evaluation alone. The next real refactor should build a
  collected path-sum representation for a plan entry before
  `ActWithOpenCDs`, symmetry pruning, `WilsonExpand`, and idenso cleanup,
  then split only where topology or diagnostics require it. This mirrors
  Matchete's `DeterminePowerInsertions -> EvaluateSTr` ordering more closely
  than running the full open-CD/Wilson/postprocess chain independently on
  every path and every generated term.

## Current Slice Update: Collected Wilson-Line Path Sums

This slice added `OneLoopMatchOptions.wilson_line_collect_path_sums` and
setup-level `collect_path_sums` plumbing for selected Wilson-line expansion.
The new path sums collect raw same-topology Wilson-line numerators before
`ActWithOpenCDs`, Wilson-term expansion, and idenso cleanup, while leaving the
older pathwise route available for term diagnostics.

Focused regression coverage was added to the Singlet four-slot
`hScalar-lScalar-lVector-lScalar` fixture: the pathwise zero-order scalar-vector
probe now produces 16 nonzero path terms, while the collected route collapses
the same source to one term. The summed numerators agree both before and after
open covariant derivatives act.

Performance findings:

- Setup and plan generation remain cheap: about 1.9 seconds and 0.03 seconds
  respectively for the selected `hScalar-lScalar` plus
  `hScalar-lScalar-lVector-lScalar` two-trace public composition with 85 plan
  entries.
- The broad two-trace collected generation still exceeded the useful
  interactive budget and was stopped through `stop.order`. Therefore
  collection after raw path materialization is still not enough for public
  parity-speed composition.
- Per-entry profiling localizes the active cost to the four-slot total-order-2
  derivative allocations. Representative collected timings:
  `o2_0_0_0` about 9.8 seconds, `o0_2_0_0` about 5.3 seconds,
  `o1_1_0_0` about 4.3 seconds, `o1_0_1_0` about 2.8 seconds, and
  `o0_0_2_0` about 2.5 seconds. Two-slot `hScalar-lScalar` entries remain
  subsecond.
- Path-sum collection reduces output term count on the slow entries, e.g.
  eight pathwise terms become two collected topology terms, but runtime barely
  changes. The cost is not raw path construction or final term count.
- Stage profiling of the slow `o2_0_0_0` entry shows raw construction and
  `sum_expr(...).expand()` are negligible. The time is in expanded
  `ActWithOpenCDs`, NCM distribution, symmetry pruning, Wilson expansion, and
  idenso cleanup. One group grows temporarily to roughly 4.6 MB / 5120
  expression nodes after open-CD action, then 6.7 MB / 8560 nodes after NCM
  distribution before being pruned and simplified.

Matchete comparison:

- Matchete's relevant source boundary remains `PowerTypeSTr`:
  `GenericPropagatorExpansion`, `DeterminePowerInsertions`, then
  `EvaluateSTr`.
- `EvaluateSTr` first applies the insertion replacements and `$Xsubs/$Msubs/$Gsubs`
  to a collected generic expression, then runs `ActWithOpenCDs`,
  `GatherLoopMomenta`, `RemoveSymmetryVanishingWilsonTerms`,
  `CloseFermionLoop`, `EvaluateSymmetricLorentzInds`, `ContractMetric`,
  `WilsonExpand`, `LoopIntegrate`, and final algebra cleanup.
- The pychete slowdown is therefore structural: it still materializes raw
  path-level expressions and runs repeated bounded `NCM`/open-CD replacement
  passes over already expanded pychete expressions. The next refactor should
  move closer to Matchete's insertion-level collected expression pipeline,
  not add more pathwise caches.

## Current Slice Update: Earlier Wilson-Term Symmetry Pruning

This slice moves Wilson-line loop-momentum symmetry pruning earlier in the
shared raw Wilson-line postprocessor: after `ActWithOpenCDs` and before the
second `distribute_ncm_additions(...)` pass. This is closer to Matchete's
`EvaluateSTr` order, where `RemoveSymmetryVanishingWilsonTerms` follows the
open-CD/gather stage before later Wilson expansion and algebra cleanup.

The change is intentionally semantic-preserving: focused Singlet
four-slot pathwise-vs-collected numerator checks still pass, and the public
four-slot `cHD` checkpoint remains green under the 30 GiB watchdog.

Performance evidence on the same collected four-slot total-order-2 family:

- `o2_0_0_0`: about 9.8 seconds before, about 9.1 seconds after.
- `o0_2_0_0`: about 5.3 seconds before, about 5.0 seconds after.
- `o1_1_0_0`: about 4.3 seconds before, about 3.7 seconds after.
- `o1_0_1_0`: about 2.8 seconds before, about 2.5 seconds after.
- `o0_0_2_0`: about 2.5 seconds before, about 2.4 seconds after.

The improvement is useful but not decisive. A Symbolica
`Transformer.map_terms(...)` prototype for the open-CD and additive-NCM
passes was also tested and found to be neutral or slightly slower on the worst
entry. The remaining performance frontier is still structural: implement a
more Matchete-like insertion-level collected `EvaluateSTr` expression
pipeline, rather than optimizing the existing raw-path postprocessor further.

## Current Slice Update: Two-Trace Public Composition Performance Audit

The full selected two-trace public composition in pychete is currently slower
than Matchete. The best apples-to-apples conclusion remains the committed
Matchete Singlet validation timing: Matchete runs a broader full-model
boundary in roughly 25 seconds total (`Match`, `GreensSimplify`,
`EOMSimplify`, and `MapEffectiveCouplings`), while pychete's narrower selected
two-trace public composition still exceeded the useful interactive budget.
This is not acceptable as a final architecture because the selected pychete
job should not be slower than Mathematica's broader route.

The relevant Matchete implementation was rechecked directly in
`Package/SuperTrace.m`. The hot path is:
`PowerTypeSTr -> GenericPropagatorExpansion -> DeterminePowerInsertions ->
EvaluateSTr`. `EvaluateSTr` substitutes concrete insertions and `$Xsubs`,
`$Msubs`, `$Gsubs` into one generic noncommutative expression, then runs
`ActWithOpenCDs`, `GatherLoopMomenta`,
`RemoveSymmetryVanishingWilsonTerms`, `CloseFermionLoop`,
`EvaluateSymmetricLorentzInds`, `ContractMetric`, `WilsonExpand`,
`LoopIntegrate`, and final index/group/Dirac cleanup. pychete still reaches
too much of that work through path-derived raw numerators, even after
same-topology path-sum collection.

A bounded `wolframscript` probe of the direct Matchete helper for the four-slot
prop-order-2 family completed in about five seconds, but the selected raw sum
was zero; this repeats the earlier warning that this helper is not the
nonzero public-composition timing boundary. The useful comparison remains the
full validation route and the stage structure above.

One local pychete shortcut was tried and rejected: delaying
`distribute_ncm_additions(...)` until after same-topology path sums are
collected. Focused Wilson-line tests showed this is not semantics-preserving
with the current `act_with_open_covariant_derivatives(...)` implementation:
additive `NCM` operands must be linearized before open-CD action and Wilson
symmetry pruning. Therefore the next speedup must be structural, not another
pathwise cache or local distribution reorder. The intended next design is a
Matchete-like generic `FuncNCM` / insertion-level `EvaluateSTr` representation
that performs insertion replacement and termwise open-CD/symmetry/Wilson
staging once per collected insertion expression, then splits only by topology
or diagnostics.

## Current Slice Update: Staged Wilson-Line Projection Sources

This slice made selected-only Wilson-line projection closer to Matchete's
staged composition principle without introducing a Wilson-specific coefficient
patch. The public selected Singlet `hScalar-lScalar-lVector-lScalar -> cHD`
route now keeps per-entry Wilson-line sources through the scalar-commutator
and EOM/exposure boundary, then projects matching conditions from those staged
sources instead of from one monolithic on-shell expression.

Important details:

- Internal raw Wilson-line results still activate the normalized
  through-finite source for later stages, matching the existing
  `EvaluateSTr -> EpsExpand` boundary.
- Internal minimal-subtraction Wilson-line results now expose normalized
  finite and pole supertrace stages entrywise, and staged projection uses the
  normalized finite entries. Activating through-finite sources for the MS
  backend was tested and found wrong for the selected `cHD` checkpoint because
  it changed the final finite source being projected.
- `MatchingResult.staged_projection_sources("on_shell_eft_lagrangian")` now
  prefers dynamic `wilson_line_on_shell_projection_source[...]` entries, then
  appends any tree-level on-shell projection source. This keeps projection
  linear over the same selected trace entries Matchete evaluates in stages.
- The selected `cHD` source also exposed a missing native cleanup boundary:
  tensor reduction emits explicit Lorentz metrics contracting field derivative
  slots, while the Warsaw projection target uses repeated derivative indices.
  The result-wide metric cleanup now calls idenso-backed
  `simplify_pychete_field_derivative_metrics(...)` before
  `simplify_pychete_field_strength_metrics(...)`, so projection sees the
  native contracted derivative-slot form.

Focused validation:

- `test_public_match_selected_chd_four_slot_matchete_dof_weighted_route_matches_checkpoint`
  now asserts staged Wilson-line projection metadata and still reproduces the
  selected nonzero `cHD` coefficient.
- `test_public_match_selected_chd_four_slot_total_order_filter_matches_checkpoint`
  remains green for the raw internal through-finite path.
- `test_loop_normalization_exposes_through_finite_projection_sources` now also
  covers normalized finite/pole Wilson-line stages and their entrywise forms.
- The idenso field-derivative metric unit test and the staged-source
  MatchingResult smoke test pass.

## Current Slice Update: Hybrid Fixture Preview Staging

This slice carries the same staged Wilson-line projection-source idea into
hybrid preview and validation-fixture routes. The previous runtime patch
worked for selected-only public `Theory.match(...)` sources, but
`ValidationFixture.one_loop_preview(...)` always routes generated Wilson-line
requests through the hybrid selected-trace-plus-interaction-remainder result.
That path is used by Matchete-independent gap reports, so it must expose the
same bounded projection surface.

Implementation details:

- The shared Wilson-line projection-source helper now distinguishes the final
  aggregate source from the selected Wilson-line entry source.
- For hybrid internal minimal-subtraction results, the helper uses normalized
  finite Wilson-line entries as selected staged sources and adds an
  `interaction_power_type_remainder` staged source for the aggregate hybrid
  remainder.
- For raw internal results, it keeps the normalized through-finite entry
  source convention.
- `ValidationFixture.one_loop_preview(...)` now applies the same
  scalar-commutator/EOM transformations to each staged source as it applies to
  the aggregate source, and records
  `wilson_line_on_shell_projection_source_count` /
  `wilson_line_on_shell_projection_sources` metadata.
- Fixture previews now also run idenso-backed
  `simplify_pychete_field_derivative_metrics(...)` before
  `simplify_pychete_field_strength_metrics(...)`, matching public
  `Theory.match(...)` and keeping derivative-sector targets such as `cHD`
  in projectable contracted-index form.

Validation:

- `test_singlet_wilson_line_filter_keeps_derivative_higgs_sources_staged_for_projection`
  now verifies direct fixture previews expose the selected
  `hScalar-lScalar#wilson0_o0_0` source plus the interaction-power remainder
  as staged projection sources, with metric cleanup metadata.
- The affected public Singlet `cHD` staging tests still pass:
  `test_public_match_selected_chd_tree_staging_preserves_wilson_line_vector_delta`,
  `test_public_match_selected_chd_hscalar_lscalar_eom_bridge_records_next_frontier`,
  and
  `test_public_match_selected_chd_four_slot_matchete_dof_weighted_route_matches_checkpoint`.
- Targeted mypy on `matching.py`, `validation_fixtures.py`, and
  `matching_results.py` passes, and `git diff --check` is clean.
