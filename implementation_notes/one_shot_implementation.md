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
selected `hScalar-lScalar -> cHD` B-vector EOM replay now reaches Matchete's
finite dim6/dev3 replay coefficient after fixing indexed
functional-derivative alpha matching. The older
`hScalar-lScalar-lVector-lScalar -> cHD` four-slot prop-order-0 aggregate is
now explicitly recorded as a factor-two multiplicity frontier in the default
component-explicit diagnostic route. The new opt-in Matchete-style DOF route
builds that selected trace from label-level fluctuation DOFs and carries the
omitted SU(2) component multiplicity as Wilson-line path weights. That gives
four B-containing generated paths with effective weight eight, matching the
Matchete checkpoint without evaluating sixteen duplicate component paths.
The remaining blocker is full public-route composition beyond the matched
selected sources: heavy-scalar solution terms, unselected trace remainder,
pole/MS convention handling, broader component-weight validation, and broad
Singlet `cHD` projection against Matchete's full on-shell result.

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

## Matchete One-Loop Pipeline Audit

This is the current conceptual map from the local Matchete source code. Use it
as the checklist when pychete disagrees with a Matchete matching result: dump
the earliest comparable stage, then patch the first generic semantic
divergence in this order.

- `LoadModel[...]` loads the UV/EFT model definitions: gauge groups, fields,
  masses, couplings, representations, basis operators, and stored model
  options. pychete fixtures must remain Mathematica-independent, but their
  converted state must preserve the same theory metadata before any symbol is
  constructed.
- `Match[lag, EFTOrder -> 6, LoopOrder -> 1]` is the public integration entry.
  It rejects unsupported heavy vectors at loop level, calls
  `SetCurrentLagrangian`, adds tree matching through `ReplaceHeavyEOM` when
  requested, adds one-loop matching through `LoopMatch`, applies
  `ContractCGs // MatchReduce`, and finally Hermitian-symmetrizes the result.
- `SetCurrentLagrangian[...]` canonicalizes the Lagrangian with
  `HcExpand`, `CanonizeFermionMassTerms`, `IntroduceEffectiveMasses`,
  `ContractCGs`, `RelabelIndices`, and `Contract`; adds gauge-fixing and ghost
  terms; refreshes the current field/mass association; solves heavy-field EOMs
  with `DetermineEOMs`; and, for loop matching, calls `SetSubstitutions`.
- `SetSubstitutions[...]` is the source-composition boundary for loop
  matching. It builds `$XFieldDofs` through `LagrangianDofs`/`FieldDoFs`,
  subtracts `KinOpLagrangian`, takes `FluctuationOperator` derivatives of the
  remaining interaction Lagrangian, removes ghost/vector background pieces
  from X-terms, lowers covariant derivatives to
  `OpenCD[...] - I LoopMom[...]`, decomposes each X-term by `SeriesEFT` and
  momentum/open-CD order, and stores `$Xsubs`, `$XOrders`, `$XOrdMin`,
  `$Msubs`, and `$Gsubs`. pychete must keep target filtering and generated
  Wilson-line entries tied to this ordered X-term data rather than repairing a
  fully expanded expression later.
- `LoopMatch[...]` selects log-type traces and power-type traces. It obtains
  power words from `ListPowerTypeTraces`, optionally filters `WhichTraces`,
  evaluates `LogTypeSTr` for charged single-field log traces, and evaluates
  `PowerTypeSTr` for each cyclic trace word.
- `ListPowerTypeTraces[...]` enumerates trace words from heavy seeds, prunes by
  `$XOrdMin` and EFT order, enforces the maximum number of X insertions, and
  cyclically de-duplicates words. This is why pychete's Wilson-line trace
  planning must preserve cyclic factors and component/field-degree weights.
- `PowerTypeSTr[...]` applies the supertrace statistics prefactor
  `-I*hbar/2` times the fermion/ghost sign, computes the allowed propagator
  expansion order, builds a `GenericPropagatorExpansion`, generates allowed
  insertions with `DeterminePowerInsertions`, evaluates every term with
  `EvaluateSTr`, then runs `ReplaceHeavyEOM` on the matching result before
  multiplying the prefactor into every term.
- `GenericPropagatorExpansion[...]` builds the ordered noncommutative template
  `Xop, Prop, Xop, Prop, ..., WilsonLine`. Propagator mass slots are the
  post-insertion modes, matching pychete's `WilsonLineTracePath` convention.
  `PropExpand` uses bosonic expansions for scalars, the Matchete extra minus
  sign for vector slots, and `PropFermionExpand` for fermion slots with the
  explicit slash numerator and open-derivative term.
