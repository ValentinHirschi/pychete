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
- Extend paired-derivative momentum lowering beyond scalar contracted pairs
  into open derivative slots, vector/gauge Lorentz structures, and fuller
  propagator expansion.
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

- Preserved the original large log as
  `implementation_notes/one_shot_implementation_part_A.md`.
- Replaced `implementation_notes/one_shot_implementation.md` with this compact
  working summary.
- Current uncommitted code slice keeps normalized `[unnormalized]` raw
  supertrace aliases inspectable on `MatchingResult` while excluding them from
  fixture gap-report supertrace coverage counts.
- Verification in this slice:
  - focused alias-filter tests passed: 2 passed in 1.12s;
  - `mypy` passed with no issues in 30 source files;
  - `git diff --check` passed;
  - default raw/vakint and internal-MS four-model gap-report coverage tests
    passed: 2 passed in 101.16s.
