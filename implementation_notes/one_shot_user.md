# One-Shot Port User Notes

## Approved Goal

Fully implement pychete's one-shot Matchete-style one-loop matching port on the
`one-shot-port` branch. The objective is to make pychete capable of performing
one-loop EFT matching for the Matchete validation target models, especially
SMEFT UV-complete matching models, while preserving pychete's Pythonic API and
using Symbolica/idenso/spenso/vakint as the computational backends instead of
reimplementing symbolic physics algorithms in Python.

Very important: use Symbolica as much as possible and periodically rescan the
Symbolica Python stub files so the native API stays in context.

Whenever Matchete and pychete disagree, the required workflow is to narrow the
disagreement with focused Matchete-side intermediate dumps before patching
pychete. Run or refresh debug WolframScripts often enough to compare raw
`EvaluateSTr`, insertion replacements, `ActWithOpenCDs`, `GatherLoopMomenta`,
`WilsonExpand`, loop integration, `ContractCGs`/`MatchReduce`/`GreensSimplify`,
`EOMSimplify`, and saved projection stages against bounded pychete probes at
the same semantic boundary. Patch the first differing generic algorithm rather
than a final Wilson-coefficient shortcut. Runtime pychete and pytest must
remain Mathematica-independent by consuming only committed derived fixtures.
For every active mismatch, the live workflow is to keep running or refreshing
focused Matchete debug WolframScripts and dissecting as many intermediate
Matchete objects as practical until the first divergence against pychete is
localized. Each progress update should name the Matchete dump/checkpoint, the
paired bounded pychete probe, and the current suspected stage boundary. This is
how pychete stays a Symbolica/idenso/spenso/vakint port of Matchete algorithms
rather than a collection of final-coefficient fixes.

Normal pychete tests must be Mathematica-independent. pytest must never require
Mathematica, `wolframscript`, or a runnable Matchete installation. Optional
top-level `scripts/` Wolfram conversion entry points may load the read-only
Matchete checkout to generate committed pychete-owned fixtures for users who
have Mathematica, but runtime code and tests must load only those fixtures.

Keep the approved implementation plan copied into both
`implementation_notes/one_shot_user.md` and
`implementation_notes/one_shot_implementation.md`, and keep both copies updated
whenever the plan changes. Keep `one_shot_implementation.md` continuously
updated with current progress, completed milestones, test status, backend/API
discoveries, dependency patches, blockers, and remaining work.

Sandbox approval prompts must never block progress. The `exec_command`
parameter `sandbox_permissions: "require_escalated"` is banned for this
repository. Do not set it, do not request escalation, and do not ask the user
for permission through the tool approval path. If a direct command fails with
`Operation not permitted`, a sandbox write restriction, or a read-only `.git`
metadata error, immediately dispatch the same command through the user-started
`listener.py` route by writing exactly one command to `run.order` and reading
`run.output`.

Mechanical fail-closed guard: the `sandbox_permissions` key must be absent from
every `exec_command` payload, including the value `use_default`. Before sending
any shell command, check the payload; if that key is present, remove it and
re-plan. If the command might require approval, send it through `listener.py`
instead of escalation. Approval escalation is not an available path for this
branch.

Current status clarification: no complete Matchete one-loop SMEFT integration
model has been reproduced end-to-end yet. The successful tests are narrower
integration slices around Mathematica-independent fixture loading, one-loop
preview/gap-report plumbing, selected Wilson-line trace smoke paths,
internal/vakint single-scale integral cross-checks, projection/canonicalization,
and partial Singlet-style Wilson projection behavior. The broad remaining
features are the full explicit Wilson-line trace engine, robust
non-Abelian/group and Dirac algebra through idenso/spenso, full default-model
integration of the internal mixed/zero-mass analytic integral backend,
complete converted model fixtures, and generic operator-basis projection
without Warsaw-specific core assumptions.

Latest mismatch-debugging instruction, 2026-06-28: keep confirming and using
the paired Matchete/pychete debug workflow during the active Singlet frontier.
When the two systems disagree, refresh focused Matchete WolframScript dumps,
compare them against bounded pychete probes at matching semantic stages, and
only patch pychete after the first generic algorithm boundary has been found.
Latest reinforcement, 2026-06-28: this is an active cadence. Keep running or
refreshing focused debug WolframScripts often during mismatch work, dump as
many relevant Matchete intermediate stages as practical, compare them directly
with bounded pychete probes, and record the first semantic divergence before
runtime patches. The standing repository guidance in `AGENTS.md` has been
updated so future continuations remember this focus on closely porting
Matchete algorithms through Symbolica/idenso/spenso/vakint.
Latest explicit confirmation, 2026-06-28: when a mismatch is active, continue
to run focused Matchete WolframScripts often and dissect their intermediate
objects against bounded pychete probes. Each progress note should name the
Matchete script or committed dump, the paired pychete probe, and the suspected
generic algorithm boundary before runtime pychete changes are accepted.
Latest performance-focused progress, 2026-06-29: pychete must remain at least
as targeted as the corresponding Matchete intermediate checks. A concrete
performance issue was identified in discovered fluctuation-basis dummy labels:
a naive canonicalization prototype reduced duplicated Hessian modes and
Wilson-line paths, but it was rejected because it lost Matchete's
component/field-degree multiplicity and halved the four-slot `cHD` checkpoint.
A future performance refactor may collapse these modes only if it also carries
explicit multiplicity/DOf weights through path enumeration, term filtering, and
tensor-reduction workload.
The active cHD mismatch is now compared against the committed Matchete
`hScalar-lScalar/cHD` prop-order-4 dump plus the regenerated pychete cHD
boundary fixture, with the suspected boundary localized between finite
Higgs-bilinear Wilson-line evaluation and Matchete's d-dimensional scalar
Green/EOM identity conversion.
Latest Matchete source-code audit, 2026-06-29: the active one-loop parity
route has been re-read directly in Matchete's `Matching.m`, `SuperTrace.m`,
`LoopIntegration.m`, `FunctionalTools.m`, `TreeLevelMatching.m`,
`EFTCounting.m`, `Simplifications.m`, `FieldRedef.m`,
`CouplingManipulations.m`, and validation code. For the Singlet `cHD`
frontier, compare pychete against Matchete stage-by-stage in this order:
`Match`, `SetCurrentLagrangian`, `SetSubstitutions`, `LoopMatch`,
`ListPowerTypeTraces`, `PowerTypeSTr`/`LogTypeSTr`,
`GenericPropagatorExpansion`, `DeterminePowerInsertions`, `EvaluateSTr`,
`ActWithOpenCDs`, `GatherLoopMomenta`, `WilsonExpand`, `LoopIntegrate`,
`MatchReduce`, `GreensSimplify`, `EOMSimplify`/`InternalSimplify`/field
redefinitions, and `MapEffectiveCouplings`. The current selected/staged
pychete checkpoints match the finite Singlet `cHD` sources and now also the
Matchete pole-through-finite Laurent convention locally; the remaining
frontier is efficient public `Theory.match(...)` composition of these same
stage-local results, not another coefficient-specific rewrite.
Latest performance slice, 2026-06-29: pychete now has a public
`WilsonLineInternalEvaluationMode` and defaults public internal Wilson-line
matching to `entrywise`. This collects each plan entry, groups same-topology
pre-Wilson numerators, and evaluates scalar integrals per entry while keeping
termwise diagnostics available. The four-slot Singlet `cHD` checkpoint still
passes with this mode. A staged two-trace probe shows setup and plan
generation are cheap, but Wilson-line term generation itself still takes about
38 seconds for 68 kept terms; the active slowdown is therefore the repeated
open-CD/Wilson/postprocess chain over the four-slot path orientations. The
next performance refactor should follow Matchete more closely by constructing
collected path-sum entries before `ActWithOpenCDs`, `WilsonExpand`, and idenso
cleanup, then split only where topology or diagnostics require it.
Latest collected-path profiling, 2026-06-29: pychete now has
`wilson_line_collect_path_sums`, which collects raw same-topology path
numerators before open-CD action and Wilson expansion. The focused Singlet
four-slot zero-order probe confirms pathwise and collected summed numerators
agree, with 16 path terms collapsing to one collected term. However, the full
two-trace public composition is still too slow: profiling localizes the cost
to four-slot total-order-2 entries such as `o2_0_0_0`, where raw construction
is negligible but `ActWithOpenCDs`, NCM distribution, symmetry pruning,
`WilsonExpand`, and idenso cleanup run on large expanded intermediates. The
next performance refactor should move still earlier toward Matchete's actual
`GenericPropagatorExpansion` + `DeterminePowerInsertions` + collected
`EvaluateSTr` staging rather than adding more pathwise caches.
Latest stage-ordering performance update, 2026-06-29: Wilson-line
loop-momentum symmetry pruning now runs immediately after `ActWithOpenCDs` and
before the second additive-NCM distribution pass. This matches Matchete's
`EvaluateSTr` ordering more closely and trims the slow four-slot total-order-2
entries modestly, e.g. `o2_0_0_0` from about 9.8s to 9.1s and `o1_1_0_0`
from about 4.3s to 3.7s, while focused Wilson-line equivalence tests and the
watchdog-wrapped public four-slot `cHD` checkpoint remain green. A
Symbolica `Transformer.map_terms(...)` prototype was neutral/slower, so the
next real performance step remains an insertion-level collected
`EvaluateSTr` pipeline.
- Two-trace public-composition performance audit, 2026-06-29: yes, pychete's
  full selected two-trace public composition is currently slower than
  Matchete's broader Singlet validation route, so this remains a structural
  performance bug. Re-reading Matchete confirms the needed shape:
  `PowerTypeSTr` builds a generic propagator expansion, enumerates
  `DeterminePowerInsertions`, and `EvaluateSTr` runs open-CD, symmetry,
  Wilson, loop-integration, and cleanup stages on the collected insertion
  expression. A pychete experiment that simply delayed additive `NCM`
  distribution past current `ActWithOpenCDs` was rejected by focused tests;
  the current open-CD engine needs linearized `NCM` operands. The next
  redesign must therefore introduce a Matchete-like generic
  `FuncNCM`/insertion-level `EvaluateSTr` representation rather than adding
  another pathwise cache.
- Follow-up prototype result, 2026-06-29: a temporary Symbolica
  `is_linear=True` pychete `FuncNCM` shortcut was tested and reverted. It
  passed the focused small Wilson-line checks but was several times slower on
  the heavy Singlet four-slot entries (`o0_2_0_0` around 21s vs the previous
  roughly 5s local baseline). The useful Matchete lesson is the whole
  staged `GenericPropagatorExpansion -> DeterminePowerInsertions ->
  EvaluateSTr` pipeline with delayed open-CD action and custom factor
  hoisting, not just a linear/distributive function head.
- Current nonzero Singlet Wilson status, 2026-06-29: the committed fixture has
  25 nonzero Wilson coefficients. The broad default report still has all 25
  nonzero entries different, but selected/staged parity is now established for
  4 of them: `cHW`, `cHB`, `cHWB`, and staged `cHD`. The new staged `cHD`
  regression compares against the saved Matchete fixture after the explicit
  loop-convention bridge between Matchete's `epsilon`/`mubar2` and pychete's
  vakint symbols. The remaining nonzero blockers group into Higgs
  potential/derivative coefficients (`cH`, `cHBox`), fermion-current
  coefficients (`cHf` family), Yukawa-Higgs coefficients (`cfH` family), and
  four-fermion coefficients; these should be attacked through Matchete-inspired
  staged source composition and `MapEffectiveCouplings`-style target solving,
  not coefficient-specific formulas.
- Latest converted-boundary status, 2026-06-29: the converted on-shell
  effective-coupling-map boundary now matches `cHD`, `cle`, `cledq`,
  `clequ1`, and `cquqd1` out of the 25 nonzero Singlet Wilson conditions.
  The UV model is `Singlet_Scalar_Extension`; the effective theory/basis is
  SMEFT Warsaw. Keep this list distinct from the selected public Wilson-line
  parity list, which is `cHW`, `cHB`, `cHWB`, and `cHD`.
- Follow-up converted-boundary status: the SU(3) group-Fierz basis-map layer
  now also recovers the coupled colour-current pairs `cqu1/cqu8` and
  `cqd1/cqd8`. The converted on-shell boundary is therefore green for
  `cHD`, `cle`, `cledq`, `clequ1`, `cqd1`, `cqd8`, `cqu1`, `cqu8`, and
  `cquqd1` out of 25 nonzero Singlet Wilson conditions. Validate these colour
  pairs as coupled target-lagrangian solves, not as isolated one-coefficient
  projections.

## Approved Plan

# One-Shot One-Loop Matching Port

## Summary

- Build a Pythonic pychete implementation of Matchete-style one-loop matching,
  prioritizing the default SMEFT UV matching models first, then all Matchete
  validation tests that map cleanly to pychete's architecture.
- Normal pytest must be Mathematica-independent. Optional top-level `scripts/`
  Wolfram conversion entry points may load Matchete to generate serialized
  pychete fixtures under the repo for users who have Mathematica, but tests
  load only those committed fixtures.
- Use Symbolica as the symbolic engine, idenso/spenso for gamma, colour,
  metric, and tensor algebra. Use pychete's own Matchete-style analytic backend
  for one-loop vacuum integral evaluation after tensor reduction, including
  single-scale, zero-mass, and mixed-mass cases. Use vakint for
  topology-independent tensor reduction and as an optional supported backend or
  cross-check for single-scale massive analytic evaluations.
- Incorporate Matchete author feedback: CDE is an older v0.1/paper route and
  should remain an opt-in diagnostic/validation path in pychete, while the
  forward core architecture should move toward explicit Wilson-line trace
  handling that generalizes beyond one loop. SMEFT Warsaw support should be an
  optional built-in operator basis on top of generic basis machinery, not a
  special core matching module.
- Compare results by pychete canonical equality, backed by Symbolica evaluator
  numeric probes for hard-to-canonicalize expressions.

## Key Changes

- Keep optional top-level `scripts/` Wolfram conversion entry points checked in
  for users who have Mathematica and want a convenient export/convert route for
  model definitions, validation expected outputs, supertraces, matching
  conditions, and selected unit-test fixtures. Supporting implementation code
  may live under `helper_mathematica_scripts/`, but all normal pytest/runtime
  paths must remain Matchete- and Mathematica-independent.
- Treat the direct Python Mathematica loader as a documented supported-subset
  loader for simple declarative model assets and saved-result snippets only.
  For complicated Mathematica models, use the optional top-level
  Wolfram/Matchete scripts to load the model, extract Matchete's parsed
  internal data, and emit equivalent pychete serialized state or Python fixture
  files that can be committed and used by tests and users.
- Add committed fixture assets for Matchete-independent pytest validation;
  never require `wolframscript` in normal tests.
- Extend pychete metadata with gauge groups, representations, CG tensors,
  charges, chiral fermions, ghosts, Goldstones, background fields, coupling
  symmetries, diagonal/unitary metadata, and generic operator-basis metadata
  using Symbolica symbol tags/data.
- Keep SMEFT Warsaw as one optional built-in basis provider implemented through
  the same generic `OperatorBasis`/Wilson-metadata route that any user-defined
  basis should use. Do not make core matching logic depend on SMEFT-specific
  modules or maps.
- Replace the current tiny Mathematica loader as the path for complex
  validation models with fixture loading; keep direct Mathematica-input support
  explicitly secondary and limited to its documented subset.

## Matching Engine

- Add a one-loop matching API around `Theory.match(..., loop_order=1)` returning
  a structured `MatchingResult` with UV Lagrangian, fluctuation operators,
  individual supertraces, off-shell EFT Lagrangian, on-shell EFT Lagrangian, and
  matching conditions.
- Implement the Matchete pipeline in pychete terms: free Lagrangian
  construction, Feynman rules/functional derivatives, fluctuation-operator
  extraction, heavy/light DoF classification, propagator expansion, supertrace
  generation, loop-momentum tensor reduction, integral evaluation, EFT
  truncation, EOM/on-shell reduction, and effective-coupling mapping.
- Use Symbolica patterns, `replace_multiple`, `series`, `coefficient`,
  `collect`, `derivative`, `Transformer`, and evaluator APIs before adding
  Python traversal logic.
- Route gamma/colour/metric simplification through idenso adapters,
  tensor/CG contraction through spenso adapters, topology-independent tensor
  reduction through vakint where useful, one-loop analytic vacuum-integral
  evaluation through a pychete-owned Matchete-style backend, and supported
  single-scale massive cross-checks through vakint adapters.
- If idenso/spenso/vakint are insufficient, add patch files under
  `dependencies/patches/`, make `dependencies/install_dependencies.py` apply
  them after clone/reset and before build, and test the patched behavior from
  Python.

## Validation And Tests