- `DeterminePowerInsertions[...]` enumerates concrete field DOF combinations
  from `$XFieldDofs`, filters selected `Fields` when requested, attaches the
  cyclic symmetry factor, populates covariant-momentum/open-CD orders, and
  returns one replacement bundle for `Xterm`, `Mterm`, `GaugeCTerm`, and the
  closing `WilsonTerm`. pychete's selected-trace parity probes should compare
  here before doing tensor reduction.
- `EvaluateSTr[...]` applies the insertion replacements and `$Xsubs/$Msubs/$Gsubs`,
  acts open covariant derivatives with `ActWithOpenCDs`, converts `FuncNCM` to
  `NCM`, gathers loop momenta, removes symmetry-vanishing Wilson terms,
  closes fermion traces, evaluates symmetric loop-momentum tensors, contracts
  metrics, expands Wilson lines, performs `LoopIntegrate`, relabels indices,
  expands generated field strengths, contracts deltas/CGs, refines Dirac
  products, and finally `EpsExpand`s. pychete must keep idenso/spenso/vakint
  at exactly these algebra/tensor/integral boundaries.
- `WilsonExpand` / `WilsonTermExpand` evaluate coincidence-limit Wilson lines.
  Zero derivatives give the identity transporter, one derivative vanishes, and
  higher derivatives are generated by derivative-sublist partitions and
  `FSWilsonFactor`/`DevTermOnWilson`, with symmetry-vanishing cases removed
  before expansion.
- `GatherLoopMomenta`, `LoopMoms`, `EvaluateSymmetricLorentzInds`, and
  `SymGammaFactor` turn numerator loop momenta into symmetric metric tensors
  and dimension-dependent gamma factors before integration. For pychete this
  is the vakint tensor-reduction boundary; single-scale analytic evaluation
  may be checked against vakint, while mixed/zero-mass analytic evaluation is
  pychete-owned.
- `LoopIntegrate[...]` collects `Prop[m]` and `Prop[0]` powers, explicitly
  merging duplicate mass propagators into one power, then emits `LF`/`LFFull`
  loop-function placeholders. `EvaluateLoopFunctions[...]` evaluates finite
  or pole pieces through `MultiScaleIntegral` / `SingleScaleIntegral`, and
  `EpsExpand` applies `d = 4 - 2 eps`. This is the reference for pychete's
  propagator-power collection and MS/pole convention checks.
- `MatchReduce[...]` is the final off-shell loop cleanup. It contracts CGs,
  rewrites field-strength representation indices, evaluates single-scale
  `LF[...]` functions, converts trivial CG deltas, simplifies epsilon CG
  products, and removes redundant `FlavorSum`s.
- `CovariantLoop[...]` is a diagnostic selected-field path. It still calls
  `SetCurrentLagrangian`, maps fields to Matchete field-type labels, evaluates
  the relevant log/power traces, then applies `ContractCGs // MatchReduce`.
  pychete debug routes should use it only as a selected-trace oracle, not as a
  separate architecture.
- `EOMSimplify[...]` is the on-shell EFT reduction entry used after matching.
  It expands/Hermitian-expands the Lagrangian, separates constants, chooses
  loop order and reduction identity scheme, calls `InternalSimplify`, warns on
  heavy-field EOMs, applies `PerformSystematicFieldRedefs`, resubstitutes dummy
  coefficients if used, and finishes with `GreensSimplify`.
- `InternalSimplify[...]` is the key Matchete normal-form step before field
  redefinitions. It applies `ContractDelta`, `ContractCGs`, `IBPSimplify` with
  the requested `ReductionIdentities`, `CollectCoefficients`, and then
  `AtomicToOperatorForm` unless internal operator representation is requested.
  The Singlet `cHD` debug fixture shows this is the stage that creates the
  formal B-vector EOM source and removes broad heavy-sector `kappa/muphi`
  branches before the field shift.
- `IBPSimplify[...]` / `ConstructOperatorIdentities[...]` classify operators,
  generate IBP, CD-commutator, Jacobi, spinor, chirality, symmetry, group,
  Fierz, and Lorentz-Schouten identities according to `ReductionIdentities`,
  rank operators by `OpScore`, row-reduce the identity matrix, and return
  replacement rules for redundant `AtomicOp`s. pychete's Green-basis and
  vector-EOM normal forms must match this class-local identity logic, not
  global expression heuristics.
