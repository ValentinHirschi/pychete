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
  nonzero. Pychete currently has meaningful nonzero parity for 3 of them
  (`cHW`, `cHB`, `cHWB`). `cHD` is the active first full on-shell frontier.

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