- First green milestone: fixture-generation scripts plus committed fixtures for
  the default integration models: `VLF_toy_model`,
  `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Then port mappable unit validations for definitions, covariant derivatives,
  EFT counting, Feynman rules, loop integration, Dirac/NCM algebra,
  simplifications, coupling manipulation, flavor/group/CG behavior, SSB, and
  dimensional reduction.
- Exclude tests that only assert Matchete's internal structure, caching,
  package globals, print forms, or Mathematica-specific behavior with a
  documented skip map.
- For every symbolic equality test, canonicalize with
  pychete/Symbolica/idenso/spenso/vakint; where canonical equality is fragile,
  add Symbolica `Evaluator`-based numeric probes with deterministic sample
  points.
- Keep `pytest` and `mypy` green at each committed milestone.
- Structure validation around larger implementation slices. While building,
  use smoke probes and focused pytest markers such as `definitions`,
  `functional`, `loaders`, `models`, `backend`, `matching`, `validation`, and
  `typing`; run broader `not slow` or slow validation gates only when the
  completed slice justifies the cost. Before starting a slice, consider the
  remaining implementation frontier and choose a coherent feature family to
  finish together; do not repeatedly run the whole suite while a design is
  still being reshaped.

## Workflow

- During implementation, create and maintain
  `implementation_notes/one_shot_user.md` and
  `implementation_notes/one_shot_implementation.md`.
- Commit and push only green, coherent milestones to remote branch
  `one-shot-port`.
- For one-shot work, plan and implement complete feature families before broad
  validation. Avoid repeated full-suite runs for individual local edits.
- Preserve the existing public API discipline: intended user APIs are exported
  through `pychete.api` and package root `pychete`, with docstrings and Jupyter
  `_repr_html_` / `_repr_latex_` where relevant.

## Assumptions

- Public API should remain Pythonic pychete, with Matchete-inspired helpers only
  where they reduce friction.
- Pytest must not depend on Mathematica, Matchete runtime loading, or
  `wolframscript`.
- Full validation means "all tests that map to pychete's implementation model,"
  with one-loop SMEFT matching treated as the primary acceptance target.

## Additional User Decisions

- Keep the Mathematica conversion route as an optional committed convenience
  for users who have Mathematica, preferably through a top-level `scripts/`
  directory. This does not change the core rule: pychete runtime code and
  pytest remain completely Matchete- and Mathematica-independent, and committed
  pychete-owned fixtures are the normal validation/user artifacts.
- Keep both the loaded-model-state conversion route and the previous
  matching-result conversion route discoverable under the top-level `scripts/`
  directory. Supporting implementation code can still live under
  `helper_mathematica_scripts/`, but the user-facing convenience entry points
  must stay committed with pychete.
- Continue treating the top-level Mathematica conversion scripts as optional
  convenience tooling only. It is acceptable to improve those scripts so users
  with Mathematica can generate pychete-owned fixtures, but runtime pychete and
  pytest must remain independent of Matchete and Mathematica.
- Keep a one-command optional Wolfram entry point under top-level `scripts/`
  for users who want Mathematica to perform the loaded-model export and then
  invoke pychete's fixture converter. This is a convenience wrapper only; the
  committed fixtures remain the canonical pychete inputs for users/tests
  without Mathematica.
- Keep the converter Mathematica scripts pushed with pychete in the top-level
  `scripts/` directory because users with Mathematica may appreciate the
  convenience route. This does not soften the independence rule: pychete
  itself, normal pytest, and committed validation fixtures must remain fully
  Matchete- and Mathematica-independent.
- Because full pytest is becoming slow, batch larger related implementation
  slices before paying the full-suite validation cost. Use targeted tests and
  focused smoke checks during the slice, then run full verification before
  committing and pushing a green milestone.
- In vakint topology handling, collect propagators with identical signatures
  into a single propagator with the corrected summed power. This must be done
  consistently for arbitrary integer powers, not only square numerator cases.
- Strengthen the workflow further: spend more time planning and implementing
  larger coherent chunks before running broad validation. Group tests so
  backend, matching, validation, and non-slow subsets can be run independently;
  use small focused tests while building a chunk, then targeted grouped gates,
  and reserve full pytest for larger milestones rather than every local fix.
- Before starting a new one-shot implementation slice, review the remaining
  frontier and choose a full feature family that can be completed coherently.
  Implement that family before paying any broad validation cost. If tests
  reveal a design problem, refactor fearlessly inside the slice, then rerun the
  smallest targeted marker group that exercises the redesigned surface.
- Store SMEFT Wilson projection metadata through pychete-owned Symbolica
  operator expressions through generic operator-basis metadata. Known
  Warsaw-basis coefficients should be registered through
  `pychete.bases.smeft_warsaw` helpers only because SMEFT is a bundled
  convenience basis; unsupported coefficients remain valid Wilson targets with
  missing operator metadata documented explicitly.
- For the default SMEFT validation fixtures, the optional
  `pychete.bases.smeft_warsaw` basis provider should cover the full 64-name
  Warsaw coefficient set from Matchete's `SMEFT_Warsaw.m`. That provider is
  the source of truth for the bundled SMEFT basis, but user-defined bases must
  be able to use the same generic mechanism.
- Matching-condition projection should be able to consume theory-owned
  registered Wilson metadata directly, without reconstructing target maps from
  reference fixtures. A selector such as `registered_wilsons` is the preferred
  user-facing path for projecting all Wilson coefficients that have stored
  operator metadata.
- Default SMEFT model fixtures must carry the same theory-owned Wilson symbol
  metadata as their matching fixtures. This avoids Symbolica symbol
  redefinition conflicts and lets validation projection prefer candidate
  theory metadata instead of reference-owned Wilson targets.
- Keep performance and scaling under active consideration throughout the
  one-shot implementation. Do not over-optimize prematurely, but for heavy
  symbolic matching paths prefer algorithms that avoid unnecessary global
  expansion, support target-selective projection/simplification, and delegate
  expensive algebra to native Symbolica/idenso/spenso/vakint primitives.
- After the current continuation slice, provide a brief user-facing summary of
  the main technical blockers still preventing full one-loop matching parity
  with Matchete's integration tests.
- While continuing the CDE/projection slice, remember that Symbolica has native
  tensor-index canonicalization. Use `Expression.canonize_tensors(...)`, which
  returns the canonical expression and canonical external/dummy index lists, to
  compare or project expressions whose dummy-index names need to line up.
- Matchete author feedback clarified that CDE should not remain the core port
  direction: treat existing CDE code as legacy-compatible diagnostics and
  validation support, and steer new one-loop architecture toward explicit
  Wilson-line trace handling. Also avoid treating SMEFT Warsaw as a bespoke
  core module; expose it as an optional basis on top of generic operator-basis
  registration.
- Matchete authors specifically flagged that CDE was the v0.1/accompanying
  paper technique, while current Matchete has moved to explicit Wilson lines to
  generalize trace handling beyond one loop. Course-correct future one-loop
  work around this Wilson-line representation and keep CDE bounded as legacy
  support.
- Matchete authors also flagged that building SMEFT Warsaw as a special module
  is philosophically risky for a generic matching tool. Keep the bundled SMEFT
  basis only as an optional `OperatorBasis` provider and make all matching
  machinery consume generic basis metadata.
- Latest author-feedback implementation adjustment: add Wilson-line-named
  propagator expansion diagnostics and term objects as the forward structured
  route. CDE-named APIs may remain for legacy diagnostics, but new public
  matching surfaces should not deepen CDE-first naming or SMEFT-specific core
  assumptions.
- Latest continuation requirement interpretation: selected Wilson-line trace
  expansion must be callable through `Theory.match(..., loop_order=1)` with
  explicit `OneLoopMatchOptions.wilson_line_*` controls, separate from the
  legacy `bosonic_cde_*` controls.
- Follow-up direction: public Wilson-line matching should be hybrid by default,
  replacing only the selected trace families while preserving the unselected
  interaction-power remainder. Pure selected Wilson-line result methods remain
  diagnostic helpers.
- Latest author-feedback course correction must apply to validation tooling as
  well as core matching: Matchete parity previews and gap reports should expose
  Wilson-line-named controls and prefer them for new frontier checks, while
  keeping CDE controls only for legacy diagnostic coverage.
- Generated derivative-order trace plans should also be Wilson-line-native:
  expose and use `wilson_line_trace_names`, `wilson_line_max_total_order`,
  `wilson_line_max_slot_order`, and `wilson_line_index_prefix` instead of
  relying on the legacy CDE planner for convenience.
- Target-local Matchete parity probes should also have a Wilson-line-native
  filter route: use a conservative Symbolica-pattern atom filter for selected
  Wilson-line terms before tensor reduction/evaluation, while keeping final
  coefficient extraction in the generic matching projection path and avoiding
  SMEFT-name-specific filters.
- Continue expanding the Wilson-line-native path directly. A bounded next
  step is to make vector Wilson terms use the implicit non-Abelian adjoint
  transporter and Lorentz endpoint metric instead of staying formal, while
  still leaving unsupported higher-order/combinatoric cases formal until they
  are explicitly validated.
- Wilson-line expansion should now include the current Matchete cleanup stage
  that removes symmetry-vanishing `WilsonTerm(...)` factors before lowering
  supported terms. The marker for loop-integration symmetry is represented as
  `SymmetricLorentzInds(...)`, and the implementation must use Symbolica
  pattern matches over this marker and `WilsonTerm(...)`.
- Generated Wilson-line propagator-expansion terms should carry explicit
  loop-momentum index metadata so pychete can apply the Matchete
  `SymmetricLorentzInds(...)` vanishing rule without reconstructing factor
  multiplicity from simplified products. The marker should be temporary in
  the vakint-backed path; public numerators keep `LoopMomentum(...)` factors
  for backend tensor reduction.
- The same Wilson-line helper should also apply Matchete's gather-stage
  odd-rank loop-momentum rule: generated odd-rank loop-vector numerator terms
  vanish before Wilson-term expansion instead of being expanded and only later
  killed by vakint tensor reduction.
- Generated Wilson-line numerators should also be normalized like Matchete's
  noncommutative products: flatten nested pychete `NCM(...)` operands, hoist
  only scalar commutative coefficients, and then delegate projector/gamma-word
  cleanup to idenso before scalarizing commutative chains.
- Wilson-line propagator expansion must be slot-statistics aware. Bosonic
  propagator slots use the existing bosonic covariant propagator expansion,
  while fermionic slots must use a Matchete `PropFermionExpand`-style
  `(slash(k)+M)`/`Gamma(mu) OpenCD(mu)` expansion with generated pychete
  Lorentz indices and idenso-backed gamma cleanup.
- Vector propagator slots are not just ordinary bosonic slots: Matchete's
  current `PropExpand` applies `Vector -> -PropBosonExpand[...]`. pychete must
  apply this extra sign from `FluctuationMode.field_type` metadata in the
  Wilson-line path, not from trace-name string checks.
- Current Matchete `CloseFermionLoop` behavior must be represented in the
  Wilson-line path. Closed compact Dirac words should be traced through native
  idenso via `pychete.backends.idenso.trace_pychete_closed_dirac_chains(...)`,
  while open chains with registered fermion endpoints must stay open. Do not
  implement gamma traces by hand in Python; if native idenso cannot reduce a
  projector-only closed word, leave it formal and document the backend gap.
- Raw `Theory.define_wilson_coefficient(...)` calls should not implicitly mean
  SMEFT. Basis metadata must be explicit through `OperatorBasis`,
  `define_wilson_coefficient_from_basis(...)`, or optional basis-provider
  helpers such as
  `pychete.bases.smeft_warsaw.define_smeft_wilson_coefficient(...)`.
- In response to the Matchete author feedback, the SMEFT Warsaw implementation
  now belongs under the generic optional basis-provider namespace
  `pychete.bases.smeft_warsaw`; `pychete.smeft` is a compatibility shim only.
  Do not add root-level SMEFT exports, matching-engine imports, or branches
  that depend on the SMEFT module or Warsaw names.
- Latest Matchete-author clarification reinforces that this is not merely a
  naming issue: future parity work should not deepen the legacy CDE route, and
  the implementation should not use the bundled SMEFT Warsaw provider as the
  architectural template for pychete. The engine should discover and consume
  operator bases through generic `OperatorBasis`/registry metadata, while
  Warsaw remains optional fixture/convenience data.
- Latest status check: backend-level vacuum-integral tests already cover
  single-scale vakint/internal agreement, internal two-mass topologies,
  massless-plus-massive topologies, scaleless massless topologies, and
  Matchete-style loop-function simplification cases. These are not yet the
  same as reproducing a full one-loop Matchete SMEFT integration model.
- Latest Wilson-line regression added for the conjugate non-Abelian
  `WilsonTerm(...)` lowering path, locking the generator orientation for barred
  fields through theory-owned Symbolica group/representation metadata.
- When running tests or exploratory workloads that can exceed machine memory,
  use the 30 GiB watchdog wrapper rather than invoking them directly. The
  wrapper now polls `stop.order` in the current working directory by default;
  remove stale `stop.order` before launching long work, and touch/create
  `stop.order` to terminate the wrapped process group without needing
  sandboxed process-management permissions.
- Do not let future work stall on sandbox permission prompts for process
  management. For long-running tests/probes, run through the watchdog and use
  `stop.order` as the user/agent control file to terminate the wrapped process
  group or communicate that the workload should stop.
- Do not let future work stall on sandbox approval prompts for blocked shell
  commands either. The user explicitly reiterated that this must be treated as
  the first shell-operating rule: never leave the thread waiting for sandbox
  approval when `listener.py` can dispatch the command. The user-started
  `listener.py` route is mandatory for known sandbox-sensitive repository
  commands, especially `.git` writes such as commits, rebases, merges, lock
  cleanup, or similar repository-maintenance commands. Queue exactly one
  command in `run.order` and read `run.output`. For ordinary direct commands,
  if one unexpectedly fails with `Operation not permitted`, a sandbox write
  restriction, or the known read-only `.git` metadata failure, immediately
  retry through the listener rather than waiting for an approval prompt.
- Current Wilson-line direction: order-four `hScalar` Wilson-line generation
  now keeps field-strength-bearing Singlet `cHW` source terms even with
  pychete colour simplification enabled. Exact public projected `cHW` parity
  remains a later projection/evaluation slice.
- Latest status clarification: the current active Matchete integration target
  is `Singlet_Scalar_Extension`, specifically the SMEFT `cHW` one-loop matching
  condition. This is not yet a full passing Matchete integration test. The
  latest backend work normalizes generated Wilson-line/CDE Lorentz index
  aliases to a pychete namespace before idenso field-strength metric
  contraction, making the selected `hScalar` Wilson-line contribution project
  nonzero. The projected partial contribution is still not the Matchete
  reference `hbar*A^2*gL^2/(12*M^4)`, so the next work is mixed scalar trace
  source coverage, finite/pole convention cleanup, and target-local
  performance for those mixed traces.
- Latest mixed-trace performance update: selected `hScalar-lScalar` Wilson-line
  probes for Singlet `cHW` are now bounded. Term generation skips trace entries
  that cannot satisfy the projected field-strength requirements, keeping only
  five order-four entries and 40 generated terms. Internal Laurent extraction
  now uses Symbolica series coefficients before falling back to full
  coefficient lists, and the hybrid internal result reuses component pole and
  finite parts instead of recomputing them from the aggregate. The real
  fixture-level `hScalar-lScalar`/`cHW` gap-report probe returns under the
  30 GiB watchdog in about 153 seconds with one candidate and one reference
  condition, still different; the selected mixed-trace finite projection alone
  is currently zero.
- Latest structural fix in progress: Wilson-line and supertrace matrix paths
  now insert the free-propagator field-space pairing between interaction
  entries. Complex scalar and fermion traces therefore close through conjugate
  modes instead of reusing the same basis mode index. This fixes the immediate
  Singlet mixed-scalar source problem where `hScalar-lScalar` zero-order terms
  were `H H`/`Bar(H) Bar(H)` rather than mixed `H_i Bar(H_j)`. No full Matchete
  one-loop integration test is reproduced yet; the first milestone remains
  Singlet `cHW`, with order-four Wilson-line finite/pole conventions,
  basis/on-shell/IBP reduction, and idenso/spenso group simplification still
  ahead.
- Follow-up projection fix: target-local tensor-canonized exact coefficient
  extraction now runs before the large-source generic projection guard, so
  focused complex-Higgs CDE projections such as `cHD` and heavy-solution `cH`
  remain nonzero without enabling expensive collect/factor fallbacks. Numeric
  validation probes now build Symbolica evaluator parameters from the same
  tensor-canonized expressions that are actually compared, avoiding missing
  function-atom parameters after dummy-index canonicalization. Full
  `tests/integration/matching/test_fluctuation_operator.py` now passes locally
  under the 30 GiB watchdog.
- Latest generated-numerator cleanup: commutator-enabled Singlet `cHW`
  Wilson-line source generation now keeps 25 filtered field-strength terms for
  the selected order-four `hScalar`/`hScalar-hScalar` plan, and generated
  `CD(..., 0)` wrappers are removed with a Symbolica replacement helper before
  idenso/vakint work. This is a performance and source-cleanliness improvement,
  not yet full `cHW` parity; the remaining blockers are still backend finite
  extraction/projection through the full hybrid result, generic on-shell/IBP
  reductions, and group/CG simplification.
- Latest idenso boundary cleanup: native-color wrapper decoding and
  field-strength group-bilinear simplification are now centralized in the
  idenso backend and applied by both public `Theory.match(...)` and direct
  `ValidationFixture.one_loop_preview(...)` when pychete color simplification
  is requested. This aligns direct fixture probes with the public match path
  for SU(2) and mixed SU(2)-U(1) gauge field-strength structures.
- Latest Wilson-line target-filter update: the pre-generation filter now uses
  theory-owned Symbolica field/gauge metadata to skip Wilson-line plan entries
  that cannot possibly generate a requested field-strength label or required
  field content. This keeps impossible target-local probes from entering
  Wilson-term lowering, commutator expansion, tensor reduction, or integral
  evaluation. It is a scaling improvement for the Singlet `cHW` frontier and
  broader Wilson-line fixture probes, not a full `cHW` parity result yet.
- Latest fixture-report diagnostic update: gap reports now include JSON-safe
  snapshots of candidate/reference `MatchingResult.metadata`, so Wilson-line
  plan counts, generated term counts, target-filter flags, backend stage, and
  normalization choices are visible directly in report objects and
  `to_json_obj()` output. This helps triage Singlet `cHW` and other
  Wilson-line fixture probes without rerunning separate ad hoc diagnostics.
- Latest Wilson-line accounting update: Wilson-line matching metadata now
  breaks generated term counts down by expansion-plan entry, by original trace
  name, and by plan-entry/path index, preserving empty plan entries and listing
  nonzero plan labels. The same data appears in validation gap-report metadata
  snapshots, so future Singlet `cHW` mismatch probes can identify exactly
  which Wilson-line trace/order/path family survived target filtering.
  The same slice also makes the native-vakint Wilson-line minimal-subtraction
  path reuse one grouped expansion for evaluated sums, named integrals, kernel
  maps, and metadata instead of regenerating the same Wilson-line terms
  repeatedly.
- Latest sandbox-policy update: `AGENTS.md` and both live one-shot notes now
  explicitly ban `sandbox_permissions: "require_escalated"` for this
  repository. Direct sandboxed commands may still run when appropriate, but
  `.git` metadata writes and direct `Operation not permitted` failures must go
  through the user-started `listener.py` route instead of tool approval
  escalation.
- Latest Singlet `cHW` frontier measurement: the Wilson-line route with
  target filtering and internal minimal subtraction still differs from the
  Matchete `cHW` reference. The completed diagnostic found 65 surviving
  target-filtered Wilson-line terms across 35 plan entries, with only 11
  nonzero order-four entries: `hScalar` contributes 5 terms,
  `hScalar-hScalar` contributes 20 terms, and `hScalar-lScalar` contributes
  40 terms. The next projection work should use smaller entrywise finite-part
  sources rather than one monolithic hybrid expression.
- Latest Wilson-line backend update: internal Wilson-line results now expose
  entry-level evaluated, pole, and finite sums in `MatchingResult.supertraces`
  using names such as
  `interaction_wilson_line_internal_integral_finite_part[<entry>]`. Aggregate
  results are unchanged. This gives the next `cHW` probe a smaller source
  boundary for locating the mismatching trace/order family.
- Latest projection-performance update: powered field-strength matching
  targets with denominator factors, including Singlet `cHW`, now normalize
  those factors before the generic coefficient path and try the bounded
  indexed-field-strength wildcard projection before broad collect/factor
  fallbacks. The 11 nonzero order-four Wilson-line entrywise finite sources
  can now be projected without the previous monolithic stall; all currently
  project to zero. This moves the active `cHW` gap away from coefficient
  extraction and toward Wilson-line source generation/simplification, especially
  Lorentz, field-strength, group, and basis/on-shell reduction.
- Latest Wilson-line propagation/backend update: explicit Wilson-line paths
  now insert field-space propagation `Delta(...)` factors between adjacent
  interaction entries, the idenso bridge contracts those pychete deltas into
  registered `CG(...)` tensors before group simplification, and the vakint
  tensor-reduction adapter now uses an evaluation-free engine so PySecDec is
  not required for tensor reduction. A focused projection regression now
  handles Wilson-line-shaped `Metric * Delta * CG * CG * F * F * H^\dagger H`
  sources. The actual Singlet `cHW` entrywise probe is still not green: after
  the new cleanup, mixed heavy-light sources visibly contain target-shaped
  `A^2*gL^2*H^\dagger H*W^2/M^4` terms and isolated terms project correctly,
  but full entry sums still cancel to zero for the mixed entries. The only
  projected entrywise total remains the spurious
  `-hbar*gL^4*kappa/(12*M^2)` pure-heavy contribution, so no full Matchete
  one-loop integration test is reproduced yet.
- Latest Wilson-line coupling-convention update: Matchete's current
  Wilson-line route lowers generated Wilson-term field strengths without
  explicit gauge-coupling factors; operator/Warsaw normalizations carry those
  factors separately. pychete now supports this through
  `Theory.expand_covariant_derivative_commutators(..., include_gauge_coupling=False)`
  for generated CDE/Wilson-line numerator postprocessing while preserving the
  public coupled default for ordinary covariant-derivative expansion. This
  fixes a convention mismatch but does not yet make the first full Matchete
  one-loop integration target pass: `Singlet_Scalar_Extension` `cHW` remains
  the active milestone, with selected mixed `hScalar-lScalar` order-four
  entries still projecting to zero.
- Latest Wilson-line ordering update: explicit Wilson-line traces now apply
  open covariant derivatives only to factors on their right, matching
  Matchete's ordered chain ending in the closing `WilsonTerm(...)`. The legacy
  cyclic wrapping behavior remains available for CDE-style closed chains but is
  no longer used by `WilsonLineTracePath.propagator_expansion_terms(...)`.
  This removes non-Matchete cyclic source terms from the Singlet frontier:
  selected order-four generation now has no surviving pure `hScalar` entry,
  only 8 `hScalar-hScalar` terms and 16 `hScalar-lScalar` terms. The surviving
  order-four finite projections still give `cHW = 0`, so the first full
  Matchete one-loop integration target remains incomplete.
- Latest Wilson-line symmetry update: pychete now matches Matchete's
  rank-agnostic `RemoveSymmetryVanishingWilsonTerms` subset rule, so Wilson
  terms vanish whenever their derivative-index list contains the full
  symmetric loop-momentum index group, not only in the two-derivative case.
  The focused symmetry regression passes. Re-measuring the Singlet `cHW`
  frontier after this correction shows that the earlier field-strength-bearing
  selected Wilson-line terms were artifacts of under-removing symmetry-killed
  Wilson terms. With Higgs-derivative commutator emission/lowering enabled,
  generated `hScalar-lScalar` terms still do not contain an exact power-aware
  `H^2 W^2` source with no extra dynamical labels, while the Matchete fixture
  projects the full `cHW = hbar*A^2*gL^2/(12*M^4)` contribution entirely from
  `hScalar-lScalar`. The first full one-loop matching integration test is
  still not reproduced; the active blocker is now specifically
  Matchete-equivalent `hScalar-lScalar` Wilson-line source generation and
  background-heavy-scalar elimination before target-local projection.
- Latest Wilson-line `NCM` linearity update: generated Wilson-line chains now
  distribute additive operands inside `NCM(...)` before and after open
  covariant derivatives act. This keeps additive heavy-light entries such as
  `A*H + kappa*phi*H` as separate ordered chains before symmetry pruning and
  target filtering, matching Matchete's termwise noncommutative processing
  more closely. Focused noncommutative and Wilson-line tests pass. The Singlet
  `cHW` milestone is still not green: diagnostics now show the pure `A^2`
  `hScalar-lScalar` terms reach the pre-commutator stage as loop-momentum
  tensors multiplying four covariant derivatives on a charged Higgs, but the
  current commutator lowering can produce only one field strength. The next
  required stage is a Matchete-style loop-symmetric multi-commutator lowering
  tied to tensor-reduced/symmetric loop-momentum structures, not another
  projection or heavy-scalar-substitution fix.
- Latest post-tensor Wilson-line cleanup update: pychete now contracts
  vakint-generated `Metric`/`Delta` tensors into derivative slots on
  `Field(...)` and `FieldStrength(...)` atoms before internal scalar integral
  evaluation, and it restores generated Wilson-line/CDE Lorentz labels to
  theory-owned index symbols before calling `Theory` derivative routines.
  Focused backend and Wilson-line tests pass, and the guarded Singlet `cHW`
  diagnostic now runs through this stage without generated-index validation
  errors. The diagnostic still projects `cHW = 0`, so the first full Matchete
  one-loop integration test remains unreproduced; the blocker is now the
  generic loop-symmetric double-commutator/basis-identity reduction that turns
  the pure `A^2` four-derivative Higgs bilinear into `H^\dagger H W^2`.
- Latest Wilson-line projection update: vakint-decoded backend deltas and
  generated covariant-commutator indices are now normalized into pychete/theory
  objects before idenso group simplification, and the SU(2) field-strength
  generator projectors are guarded by native Symbolica prefilters so the
  selected Wilson-line path remains responsive. The Singlet `cHW` diagnostic
  now projects a nonzero contribution from the expected
  `hScalar-lScalar#wilson14_o4_0` order-four entry. It is still not Matchete
  equal: after the Matchete evaluated-hbar normalization and setting
  `mu_r^2=M^2`, pychete currently gives
  `7/24*hbar*A^2*gL^2/M^4` while the reference expects
  `1/12*hbar*A^2*gL^2/M^4`. The first full Matchete one-loop integration
  target is therefore closer, but still incomplete; the active blocker is now
  the order-four Wilson-line/tensor-integral coefficient and finite-part
  convention.
