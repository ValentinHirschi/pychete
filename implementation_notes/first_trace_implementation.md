# First Trace Implementation Log

## 2026-07-01 Start

- Began implementation of VLF one-loop functional matching.
- Confirmed the working tree was clean before edits.
- Created the requested prompt trail and implementation log.
- Immediate implementation order:
  1. Re-inspect pychete's current symbol, functional, spinor, matching, theory, and API modules.
  2. Add central loop/matching symbols and public exports.
  3. Add immutable one-loop matching context scaffolding with VLF trace inventory validation.
  4. Add ordered functional-operator helpers, propagator/log expansion surfaces, Wilson-line derivative helpers, and loop-function placeholders.
  5. Wire `Theory.match(..., loop_order=1)` and low-level trace APIs.
  6. Add focused tests and run the managed pytest suite.

## Symbol and Functional Operator Foundation

- Added central builtins for loop matching:
  - `FuncNCM`, `OpenCD`, `Prop`, `LoopMom`, `LFFull`, `LF`
  - `WilsonLine`, `WilsonTerm`, `XTerm`, `MTerm`, `GaugeCTerm`
  - `PowerTypeSTr`, `LogTypeSTr`
  - `Transp`, `GammaCC`, `CConj`
  - `DimRegEpsilon`, `MuBar2`, `hbar`
- Added printing coverage for the new builtins in all Symbolica print modes.
- Added functional helpers:
  - `open_cd_expr(...)`
  - `func_ncm_expr(...)`
  - `functional_derivative_operator(...)`
  - `second_functional_derivative_operator(...)`
  - `strip_free_lagrangian(...)`

## Matching Context and VLF Loop Layer

- Added `src/pychete/one_loop.py` with immutable one-loop dataclasses:
  - `FieldDegreeOfFreedom`
  - `XTermMetadata`
  - `FluctuationOperator`
  - `FunctionalTrace`
  - `MatchingContext`
- Added Matchete-style field class and trace kind enums:
  - `FieldDofClass`
  - `FunctionalTraceKind`
- Added `matching_context(...)` to collect field dofs, heavy masses, gauge couplings, fluctuation operators, log traces, and power traces.
- Added VLF trace inventory matching the Matchete `ListPowerTypeTraces[6]` result.
- Added VLF power/log trace evaluators and `covariant_loop(...)`.
- Added `evaluate_loop_functions(...)`; after the loop-function convention clarification, VLF single-mass loop functions are already written as explicit logs following Matchete's default output.
- Wired:
  - `Theory.match(..., loop_order=0)` unchanged.
  - `Theory.match(..., loop_order=1)` to tree plus one-loop.
  - `Theory.match(..., loop_order=(1,))` to one-loop only.
- Re-exported the public loop/context API through `pychete.api` and package root.

## Functional Trace Machinery Follow-Up

- Added `functional_trace_template(...)` to expose inspectable Prop/XTerm skeletons for selected log/power traces before evaluation.
- Added `FunctionalTraceEvaluation` and `evaluate_functional_trace(...)`, so individual trace evaluation now carries:
  - the selected trace metadata;
  - the inspectable trace template;
  - the instantiated template with context X-term expressions substituted;
  - the evaluated expression contribution.
- Updated `covariant_loop(...)` to assemble its result through `evaluate_functional_trace(...)`.
- Added `fluctuation_operator_sum(...)` and `instantiate_functional_trace_template(...)` to substitute actual context fluctuation operators into class-level trace skeletons.
- Added `normalize_hybrid_spinor_wrappers(...)` and `close_fermion_loop(...)` for matrix-only fermion-loop closure through the existing pychete Dirac trace engine, accepting Matchete-compatible `Transp`, `GammaCC`, and `CConj` wrappers.
- Added `act_with_open_cds(...)`:
  - open derivatives in `FuncNCM` act by the product rule on factors to their right;
  - terminal open derivatives vanish;
  - consecutive open derivatives immediately before a `WilsonLine` are evaluated as Wilson-line coincidence derivatives, so U(1) field-strength terms are not lost.
- Added `loop_integrate_tadpoles(...)` for one-scale `Prop(M)^n -> I LFFull(M,n)` tadpole placeholders.
- Added `bosonic_log_expansion(...)` and low-order hard-region tests for bosonic propagator, bosonic log, and fermionic propagator templates.
- Expanded the VLF matching context's fluctuation-operator inventory:
  - retained generic Symbolica-derived conjugate Yukawa blocks;
  - added vector X-term placeholders and metadata for charged heavy/light fermion kinetic couplings;
  - preserved the Matchete-style sample lookups used by the validation tests.

## Validation