- `PerformSystematicFieldRedefs[...]` first runs `RenormalizeMatterFields`,
  computes gauge-field normalization/kinetic mixing, then loops over EFT
  dimension and derivative count with `ShiftLagrangian`. Each shift selects
  EOM terms of one class, determines field shifts, inserts dummy shifted
  fields into only the terms that can contribute at the requested order, and
  calls `InternalSimplify` again. This is the conceptual reason pychete's
  Wilson-line scalar/EOM bridge must project from the scalar/EOM-exposed,
  `InternalSimplify`-like source rather than applying tree heavy-field
  solutions after that bridge.
- `GreensSimplify[...]` is the final public Green-basis simplification:
  `HcExpand`, `LagrangianExpand`, constants separation, `ContractDelta`,
  `ContractCGs`, `IBPSimplify`, `CollectCoefficients`, and
  `AtomicToNormalForm`. It is the broad final cleanup, not a substitute for
  matching the earlier class-local `InternalSimplify` and field-redefinition
  stages.

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

1. Keep the current refactor/context cleanup semantic: the live note is still
   compact after the `part_G` archive, so do not create duplicate archives;
   instead keep updating this summary.
2. Continue splitting performance-critical helper families out of the
   oversized `src/pychete/matching.py` without changing behavior or widening
   any cHD parity probe.
3. Preserve compatibility aliases from `pychete.matching` for existing tests,
   notebooks, and debug scripts while giving each subsystem a semantic module
   home.
4. Run only targeted checks for the touched slice, then stage, commit, and push
   through `listener.py` once the slice is coherent.
5. Resume the full Singlet `cHD` public-route composition frontier after this
   code-organization slice is green.

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
- Extracted Wilson-line/CDE vakint staging, internal termwise evaluation, and
  Wilson-line postprocessing helpers from `src/pychete/matching.py` into
  `src/pychete/matching_integrals.py`. Existing private names remain imported
  compatibility aliases from `pychete.matching`, while the performance-critical
  tensor-reduction/evaluation boundary is now easier to inspect. This reduced
  `matching.py` from 9,190 to 8,563 lines in this slice without changing the
  selected cHD evaluation order.
- Fixed the indexed functional-derivative alpha-matching boundary in
  `src/pychete/functional.py`: indexed targets now try the native indexed
  Symbolica-pattern variation before accepting exact replacement output. This
  restores the missing `H[d2]` EOM entries in the Singlet fluctuation Hessian,
  doubles the selected `hScalar-lScalar` source multiplicity to Matchete's
  eight insertion neighborhood, and closes the residual factor-two gap in the
  selected B-vector replay finite coefficient.
- Added the paired idenso bridge support needed by that indexed variation:
  open identity deltas such as `Delta(Index(i,R), Index(i,Bar(R)))` reduce to
  one, while closed deltas with independent dummy labels continue to reduce to
  the registered representation dimension.
- Updated the older selected four-slot cHD frontier assertions after the
  indexed-variation fix exposed sixteen alpha-aware component paths where the
  committed Matchete prop-order-0 checkpoint has eight target quarter
  insertions. The tests now record this as a factor-two
  multiplicity-preserving canonical-basis frontier instead of claiming that
  aggregate as matched.