- Current first-milestone clarification: no full Matchete one-loop matching
  integration test is green yet. A broader selected Wilson-line plan over
  `hScalar`, `hScalar-hScalar`, and `hScalar-lScalar` still localizes the only
  nonzero entrywise `cHW` contribution to the expected `hScalar-lScalar`
  order-four entry, with the same `7/24` finite coefficient after log
  cancellation. The aggregate projection can still return zero on the larger
  combined source, which is a separate projection-scaling guard issue. Reading
  current Matchete shows `ContractMetric` only substitutes metric-contracted
  indices; the derivative commutator identities enter later through
  normal-form / basis simplification. pychete is currently exposing the
  `H^\dagger H W^2` coefficient too early in the Wilson-line backend, so the
  next physics slice should implement the generic Matchete-style
  loop-symmetric commutator and basis-normal-form reduction rather than a
  `cHW`-specific coefficient patch.
- Latest user request in this slice: continue as planned, but quickly summarize
  how far pychete has gotten toward the first Matchete one-loop integration
  test. The answer remains that no full test is green; the closest target is
  Singlet `cHW`, with the expected `hScalar-lScalar` Wilson-line entry now
  projecting nonzero but still giving `7/24` instead of Matchete's `1/12`
  after the evaluated-hbar normalization and log cancellation.
- Follow-up implementation progress after that summary: added a generic
  Symbolica-pattern scalar derivative-bilinear normal-form helper and wired it
  into the internal Wilson-line route behind an explicit opt-in matching
  option. This advances the missing Matchete-style Wilson-line normal-form
  layer but does not yet make the first full Matchete one-loop integration test
  pass.
- Latest follow-up progress: extended that opt-in helper to the Wilson-line
  VAKINT and VAKINT-minimal-subtraction routes and to validation fixture
  previews/gap reports. This makes the same generic normal-form switch usable
  in the Singlet `cHW` frontier probes that go through VAKINT/evaluated-hbar
  paths, but it is not yet a full `cHW` parity result.
- Latest validation-facing option parity update: fixture previews and gap
  reports now also forward
  `wilson_line_covariant_derivative_commutator_mode`, including the bounded
  `all_distinct` mode used by the Singlet Wilson-line diagnostics. A bounded
  selected `hScalar-lScalar` internal probe with that mode and scalar-bilinear
  exposure active still projects zero for `cHW`, confirming the next blocker is
  the remaining heavy-scalar on-shell/basis/source reduction work rather than
  missing option plumbing.
- Direct validation previews now also support and gap-report-forward the
  public matcher's heavy-scalar solution substitution controls. This makes
  future bounded Singlet Wilson-line diagnostics able to apply the same
  existing heavy-scalar on-shell reduction machinery before projection, but it
  does not by itself complete the first Matchete one-loop integration target.
- Projection progress after that: target-local exact and wildcard-index
  coefficient extraction now normalize inverse coupling powers in registered
  Wilson operators before delegating to Symbolica. The selected Singlet
  `hScalar-lScalar -> cHW` diagnostic now projects a nonzero
  `-1/8*hbar*A^2*gL^2/M^4` instead of zero after heavy-scalar substitution.
  The Matchete fixture still expects `1/12*hbar*A^2*gL^2/M^4`, so the first
  full Matchete one-loop integration target remains incomplete; the next
  blocker is the Wilson-line coefficient/sign/finite-part normal-form layer.
- Latest user-facing status request: continue as planned, but give a quick
  summary of how far pychete is from reproducing at least one Matchete
  one-loop integration test. Current answer: no full Matchete one-loop test is
  green; the closest target is still Singlet `hScalar-lScalar -> cHW`, where
  all broad plumbing is connected but the order-four Wilson-line coefficient
  remains mismatched.
- Follow-up implementation progress in response: added an opt-in
  Matchete-order Wilson-line tensor-reduction path. It stores formal
  pre-Wilson numerators, lets vakint reduce loop momenta before
  `WilsonTerm(...)` expansion, decodes `vakint::WilsonTerm(...)`, contracts
  emitted metrics into formal Wilson derivative slots with Symbolica
  replacement rules, and exposes the option through `OneLoopMatchOptions` and
  validation fixture helpers. Focused tests and mypy pass. A full selected
  Singlet `cHW` fixture probe with the new flag was still too slow for a quick
  check and was stopped through the watchdog stop file; next diagnostics should
  split the surviving `hScalar-lScalar#wilson14_o4_0` terms.
- Follow-up diagnostic result: the pre-Wilson slowdown was a bug in
  `contract_wilson_term_derivative_metrics(...)`, where `repeat=True` could
  rematch an unchanged noncontracting `Metric * WilsonTerm` product forever.
  The helper now uses bounded convergence and has a regression test. With that
  fixed, the selected Singlet `cHW` fixture-status probe finishes under the
  30 GiB watchdog. It is still not Matchete-equal: the pre-Wilson path halves
  the old selected contribution by killing the path-0 `(3, 1)` term, but the
  external `cHW` condition remains different from the Matchete reference.
- Latest user instruction for this milestone: dissect the Singlet
  `hScalar-lScalar -> cHW` disagreement with frequent focused Matchete
  WolframScript debug dumps rather than only pychete-side probes. The first
  dump shows raw Matchete `EvaluateSTr` keeps both `Bar[H] ... H`
  orientations derivative-only, with no explicit `W` field strengths until the
  saved validation-stage `ContractCGs // MatchReduce // GreensSimplify`
  result. This led to a generic Wilson-line filter correction: field-strength
  target filters must keep derivative-only charged-field terms when they can
  generate the requested field strengths later.
- Follow-up remeasurement: that filter correction is policy-correct but does
  not change the current Singlet `hScalar-lScalar#wilson14_o4_0` term count
  (`10/10` filtered/unfiltered). The remaining mismatch is therefore in
  pychete's Wilson-line normal-form/reduction representation rather than in
  the target-filter count for this entry.
- Follow-up in the same direction: ran additional Matchete WolframScript
  prop-order dumps for `0`, `2`, and `4`, and separate minimal
  `GreensSimplify` probes for scalar derivative bilinears. These probes fixed
  the reference weights for the local `H^\dagger H F_W^2` component and drove
  a generic pychete scalar Green-bilinear correction with focused pytest
  coverage. The selected Singlet trace still disagrees afterward, now
  localized more tightly to the pre-Wilson tensor-reduction/WilsonTerm
  metric-contraction representation.
- Latest debugging instruction: for the active Singlet
  `hScalar-lScalar -> cHW` milestone, keep dumping as many useful
  Matchete-side intermediate results as possible with focused WolframScripts
  and compare them against pychete stages. The goal is to identify the first
  representation/source/coefficient stage where Matchete and pychete diverge,
  instead of only comparing the final projected matching condition.
- Follow-up implementation response: added a paired pychete-side development
  dump script, `scripts/debug_pychete_singlet_wilson_trace.py`, and generated
  `assets/validation/pychete/debug/singlet_hScalar_lScalar_cHW.pychete.debug.json`.
  It mirrors the current Matchete debug workflow for the selected
  `hScalar-lScalar -> cHW` frontier and records termwise post-Wilson and
  pre-Wilson tensor-reduction projections. The current dump confirms the
  nonempty selected pychete entry is only `hScalar-lScalar#wilson14_o4_0`;
  post-Wilson projection comes from term 4/path 0, pre-Wilson projection comes
  from term 9/path 2, and both give the same finite selected total, still
  mismatched against Matchete's saved `+1/12*hbar*A^2*gL^2/M^4`.
- Latest user instruction: explicitly confirm and continue the policy of
  running focused debug WolframScripts and dissecting as many Matchete
  intermediate results as practical for the active Singlet
  `hScalar-lScalar -> cHW` disagreement. Response and implementation status:
  yes, the active workflow is paired Matchete/pychete debug dumping, not just
  final Wilson-coefficient comparison. The Matchete dump now records
  derivative-word and `SymGammaFactor` histograms at order four, the pychete
  dump records matching derivative histograms and native Symbolica coefficient
  slices, and the current comparison narrows the remaining mismatch to
  Wilson-line derivative/tensor/Green-normal-form weighting rather than broad
  trace selection or final target projection.
- Follow-up diagnostic progress: the Matchete and pychete debug dumps now also
  record representative terms per derivative-word signature. pychete's dump
  additionally records pipeline snapshots through raw vakint input, decoded
  tensor reduction, formal WilsonTerm metric contraction, WilsonTerm
  expansion, and postprocessing with/without scalar-bilinear exposure. The
  comparison now shows Matchete has a compact derivative-only
  `aabb/abab/abba` structure before `GreensSimplify`, while pychete still
  carries broader generated-index derivative classes and field-strength-heavy
  postprocessed terms. The next correction should therefore target generic
  Wilson-line tensor/index normal form and metric contraction into derivative
  slots, not a final `cHW` coefficient patch.
