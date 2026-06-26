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
- When running tests or exploratory workloads that can exceed machine memory,
  use the 30 GiB watchdog wrapper rather than invoking them directly.
