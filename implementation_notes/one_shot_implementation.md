# One-Shot Port Implementation Notes

This is the active, compact implementation log for the `one-shot-port` branch.
The full historical log for the first large phase is preserved unchanged in
`implementation_notes/one_shot_implementation_part_A.md`.

When this file again grows too large to use comfortably as live context, repeat
the rollover procedure: move the current file to the next part file
(`one_shot_implementation_part_B.md`, then `part_C`, and so on), keep that part
unchanged, and rewrite this file as a compact current summary.

## Approved Goal And Guidelines

Fully implement pychete's one-shot Matchete-style one-loop matching port. The
target is a Pythonic pychete one-loop EFT matching implementation that can
reproduce the mappable Matchete validation targets, especially the default
SMEFT-oriented UV matching models: `VLF_toy_model`,
`Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.

Core rules:

- Use Symbolica as the canonical symbolic engine. Periodically inspect the
  Symbolica Python stubs and prefer native APIs such as patterns, matches,
  replacement rules, `replace_multiple`, `series`, `coefficient`, `collect`,
  `derivative`, transformer pipelines, polynomial tools, and evaluator APIs.
- Do not use or import `sympy` or `scipy`.
- Use idenso for gamma, colour, metric, and abstract-index algebra whenever
  possible.
- Use spenso for tensor-network and CG/tensor contraction work when needed.
- Use pychete's own analytic backend for one-loop vacuum-integral evaluation
  after tensor reduction, including single-scale, zero-mass, and mixed-mass
  cases. Use vakint for topology-independent tensor reduction and as an
  optional backend/cross-check for supported single-scale massive analytic
  evaluations.
- If idenso, spenso, vakint, or GammaLoop require local fixes, patch the local
  dependency sources through committed patch files and installer logic; do not
  vendor dependency source changes into pychete.
- Normal pytest and runtime pychete must remain completely Mathematica- and
  Matchete-independent. Optional top-level `scripts/` Wolfram conversion
  wrappers may load the read-only Matchete checkout for users who have
  Mathematica, but committed fixtures are the canonical test/runtime inputs.
- Keep public user-facing APIs exported through `pychete.api` and package-root
  `pychete`, with useful docstrings and Jupyter `_repr_html_` /
  `_repr_latex_` methods for public result/metadata objects.
- Commit and push only coherent green milestones to `origin/one-shot-port`.

## Approved Plan

1. Maintain the Mathematica-independent fixture-generation and fixture-loading
   path for Matchete references.
2. Extend theory/model metadata to cover Matchete-style matching needs:
   gauge/global groups, representations, charges, CG tensors, scalar/fermion/
   vector fields, chiral fermions, ghosts, Goldstones, background fields,
   mass metadata, coupling metadata, SMEFT basis data, and Symbolica symbol
   tags/data.
3. Build and harden backend adapters for idenso, spenso, vakint, and pychete's
   analytic vacuum-integral backend.
4. Implement the one-loop matching pipeline: free Lagrangians, functional
   derivatives/Feynman rules, fluctuation operators, heavy/light DoF
   classification, propagator expansion, supertrace generation, loop momentum
   and tensor reduction, vacuum-integral evaluation, EFT truncation,
   simplification, EOM/on-shell reduction, and matching-condition projection.
5. Validate against committed Matchete-independent fixtures using canonical
   equality first and Symbolica evaluator numeric probes where canonical forms
   legitimately differ.
6. Port all mappable Matchete validation areas; document Matchete-internal or
   Mathematica-specific exclusions explicitly.

## Summary Of Implementation Status In Part A

Part A established the current pychete one-shot matching scaffold and pushed a
series of green milestones on `one-shot-port`.

Implemented validation infrastructure:

- Added `ValidationFixture`, `PycheteState`, committed fixture loaders, and
  structured `MatchingResult` reconstruction from JSON expression references.
- Added committed model and matching fixtures for the four default Matchete
  matching targets.
- Added optional helper and top-level `scripts/` conversion wrappers for users
  with Mathematica/Matchete. These are convenience tools only; normal pytest
  never invokes Mathematica.
- Added fixture gap reports that compare candidate and reference supertraces,
  matching conditions, Wilson-condition subsets, per-order supertrace coverage,
  and JSON report output.
- Added Symbolica evaluator-based numeric probes for supertraces and matching
  conditions, including selectable presets such as `canonical_different`,
  `wilson`, and `canonical_different_wilson`.

Implemented public/API structure:

- Promoted `MatchingResult`, matching options, validation report objects,
  backend helpers, and relevant metadata through `pychete.api` and package root.
- Added Jupyter-friendly repr methods for important result/report objects.
- Kept implementation modules split by domain while keeping public API
  discoverable.

Implemented model/theory metadata:

- Added field chirality, mass-kind metadata, representation/group metadata,
  coupling metadata, coupling symmetries, stored Symbolica symbol data, and
  custom Symbolica print/serialization discipline.
- Added support for loaded-model state fixtures and richer Matchete-derived
  model metadata, including stored sparse CG tensor components where supported.
- Kept the direct Python Mathematica loader explicitly limited to simple
  declarative/saved-result syntax; complex model conversion is routed through
  optional Wolfram/Matchete scripts and committed pychete-owned fixtures.

Implemented backend and algebra groundwork:

- Added `pychete.backends.vakint` delegation helpers and single-scale vakint
  cross-check support.
- Added pychete's analytic one-loop vacuum-integral backend for covered scalar
  zero/mixed/single-scale and finite two-mass loop-function cases.
- Added spenso metadata bridge pieces for representations, tensor structures,
  tensor indices, stored CG components, and expression-wide CG replacement.
- Added idenso/Dirac bridge pieces for covered gamma/projector simplifications
  and endpoint-aware NCM lowering.

Implemented one-loop matching scaffold:

- Added `Theory.match(..., loop_order=1)` plumbing and `OneLoopMatchOptions`.
- Added fluctuation-basis, fluctuation-operator, block-trace, supertrace-plan,
  and interaction-power preview machinery.
- Added vakint/raw, internal, and internal minimal-subtraction preview stages.
- Added named finite/MS staging so internal-MS named traces expose finite parts,
  not pole-containing raw expressions.
- Added loop-normalization support, including normalized primary named
  supertraces and `[unnormalized]` aliases for direct result inspection.
- Added validation filtering so these `[unnormalized]` aliases do not inflate
  fixture gap-report coverage counts.

Latest verified baseline before this compact rollover:

- Full test suite passed with `272 passed, 1 skipped`; the skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `mypy` passed.
- Current branch is `one-shot-port`; latest pushed milestone before the
  rollover was `fcc3f52 Normalize named one-loop supertraces`.

## Current Remaining Work

- Continue using the four default Matchete fixtures as acceptance targets.
  Final Matchete equivalence is still incomplete.
- Extend the loaded-model-state exporter/converter for richer vector/zero-mode
  metadata and complicated Matchete models outside the direct loader subset.
- Extend momentum lowering beyond scalar contracted pairs and the current open
  derivative `LoopMomentum(index)` numerators plus metric/delta loop-momentum
  contractions into vector/gauge Lorentz structures, higher-rank tensor
  numerator reduction, and fuller propagator expansion.
- Extend `FluctuationBasis` metadata into backend-evaluated vector Lorentz
  traces, real/complex coefficient placement, and SMEFT basis classifications.
- Extend spenso/idenso lowering for remaining tensor contractions, generators,
  invariant tensors, gamma/colour/index algebra, and field-endpoint Dirac
  chains.
- Turn the current interaction-power internal-MS preview into a fully physical
  one-loop matching result with phase/sign/order conventions, tensor
  reductions, scheme-specific renormalization, and Matchete fixture validation.
- Extend the analytic vacuum-integral backend to more loop-function behavior:
  higher numerator structures, near-degenerate expansions, and real fixture gap
  simplifications.
- Add full SM/CG Lagrangian expression handling through generated fixtures or
  carefully bounded loader support.
- Expand converter/fixture coverage beyond the default matching targets.
- Apply evaluator-probe comparison plumbing to concrete remaining Matchete
  fixture gaps once stable deterministic probe plans are identified.

## Current Slice After Rollover

- Restored exact indexed fluctuation-mode support in the Euler-Lagrange
  differential matrix. `derive_eom(...)` now accepts an exact `Field` or
  `Bar(Field)` expression and uses a Symbolica pattern that fixes the field
  label, type, and concrete index list while matching only the derivative-slot
  wildcard. This keeps indexed modes such as the E_VLL `l[i,a]` and `H[i]`
  entries from collapsing to the label-only `definition.expr()` target.
- Updated `_fluctuation_differential_entry(...)` to derive the EOM from the
  exact row fluctuation mode rather than from the field definition. The
  algebraic Hessian already had these indexed heavy-light Yukawa entries; this
  makes the momentum/differential interaction matrix expose them too.
- Added a regression test with an indexed light fermion and indexed complex
  scalar coupled to a heavy fermion. It checks both `differential_entry` and
  `interaction_entry` for the light-to-heavy and conjugate light-to-heavy NCM
  Yukawa directions.
- E_VLL now produces nonzero `hFermion-lFermion` and `hFermion-lScalar`
  interaction-power numerators from the restored light-to-heavy blocks.
- Gap-report expectations were updated because several previously accepted
  common traces were accepted only as zero/zero matches. With exact indexed
  light-side interactions retained, those traces are now honest
  canonical-different gaps:
  - E_VLL raw/internal-MS canonical-equal common traces are now only
    `hFermion-lFermion-lFermion`.
  - S1S3LQs raw canonical-equal common traces are now empty.
- S1S3LQs remains covered by the raw order-three fixture gap report. Its
  internal-minimal-subtraction order-three report became too expensive after
  exact indexed light-side interactions were retained, so the internal-MS smoke
  coverage currently tracks VLF, Singlet, and E_VLL until stronger expression
  filtering/reduction is implemented.
- Verification in this slice:
  - focused indexed/NCM fluctuation tests passed;
  - default raw order-three gap-report coverage passed;
  - narrowed internal-MS gap-report coverage for VLF, Singlet, and E_VLL
    passed;
  - selected numeric-probe and validation slice passed: 25 passed in 107.75s;
  - broader functional/fluctuation tests passed: 47 passed in 1.04s;
  - `mypy` passed with no issues in 30 source files;
  - `git diff --check` passed;
  - full pytest suite passed: 273 passed, 1 skipped in 276.10s. The skip is
    the existing GammaLoop API import check because GammaLoop was not requested
    in the current dependency manifest.

## Current Slice: NCM EFT Marker Extraction

- Found a direct `series_eft(...)` bug exposed by the newly nonzero E_VLL
  fermion traces: EFT weights inserted into fields inside `NCM(...)` operands
  remained trapped as `NCM(eft_order_parameter^n * field, ...)`, so
  Symbolica's top-level `coefficient_list(EFTExpansionParameter)` could not
  see those weights.
- Added an NCM-specific Symbolica replacement pass in `src/pychete/eft.py`.
  For bounded NCM arities it uses each operand's native
  `coefficient_list(EFTExpansionParameter)`, expands the multilinear NCM
  product over operand marker terms, and pulls the total marker power outside
  as a commutative prefactor before the existing EFT coefficient selection.
- Added unit coverage showing that `series_eft(...)` now truncates and selects
  direct noncommutative fermion chains correctly and leaves no
  `eft_order_parameter` residue in the retained expression.
- Added an integration assertion that the VLF-style
  `hFermion-lFermion` numerator no longer leaks the EFT marker while still
  simplifying projector words through idenso.
- Verified by direct fixture inspection that the E_VLL affected traces no
  longer contain `eft_order_parameter`. S1S3LQs still has marker residue inside
  derivative-wrapped external constructs such as `der(..., NCM, ...,
  external_Transp(...))`; this is a separate external-function/linearity
  lowering gap for a later slice.
- Verification in this slice so far:
  - EFT unit tests and VLF projector numerator test passed: 6 passed in 0.26s;
  - default raw order-three gap-report coverage passed: 1 passed in 42.02s;
  - narrowed internal-MS gap-report coverage passed: 1 passed in 23.37s;
  - `mypy` passed with no issues in 30 source files;
  - full fluctuation-operator integration file passed: 39 passed in 1.01s;
  - selected numeric-probe and validation slice passed: 22 passed in 65.30s;
  - `git diff --check` passed;
  - full pytest suite passed: 274 passed, 1 skipped in 279.84s. The skip is
    the existing GammaLoop API import check because GammaLoop was not requested
    in the current dependency manifest.

## Current Slice: Linear External Wrapper Extraction

- Addressed the S1S3LQs follow-up from the NCM EFT marker slice. The raw
  order-three traces `hScalar-lFermion-lScalar` and
  `hScalar-lScalar-lFermion` no longer contain formal `der(...)` wrappers or
  leaked `eft_order_parameter` factors inside `external_Transp(...)`.
- Added structural metadata for known linear external helper functions.
  `Theory.define_external("Transp")` now attaches the
  `external_linear_function` Symbolica tag during normal creation and fixture
  restoration. This keeps the behavior tied to symbol tags/data rather than to
  ad hoc parser-side string checks in the matching pipeline.
- Centralized discovery of tagged linear external function heads in the
  internal `src/pychete/linear_external.py` helper so functional variation and
  EFT marker extraction share the same Symbolica tag semantics.
- Extended functional variation and covariant-derivative variation lowering to
  discover tagged linear external function heads with
  `Expression.get_all_symbols()`, then build exact-head Symbolica
  `Replacement` rules. The replacement uses native coefficient extraction in
  the temporary variation parameter before the existing NCM multilinear
  extraction runs.
- Extended `series_eft(...)` so EFT weights hidden inside tagged linear
  external wrappers are first expanded as external multilinear terms, then
  passed through the existing NCM marker extractor. This prevents Symbolica's
  top-level EFT coefficient selection from missing weights inside constructs
  such as `NCM(Transp(eft^3 field), ...)`.
- Added focused tests for:
  - functional derivative linearization of `Transp(field)` inside NCM chains;
  - covariant derivative linearization of `Transp(field)`;
  - EFT truncation of NCM chains containing `Transp(field)`;
  - S1S3LQs fixture preview traces that previously leaked markers.
- Updated `AGENTS.md` to state that known linear external helper functions
  must be tagged and linearized before variation, EFT marker extraction, or
  NCM coefficient selection.
- Verification in this slice so far:
  - functional and EFT unit tests passed: 16 passed in 0.04s;
  - default model order-three one-loop preview fixture test passed:
    1 passed in 43.14s;
  - `mypy` passed with no issues in 31 source files;
  - fluctuation-operator integration plus raw/internal-MS gap-report smoke
    coverage passed: 41 passed in 66.35s;
  - full pytest suite passed: 277 passed, 1 skipped in 304.04s. The skip is
    the existing GammaLoop API import check because GammaLoop was not requested
    in the current dependency manifest.

## Current Slice: Open Derivative Momentum Numerators

- Added a central `pychete::LoopMomentum(index)` Symbolica head, exposed through
  `s.LoopMomentum`, with custom print support in Symbolica, LaTeX,
  Mathematica, Sympy, and Typst display modes.
- Extended `DifferentialOperator(...)` lowering so contracted adjacent
  derivative pairs still lower directly to `LoopMomentumSquared`, while open
  derivative slots now lower to explicit products of `I*LoopMomentum(index)`.
  This turns fermion kinetic entries such as
  `-I Gamma(mu) DifferentialOperator({mu})` into the explicit numerator
  `Gamma(mu) LoopMomentum(mu)` instead of leaving an opaque differential
  operator in momentum-space entries.
- Added focused tests for:
  - `LoopMomentum(index)` printing across display modes;
  - fermion momentum entries lowering open first derivatives;
  - two distinct open derivative slots lowering to a rank-two loop-momentum
    numerator.
- Updated `AGENTS.md` to preserve the convention that open Lorentz derivative
  slots become explicit `LoopMomentum(index)` factors and tensor numerator
  reduction should be delegated to native backends where applicable.
- Verification in this slice so far:
  - targeted print/open-momentum tests passed: 3 passed in 0.14s;
  - full fluctuation-operator integration file passed: 40 passed in 1.27s;
  - pretty-printing unit tests passed: 10 passed in 0.29s;
  - `mypy` passed with no issues in 31 source files;
  - default preview and raw/internal-MS validation smoke checks passed:
    3 passed in 121.33s;
  - full pytest suite passed: 278 passed, 1 skipped in 293.51s. The skip is
    the existing GammaLoop API import check because GammaLoop was not requested
    in the current dependency manifest.

## Current Slice: Loop-Momentum Metric Contractions

- Added a pychete-specific idenso bridge for metric and Kronecker-delta
  contractions of explicit loop-momentum numerator factors. The new
  `simplify_pychete_loop_momentum_metrics(...)` adapter uses Symbolica
  `Replacement` rules to contract:
  - `Metric(mu, nu) * LoopMomentum(mu) -> LoopMomentum(nu)`;
  - `Delta(mu, nu) * LoopMomentum(mu) -> LoopMomentum(nu)`;
  - `LoopMomentum(mu) * LoopMomentum(mu) -> LoopMomentumSquared`.
- Integrated the bridge into `simplify_index_algebra(..., metrics=True)` before
  and after the native idenso metric simplifier. This keeps the pychete
  `LoopMomentum(index)` head in the public expression representation while
  still routing index-algebra cleanup through the idenso backend adapter.
- Added focused backend tests for direct loop-momentum metric/delta contraction
  and for the full `simplify_index_algebra` path.
- Added an integration test through `SupertraceBlockTrace.simplify_index_algebra`
  showing generated kernels with `Metric(mu, nu) * LoopMomentum(mu) *
  LoopMomentum(nu)` reduce to `LoopMomentumSquared`.
- Updated `AGENTS.md` to record the convention that pychete loop-momentum
  metric contractions must go through the idenso adapter before vacuum-integral
  evaluation.
- Verification in this slice so far:
  - targeted idenso loop-momentum contraction tests passed: 3 passed in 0.14s;
  - `mypy` passed with no issues in 31 source files;
  - full idenso backend plus fluctuation-operator integration files passed:
    53 passed in 1.26s;
  - default preview and raw/internal-MS validation smoke checks passed:
    3 passed in 123.31s;
  - full pytest suite passed: 281 passed, 1 skipped in 290.74s. The skip is
    the existing GammaLoop API import check because GammaLoop was not requested
    in the current dependency manifest.

## Current Slice: Vakint Loop-Momentum Numerator Lowering

- Confirmed from vakint's Python stub and Rust examples that native tensor
  numerators use `vakint::k(loop_id, index)` and scalar loop-momentum products
  use `vakint::k(loop_id, scalar_index)^2`, while topology propagators keep
  using `vakint::k(loop_id)`.
- Added central `s.LoopMomentumIndexWildcard` for reusable Symbolica pattern
  matching of pychete loop-momentum heads.
- Extended `pychete.backends.vakint.loop_momentum(...)` so it can build both
  topology momenta and indexed tensor-numerator components, and added
  `loop_momentum_squared(...)` for vakint's scalar-product convention.
- Added `lower_pychete_loop_momentum_numerators(...)`, implemented with
  Symbolica `Replacement` / `replace_multiple`, to map:
  - `LoopMomentum(index) -> vakint::k(loop_id, index)`;
  - `LoopMomentumSquared -> vakint::k(loop_id, scalar_index)^2`.
- Integrated this lowering at the vakint handoff boundary:
  `one_loop_vacuum_integral(...)`, `to_canonical(...)`, `tensor_reduce(...)`,
  `evaluate_integral(...)`, and `evaluate(...)` now normalize pychete momentum
  heads before native engine calls.
- Updated `AGENTS.md` to preserve this vakint-lowering convention for future
  work.
- Verification in this slice so far:
  - focused vakint backend tests passed: 20 passed in 0.06s;
  - `mypy` passed with no issues in 31 source files;
  - backend/fluctuation regression coverage passed: 94 passed in 5.08s;
  - native vakint smoke check accepted a lowered `LoopMomentum(mu) *
    LoopMomentum(nu)` numerator and tensor-reduced it to a metric times
    scalar loop momentum;
  - full pytest suite passed after preserving expression shape in the lowering
    helper: 285 passed, 1 skipped in 293.06s. The skip is the existing
    GammaLoop API import check because GammaLoop was not requested in the
    current dependency manifest.

## Current Slice: Package Logging And Progress Output

- Added `src/pychete/logging.py`, a package-level Python `logging` wrapper with
  `get_logger(...)`, `configure_logging(...)`, `disable_logging()`, and a
  `progress(...)` context manager for timed start/done/failure messages.
- Exported `configure_logging`, `disable_logging`, and `get_logger` through
  `pychete.api` and the package root. Notebook users can now call
  `pychete.configure_logging()` before heavier matching/validation workflows to
  see concise progress messages.
- Instrumented high-level one-loop stages:
  - fluctuation-basis discovery and fluctuation-operator construction;
  - one-loop setup generation with fluctuation-mode and supertrace-kernel
    counts;
  - `match_one_loop(...)` backend/normalization selection and result counts;
  - optional tensor-network evaluation;
  - interaction/power-type vakint integral assembly, native tensor reduction,
    and internal scalar vacuum-integral evaluation;
  - validation fixture preview generation and gap-report summaries.
- Added backend logs for direct native vakint engine construction and direct
  internal analytic vacuum-integral evaluation.
- Updated `README.md` and `AGENTS.md` to document the logging convention and to
  forbid ad hoc library `print(...)` progress output.
- Verification in this slice so far:
  - logging and public API tests passed: 9 passed in 0.08s;
  - `mypy` passed with no issues in 32 source files;
  - logging-enabled one-loop preview smoke showed concise fixture/backend
    selection, timed setup, fluctuation-mode/kernel counts, and preview
    supertrace count;
  - affected backend/matching/validation tests passed: 104 passed in 24.65s;
  - `git diff --check` passed;
  - full pytest suite passed: 289 passed, 1 skipped in 314.76s. The skip is
    the existing GammaLoop API import check because GammaLoop was not requested
    in the current dependency manifest.

## Planning Note For Future Slices

- Full pytest now takes about five minutes because of the validation fixtures.
  Future implementation slices should batch more related one-shot matching
  features before paying the full-suite validation cost, while still using
  targeted tests and focused smoke checks during the slice.

## Current Slice: Scalar Loop-Momentum Numerator Absorption

- Added general vakint topology propagator collection in
  `pychete.backends.vakint.collect_identical_propagators(...)`. It rewrites
  duplicate `vakint::prop(...)` factors with identical edge/momentum/mass
  signatures into one propagator whose power is the sum of all matching powers.
  Powered propagator factors contribute multiplicatively to that sum, so this
  works for arbitrary integer prop powers rather than only square numerator
  cases.
- Integrated propagator collection into `vakint.topology(...)`, so standard
  topology construction now canonicalizes duplicate signatures at creation.
- Added
  `pychete.backends.vacuum_integrals.absorb_vakint_scalar_loop_momentum_numerators(...)`.
  It expands the expression enough to expose terms of the form
  `vakint::k(loop_id, index)^(2*n) * vakint::topo(...)`, replaces those scalar
  loop-momentum numerator powers by negative massless-propagator powers, and
  then runs the general identical-propagator collection step.
- `evaluate_one_loop_vakint_expression(...)` now calls this absorber before
  validating/evaluating topologies. This lets pychete's internal analytic
  integral backend consume scalar loop-momentum powers left by native vakint
  tensor reduction instead of leaving residual `vakint::k(...)` numerators in
  evaluated results.
- Exported the absorber through `pychete.api` and package-root `pychete`.
- Added focused tests for:
  - duplicate vakint propagator signature collection;
  - powered propagator factor collection;
  - zero total power cancellation;
  - direct vakint adapter calls collecting duplicate propagators before
    handing expressions to native engines;
  - scalar `vakint::k(...)^2` absorption into negative massless powers;
  - multiple scalar numerator factors;
  - the one-loop setup internal-integral path with a fake tensor reducer that
    returns a scalar native vakint numerator.
- Updated `AGENTS.md` and `one_shot_user.md` with the propagator-collection
  convention and the user's instruction to batch larger future slices before
  full-suite validation.
- Verification in this slice so far:
  - focused vakint/vacuum-integral backend tests passed: 58 passed in 3.90s;
  - targeted one-loop setup scalar numerator absorption regression passed:
    2 passed in 0.07s;
  - combined focused backend plus integration regression passed twice, most
    recently after direct vakint adapter collection was added: 60 passed in
    4.32s;
  - `mypy` passed with no issues in 32 source files;
  - full fluctuation-operator integration plus targeted internal-MS/public API
    validation checks passed: 44 passed in 13.19s;
  - default one-loop target raw/internal-MS gap-report tests passed:
    2 passed in 73.55s;
  - `git diff --check` passed;
  - full pytest passed: 296 passed, 1 skipped in 283.44s. The skipped test was
    the GammaLoop API import check because the dependency manifest indicates
    GammaLoop was not requested for this local dependency build.

## Current Slice: Bounded NCM Power Expansion

- Found another generated-fermion-trace artifact while inspecting VLF-style
  traces: open noncommutative chains such as `NCM(Bar(psi), PR)^2` and
  `NCM(PL, psi)^2` survived as commutative powers in the interaction-power
  numerator. This is not a valid final representation for fermion-chain
  algebra and blocks later idenso/Dirac simplification from seeing the explicit
  noncommutative operand order.
- Added `pychete.backends.idenso.expand_pychete_ncm_powers(...)`. It is a
  bounded Symbolica replacement-rule pass over `NCM(...)^n` for positive
  integer powers with unambiguous repeated order. Symbolic, non-positive, or
  oversized powers are left unchanged.
- Integrated this pass at the start of
  `simplify_pychete_dirac_algebra(...)`, before projector and Dirac-product
  lowering to native idenso. This keeps generated trace simplification in the
  existing idenso adapter instead of adding ad hoc matching-pipeline logic.
- Deliberately did not attempt to recover ordering for arbitrary products of
  distinct `NCM` factors after Symbolica has represented them as commutative
  multiplication. That remains a broader representation/design issue; this
  slice only handles powers where the repeated order is clear.
- Updated `AGENTS.md` with the new convention so future fermion-trace work uses
  the central idenso adapter and does not leave `NCM(...)^n` artifacts in
  numerators.
- Added unit coverage for direct NCM-power expansion, symbolic-power fallback,
  and the full `simplify_pychete_dirac_algebra(...)` path.
- Extended the VLF-style projector integration test to assert that generated
  `hFermion-lScalar` EFT numerators contain explicit `NCM` chains rather than
  the previous `NCM(...)^2` powers.
- Verification in this slice so far:
  - idenso backend tests passed: 13 passed in 0.10s;
  - focused VLF/projector and mixed-NCM tests passed with the idenso backend
    file: 15 passed in 0.31s;
  - broader fluctuation-operator plus default raw/internal-MS fixture gap-report
    coverage passed: 44 passed in 78.11s;
  - `mypy` passed with no issues in 32 source files;
  - repeated targeted idenso/fluctuation/default gap-report gate passed:
    57 passed in 75.95s;
  - `git diff --check` passed;
  - full pytest passed: 297 passed, 1 skipped in 322.15s. The skipped test was
    the GammaLoop API import check because the dependency manifest indicates
    GammaLoop was not requested for this local dependency build.