- Current confirmation/debug response: yes, the active Singlet
  `hScalar-lScalar -> cHW` workflow is explicitly paired Matchete/pychete
  dissection with focused WolframScript dumps. The refreshed Matchete JSON now
  includes derivative-signature samples and `SymGammaFactor` histograms, and a
  new `scripts/compare_singlet_wilson_debug.py` helper reads the Matchete and
  pychete artifacts side by side. The latest comparison localizes the first
  remaining mismatch to Matchete's cleanup between `loop_integrated`,
  `post_index_group_cleanup`, and `eps_expanded_relabelled`: Matchete removes
  lower-derivative families and balances `aabb/abab/abba`, while pychete's
  corresponding rows still carry lower-derivative/two-field signatures. A
  scratch native Symbolica tensor-canonicalization pass helps counts but does
  not change the selected `cHW` value, so the next implementation target is a
  generic post-index/group and Green-normal-form reduction, not a final
  coefficient patch.
- Latest continuation: confirmed the workflow explicitly and ran additional
  Matchete WolframScript dumps for prop orders `0`, `2`, and `6` under the
  30 GiB watchdog, alongside the existing order-4 dump. The key correction is
  that the isolated order-4 pychete row should not be compared directly to the
  final Matchete `+1/12 cHW` condition. Matchete's final condition comes from
  the full `hScalar-lScalar` trace after validation/on-shell simplification:
  order `0` gives threshold `H^\dagger H` terms, order `2` gives
  two-derivative Higgs bilinears, order `4` gives four-derivative Higgs
  bilinears, and order `6` is empty. The next milestone is therefore full
  selected Wilson-line trace aggregation plus Green/on-shell projection, with
  the prop-order dumps used as intermediate checkpoints.
- Follow-up pychete aggregate checkpoint: updated the pychete Singlet debug
  script so artifacts record plan entries, target-filter status, nonempty
  entries, and per-entry/per-order totals and `cHW` projections. Regenerated
  the filtered artifact and added an unfiltered artifact. The unfiltered
  pychete selected trace has nonempty order `0`, order `2`, and order `4`
  entries, but only order `4` contributes to the current `cHW` projection.
  This keeps the next fix focused on the order-four Wilson-line
  Green/on-shell normal form and coefficient weighting while preserving
  lower-order checkpoints.
- Latest user instruction: when a precise mismatch is identified, carefully
  review the corresponding Matchete algorithms before modifying pychete, so
  changes are based on an understood algorithmic difference rather than only
  on final coefficient disagreement. Current response: the active
  `hScalar-lScalar -> cHW` loop now explicitly audits Matchete
  `DeterminePowerInsertions`, `EvaluateSTr`, `ActWithOpenCDs`,
  `RemoveSymmetryVanishingWilsonTerms`, `LoopMoms`/
  `EvaluateSymmetricLorentzInds`, and `WilsonExpand` against the pychete
  Wilson-line path. A new focused regression captures the first fixed
  source-level mismatch: target-local pre-generation filtering now reproduces
  Matchete's order-four pre-action selected insertion checkpoint with slot
  counts `[0,4]=10`, `[1,3]=6`, `[2,2]=8`, `[3,1]=6`, `[4,0]=10`, summing to
  40 candidate terms and with no heavy `phi` branch leaking into the
  `cHW` candidate. The updated debug artifacts also distinguish the
  Matchete-comparable pre-action prefilter checkpoint from the later
  post-action/post-Wilson filtering checkpoint.
- Continuation of that instruction: when a newly spotted mismatch seems
  precise, first verify that the compared objects are the same Matchete
  algorithmic stage and the same prop-order/slot aggregate. A fresh audit
  showed that comparing pychete's isolated `[4,0]` Wilson-line row directly
  to Matchete's full prop-order-four `EvaluateSTr` stage is invalid; the next
  fixes must compare full compatible aggregates or add finer Matchete dumps
  before changing pychete.
- Latest progress following that policy: added a finer Matchete prop-order
  four slot split to `debug_singlet_wilson_trace.wls` and used it to compare
  pychete stage-by-stage. After verifying the helper emitted the same
  Matchete package-scope heads as `GenericPropagatorExpansion`, pychete now
  matches Matchete through `ActWithOpenCDs` and `GatherLoopMomenta`.
- Fixed two precise Matchete algorithm mismatches in pychete:
  `RemoveSymmetryVanishingWilsonTerms` now uses Matchete's containment
  direction (`wilsonInds` contained in `symInds`) and preserves empty
  Wilson-term derivative lists, and `EvaluateSymmetricLorentzInds` now
  contracts top-level metrics before distributing metric-pairing sums. With
  these fixes, the selected Singlet `hScalar-lScalar -> cHW` order-four
  checkpoint matches Matchete through
  `removed_symmetry_vanishing_wilson_terms` and
  `evaluated_symmetric_lorentz_indices` (49 terms per orientation with
  matching derivative-word histograms).
- Latest audit under the instruction to review Matchete before patching:
  after adding generic pychete delta contraction, the selected
  `hScalar-lScalar -> cHW` projection is a clean sign mismatch rather than a
  residual-index mismatch. Matchete's `GAction`/`CommuteCDs`,
  `WilsonExpand`/`DevPreFact`/`ExpandGenFSs`, `SingleScaleIntegral`, and
  `GreensSimplify`/`IdentitiesCDCommutation` code were inspected, and focused
  WolframScript probes confirm that Matchete's one-sided four-derivative
  Higgs Green weights are `aabb -> 0`, `abab -> +1/8`, and
  `abba`/`baab -> +1/4`, matching pychete's local tests. Disabling pychete's
  one-sided four-derivative exposure alone restores the log-bearing unexposed
  projection, while the mixed/first-derivative/two-derivative exposure
  families do not affect this selected cHW probe. The next fix should compare
  and correct the Wilson-line `contracted_metric`, `wilson_expanded`,
  `loop_integrated`, and post-index/group normal form that feeds the
  one-sided Green reduction, not flip the verified Green weights or add a
  cHW-specific coefficient patch.
- Follow-up under the same policy: the precise sign mismatch was then
  re-audited against Matchete's `SuperTrace.m` and `LoopIntegration.m`
  conventions before modifying pychete. Matchete's selected X-term insertions
  are positive, the scalar/vector power-type trace prefactor is
  `-I hbar/2`, and the loop-integrated `Prop[M] Prop[0]^3` topology supplies
  the expected `+I LF[{M},{1,3}]` stage before LF evaluation. pychete's
  Wilson-line trace prefactor remains real `-1/2`, and the internal evaluated
  integral already contains `+I/(16*pi^2)`, so the global
  `MATCHETE_EVALUATED_HBAR` bridge was corrected from the old negative sign
  to `+16*pi^2*i*hbar`. A focused regression now reproduces the selected
  order-four Singlet `hScalar-lScalar -> cHW` coefficient
  `hbar*A^2*gL^2/(12*M^4)`, and the normalization plus cHW tests pass under
  the 30 GiB watchdog. The legacy bosonic-CDE heavy-scalar `cH` expectation
  was also updated by the same global convention sign because it uses the same
  evaluated-HBAR bridge. A broader focused gate covering idenso delta
  contraction, numeric projection probes, loop integration, Wilson-line
  tensor reduction, normalization, selected `cHW`, and the legacy CDE
  expectation now passes: 110 tests under the 30 GiB watchdog.
- Latest validation promotion: the selected Singlet `hScalar-lScalar -> cHW`
  checkpoint is now exercised through
  `ValidationFixture.one_loop_preview_gap_report(...)` against the committed
  Matchete-derived matching fixture, not only through a lower-level unit path.
  With the current Wilson-line controls, the report accepts the registered
  `cHW` Wilson condition and the saved Matchete coefficient
  `hbar*A^2*gL^2/(12*M^4)`. The pychete debug artifact now includes a
  `runtime_internal_evaluated` section that calls the same runtime helper as
  the fixture report, and the comparison helper prints that accepted path
  separately from older manual pipeline diagnostics. Added the slow regression
  `test_singlet_wilson_line_gap_report_accepts_selected_chw_against_matchete_fixture`,
  which passes under the 30 GiB watchdog. The focused lower-level `cHW`
  regression, validation Wilson-line preview smoke, and static typing pytest
  gate also pass for this slice. This validation remains a stage-local
  success, not yet full-model one-loop parity.
- Latest continuation under the same mismatch-review policy: the selected
  Singlet `hScalar-lScalar` fixture route now also accepts `cHB` and `cHWB`
  against the committed Matchete fixture, using the same Wilson-line controls
  as the accepted `cHW` checkpoint. The first remaining precise mismatch is
  the derivative/Higgs family (`cHD`, `cHBox`, `cH`). Matchete's
  `SuperTrace.m` applies `ReplaceHeavyEOM` after matching-mode supertrace
  evaluation, while pychete's target filter was running before heavy-scalar
  EOM substitution. pychete now conservatively relaxes Wilson-line atom
  requirements when `substitute_heavy_scalar_solutions=True`, keeping pre-EOM
  terms such as `H^2 phi` that can become four-Higgs operators after the
  heavy singlet solution is applied.
- Projection-cost follow-up: selected `hScalar-lScalar -> cHD` no longer
  stalls in target-local projection. pychete now prunes derivative-slot
  incompatible branches before native tensor canonicalization, comparing
  derivative-slot shapes rather than exact dummy-index names at that
  pre-canonicalization stage. The selected scalar-only `cHD` fixture report
  now returns boundedly and still projects to zero, while the Matchete fixture
  coefficient is nonzero; the remaining issue is therefore source generation
  or downstream `ReplaceHeavyEOM`/`GreensSimplify`/basis reduction, not the
  projection hang. Initial light-vector trace diagnostics found zero generated
  `cHD` terms for the simple selected families tested, and the order-five
  two-vector diagnostics currently expose a separate vakint/FORM tensor
  reduction crash to investigate.
- Latest instruction: whenever a precise mismatch is identified, carefully
  review the corresponding Matchete or backend algorithm before changing
  pychete, and use that comparison to locate the real semantic difference.
  Applied immediately to the two-vector `cHD` diagnostic crash: the selected
  Wilson-line terms were zero, while the hybrid interaction-power remainder
  crashed in native vakint tensor reduction. Inspecting vakint's tensor
  reducer and generated FORM file showed that native user-symbol escaping
  rewrote its internal `vec(...)` helper to `v[e]c(...)` when the model
  contained a short field symbol `e`.
- Latest cHD mismatch review: Matchete's saved trace pipeline was re-read
  before patching. `SaveValidationResults` applies
  `ContractCGs // MatchReduce // GreensSimplify`; `GreensSimplify` builds
  operator classes, generates IBP and covariant-derivative commutation
  identities, row-reduces them, and chooses preferred Green-basis
  representatives; `EOMSimplify` then performs matter/vector field
  redefinitions with vector EOM normal form
  `FieldStrength[V,{nu,mu},inds,{nu}]`. pychete now has a registered-Wilson
  Abelian vector-EOM projection alias and Wilson-line filtering includes
  projection aliases. Focused checks show the selected
  `hScalar-lScalar -> cHD` run keeps the same 16 terms with or without target
  filtering, so the remaining mismatch is not premature filtering or direct
  coefficient extraction. The next slice should implement a generic bounded
  scalar Green-basis reduction, not another Warsaw-specific `cHD` patch.
- Latest continuation instruction: continue the one-shot implementation, and
  whenever a precise mismatch is identified, carefully review the relevant
  Matchete algorithms before changing pychete. Applied to the scalar
  derivative `cHD` frontier by rechecking Matchete `IdentitiesIBP`,
  `IdentitiesCDCommutation`, `CommuteCDs`, `OperatorToNormalForm`, and
  `EoMStandardForm` before adding a bounded scalar-Laplacian IBP helper.
- Follow-up Green-basis projection slice: pychete now adds registered-Wilson
  target-local scalar first-derivative IBP aliases, so a target factor
  `A * D_mu(phi)` can also project from its full total-derivative-equivalent
  source `-D_mu(A) * phi`. This remains generic and Symbolica-pattern-driven;
  the selected Singlet order-zero `cHD` smoke still projects zero, so the next
  mismatch remains the higher-derivative selected-source normal form.
- Latest continuation instruction: continue as planned, and for every precise
  mismatch carefully review the corresponding Matchete algorithms before
  patching pychete. Applied to the scalar derivative frontier by comparing
  pychete's target-local IBP projection aliases against Matchete
  `IdentitiesIBP`: Matchete generates an identity for the outermost derivative
  on every differentiated scalar field, while pychete only covered
  first-derivative slots and explicit scalar-box bilinears.