- Added tests for loop/matching symbols and printing.
- Added a functional-operator test verifying open-CD preservation in `FuncNCM`.
- Added VLF one-loop tests for:
  - field degrees of freedom by Matchete field class;
  - heavy mass and gauge-coupling substitutions;
  - exact Matchete power-trace inventory;
  - representative X-term samples;
  - original LF placeholder retention and log evaluation, later superseded by Matchete-default single-mass log output;
  - a Matchete-derived `phi^6` coefficient;
  - `loop_order=1` equals tree plus `loop_order=(1,)`;
  - individual zero/current power traces.
- Added follow-up tests for:
  - Prop/XTerm trace-template skeletons;
  - open-CD action on ordinary fields;
  - terminal open-CD vanishing;
  - U(1) Wilson-line second derivative to field strength;
  - internal `LFFull` tadpole generation;
  - multiple Matchete-derived full off-shell coefficients after finite-loop-function evaluation.
  - conjugate Yukawa and vector X-term metadata in the VLF context.
  - full Matchete-derived off-shell dimension-6 expression after finite-loop-function evaluation.
  - structured trace evaluation carrying template and expression.
  - trace-template instantiation replacing class-level XTerm placeholders with VLF context X expressions.
  - hybrid spinor wrapper normalization and fermion-loop Dirac trace closure.
  - low-order hard-region propagation/log templates.
- Updated the old nonzero-loop-order rejection test to reject only unsupported loop orders.
- Verified with:
  `source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest tests`
- Current result: 123 passed, 1 skipped. The skip is the existing GammaLoop API optional-build skip.

## VLF Notebook Follow-Up

- Began updating `examples/scalar_theory_playground.ipynb` so the VLF section demonstrates the one-loop matching path.
- Retitled the VLF section from tree-only to tree plus one-loop.
- Imported the public one-loop context/trace helpers in the VLF cell.
- Added VLF notebook cells that:
  - display the immutable matching context's heavy masses, log traces, and power-trace inventory;
  - evaluate a representative individual power trace through `evaluate_functional_trace(...)`;
  - compute the one-loop-only contribution via `Theory.match(..., loop_order=(1,))`;
  - compute tree plus one-loop via `Theory.match(..., loop_order=1)`;
  - compare the public one-loop result with `covariant_loop(...)`;
  - originally expanded finite `LF` placeholders through `evaluate_loop_functions(...)`; after the loop-function convention clarification, the notebook now shows that VLF one-loop output already contains explicit Matchete-default single-mass logs.
- Validated notebook JSON with `dependencies/.venv/bin/python -m json.tool`.
- Verified the relevant implementation surface with:
  `source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest tests/integration/matching/test_vlf_one_loop.py`
- Current focused result: 17 passed.

## Loop-Function Convention Clarification

- User clarified the desired loop-function convention:
  - no synthetic semantic loop-function heads such as `LF(LoopLog, M)` in the conceptual design;
  - true loop functions should be Matchete-shaped, i.e. specified by a mass tuple/list and an integer-power tuple/list;
  - for the current VLF/default matching output, follow Matchete's default behavior and evaluate single-mass LFs, so the written result contains explicit logs.
- Traced the synthetic placeholder to `_loop_log(mass)` in `src/pychete/one_loop.py`, which encoded the already-evaluated single-mass log as `LF(LoopLog, M)`.
- Removed the synthetic `LoopLog` builtin from the central symbol store and pretty-printer coverage.
- Replaced `_loop_log(...)` with a direct Matchete-default single-mass logarithm in VLF trace formulas.
- Updated `loop_integrate_tadpoles(...)` to emit Matchete-shaped `LFFull[{M}, {n, 0}]` placeholders for internal tadpole tests.
- Updated the VLF notebook text and assertions so it no longer advertises or checks for finite `LF` placeholders in the one-loop output.
- Verified with:
  `source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest tests`
- Current result after removing `LoopLog`: 123 passed, 1 skipped.

## LaTeX Gamma Follow-Up

- Began adding LaTeX pretty-printing for `Gamma` with multiple Lorentz indices.
- Identified the source of the fallback output:
  - `_print_gamma(...)` only emitted `\gamma^{...}` for a single argument;
  - `_latex_expr(...)` also only special-cased `Gamma` with exactly one argument.
- Updated both paths so any nonempty `Gamma` index list prints as one superscript, e.g. `\gamma^{\mu \nu}`.
- Added pretty-printing tests for direct `Gamma(mu, nu)` and a closed spinor chain containing `Gamma(mu, nu)`.
- Verified with:
  `source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest tests`
- Current result after LaTeX multi-index gamma update: 123 passed, 1 skipped.
