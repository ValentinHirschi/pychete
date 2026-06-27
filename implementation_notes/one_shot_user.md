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