- Latest Matchete comparison for the covariant-derivative commutator frontier:
  `IdentitiesCDCommutation` generates a separate identity for every adjacent
  distinct derivative pair on each differentiated field/field-strength atom,
  while pychete's `emit_covariant_derivative_commutators(...,
  mode="all_distinct")` is an equality-preserving rewrite of only one eligible
  pair per atom. Added a separate identity-source primitive so future
  Green-basis row reduction can use the correct Matchete-style input without
  changing Wilson-line numerator rewrite semantics.
- Latest Green-basis row-reduction infrastructure slice: added an explicit
  basis normal-form helper that encodes composite operator monomials as
  temporary Symbolica variables and delegates the linear solve to
  `Expression.solve_linear_system(...)`. This is now wired through
  `Theory.covariant_derivative_commutator_normal_form(...)` for local
  `CommuteCDs` identities, but the full automatic Matchete operator-class
  discovery/scoring layer is still future work.
- Latest continuation instruction: continue as planned, and whenever a precise
  mismatch is identified, carefully review the corresponding relevant Matchete
  algorithms before patching pychete. Applied to the current Green-basis slice
  by rereading `Simplifications.m` around `ConstructOperatorIdentities`,
  `IdentitiesIBP`, `IdentitiesCDCommutation`, `IBPSimplify`, and
  `GreensSimplify` before adding a local automatic basis-construction helper.
  pychete now has bounded local basis discovery for expression-plus-identity
  neighborhoods, while preferred Green-basis representatives remain explicit
  until Matchete's operator-class scoring is ported generically.
- Follow-up scalar Green-basis slice: pychete now has a source-side scalar
  `IdentitiesIBP` helper and a combined bounded scalar
  IBP/commutator normal-form helper. The existing opt-in Wilson-line scalar
  derivative postprocess now uses this broader source-side Green-basis pass,
  lowers any generated formal commutators, and then applies the existing
  field-strength exposure helper. Focused tests pass, and the selected Singlet
  order-zero `hScalar-lScalar -> cHD` smoke still preserves two pre-EOM terms
  but projects no matching condition, so the first `cHD` milestone remains
  open at the larger higher-derivative operator-class/scoring layer.
- Latest scalar Green-basis scoring slice: re-read Matchete `OpScore` and the
  `ConstructOperatorIdentities` row-reduction ordering before changing
  pychete. pychete now gives the scalar normal-form solver an automatic local
  preferred-representative order when no explicit preference is supplied:
  field-strength-like representatives are preferred, explicit `CD(...)`
  wrappers and repeated scalar derivative slots are penalized, and
  derivative-balanced scalar factors are preferred over one-sided
  higher-derivative representatives. The selected Singlet order-zero `cHD`
  smoke remains unchanged, so the milestone still requires the larger
  higher-derivative operator-class policy rather than only this local score.
- Latest mismatch-debugging instruction: whenever a precise Matchete-parity
  mismatch is identified, first review the corresponding Matchete Mathematica
  algorithm and compare it directly with the pychete implementation before
  patching. Use intermediate dumps/probes to find the first semantic
  difference instead of inferring a fix from only the final Wilson coefficient.
- Latest diagnostic slice: made the Singlet Wilson-line debug scripts
  target-aware so `cHD` probes no longer reuse `cHW` labels or target-filter
  requirements. The Matchete dump can now emit the saved reference condition
  for a requested target, and the pychete dump can apply the public
  heavy-scalar substitution plus scalar Green normal-form aggregate summaries.
  Order-zero `hScalar-lScalar -> cHD` with EOM-aware filtering keeps the two
  pychete terms, but projection stays zero after heavy substitution and scalar
  Green normal form; the next mismatch comparison should therefore focus on
  the higher-derivative `wilson14_o4_0` class and Matchete's full
  operator-class row reduction.
- Latest source-identification correction: a target-aware Matchete
  prop-order-4 dump shows selected `hScalar-lScalar -> cHD` is killed by
  `GreensSimplify`, so it is not the source of the nonzero saved Matchete
  `cHD` condition. Projecting the converted Matchete reference supertraces
  identifies `hScalar-lScalar-lVector-lScalar` as the current nonzero
  supertrace source for `cHD`. The next comparison now targets that exact
  four-slot Wilson-line trace, and any precise mismatch there should be
  checked against the corresponding Matchete algorithm before patching
  pychete.
- Latest four-slot trace slice: the first precise mismatch was source-level,
  not projection-level. Matchete `SetSubstitutions` forms scalar-vector
  X-terms from the charged scalar covariant kinetic current after subtracting
  `KinOpLagrangian`, while pychete's Matchete-convention free lagrangian kept
  the covariant derivative implicit and produced zero `lScalar-lVector`
  fluctuation entries. pychete now adds a bounded implicit-Abelian
  scalar-vector fluctuation contribution after checking that the ordinary
  explicit entry is zero, and a Singlet regression confirms
  `hScalar-lScalar-lVector-lScalar` generates four zero-order `gY^2`
  Wilson-line terms. The full `cHD` coefficient remains open downstream in
  Wilson-term/tensor/integral/Green-basis/projection stages.
- Latest Green-basis frontier update: the selected Singlet
  `hScalar-lScalar -> cHW` regression no longer crashes in Symbolica's linear
  solver after pychete strips scalar identity prefactors and encodes complex
  numeric row coefficients before solving. It now reaches projection, but the
  coefficient is still wrong (`25/72` at `mu_R^2=M^2` instead of Matchete's
  `1/12`). Pre-Green Matchete and pychete derivative-bilinear probes line up
  structurally, but finite-first and pre-finite Green exposure give different
  wrong constants, so the next semantic gap is Matchete's d-dimensional
  Green-basis/finite-shift handling rather than source generation.
- Latest Wilson-line ordering correction: a targeted pychete probe showed
  that the selected `hScalar-lScalar -> cHW` coefficient becomes Matchete's
  `1/12` when scalar derivative commutator-bilinear exposure is delayed until
  after finite scalar integral evaluation. The current implementation slice is
  changing the Wilson-line option and validation/debug paths to use that
  post-finite exposure boundary, while retaining pre-integral scalar
  Green-basis normal form only as a diagnostic comparison path.
- Focused result: the selected Singlet `hScalar-lScalar -> cHW` one-loop
  Wilson-line parity check now passes against the saved Matchete fixture.
  This is the first selected-trace coefficient milestone; it is not yet a full
  Matchete integration-test reproduction for an entire UV model.
- Latest user reminder: whenever Matchete and pychete disagree, dump and
  compare as many Matchete intermediate stages as practical before patching.
  The current cHD four-slot slice followed that route: Matchete insertion
  stages identified the expected paired Higgs-derivative structure before
  pychete patches were made.
- Current selected cHD status: pychete now reproduces the selected pre-heavy
  Singlet `hScalar-lScalar-lVector-lScalar -> cHD` Wilson-line finite
  coefficient with registered Wilson projection and EOM-aware target
  filtering. Full-model matching parity is still open, especially the
  registered projection/truncation behavior after heavy-scalar substitution
  and post-finite scalar commutator-bilinear exposure.
- Latest course adjustment: the requested Matchete-intermediate comparison
  was applied again to the selected `cHD` frontier. The first post-heavy
  mismatch was isolated inside pychete's registered Wilson projection guard,
  not in Matchete source generation or integral evaluation. The guard now
  permits a bounded termwise exact Symbolica coefficient pass before blocking
  oversized generic projection fallbacks, and the selected `cHD` coefficient
  survives the post-heavy/post-commutator registered projection path.
- Latest testing adjustment: first-success one-loop Wilson coefficients are
  now covered by partial integration regressions. The selected Singlet
  `hScalar-lScalar` test projects only the related `cHW`, `cHB`, and `cHWB`
  Higgs-gauge subset from one generated source, while the selected four-slot
  `cHD` test remains scoped to the single derivative-Higgs coefficient. This
  is intended to keep future regressions fast and localized before broader
  all-operator fixture checks are attempted.
- Latest cHD on-shell frontier checkpoint: added a development-only Matchete
  dump script and committed debug JSON for the Singlet `cHD`
  `EOMSimplify` shift. pytest now has a fast Mathematica-independent partial
  regression that separately checks the committed off-shell `cHD` projection,
  the Matchete on-minus-off `EOMSimplify` delta, and the stored on-shell
  matching condition. This makes the remaining full-model blocker explicit:
  pychete still needs a generic Matchete-style on-shell field-redefinition
  implementation, while the selected Wilson-line coefficient regressions are
  already scoped and passing for `cHW/cHB/cHWB` and the selected four-slot
  `cHD` contribution.
- Latest EOM prerequisite fix: pychete now builds free Lagrangians with the
  declared internal indices of registered fields and derives complex scalar
  EOMs with the correct conjugate variation for exact indexed fields. This
  means indexed SMEFT-like fields such as `H[i]` can now produce native
  Symbolica EOM replacement rules from the model Lagrangian. A Singlet fixture
  regression confirms two Higgs EOM rules are generated for the committed
  off-shell reference Laplacians, while also confirming that the remaining
  full `cHD` on-shell shift still requires the larger Matchete-style
  raw-Lagrangian field-redefinition loop.
- Latest partial-success/test-scoping update: pychete now has bounded
  Abelian vector EOM replacement support for scalar charged currents,
  including both `D_nu F_{nu mu}` orientations, and the public one-loop
  matching path applies those replacements before projection. The first
  successful selected one-loop Wilson coefficients are also covered by
  narrower partial integration tests: `cHW`, `cHB`, and `cHWB` are checked as
  separate parametrized cases from a cached selected `hScalar-lScalar`
  Wilson-line source, while the selected four-slot `cHD` coefficient remains a
  separate scoped regression. Full-model Singlet on-shell parity is still open
  because the generic Matchete-style field-redefinition loop is not complete.
- Latest `cHD` on-shell progress: after reviewing Matchete `FieldRedef.m`,
  pychete now has an opt-in Abelian vector field-redefinition companion for
  charged scalar currents. This accounts for the charged-covariant-derivative
  part of Matchete's vector `DummyGaugeShift`, in addition to the direct
  `D_nu F_{nu mu}` EOM replacement. On the committed Singlet reference
  fixture, vector EOM replacement plus this companion reproduces the saved
  Matchete on-shell `cHD` matching coefficient from the committed off-shell
  result. This is still a bounded subset: fermion currents, non-Abelian vector
  shifts, kinetic mixing, anomalies/Jacobians, and full iterative
  `EOMSimplify` remain to be implemented.
- Latest validation-route update: the same on-shell EOM options, including the
  Abelian vector field-redefinition companion, are now available through
  `ValidationFixture.one_loop_preview(...)` and
  `ValidationFixture.one_loop_preview_gap_report(...)`. This means future
  Matchete-independent Singlet `cHD` gap reports can use the public validation
  entry points instead of bespoke postprocessing.
- Latest partial-test update: the first selected one-loop Wilson-coefficient
  successes are now isolated in
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py`.
  The `cHW`, `cHB`, `cHWB`, and selected four-slot `cHD` checks can now be run
  as targeted partial integration tests, giving fast coefficient-level
  regression scoping before attempting broader Matchete integration parity.
- Latest public-route update: the selected Singlet `cHW/cHB/cHWB` subset now
  also passes through the public `Theory.match(...)` route via
  `ValidationFixture.one_loop_preview_gap_report(..., use_public_match_api=True)`.
  This is the first public one-loop Wilson-coefficient success surface. A
  bounded order-one `cHD` probe remains different, so full Singlet `cHD`
  parity still requires more generated source coverage beyond the current
  order-one/full-model route.
- Latest selected-`cHD` update: the public `Theory.match(...)` route now also
  reproduces the selected Singlet
  `hScalar-lScalar-lVector-lScalar -> cHD` coefficient with target filtering
  enabled. The fix keeps pre-generation Wilson-line entry filtering only for
  purely field-strength-local target requirements; mixed/pure field targets
  like registered `cHD` are filtered after full Wilson-line term generation so
  heavy-mediated path products are not removed too early.
- Latest partial-regression update: pychete now has a source-by-source
  matching-condition projection diagnostic on `MatchingResult`. A new
  Matchete-independent Singlet fixture test projects registered `cHD` from
  each committed reference supertrace and proves that
  `hScalar-lScalar-lVector-lScalar` is the only nonzero off-shell source for
  that coefficient in the saved reference. Together with the selected
  `cHW/cHB/cHWB` and selected four-slot `cHD` pychete coefficient tests, this
  gives narrower one-loop Wilson-coefficient regression surfaces before full
  all-operator matching parity is attempted.
- Latest partial-insertion update: added a Matchete debug fixture for the
  selected Singlet `hScalar-lScalar-lVector-lScalar -> cHD` trace at
  propagator order zero. The dump exposes 88 Matchete insertion replacements,
  and pychete now has two narrow path-level regressions proving that Wilson-line
  paths 0 and 26 each reproduce the same single quarter contribution seen in
  the Matchete insertion checkpoint. This is the first layer of subset
  matching tests below the selected aggregate coefficient: the remaining
  off-shell mismatch is now scoped to the missing four equivalent quarter
  insertions rather than to the loop integration or final projection pipeline.
- Latest scalar-vector debugging update: the Matchete debug script now also
  records the scalar-vector `Xterm` replacements for the selected `cHD`
  trace. A new full JSON fixture stores all 88 insertion replacements and a
  fast pytest regression checks the key counts: 20 nonzero `A^2 gY^2`
  scalar-vector insertion variants and eight explicit quarter-insertion
  checkpoints. This confirms the next implementation target is the
  scalar-vector `LoopMom`/`OpenCD` Xterm decomposition and its Green-basis
  projection behavior, not the already-green loop integration or projection
  machinery for paths 0 and 26.
- Latest partial-success update: pychete now mirrors Matchete's `FuncNCM`
  flattening before acting with open covariant derivatives, so nested
  Wilson-line `NCM(..., OpenCD, ...)` terms are handled correctly. The first
  selected one-loop Wilson-coefficient successes are also split into
  single-target partial integration tests: `cHW`, `cHB`, and `cHWB` each run
  with only their requested projection target and assert the exact filtered
  Wilson-line source size, making future coefficient regressions faster and
  easier to localize.
- Latest scalar-vector source update: pychete now generates the missing
  implicit Abelian scalar-vector `OpenCD` branch seen in Matchete's
  `Xterm[..., 1, 1, 1]` values. The selected Singlet four-slot source now has
  explicit `OpenCD` terms in all four nonzero scalar-vector paths. The
  pre-heavy selected `cHD` coefficient and the path `0`/`26` quarter
  checkpoints still pass; the post-heavy selected `cHD` projection is now
  correctly exposed as the next Green-basis/projection frontier instead of
  being hidden by the previous source-incomplete checkpoint.
- Latest public partial-test update: the public selected Singlet
  `Theory.match(...)` route for the first successful Higgs-gauge Wilson
  coefficients is now split into coefficient-specific pytest nodes for
  `cHW`, `cHB`, and `cHWB`. One cached public selected-source run backs those
  checks, so future regressions can identify the failing public coefficient
  without recomputing the slow selected matching route three times.
- Latest selected-`cHD` progress: the post-heavy selected four-slot
  `hScalar-lScalar-lVector-lScalar -> cHD` aggregate no longer projects to
  zero. The issue was localized to a projection guard: individual contributing
  paths were correct, but the target-local tensor-canonized aggregate was just
  over the old single-pass termwise byte limit. pychete now has a bounded
  chunked exact projection fallback that preserves linearity without enabling
  expensive global collect/factor fallbacks, and the selected aggregate keeps
  the Matchete coefficient after heavy-scalar substitution.
- Latest persistent-guidance update: the active goal objective and `AGENTS.md`
  now explicitly state that sustained Matchete/pychete disagreements must be
  narrowed with focused debug WolframScript dumps whenever Mathematica is
  available. The intended workflow is to inspect Matchete intermediate stages
  such as raw `EvaluateSTr`, insertion replacements, `ActWithOpenCDs`,
  `GatherLoopMomenta`, `WilsonExpand`, loop integration,
  `GreensSimplify`, `EOMSimplify`, and saved projections, then compare those
  to bounded pychete probes at the same semantic boundaries before patching
  the first differing generic algorithm.
- Latest selected-`cHD` diagnostic update: the current slice followed the
  requested Matchete-intermediate comparison workflow. Matchete insertion and
  scalar-vector `Xterm` dumps were compared to bounded pychete path probes,
  which localized the disagreement before projection to two generic
  Wilson-line source issues: the open-derivative action arity cap was too low
  for four-slot `NCM` chains, and the implicit Abelian scalar-vector `OpenCD`
  companion sign for barred scalar atoms had the wrong orientation.
- After the fix, selected
  `hScalar-lScalar-lVector-lScalar -> cHD` paths `0`, `2`, and `26` project to
  the finite Matchete quarter coefficient after heavy-scalar substitution,
  while path `24` carries the compensating opposite sign. The aggregate public
  selected `cHD` coefficient remains the Matchete value. This is still a
  selected-trace partial integration milestone, not a complete end-to-end
  Matchete model reproduction.
- Latest public-route `cHD` projection update: the next comparison moved from
  the selected four-slot source to the registered Wilson projection/EOM
  boundary. The source-only order-four `hScalar-lScalar -> cHD` probe confirms
  that registered target filtering keeps the Abelian field-strength candidate
  families needed for Matchete-style vector EOM reduction. pychete now also
  projects the IBP-equivalent representative `F_{nu mu} D_nu J_mu` through the
  same registered `cHD` vector-EOM alias as `J_mu D_nu F_{nu mu}`.
- The development debug script now resolves names like `cHD` to registered
  Wilson coefficient targets when possible, preserving operator metadata and
  EOM aliases in future Matchete/pychete dumps. This improves the next
  mismatch-dissection loop but still does not complete a full Matchete
  one-loop model test; the remaining task is the larger public order-four/full
  Singlet `cHD` route and whatever post-evaluation/EOM mismatch it exposes.
- Latest instruction confirmed and recorded: when pychete disagrees with
  Matchete, the active workflow is to keep dumping/dissecting focused Matchete
  WolframScript checkpoints and compare them with bounded pychete probes until
  the first generic algorithm boundary is found. This is now reinforced in
  `AGENTS.md` and the live one-shot implementation objective.
- Latest confirmation repeated for the active objective: mismatch updates must
  identify the Matchete dump/checkpoint, the paired bounded pychete probe, and
  the first semantic boundary compared. This keeps the one-shot port aligned
  with Matchete's algorithms while still implementing them in pychete with
  Symbolica/idenso/spenso/vakint.
- Latest implementation progress: the full public Singlet `cHD` order-zero
  Wilson-line route now finishes under the 30 GiB watchdog instead of blowing
  up during heavy-scalar substitution. The fix bounds heavy-scalar solution
  replacement by the requested EFT order and keeps staged projection sources
  synchronized. It was checked against the committed Matchete `cHD` insertion,
  EOM, and matching-condition fixtures plus a bounded pychete public internal
  probe. The coefficient still differs from Matchete: after factoring
  `hbar*A^2*gY^2/M^4`, pychete has the `-1/2` pole/log coefficient while
  Matchete has `-5/3`, so the next mismatch slice should target the missing
  source/EOMSimplify/field-redefinition contribution rather than projection
  performance.
- Latest user reminder recorded again: for every Matchete/pychete mismatch,
  keep running focused debug WolframScripts and dissect Matchete intermediate
  stages until the first semantic divergence is identified. The active
  `cHD` work should continue by comparing refreshed Matchete dumps with
  bounded pychete probes at source, Wilson expansion, loop integration,
  Green-basis, EOM/field-redefinition, and projection boundaries before any
  generic algorithm patch is accepted.
- Latest `cHD` mismatch-dissection update: the refreshed pychete public
  generated-source probe confirms the current source has no differentiated
  Abelian `FieldStrength(B)` atoms, no Abelian vector EOM replacement rule, and
  no vector field-redefinition delta, even with Wilson-line commutator
  emission/expansion enabled. The converted Matchete reference off-shell
  source does contain the differentiated field-strength representative and
  produces the expected vector-EOM machinery. The next generic fix should
  therefore target Wilson-line Green/commutator source exposure into
  Matchete's field-strength-divergence/current form, guided by the committed
  insertion-level `cHD` debug dump.
- Latest persistent-guidance reinforcement: the requested workflow is now
  recorded as a mandatory mismatch checklist in `AGENTS.md` and the live
  implementation notes. For any Matchete/pychete disagreement, future patches
  must name the Matchete debug script or fixture, the paired bounded pychete
  probe, the first differing stage boundary, and why the change is a generic
  Matchete-algorithm port rather than a coefficient-specific repair.
- Latest scalar Green source-exposure progress: following the Matchete-dump
  workflow, pychete now lowers bounded three-plus-one scalar derivative
  bilinears through the existing Green normal-form/commutator path, exposing
  the differentiated Abelian field-strength representative seen in the
  committed Matchete `cHD` dumps. A watchdog cHD boundary probe now finds two
  differentiated `FieldStrength(B)` atoms and two vector EOM rules in the
  generated public source. This is still not a full Matchete one-loop model
  pass: the public projected coefficient remains at the old `-1/2` pole/log
  value, and the next issue is Matchete-style source scoping plus
  EOM/field-redefinition ordering.
- Latest user reminder reinforced again: whenever Matchete and pychete results
  disagree, the active workflow is to dump and dissect as many focused
  Matchete intermediate stages as possible with debug WolframScripts, compare
  them to bounded pychete probes at the same semantic boundaries, and patch
  only the first generic algorithm divergence. This has been made explicit in
  `AGENTS.md` and the live implementation objective notes so future slices keep
  following Matchete's algorithms rather than fitting final coefficients.