- Added a sharper diagnostic for that four-slot multiplicity frontier. The
  Matchete checkpoint is
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`;
  the paired pychete probe is
  `test_public_match_selected_chd_four_slot_wilson_coefficient_records_current_source_frontier`.
  The first ruled-out boundary is idenso delta contraction: unequal open
  fundamental/anti-fundamental labels remain explicit, so the factor two is
  not caused by a too-broad `Delta(Index(i,R), Index(j,Bar(R))) -> 1` rule.
  The current suspected first divergence is fluctuation path component
  enumeration versus Matchete's component/field-degree weighting: pychete
  enumerates paths `0,1,2,3,12,13,14,15,24,25,26,27,36,37,38,39`, all
  projecting to the same quarter contribution, while Matchete records eight
  target quarter insertions. Raw Symbolica tensor canonicalization is not yet
  a sufficient fix because several path templates reuse an index label in
  multiple contractions and `canonize_tensors(...)` correctly rejects them.
- Added the cheap Matchete-DOF path-weight boundary for that frontier. The new
  `src/pychete/matching_field_dofs.py` helper uses Symbolica tagged
  field/field-strength matches to build Matchete-style label-level fluctuation
  DOFs, exposed as `matchete_fluctuation_dof_basis_fields(...)` and
  `matchete_fluctuation_dof_basis(...)`. On the Singlet fixture this reduces
  the discovered basis from the current 26 concrete dummy-label modes to 16
  label-level DOFs. The paired `wilson_line_path_component_weight(...)`
  diagnostic shows that the canonical
  `hScalar-lScalar-lVector-lScalar` setup has 12 total paths and four
  B-containing paths `(0, 1, 6, 7)`, each with SU(2) component weight two,
  matching Matchete's eight nonzero target insertion checkpoints before any
  Wilson-term expansion or tensor reduction.
- Promoted that boundary into an explicit opt-in runtime route. The setup and
  public one-loop options now expose Matchete-style label-level fluctuation
  DOFs plus component-weighted Wilson-line paths, while default component
  enumeration remains unchanged for diagnostics. Generated Wilson-line terms
  carry both their raw term count and component-weighted effective count in
  metadata, making parity/performance comparisons explicit.
- Extended the performance validation to the active `hScalar-lScalar`
  selected public routes. For the accepted `cHW/cHB/cHWB` field-strength
  subset, Matchete-style label-level DOFs alone preserve the Matchete
  coefficients and keep the 14-term route; adding component weights doubles
  those coefficients and is therefore explicitly not valid there. For the
  scalar-EOM `cHD` public bridge, label-level DOFs plus component weights
  preserve the selected coefficient and vector-field-redefinition delta while
  reducing raw generated Wilson-line terms from 32 to 16 with effective
  weighted count 32.

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
- The Matchete-DOF helper now pins the intended weighted replacement boundary:
  use label-level DOFs from `matchete_fluctuation_dof_basis_fields(...)`, then
  carry `wilson_line_path_component_weight(...)` through selected trace
  generation with `OneLoopMatchOptions.use_matchete_fluctuation_dof_basis`
  and `OneLoopMatchOptions.wilson_line_weight_paths_by_component_dofs`. Do not
  evaluate all sixteen duplicate component paths when the weighted four-path
  canonical probe is available and validated for the same target. Keep the
  route opt-in until broader Singlet and non-Singlet fixtures validate the
  same Matchete field-degree/component semantics.
- Component weights are target/stage semantics, not a global switch. Current
  Singlet evidence says to use label-level DOFs without component weights for
  the accepted field-strength subset `cHW/cHB/cHWB`, and label-level DOFs
  with component weights for the scalar-EOM `cHD` route. Any broader use of
  component weights must first be backed by a Matchete checkpoint and paired
  pychete probe.
- For the four-slot `cHD` factor-two overcount, do not patch projection,
  tensor reduction, or idenso delta contraction next. The next useful slice is
  to port Matchete's field-degree/component weighting at the fluctuation path
  enumeration boundary, or to refresh the Matchete dump with the exact
  component/field-degree metadata needed to derive those weights generically.
- Projection filtering is now isolated in
  `src/pychete/matching_projection_filters.py`; keep future performance work
  there when it is about target-local Wilson-line/CDE pruning rather than
  supertrace construction itself. The focused extraction gate was:
  `test_wilson_line_target_filter_skips_impossible_entries_before_generation`,
  `test_singlet_wilson_line_target_prefilter_matches_matchete_order_four_insertions`,
  and `test_registered_chd_filter_requirements_keep_vector_eom_alias_candidates`,
  all under the 30 GiB watchdog.
- The public `hScalar-lScalar -> cHD` route now gets past the previous
  post-heavy scalar Green-basis capacity failure. The mismatch checklist for
  this slice is:
  Matchete fixture `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`,
  paired pychete probe
  `test_public_match_selected_chd_hscalar_lscalar_eom_bridge_records_next_frontier`,
  first differing boundary = public Wilson-line scalar EOM exposure after
  target-local heavy-scalar substitution. Before the patch, that stage fed the
  whole 1.3 MB/2592-term selected source into class-local Green-basis
  reduction and one unrelated H4/H6 operator class exceeded the 1536 basis-term
  cap. The runtime change ports a bounded Matchete-style class locality rule:
  in the Wilson-line EOM bridge, oversized operator classes are left
  unreduced while smaller classes continue through Symbolica-backed
  Green-basis reduction. This is not a final `cHD` coefficient patch.
- The public selected route now keeps the Wilson-line scalar-EOM bridge closer
  to the Matchete staged replay. When formal scalar-EOM exposure is enabled,
  pychete no longer runs a separate setup-level scalar commutator exposure
  before the formal-EOM pass; the combined post-integral scalar/EOM exposure
  owns that rewrite after loop normalization. The same route now automatically
  enables native tensor reduction for Wilson-line internal backends, because
  unreduced loop-momentum numerators hide the selected B-source from
  Symbolica coefficient projection. After the indexed-variation fix, the
  focused public regression records the selected Abelian B-vector
  field-redefinition delta
  `hbar*A^2*gY^2*(-log(mursq)/12 + log(M)/6 - 17/72)/M^4`; the combined
  direct formal-EOM replacement plus vector companion gives the Matchete B-only
  replay finite piece
  `hbar*A^2*gY^2*(-log(mursq)/6 + log(M)/3 - 17/36)/M^4`.
- Performance check for the indexed-variation fix: the public selected cHD
  probe still runs in about 53 seconds under the 30 GiB watchdog. The debug
  fixture refresh is slower because it records broad stage diagnostics, but
  the topology-lowered source probe remains around 100 KB and uses the same
  bounded projection chunks. If this fixture grows again, split it into a
  cheap path-multiplicity smoke and a slower explicit source-boundary refresh.
- Selected Higgs-gauge fixture tightening: the slow `cHW/cHB/cHWB` validation
  fixture now explicitly uses the label-level Matchete fluctuation-DOF route
  with component path weights disabled. The accepted coefficients and final
  term counts remain `10/10/14`, but the test now pins the bounded nonzero
  Wilson plan entries (`wilson14_o4_0` for `cHW/cHB`, `wilson5_o2_0` plus
  `wilson14_o4_0` for `cHWB`). This prevents future regressions from silently
  broadening back to explicit component enumeration for the already matched
  selected field-strength subset.
- Current Singlet Wilson-count audit: the committed
  `Singlet_Scalar_Extension.matchete_previous` fixture has 72 matching
  conditions, of which 64 are external SMEFT/Wilson entries and 25 are
  nonzero external Wilson coefficients. The broad max-trace-1 preview accepts
  39 Wilson entries, but those are the 39 zero Wilson coefficients. The
  meaningful nonzero-Wilson parity count is currently 3/25:
  `cHW`, `cHB`, and `cHWB` through the selected Wilson-line route.
  `cHD` remains the active first full-coefficient frontier.
- Staged projection composition fix: a bounded public-route probe showed that
  Wilson-line scalar/EOM exposure and Abelian vector-field redefinition
  updated the final on-shell Lagrangian after tree/loop staged projection
  sources had already been recorded. With `include_tree_level_matching=True`,
  staged matching-condition projection could therefore miss the generated
  `A^2*gY^2` vector-field-redefinition contribution even though direct
  projection from the final on-shell expression saw it. Runtime now
  re-synchronizes the loop-only on-shell projection source against the final
  on-shell expression minus the tree-level source after these additive
  Wilson-line transformations. This is a generic staging/composition fix; it
  does not claim full `cHD` parity because the heavy-solution
  `kappa/muphi` source-composition frontier remains.
- Latest Matchete/pychete stage dissection, 2026-06-29: the Matchete
  `singlet_eom_cHD.debug.json` fixture shows that `raw_lagrangian_eft`
  initially contains broad heavy-sector `cHD` branches, but
  `InternalSimplify` removes them before systematic field redefinitions; the
  B-vector replay then carries the finite `A^2*gY^2/M^4` shift while W
  projects zero to `cHD`. A bounded pychete public-route probe now mirrors the
  same boundary: before heavy-scalar solution reduction, the
  scalar/EOM-exposed selected source projects to a clean `A^2*gY^2/M^4`
  branch with no `kappa` or `muphi`; applying the heavy solution afterwards
  reintroduced a spurious `-hbar*A^2*kappa/M^4` term. Runtime now records but
  skips heavy-scalar solution replacement when
  `substitute_heavy_scalar_solutions=True` is combined with
  `wilson_line_expose_scalar_eom_terms=True`. This removes the `kappa/muphi`
  source-composition pollution from the selected public `cHD` bridge; the
  remaining full-coefficient gap is now missing public-source composition
  beyond this selected branch, especially unselected trace remainder and
  pole/MS convention handling.

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