- Latest Matchete EOMSimplify dissection: the Singlet `cHD` debug WolframScript
  and JSON fixture now record Matchete's `FieldsToShift[offShell]` output.
  Matchete shifts matter fields including `H` at EFT order 4 and does not list
  `B` at this checkpoint. A pychete public-route probe shows the current EOM
  pass runs before late scalar commutator exposure and therefore applies zero
  rules, while a manual post-exposure probe finds vector EOM rules whose
  companion projects into `A*muphi*gY^2`, not the saved Matchete `A^2*gY^2`
  `cHD` delta. The next implementation work should therefore port the
  Matchete-style systematic matter-field redefinition/source-scoping step
  rather than simply reordering the existing vector-only helper.
- Latest projection fix: registered-Wilson Abelian vector-EOM projection
  aliases are now on-shell scoped. This prevents explicit off-shell reference
  projections and source-map diagnostics from absorbing part of Matchete's
  `EOMSimplify` shift, while preserving those aliases for on-shell projection
  and conservative Wilson-line filtering. Focused `cHD` fixture, selected
  coefficient, projection-alias, mypy, and diff checks passed.
- Latest confirmation and debug update: yes, the active mismatch workflow is
  to keep running focused debug WolframScripts, dissect Matchete intermediate
  stages, compare them with bounded pychete probes, and patch only the first
  generic algorithm boundary that diverges. This was reinforced again in
  `AGENTS.md` and the live objective notes. The Singlet `cHD`
  EOMSimplify dump now uses Matchete's real package-scope `EoM`, `Operator`,
  `TermsToList`, `InternalSimplify`, and `$FieldAssociation` symbols, and the
  regenerated JSON fixture records six prepared EOM terms for
  `{d, e, l, q, u, H}` plus a Higgs `ScalarShift` checkpoint. The next
  implementation frontier remains the generic Matchete-style systematic
  matter-field redefinition/source-scoping step, not a coefficient-specific
  `cHD` repair.
- Latest replay checkpoint: the Singlet `cHD` debug fixture now also replays
  Matchete private `FieldRedef.m` stages on the saved off-shell expression and
  on the sum of saved simplified supertraces. Both replays leave the `cHD`
  projection unchanged at every recorded stage, even though the saved
  Matchete on-shell result has a nonzero `EOMSimplify` delta. This narrows the
  next debugging target: the required Matchete evidence is the original
  unsimplified `LagrangianEFT` entering `EOMSimplify`, not the already saved
  Greens-simplified off-shell fixture.
- Latest user reminder and raw-boundary update: the active workflow remains to
  run focused debug WolframScripts frequently, dump as many relevant Matchete
  intermediate stages as possible, compare them with bounded pychete probes,
  and patch only the first generic algorithm boundary that diverges. This is
  now reinforced in `AGENTS.md`, the persistent goal objective, and the live
  implementation notes. The Singlet `cHD` EOMSimplify debug fixture now also
  records Matchete's raw `LagrangianEFT` boundary: raw source differs from the
  saved coefficients, `InternalSimplify` lands exactly on the saved off-shell
  coefficient, and `PerformSystematicFieldRedefs`/`GreensSimplify`/direct
  `EOMSimplify` land exactly on the saved on-shell coefficient. The next
  runtime patch should therefore compare pychete's generated pre-EOM source to
  this raw/internal/on-shell sequence, not fit the final coefficient.
- Latest paired pychete boundary update: added a pychete-side debug script and
  committed JSON fixture for the Singlet `cHD` pre-EOM selected Wilson-line
  boundary. The comparison now shows that pychete's selected normalized
  unrenormalized source already has only the `-1/2` pole/log weight, while
  Matchete's selected trace/off-shell checkpoint has the `-3/2` pole/log
  weight. The immediate first divergence is therefore before EOM, in selected
  Wilson-line source/Green-basis coverage; the next runtime patch should
  revisit Matchete's insertion/Xterm/WilsonExpand/GreensSimplify behavior for
  this trace before adding broader field-redefinition machinery.
- Latest user reinforcement recorded: when pychete and Matchete disagree,
  continue running or refreshing focused debug WolframScripts and compare as
  many Matchete intermediate stages as practical against bounded pychete
  probes. Future mismatch updates should explicitly name the Matchete
  checkpoint, the paired pychete probe, and the current suspected stage
  boundary so the port keeps following Matchete's algorithms rather than
  fitting final coefficients.
- Latest user reinforcement recorded again: this paired-debug workflow is now
  an acceptance gate for mismatch-driven runtime changes. Each such change
  must name the current Matchete WolframScript/fixture checkpoint, the bounded
  pychete probe, and the first differing semantic boundary; if that evidence
  is not available, continue dumping/dissecting Matchete intermediates before
  patching runtime code.
- Latest cHD source/path comparison: the pychete boundary fixture now records
  Matchete's eight quarter insertion checkpoints for
  `hScalar-lScalar-lVector-lScalar -> cHD` alongside pychete's four nonzero
  Wilson-line paths. A focused comparison of Matchete scalar-vector `Xterm`
  values with pychete implicit Abelian scalar-vector differential entries
  exposed a generic derivative/OpenCD sign mismatch. After the fix, paths
  `0`, `2`, `24`, and `26` all project with the Matchete `-1/4` sign, and the
  selected aggregate moved from `-1/2` to the `-1` pole/log weight. The
  remaining gap to Matchete's `-3/2` selected trace/off-shell checkpoint is now
  source/path coverage or component-index delta handling before EOM.
- The paired pychete source-only debug fixture for the same narrowed trace and
  target is now kept under
  `assets/validation/pychete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.pychete.source.debug.json`
  and has a cheap pytest assertion. It originally recorded the four-term
  filtered pychete source frontier; the latest indexed-functional-derivative
  update below supersedes that count with eight terms while preserving the
  same source-generation versus post-evaluation/EOM diagnostic role.
- Latest cHD source/path update: the active Matchete checkpoint remains
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`,
  paired with the pychete boundary/source fixtures under
  `assets/validation/pychete/debug/`. A generic indexed-functional-derivative
  fallback now uses Symbolica field-pattern replacement plus idenso delta
  contraction to recover component-related paths. pychete now has eight
  nonzero paths `{0, 2, 12, 14, 24, 26, 36, 38}`, matching Matchete's eight
  `-1/4` insertion checkpoints path by path. Filtered and unfiltered pychete
  source fixtures both have eight terms, so target filtering is not the
  current mismatch. The remaining boundary is Matchete's reduction/aggregation
  from insertion checkpoints or raw selected prop-order data to the saved
  `-3/2` selected trace/off-shell coefficient, while pychete's selected
  prop-order-zero aggregate is `-2`.
- Latest reinforcement confirmed: when pychete and Matchete disagree, the
  active workflow is to keep running or refreshing focused debug
  WolframScripts, dump as many Matchete intermediate stages as practical,
  compare them against bounded pychete probes at the same stage, and patch only
  the first generic Matchete algorithm boundary through
  Symbolica/idenso/spenso/vakint rather than final-coefficient fitting.
- Latest selected `cHD` propagation-order update: the requested
  Matchete-intermediate workflow was applied again with refreshed
  `debug_singlet_wilson_trace.wls` dumps for
  `hScalar-lScalar-lVector-lScalar -> cHD` at propagation orders 1 and 2.
  Comparing those dumps to bounded pychete total-order probes showed that the
  saved Matchete selected trace is prop-order 0 + 1 + 2. pychete now matches
  the selected finite projection for all three pieces individually. The two
  generic fixes were Wilson-line loop-symmetry pruning over explicit loop
  momenta plus uncontracted `DifferentialOperator(...)` Xterm slots, and
  d-dimensional closed Lorentz metric traces `Metric(mu,mu) -> 4 - 2 epsilon`
  before finite Laurent extraction. The remaining first full-matching
  frontier is broader Green/EOM/on-shell/full-model parity, not this selected
  four-slot trace aggregation.
- Latest pychete boundary-fixture refresh: the pychete-side
  `singlet_eom_cHD.pychete.debug.json` fixture now uses the selected
  Wilson-line plan through total order 2 and records order-local projections
  before summing. This confirms the selected four-slot trace now matches
  Matchete's off-shell checkpoint with pole/log weight `-3/2`. The remaining
  Singlet `cHD` frontier is the Matchete on-shell/EOM shift to `-5/3`, so the
  next comparison should target Matchete's raw `LagrangianEFT` /
  `InternalSimplify` / `PerformSystematicFieldRedefs` sequence rather than
  selected trace aggregation.
- Latest Matchete EOM dissection: refreshed the Singlet `cHD` Matchete debug
  fixture with the internal-source field-redefinition replay. The selected
  pychete trace already matches the Matchete off-shell checkpoint; the first
  narrowed on-shell boundary is Matchete's dimension-6, three-derivative
  `PerformSystematicFieldRedefs` shift (`after_shift_dim6_dev3`). The next
  runtime work should port that generic scalar/matter field-redefinition
  machinery through Symbolica/idenso/spenso/vakint boundaries rather than
  repairing the final `cHD` coefficient.
- Latest scalar field-redefinition implementation: pychete now has a bounded
  formal-EOM scalar consumer,
  `scalar_eom_field_redefinition_delta(...)` /
  `Theory.scalar_eom_field_redefinition_delta(...)`, which consumes explicit
  `EOM(Field(...))` and `EOM(Bar(Field(...)))` atoms through Symbolica
  coefficient extraction and source-scoped `derive_eom(...)` variations. The
  remaining Singlet `cHD` gap is now the preceding Matchete-like
  Green/InternalSimplify exposure stage that must turn derivative-source terms
  into explicit formal EOM atoms before the field-redefinition consumer can
  reproduce `after_shift_dim6_dev3`.
- Latest current-exposure probe: pychete now has
  `expose_abelian_vector_eom_currents(...)` /
  `Theory.expose_abelian_vector_eom_currents(...)`, a bounded generic helper
  for exact Abelian vector-EOM current-current products. The refreshed paired
  Singlet `cHD` pychete probe compared against
  `debug_singlet_eom_simplify.wls` still finds zero exposed vector-EOM
  divergences and zero vector field-redefinition deltas across the selected
  entries. This confirms the active mismatch is broader Matchete
  `InternalSimplify`/Green representative conversion, not a simple exact
  inverse Abelian current-product rewrite.
- Latest `FieldRedef` consumer update: pychete now has
  `operator_derivative_count(...)`,
  `select_terms_by_dimension_and_derivatives(...)`, and
  `systematic_scalar_eom_field_redefinition_delta(...)`, with matching
  `Theory` methods, to mirror Matchete's `SelectOperatorDevsAndDim` and
  scalar formal-EOM `ShiftLagrangian` loop once formal EOM terms have already
  been exposed. Formal `EOM(Field(...))` atoms now carry Matchete-compatible
  EFT dimensions for `operator_dimension(...)`. This is still consumer-side
  machinery; the active Singlet `cHD` gap remains the upstream
  `InternalSimplify`/Green representative exposure that must generate the
  formal EOM terms feeding Matchete's `after_shift_dim6_dev3` shift.
- Latest scalar `EoMSplitter` update: pychete now has
  `scalar_formal_eom_ibp_identities(...)`, the scalar subset of Matchete's
  `IdentitiesIBP` branch that replaces a formal scalar `EOM(...)` by
  `CD(mu, field)` and adds the resulting total-derivative identity to the
  Green-basis system. The systematic scalar field-redefinition helper can now
  also take separate high-order EOM terms and lower-order source Lagrangian
  inputs, matching Matchete's `ShiftLagrangian` separation. Fermion/vector EOM
  splitters and the upstream Singlet `cHD` formal-EOM exposure remain future
  work.
- Latest Wilson-line scalar EOM finalization update: when
  `wilson_line_expose_scalar_eom_terms=True`, pychete now follows the exposed
  formal scalar EOM source with the bounded systematic scalar field-redefinition
  delta, using `on_shell_eom_lagrangian` as the lower-order source and storing
  the delta/after-shift expressions in supertraces. This is the generic
  Matchete `PerformSystematicFieldRedefs` consumer wiring for the current
  `debug_singlet_eom_simplify.wls` / `singlet_eom_cHD.debug.json` checkpoint.
  The remaining Singlet `cHD` blocker is still upstream: pychete must expose
  the same formal EOM terms that Matchete `InternalSimplify` records before
  this consumer can close the on-shell shift.
- Latest scalar Green-closure update: the Wilson-line scalar EOM exposure hook
  now uses a deeper bounded local Green-basis closure for formal-EOM exposure.
  This fixes the generic local boundary where fourth-derivative scalar
  representatives like `Bar(H[{mu, mu, nu, nu}]) H` failed to expose formal
  scalar EOM factors under the lightweight default closure. The change is tied
  to Matchete `Simplifications.m` (`EoMStandardForm` / `IdentitiesIBP` /
  `EoMSplitter`) and the active Singlet `cHD` EOM debug fixture; it is not a
  final-coefficient patch. The full Singlet on-shell coefficient still needs
  broader `InternalSimplify` exposure parity.
- Latest user instruction, 2026-06-28: continue using repeated focused
  Matchete debug WolframScripts and intermediate-stage dissection whenever a
  pychete/Matchete mismatch appears. Add the rule to persistent markdown so
  future work keeps comparing Matchete dumps with bounded pychete probes,
  locating the first semantic disagreement, and only then porting the
  corresponding generic Matchete algorithm through Symbolica/idenso/spenso/
  vakint.
- Latest Singlet `cHD` paired-probe status, 2026-06-28: the refreshed
  pychete boundary fixture records scalar-EOM exposure attempts for the 10
  nonzero selected `hScalar-lScalar-lVector-lScalar` Wilson-line entries. All
  currently hit the bounded scalar Green-basis cap before formal `EOM(...)`
  atoms appear, while Matchete's `debug_singlet_eom_simplify.wls` checkpoint
  records 105 Higgs formal-EOM terms after `InternalSimplify`. The next generic
  port target is therefore Matchete `InternalSimplify`'s operator-basis /
  identity-neighborhood control, not final-coefficient tuning.
- Latest performance/parity correction, 2026-06-29: the `cHD` on-shell
  vector-EOM shift should be dissected through the target-filtered
  `hScalar-lScalar` order-four two-Higgs source trace, not by heavy-first
  expansion of the four-slot `hScalar-lScalar-lVector-lScalar` entries. The
  four-slot trace remains the off-shell cHD source, but the Matchete
  `after_shift_dim6_dev3` field-redefinition delta is fed by
  hScalar-lScalar two-Higgs formal B/W vector-EOM terms. pychete now records a
  bounded hScalar-lScalar B-vector EOM source and nonzero cHD projection in
  the debug fixture; the remaining gap is coefficient parity for the scalar
  Green / EoMSplitter source, with W-vector EOM support tracked separately if
  needed.
- Latest cHD vector-split update, 2026-06-29: the Matchete debug script now
  replays the dim6/dev3 vector shift separately for B and W. B selects six
  two-Higgs formal vector-EOM terms and produces the full on-shell cHD delta,
  while W selects six terms but projects zero to cHD. pychete now has the
  generic vector formal-EOM IBP splitter
  `vector_formal_eom_ibp_identities(...)`, matching Matchete
  `EoMSplitter[mu, Vector[nu]] -> FieldStrength[mu, nu]`; focused unit tests
  pass, but the refreshed hScalar-lScalar B-source coefficient is unchanged.
  The first remaining mismatch is therefore still upstream scalar Green /
  source coefficient parity, not the vector EOM consumer or a W-side
  field-redefinition gap.
- Latest source-boundary/performance update, 2026-06-29: pychete now records
  formal B-vector EOM source-operator projections in the bounded
  `hScalar-lScalar` cHD debug fixture. The `Bar[H] EOM[B_mu] D_mu H` source
  coefficient has Matchete-aligned pole/log terms, but the finite term is
  `7 i/36 * hbar A^2/M^4` instead of Matchete's `17 i/72 * hbar A^2/M^4`.
  This pins the next generic patch to the scalar Green/tensor source producer.
  The diagnostic route remains the target-filtered aggregate source probe,
  because per-term Green splitting is not performance-competitive with the
  corresponding Matchete stage and should not be rescued by raising caps.
- Latest evanescent-source diagnosis, 2026-06-29: a Matchete replay with
  inert `EvaluateGammaFactor` shows the dim6/dev3 B source as
  `(-G1 + 8 G2) * (1/eps + log(mubar2/M^2) + 1)`, while pychete's raw
  topology/source probe gives `(2 G1 - 4 G2 - 1/4)` on the same
  `Prop[0]^3 Prop[M]` topology. These agree at strict four dimensions but
  differ by `epsilon/24`, exactly the finite cHD gap after the topology pole.
  Checks ruled out metric-contraction order, closed metric-trace epsilon, and
  preferred Green-basis representative order. The next implementation target
  is the missing d-dimensional `InternalSimplify`/identity-set semantics that
  produce Matchete's evanescent representative in the aggregate source path.
- Latest user instruction and implementation response, 2026-06-28: perform a
  short remaining-gap study for the first full one-loop matching parity target,
  archive the large live implementation notes to
  `implementation_notes/one_shot_implementation_B.md`, rewrite the live notes
  as a compact summary, and start reducing `matching.py` by dispatching code
  into semantic modules. The current estimate is 3-5 coherent slices to get the
  first full nontrivial Singlet Scalar Extension `cHD` parity test: class-wise
  scalar `InternalSimplify`, formal Higgs EOM exposure into the existing scalar
  field-redefinition consumer, full public Singlet route composition, then a
  locked full regression. The first refactor slice moved Wilson-line scalar
  EOM postprocessing into `src/pychete/wilson_line_eom.py`.
- Latest fixture-backed evanescent-source update, 2026-06-29: refreshed the
  focused Singlet `cHD` Matchete and pychete debug fixtures so the first
  source-level mismatch is now committed data, not only an exploratory note.
  Matchete's inert `EvaluateGammaFactor` replay records the B-source
  coefficient as `-(1 + eps + eps log)/eps * (SG[1,4] - 8 SG[2,4])`, while
  pychete's paired target-filtered raw-topology probe records
  `32*pi^2*G1 - 64*pi^2*G2 - 4*pi^2` on the same `Prop[0]^3 Prop[M]`
  topology. These fixtures keep the next runtime slice focused on the generic
  d-dimensional `InternalSimplify`/identity-set semantics and avoid the slower
  heavy-first four-slot expansion route.
- Latest class-neighborhood probe, 2026-06-29: the relevant
  `hScalar-lScalar#wilson14_o4_0` two-Higgs source class is small enough for a
  Matchete-like class solve (`32` basis terms, `18` identities), but pychete
  currently creates the B-vector EOM only after the Green solve. Simply
  increasing the class closure depth changes the coefficient in the wrong
  direction and then exceeds the local basis cap; pre-expanding commutator
  identities also gives the wrong sign pattern. The next runtime patch should
  therefore target Matchete's actual `AtomicOp`/`OpScore` representative
  semantics for the class, not caps or commutator-order shortcuts.
- Latest performance-focused continuation, 2026-06-29: user reinforced that
  pychete's parity probes and intermediate stages must be at least as
  performant as Matchete's corresponding stages. Implementation response:
  preserved the compact live notes while saving this slice's prior snapshot as
  `one_shot_implementation_part_G.md`, split generated expansion-plan classes
  out of the oversized `matching.py`, refreshed the Matchete cHD fixture with
  the exact `{{H, Conj[H]}, 4}` AtomicOp 13/14 identity neighborhood, and
  implemented a bounded Abelian vector-EOM scalar-bilinear orientation normal
  form. The new pychete fixture now keeps both `barH_EOMB_DH` and
  `DbarH_EOMB_H` source orientations, so the remaining cHD frontier is the
  SymGamma/d-dimensional source coefficient rather than orientation loss.
- Latest stage-parity/performance update, 2026-06-29: user asked to keep
  pychete's intermediate parity probes at least as performant as Matchete.
  Implementation response: added a bounded pychete per-stage probe only for
  `hScalar-lScalar#wilson14_o4_0`, with coefficient projection limited to the
  topology-lowered current and Matchete-order boundaries. The probe shows that
  current pychete order and diagnostic `ContractMetric`-before-`WilsonExpand`
  order give identical source projections, while the selected expression
  shrinks from about 324 KB at formal SymGamma to about 99 KB at topology
  lowering. The Matchete debug fixture now also records that inert-SymGamma
  B/W vector-EOM source counts are zero before
  `InternalSimplify[..., dDimensional]` and become 12 B plus 12 W terms after
  that stage. This pins the next runtime fix to d-dimensional
  `InternalSimplify`/Green-basis identity semantics.
- Latest scalar `OpScore` parity update, 2026-06-29: the bounded scalar
  Green-basis scorer now follows Matchete's local score scale instead of using
  pychete's earlier dominant Python-side derivative penalties. Kinetic scalar
  representatives outrank formal EOMs, formal EOMs outrank field strengths,
  and repeated-derivative penalties remain small. The refreshed pychete cHD
  source fixture now gives the Matchete-aligned inert-SymGamma polynomial
  `-8*pi^2*SG[1,4] + 64*pi^2*SG[2,4]` for `Bar[H] EOM[B] D H` and the
  opposite orientation for `D Bar[H] EOM[B] H`, removing the previous spurious
  constant term and fixing the local evanescent finite source gap without
  broadening the probe. The next checkpoint is public-route composition to the
  full Singlet `cHD` matching coefficient.
- Latest performance correction, 2026-06-29: a canonical fluctuation-basis
  prototype reduced the Singlet setup from 26 modes to 16 and the selected
  four-slot `cHD` path map from eight nonzero paths to four, but the aggregate
  coefficient lost a factor of two. The prototype was discarded; future
  canonicalization must be multiplicity-preserving and should model the
  Matchete field-degree/component weights explicitly before it replaces the
  current path-expanded representation.
- Latest performance-parity instruction, 2026-06-29: user emphasized that
  pychete's intermediate parity-comparison stages should be at least as
  performant as the corresponding Matchete stages. Implementation response:
  kept this slice bounded to the target-filtered `hScalar-lScalar`/`cHD`
  frontier, rechecked the committed Matchete and pychete source fixtures, and
  corrected the stale finite-Higgs-bilinear mismatch interpretation. The
  local formal-SymGamma source boundary is now treated as aligned after the
  Matchete-scale `OpScore` fix; the remaining first-parity work is public
  route composition from that corrected source. For code structure and
  performance visibility, extracted the CDE/Wilson-line projection-filter
  policy from `matching.py` into
  `src/pychete/matching_projection_filters.py`, preserving `pychete.matching`
  compatibility aliases and validating with focused target-filter tests under
  the 30 GiB watchdog.
- Latest public-route `cHD` progress, 2026-06-29: the selected
  `hScalar-lScalar -> cHD` public route was probed through target-local
  heavy-scalar substitution and then through scalar-EOM/vector-field
  redefinition. Heavy-only projection is efficient but produces
  `kappa/muphi`-type heavy-solution terms, not Matchete's `A^2 gY^2` cHD
  shift. Enabling the scalar-EOM bridge previously failed because the
  post-heavy selected source was about 1.3 MB / 2592 terms and an unrelated
  large operator class exceeded the Green-basis cap. Implementation response:
  added an opt-in class-local capacity fallback for the Wilson-line EOM
  bridge, leaving oversized classes unreduced while reducing smaller classes
  with Symbolica's Green-basis solve. The public heavy+EOM probe now completes,
  applies two scalar-commutator Abelian vector-EOM rules and a nonzero vector
  field-redefinition delta, and records the remaining semantic mismatch as
  `kappa/muphi` source composition versus the Matchete `A^2 gY^2` vector-EOM
  coefficient. Focused unit and slow integration frontier tests passed under
  the 30 GiB watchdog.
- Latest performance/parity continuation, 2026-06-29: user emphasized that
  pychete's intermediate parity stages must stay at least as performant as
  Matchete's. Implementation response: narrowed the public
  `hScalar-lScalar -> cHD` mismatch to Wilson-line scalar-EOM ordering and
  tensor-reduction preparation. The public and validation-preview routes now
  defer generic generated on-shell EOM replacement to the combined
  Wilson-line scalar/EOM exposure stage, avoid a duplicate setup-level scalar
  commutator exposure when formal scalar-EOM exposure is requested, and
  automatically enable native tensor reduction for Wilson-line internal
  scalar-EOM bridges. The focused public regression now records the selected
  Abelian B-vector field-redefinition delta proportional to `A^2*gY^2`; the
  remaining frontier is the heavy-solution `kappa/muphi` composition and the
  residual factor to Matchete's full dim6/dev3 vector-shift replay.
- Latest indexed-variation parity fix, 2026-06-29: the remaining selected
  `hScalar-lScalar -> cHD` factor mismatch was traced to a generic indexed
  functional-derivative issue. Exact dummy-label replacement could return a
  nonzero but partial derivative and thereby drop alpha-equivalent `H[d2]`
  fluctuation entries before Wilson-line expansion. Implementation response:
  indexed targets now prefer the native indexed Symbolica-pattern variation
  before accepting exact output; the refreshed pychete fixture doubles the
  selected source/path multiplicity to Matchete's insertion neighborhood, and
  the public selected route now reproduces Matchete's B-only dim6/dev3 finite
  replay coefficient for `cHD`. The remaining work is full Singlet public-route
  composition, including heavy-solution terms, unselected trace remainder, and
  pole/MS convention handling.
- Latest performance/code-organization continuation, 2026-06-29: user again
  emphasized that pychete parity probes and intermediate stages must be at
  least as performant as the corresponding Matchete stages. Implementation
  response: kept the live implementation note compact instead of duplicating
  archives, and extracted the Wilson-line/CDE vakint staging, internal
  termwise evaluation, propagator-power shifting, and postprocessing helpers
  from `src/pychete/matching.py` into `src/pychete/matching_integrals.py`.
  Existing private imports from `pychete.matching` remain compatibility
  aliases for tests/debug notebooks, while the performance-critical
  tensor-reduction/evaluation boundary has a dedicated module. This reduced
  `matching.py` from 9,190 to 8,563 lines without widening the selected cHD
  parity route.
- Same slice clarification: the focused slow checks exposed that the older
  selected four-slot `hScalar-lScalar-lVector-lScalar -> cHD` prop-order-0
  aggregate is no longer a matched aggregate after the indexed-variation fix.
  Matchete's committed dump has eight target quarter insertions, while
  pychete now keeps sixteen alpha-aware component paths and projects twice the
  old aggregate. The tests now record this honestly as a multiplicity-
  preserving canonical-basis frontier; the currently matched cHD sub-check is
  the selected `hScalar-lScalar` B-vector dim6/dev3 replay.
- Latest four-slot multiplicity diagnostic, 2026-06-29: the first suspected
  backend boundary was ruled out. idenso now has a regression check showing
  that equal-label open identity deltas reduce to one, while distinct-label
  open deltas such as `Delta(Index(i,R), Index(j,Bar(R)))` remain explicit.
  The public four-slot cHD frontier test now also pins the exact sixteen
  pychete path IDs (`0,1,2,3,12,13,14,15,24,25,26,27,36,37,38,39`) that each
  contribute the same quarter term, compared with Matchete's eight target
  quarter insertions. The next runtime fix should therefore target generic
  Matchete-style fluctuation component/field-degree weighting, not projection,
  tensor reduction, or delta contraction.
- Latest performance-boundary update, 2026-06-29: user reinforced that
  pychete's parity probes should be at least as performant as Matchete's
  intermediate stages. Implementation response: added a Matchete-style
  label-level fluctuation-DOF helper and path component-weight diagnostic.
  The fast Singlet four-slot `cHD` probe now compares pychete directly at
  Matchete's `$XFieldDofs` / `DeterminePowerInsertions` boundary: the canonical
  label-level setup has 16 DOFs, 12 total selected trace paths, and four
  B-containing paths with component weight two, matching Matchete's eight
  nonzero insertion checkpoints without Wilson-term expansion or tensor
  reduction. This pins the scalable route for the next runtime promotion.
- Latest continuation, 2026-06-29: user asked to continue while making sure
  pychete performance is always at least as good as Matchete for intermediate
  parity comparisons. Implementation response: promoted the label-level
  Matchete-DOF boundary into an explicit opt-in Wilson-line route. The route
  uses Matchete-style fluctuation DOFs plus component-weighted path terms, so
  the four-slot Singlet `cHD` checkpoint can evaluate four generated B paths
  with effective weight eight instead of sixteen duplicate component paths.
  The default explicit-component route remains available as a diagnostic until
  broader fixtures validate the weighted route.
- Follow-up performance validation, 2026-06-29: implementation checked the
  same DOF classing idea against the accepted `hScalar-lScalar -> cHW/cHB/cHWB`
  field-strength subset and the active `hScalar-lScalar -> cHD` scalar-EOM
  bridge. Result: label-level DOFs alone preserve the accepted Higgs-gauge
  Wilson coefficients and keep the 14-term route; component weights are wrong
  for those field-strength targets. For the scalar-EOM `cHD` route, label-level
  DOFs plus component weights preserve the selected coefficient while reducing
  raw generated Wilson-line terms from 32 to 16 with effective weighted count
  32. Future use of component weights must be backed by a matching Matchete
  checkpoint.
- Latest selected Higgs-gauge fixture tightening, 2026-06-29: the accepted
  `cHW/cHB/cHWB` validation fixture now explicitly uses label-level Matchete
  fluctuation DOFs with component path weights disabled, and pins the bounded
  nonzero Wilson-plan entries so this matched subset stays on the targeted
  performance route.
- Latest Singlet status audit, 2026-06-29: the committed Singlet Matchete
  fixture has 64 external SMEFT/Wilson entries, 25 of which are nonzero. The
  broad preview accepts 39/64 only because those are zero Wilson coefficients;
  the meaningful nonzero-Wilson count currently validated by pychete is 3/25
  (`cHW`, `cHB`, `cHWB`). `cHD` remains the active first full-coefficient
  frontier.
- Latest staged projection fix, 2026-06-29: when tree-level matching is
  included, Wilson-line scalar/EOM exposure and Abelian vector-field
  redefinition now re-synchronize the staged loop-only on-shell projection
  source with the final on-shell expression. This preserves generated
  Wilson-line vector-field contributions during staged projection; it does
  not yet resolve the full `cHD` heavy-solution/source-composition gap.
- Latest user focus, 2026-06-29: keep the work centered on finishing the first
  Matchete/pychete one-loop matching parity test, and whenever a result
  disagrees, dump as many Matchete intermediate stages as possible and compare
  them with bounded pychete probes to locate the first mismatch. Current
  response: the Singlet `cHD` scalar/EOM bridge was dissected at the
  Matchete `InternalSimplify` / systematic-field-redefinition boundary, which
  showed that pychete should skip post-bridge heavy-scalar solution
  substitution because the source is already `kappa/muphi`-free at that stage.
- Follow-up direction, 2026-06-29: take a step back and deeply inspect the
  Matchete source behind the one-loop matching path so pychete can mirror the
  conceptual algorithm, not only final Wilson coefficients. Current response:
  `one_shot_implementation.md` now contains a Matchete one-loop pipeline audit
  covering `LoadModel`, `Match`, `SetCurrentLagrangian`, `SetSubstitutions`,
  `LoopMatch`, `PowerTypeSTr`, `GenericPropagatorExpansion`,
  `DeterminePowerInsertions`, `EvaluateSTr`, `WilsonExpand`,
  `LoopIntegrate`, `MatchReduce`, `EOMSimplify`, `InternalSimplify`,
  `ConstructOperatorIdentities`, `PerformSystematicFieldRedefs`, and
  `GreensSimplify`.
- Latest follow-up, 2026-06-29: deepen that audit for the active Singlet
  one-loop target by reading the Matchete source around matching, supertrace
  evaluation, loop integration, EFT counting, field redefinitions,
  simplification, validation saving, and matching-condition extraction.
  Current response: the implementation notes now explicitly include
  `DetermineEOMs`, `ReplaceHeavyEOM`, `LogTypeSTr`, `DetermineLogInsertions`,
  `GenericLogExpansion`, `SeriesEFT`, `OperatorDimension`,
  `SaveValidationResults`, `MapEffectiveCouplings`, and
  `MapEffectiveCouplingsInternal`, and tie the active `cHD` strategy to
  Matchete's validation-stage semantics.
- Follow-up implementation note, 2026-06-29: attempted to promote the
  selected four-slot `cHD` pole-through-finite checkpoint directly through the
  public hybrid `Theory.match(...)` source, but the run again behaved like a
  broad monolithic route and was stopped under the 30 GiB watchdog. The
  regression has therefore been narrowed to the actual stage-local change:
  normalized public `*_through_finite_part` projection source names are now
  exposed by `MatchingResult.with_loop_normalization(...)`, while the existing
  staged Singlet `cHD` tests continue to pin the selected pole/finite
  coefficient composition.
- Latest requested Matchete deep dive, 2026-06-29: re-read the actual
  Matchete one-loop source for the active validation path and tightened the
  function ledger around `Match`, `SetCurrentLagrangian`, `SetSubstitutions`,
  `ListPowerTypeTraces`, `LoopMatch`, `PowerTypeSTr`,
  `GenericPropagatorExpansion`, `DeterminePowerInsertions`, `EvaluateSTr`,
  `WilsonExpand`, `LoopIntegrate`, `MatchReduce`, `GreensSimplify`,
  `EOMSimplify`, and `MapEffectiveCouplings`. The important conclusion is
  that raw selected supertrace agreement is only the first layer; full Singlet
  `cHD` parity also needs Matchete's validation-layer off-shell
  Green-basis cleanup, systematic EOM/field-redefinition shifts, and final
  Wilson-condition solve.
- Latest public-route slice, 2026-06-29: added
  `OneLoopMatchOptions.wilson_line_include_unselected_traces`. The default
  keeps public Wilson-line matching hybrid, as before. Setting it to `False`
  runs selected Wilson-line trace families in isolation through
  `Theory.match(...)`, mirroring Matchete's `WhichTraces` debugging workflow
  and avoiding the slow unselected interaction-power remainder for
  target-local parity probes. This is a diagnostic/selected-trace composition
  mode, not a claim of full-model one-loop parity.
- Latest public-route decomposition, 2026-06-29: a bounded public probe of
  the selected-only, Matchete-DOF weighted four-slot `cHD` source at total
  Wilson-line orders 0/1/2 now matches the staged Matchete pole-through-finite
  checkpoint exactly, but it remains too slow as one aggregate public
  projection. The public API now has `wilson_line_total_orders` and
  `wilson_line_entry_labels` filters for generated Wilson-line plans, plus
  normalized per-entry through-finite source names. A new focused public
  order-one `cHD` regression uses this decomposition and passes in under ten
  seconds with the 30 GiB watchdog.
- Latest Matchete source deep dive, 2026-06-29: the implementation notes now
  contain a function-level audit of the active one-loop route from `LoadModel`
  and `Match` through `SetCurrentLagrangian`, `SetSubstitutions`,
  `PowerTypeSTr`, `GenericPropagatorExpansion`, `DeterminePowerInsertions`,
  `EvaluateSTr`, `WilsonExpand`, `LoopIntegrate`, `MatchReduce`,
  `GreensSimplify`, `EOMSimplify`, and `MapEffectiveCouplings`. The practical
  conclusion is that the selected four-slot Wilson-line `cHD` agreement proves
  the raw supertrace layer only; full Singlet `cHD` parity still has to compose
  Matchete's validation layers: off-shell Green-basis cleanup, on-shell
  systematic field redefinitions, and final target-basis Wilson-condition
  solving/truncation.
- Follow-up source audit refresh, 2026-06-29: re-read the concrete Matchete
  source files for the active one-loop path:
  `Package/Matching.m`, `Package/SuperTrace.m`,
  `Package/LoopIntegration.m`, `Package/EFTCounting.m`,
  `Package/Simplifications.m`, `Package/FieldRedef.m`,
  `Package/CouplingManipulations.m`, and
  `Package/DevTools/Validation.m`. The live implementation notes now record
  the source-level concepts behind `SetSubstitutions`,
  `DeterminePowerInsertions`, `EvaluateSTr`, `LoopIntegrate`,
  `InternalSimplify`, `ConstructOperatorIdentities`, `IdentitiesIBP`,
  `EOMSimplify`, `PerformSystematicFieldRedefs`, `ShiftLagrangian`,
  `VectorShift`, `SelectOperatorDevsAndDim`, and
  `MapEffectiveCouplingsInternal`. The next Singlet `cHD` target remains the
  earliest unchecked validation boundary: Matchete's class-local
  `InternalSimplify` operator identities and the subsequent vector-EOM
  `ShiftLagrangian` replay, not another final-coefficient patch.
- Latest Matchete deep-dive/log-management slice, 2026-06-29: the user asked
  to take a step back and deeply inspect every top-level Mathematica function
  in the one-loop route being reproduced. The long live implementation note
  was archived unchanged as
  `implementation_notes/one_shot_implementation_part_H.md`, and the refreshed
  `implementation_notes/one_shot_implementation.md` now keeps a compact active
  plan plus a source-derived function ledger from `LoadModel` and `Match`
  through `SetCurrentLagrangian`, `SetSubstitutions`, `LoopMatch`,
  `PowerTypeSTr`, `EvaluateSTr`, `WilsonExpand`, `LoopIntegrate`,
  `MatchReduce`, `InternalSimplify`, `IBPSimplify`,
  `PerformSystematicFieldRedefs`, `ShiftLagrangian`,
  `SaveValidationResults`, and `MapEffectiveCouplings`. The practical
  conclusion is unchanged but sharper: raw selected Wilson-line agreement is
  only the supertrace layer; the active Singlet `cHD` parity slice should next
  mirror Matchete's staged `InternalSimplify` and vector-EOM
  field-redefinition loop before broad public-route projection.
- Runtime follow-up, 2026-06-29: added the generic staged Abelian vector-EOM
  consumer `systematic_abelian_vector_eom_field_redefinition_delta(...)` plus
  a `Theory` method and package-root API export. This helper consumes
  already-exposed formal vector EOM terms through the same EFT-dimension and
  descending derivative-count loop as Matchete's
  `PerformSystematicFieldRedefs` / `ShiftLagrangian`, then delegates the
  actual current replacement to the existing Symbolica-pattern Abelian vector
  consumer. Focused validation passed for the scalar/vector EOM unit tests,
  public API tests, and mypy. The next slice should wire this staged consumer
  into the Singlet `cHD` Wilson-line/on-shell bridge and compare against the
  Matchete `after_shift_dim6_dev3` checkpoint.
- Follow-up bridge wiring, 2026-06-29: wired the staged Abelian vector-EOM
  consumer into both `Theory.match(..., loop_order=1)` and validation-fixture
  previews when `wilson_line_expose_scalar_eom_terms=True`. This preserves
  the ordinary EOM replacement contribution, but computes the Abelian vector
  field-redefinition companion through Matchete-style EFT-dimension and
  descending derivative-count staging, matching the `PerformSystematicFieldRedefs`
  / `ShiftLagrangian` boundary identified in
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`. Added tests
  distinguish commutator-only exposure, where formal vector-EOM replay stays
  inactive, from formal-EOM exposure, where the staged vector companion is
  applied. Focused integration checks, the two active Singlet `cHD` frontier
  tests, mypy, and `git diff --check` passed.
- Latest requested Matchete source refresh, 2026-06-29: re-read the active
  one-loop call path in Matchete's matching, supertrace, loop-integration,
  functional-derivative, EFT-counting, simplification, field-redefinition,
  coupling-mapping, tree-matching, and validation modules. The function-level
  ledger in `one_shot_implementation.md` remains the compact reference for
  the concepts behind each top-level function in the route. The key course
  correction is to keep judging the first Singlet `cHD` milestone at
  Matchete's validation boundary: raw selected `EvaluateSTr`/Wilson-line
  agreement, off-shell `GreensSimplify`, on-shell `EOMSimplify` with staged
  `InternalSimplify`/`ShiftLagrangian` EOM production and replay, and finally
  `MapEffectiveCouplings`-style target-basis solving.
- Follow-up implementation slice, 2026-06-29: added
  `OneLoopMatchOptions.wilson_line_total_orders_by_trace` so generated
  Wilson-line plans can be filtered with different total-order windows for
  different trace families. This reflects Matchete's
  `DeterminePowerInsertions` structure better than forcing one global order
  filter. The bounded public four-slot Singlet `cHD` checkpoint now uses the
  per-trace filter and passes. A two-trace aggregate public probe remained too
  slow under the watchdog and was stopped, so the next frontier is still a
  performance-aware Matchete-stage composition path rather than a monolithic
  full-source projection.
- Performance audit follow-up, 2026-06-29: Matchete's committed Singlet
  validation timing is about 5.1 seconds for `Match`, 0.31 seconds for
  `GreensSimplify`, 4.2 seconds for `EOMSimplify`, and 15.6 seconds for
  `MapEffectiveCouplings`; pychete's selected two-trace public composition is
  therefore definitely slower than Mathematica for a narrower job. Profiling
  shows the bottleneck is repeated termwise Wilson-line cleanup
  (`replace_multiple`, idenso delta/field-strength group passes, NCM
  scalarization, open-CD action, and projection prefilter label generation),
  not the final Wilson coefficient lookup. Added conservative no-op guards so
  idenso colour/delta/field-strength group passes are skipped when the
  relevant atoms are absent, and fixed the public Wilson-line `INTERNAL`
  source ordering so later EOM/projection stages consume the through-finite
  epsilon-expanded source, matching Matchete's `EvaluateSTr -> EpsExpand`
  boundary. The next performance redesign should move toward Matchete-style
  collected `EvaluateSTr` staging while retaining termwise diagnostics.
- Current continuation, 2026-06-29: following the user's instruction to use
  Matchete as algorithmic inspiration rather than copying Mathematica
  implementation details, pychete now preserves selected Wilson-line
  projection sources entrywise across the scalar-commutator/EOM exposure
  boundary. Internal minimal-subtraction routes project from normalized finite
  entries, while raw internal routes retain the existing normalized
  through-finite activation. The selected Singlet four-slot `cHD` public
  checkpoint now asserts staged projection and still reproduces the nonzero
  coefficient. The slice also wires result-wide idenso-backed field-derivative
  metric contraction before field-strength metric cleanup, which is required
  for the selected `cHD` source because tensor reduction emits explicit
  Lorentz metrics while the Warsaw target uses contracted derivative slots.
- Follow-up continuation, 2026-06-29: extended the staged Wilson-line
  projection-source preservation to hybrid validation previews. Direct
  fixture previews now expose selected Wilson-line entry sources plus an
  `interaction_power_type_remainder` source for hybrid results, and they apply
  the same scalar/EOM transformations and idenso-backed field-derivative
  metric cleanup as the public matcher. This keeps
  `one_loop_preview_gap_report(...)` aligned with the Matchete-style staged
  composition route instead of projecting only from a monolithic preview.
- Current continuation, 2026-06-29: added a public-route selected Singlet
  `cHD` regression for the two-trace Wilson-line composition. The test runs
  `Theory.match(...)` with the validated `hScalar-lScalar` orders `{0,2,4}`
  and `hScalar-lScalar-lVector-lScalar` orders `{0,1,2}`, staged projection
  sources, Matchete-style field-DOF weighting, and internal minimal
  subtraction, then compares the finite coefficient to the committed Matchete
  fixture after the existing convention bridge. This records the first
  selected public-route derivative-sector Wilson coefficient parity; full
  Singlet fixture parity still requires broadening beyond this selected
  finite `cHD` route.
- Same continuation, 2026-06-29: added the missing
  `wilson_line_total_orders_by_trace` plumbing to validation fixture preview
  and gap-report routes. Gap reports can now forward the same per-trace
  Wilson-line order windows used by the public selected `cHD` parity route,
  instead of forcing one global Wilson-line order bound for all selected trace
  families.
- Current continuation, 2026-06-29: promoted selected Singlet `cHD` parity
  into the validation gap-report route. The new slow regression runs the
  public matcher through `one_loop_preview_gap_report(...)` with selected-only
  Wilson-line traces, per-trace order windows, Matchete-style field-DOF
  weighting, internal through-finite evaluation, theory-owned
  `epsilon`/`mubar2`, scalar/EOM exposure, and staged projection sources.
  The remaining mismatch was only Matchete's compact
  `log(mubar2/M^2)` versus pychete's backend-natural
  `log(mubar2)-2 log(M)` representation, so an opt-in Symbolica-pattern
  comparison normalization `expand_loop_scale_logs_for_comparison` was added.
  This is a generic loop-scale comparison boundary, not a final-coefficient
  patch.
- Current continuation, 2026-06-29: the user asked for the current list of
  nonzero Wilson coefficients matching in pychete and the UV/effective theory
  names. The active converted-boundary fixture is
  `Singlet_Scalar_Extension -> SMEFT Warsaw`; the matching nonzero
  coefficients after this slice are `cHD`, `cHud`, `cle`, `cledq`, `clequ1`,
  `cqd1`, `cqd8`, `cqu1`, `cqu8`, and `cquqd1`. Selected public Wilson-line
  probes remain separately green for `cHW`, `cHB`, `cHWB`, and `cHD`.
- Current continuation, 2026-06-29: after re-sweeping with exact canonical
  Wilson-condition keys, the standalone converted `MapEffectiveCouplings`
  boundary should be tracked separately from selected public Wilson-line
  parity. The latest standalone converted-boundary matches for
  `Singlet_Scalar_Extension -> SMEFT Warsaw` are `cHd`, `cHe`, `cHu`,
  `cHud`, `cle`, `clequ1`, `cqd1`, `cqd8`, `cqu1`, `cqu8`, and `cquqd1`
  (`11/25`). The latest slice added generic additive target-term alignment
  and registered external-`Delta` canonicalization to recover `cHu`, `cHd`,
  and `cHe`. Selected public Wilson-line probes remain separately green for
  `cHW`, `cHB`, `cHWB`, and `cHD`.
- Current continuation, 2026-06-29: the latest slice added a generic SU(2)
  Higgs-current crossed-contraction basis map for paired singlet/triplet
  weak-doublet targets. The standalone converted-boundary matches for
  `Singlet_Scalar_Extension -> SMEFT Warsaw` are now `cHd`, `cHe`, `cHl1`,
  `cHl3`, `cHq1`, `cHq3`, `cHu`, `cHud`, `cle`, `clequ1`, `cqd1`, `cqd8`,
  `cqu1`, `cqu8`, and `cquqd1` (`15/25`). Remaining converted-boundary gaps
  are zero `cHB/cHW/cHWB`, solve errors for `cH/cHBox/cHD`, and differing
  `cdH/ceH/cledq/cuH`; selected public Wilson-line probes remain separately
  green for `cHW`, `cHB`, `cHWB`, and `cHD`.
- Current continuation, 2026-06-29: the latest slice gates
  hermitian-conjugate target-alignment aliases so they are used only when a
  direct target-aligned source occurrence is absent. This fixes the `cledq`
  factor-of-two double count while preserving the `cHud` h.c.-only recovery,
  and it also makes the standalone converted `cHD` map exact. The standalone
  converted-boundary matches for `Singlet_Scalar_Extension -> SMEFT Warsaw`
  are now `cHD`, `cHd`, `cHe`, `cHl1`, `cHl3`, `cHq1`, `cHq3`, `cHu`,
  `cHud`, `cle`, `cledq`, `clequ1`, `cqd1`, `cqd8`, `cqu1`, `cqu8`, and
  `cquqd1` (`17/25`). Remaining converted-boundary gaps are zero
  `cHB/cHW/cHWB`, solve error `cHBox`, and differing `cH/cdH/ceH/cuH`.
- Current continuation, 2026-06-29: the latest slice adds Symbolica-backed
  tensor canonicalization and scalar-normalization splitting for unindexed
  field-strength target operators, plus idenso barred-index normalization
  `Bar(Index(label, rep)) -> Index(label, Bar(rep))`. This recovers the
  standalone converted field-strength coefficients `cHW`, `cHB`, and `cHWB`.
  The standalone converted-boundary matches for
  `Singlet_Scalar_Extension -> SMEFT Warsaw` are now `cHB`, `cHD`, `cHW`,
  `cHWB`, `cHd`, `cHe`, `cHl1`, `cHl3`, `cHq1`, `cHq3`, `cHu`, `cHud`,
  `cle`, `cledq`, `clequ1`, `cqd1`, `cqd8`, `cqu1`, `cqu8`, and `cquqd1`
  (`20/25`). Remaining converted-boundary gaps are solve error `cHBox` and
  differing `cH/cdH/ceH/cuH`.
- Current continuation, 2026-06-29: the user asked again for the current
  nonzero Wilson coefficients matching in pychete and the UV/effective theory
  names. The active converted-boundary fixture remains
  `Singlet_Scalar_Extension -> SMEFT Warsaw`. This slice used a new Matchete
  `cHBox` EOM debug dump to identify that Matchete maps `Q_HBox` through an
  EOM-reduced cross-derivative target representative. pychete now stores
  effective-projection operator metadata for Wilson coefficients and the SMEFT
  Warsaw basis attaches that representative for `cHBox`. The standalone
  converted-boundary matches are now `cHB`, `cHD`, `cHBox`, `cHW`, `cHWB`,
  `cHd`, `cHe`, `cHl1`, `cHl3`, `cHq1`, `cHq3`, `cHu`, `cHud`, `cle`,
  `cledq`, `clequ1`, `cqd1`, `cqd8`, `cqu1`, `cqu8`, and `cquqd1` (`21/25`).
  Remaining converted-boundary gaps are differing `cH/cdH/ceH/cuH`.
- Current continuation, 2026-06-29: the `Q_HBox`-sensitive
  `cH/cdH/ceH/cuH` gaps were traced to Matchete's post-map
  `ShiftRenCouplingsInMC` step. pychete now applies a tightly gated on-shell
  SMEFT effective-coupling bridge that maps the `cHBox` EOM image into the
  Higgs/Yukawa-Higgs Wilsons and EFT-truncates the corresponding
  renormalizable `lambda/Yd/Ye/Yu` shifts using `series_eft`. The standalone
  converted Matchete on-shell effective-coupling boundary for
  `Singlet_Scalar_Extension -> SMEFT Warsaw` now matches all 25 nonzero Wilson
  coefficients: `cH`, `cHB`, `cHBox`, `cHD`, `cHW`, `cHWB`, `cHd`, `cHe`,
  `cHl1`, `cHl3`, `cHq1`, `cHq3`, `cHu`, `cHud`, `cdH`, `ceH`, `cle`,
  `cledq`, `clequ1`, `cqd1`, `cqd8`, `cqu1`, `cqu8`, `cquqd1`, and `cuH`.
  This is converted-boundary parity; the next frontier is moving the same
  coverage upstream into the public Wilson-line one-loop generation path.
- Current continuation, 2026-06-29: archived the oversized live
  `one_shot_implementation.md` to `one_shot_implementation_part_I.md` and
  rewrote the live implementation note as a compact current-status document.
  A first post-`36647fc` probe tried to map selected two-trace public
  Wilson-line sources through the full effective-coupling solve, but it was
  stopped under the watchdog after several minutes because the global solve
  was too coarse. The next planned slice is therefore a target-local public
  effective-coupling mapping boundary for `Theory.match(...)` and validation
  gap reports, so selected Wilson-line sources can be compared without
  all-Wilson/global solves.
- Current continuation, 2026-06-29: implemented that target-local public
  effective-coupling mapping boundary. `MatchingResult` now has
  `with_mapped_effective_couplings(...)`, and `Theory.match(..., loop_order=1)`
  plus `one_loop_preview_gap_report(...)` accept the opt-in flags
  `matching_condition_effective_coupling_map` and
  `matching_condition_effective_coupling_allow_incomplete_target`. Defaults
  still use direct coefficient projection. Focused tests passed for the new
  structured result method, public gap-report forwarding, the existing
  converted effective-map group, targeted mypy, and the selected public
  Singlet `cHW/cHB/cHWB` and `cHD` regressions.
