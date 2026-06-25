# One-Shot Port Implementation Notes

## Active Plan And Guidelines

- Continue the one-shot Matchete-style one-loop matching port on branch
  `one-shot-port`, targeting the default SMEFT-oriented Matchete models first:
  `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Normal pychete runtime code and pytest must remain Mathematica- and
  Matchete-independent. Optional scripts may use Wolfram/Matchete only to
  generate committed pychete-owned fixtures.
- Use Symbolica as the canonical expression engine. Before adding symbolic
  algorithms, check native Symbolica APIs: patterns, `match`, `matches`,
  `replace`, `replace_multiple`, `replace_wildcards`, `series`,
  `coefficient`, `coefficient_list`, `collect`, `derivative`, `Transformer`,
  polynomial/rational-polynomial tools, and evaluators.
- Use idenso for gamma, colour, metric, and abstract-index algebra; spenso for
  tensor-network and CG/tensor contractions; vakint for topology-independent
  tensor reduction and as an optional single-scale analytic cross-check.
  pychete owns the Matchete-style one-loop vacuum-integral evaluator for
  single-scale, zero-mass, and mixed-mass analytic cases.
- Keep local symbol metadata in Symbolica tags/data through `Theory.symbol`.
  Use enum/constant metadata internally; normalize strings only at external
  boundaries.
- Keep free-Lagrangian conventions explicit with `FreeLagConvention`:
  `PYCHETE` is the default canonical pychete convention with expanded
  scalarized Abelian currents, while `MATCHETE` is for `.m` loader
  compatibility with implicit covariant derivatives and `1/g^2` gauge
  normalization.
- Preserve public API discoverability through `pychete.api` and package root
  `pychete`. Public objects and user-facing methods need useful docstrings and
  Jupyter-friendly `_repr_html_` / `_repr_latex_` where relevant.
- Use larger implementation slices with focused tests while building, then
  grouped targeted gates (`definitions`, `models`, `matching`, `backend`,
  `validation`, `not slow`) before green milestone commits. Avoid running the
  full/slow suite after every small edit.
- Commit and push only coherent green milestones to `origin/one-shot-port`.
  Keep these notes current with status, validation, backend discoveries, and
  remaining gaps.

## History Files

- `implementation_notes/one_shot_implementation_part_A.md` keeps the first
  long implementation log unchanged.
- `implementation_notes/one_shot_implementation_part_B.md` keeps the second
  long implementation log unchanged. It ends at commit `e54615a` and records
  the vector/gauge, Abelian-current, charged-fermion, and explicit
  free-Lagrangian-convention slices.
- `implementation_notes/one_shot_implementation_part_C.md` keeps the third
  long implementation log unchanged. It records the Wilson projection,
  complete SMEFT Wilson metadata, internal integral result, on-shell/EOM
  reduction, final EFT truncation, and opt-in Abelian covariant-derivative
  expansion slices.

## Summary Of Part C Status

- SMEFT Warsaw Wilson metadata is complete for the 64 Matchete
  `SMEFTWilsonCoefficients[]` names. The matching and model fixtures for
  `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs` now carry exact
  theory-owned Wilson metadata copied from their matching fixtures.
- Matching-condition projection can use `registered_wilsons`, preferring
  candidate-theory Wilson targets with stored operator metadata while falling
  back to reference non-Wilson targets when needed.
- The internal analytic one-loop backend has full power-type and
  interaction-power result paths, including internal minimal subtraction for
  single-scale, zero-mass, and mixed-mass analytic topologies after optional
  vakint tensor reduction.
- `MatchingResult.with_on_shell_reduction(...)` and
  `OneLoopMatchOptions.on_shell_replacements` apply native Symbolica
  replacement rules before condition projection.
- `Theory.eom_replacement_rule(...)` isolates one requested EOM target through
  native `Expression.coefficient(...)`; `Theory.eom_replacement_rules_for_expression(...)`
  collects derivative targets with Symbolica matching and generates rules for
  one-loop on-shell reduction through `OneLoopMatchOptions.on_shell_eom_*`.
- `MatchingResult.with_eft_truncation(...)` and
  `OneLoopMatchOptions.truncate_eft_result=True` apply a final inclusive EFT
  truncation pass after backend evaluation, normalization, and on-shell/EOM
  reduction but before condition projection.
- `Theory.expand_abelian_covariant_derivatives(...)` and
  `OneLoopMatchOptions.expand_abelian_covariant_derivatives` provide an
  explicit opt-in Symbolica replacement pass for Matchete-style implicit
  Abelian first-derivative slots. A Singlet Scalar Extension probe showed this
  infrastructure alone does not improve the current projected-condition count;
  the remaining gauge-dependent Wilson gaps need broader non-Abelian/full
  covariant-derivative and group-algebra work.

## Current Non-Abelian Infrastructure Slice

- Added `Theory.non_abelian_gauge_generator_insertion(...)` as the first tested
  structural primitive for non-Abelian covariant-derivative work. It builds the
  theory-owned Symbolica expression `g * V * CG(gen) * field` for one concrete
  field index in a registered non-Abelian gauge representation, preserving field
  derivative slots and using the registered generator CG tensor, gauge coupling,
  vector field, and representation symbol data.
- Added `Theory.expand_non_abelian_covariant_derivatives(...)` and
  `OneLoopMatchOptions.expand_non_abelian_covariant_derivatives` as an opt-in
  Symbolica replacement pass for first-derivative fields with registered
  non-Abelian gauge representation indices. The pass generates theory-owned
  plain `SymbolRole.INDEX` labels for the new output and adjoint indices and
  routes each `g * V * CG(gen) * field` term through the centralized generator
  insertion helper.
- Updated the spenso adapter so registered pychete `CG(..., List(Index(...)))`
  atoms lower by extracting pychete index labels before calling native
  `TensorStructure.index(..., cook_indices=True)`. This fixes the generated
  non-Abelian covariant-derivative CG tensors and also closes an older gap for
  loader-produced CG tensors that carry full pychete `Index(...)` arguments.
- Generalized the native HEP spenso bridge from hard-coded SU(3) colour to
  compatible registered SU(N) fundamental/adjoint metadata. The adapter now
  parses the theory-owned group type, lowers `fund`/`Bar[fund]`/`adj` through
  native `Representation.cof(N)` and `Representation.coad(N^2 - 1)`, and routes
  built-in `gen`/`fStruct` tensors for SMEFT `SU2L` as well as `SU3c` through
  spenso's native `TensorName.t()`/`TensorName.f()` objects.
- Added a pychete-aware idenso colour bridge:
  `pychete.group_algebra.simplify_pychete_color(...)` and
  `pychete.backends.idenso.simplify_pychete_color_algebra(...)` now lower only
  spenso-native HEP-compatible `gen`/`fStruct` CG tensors, delegate SU(N)
  contractions to idenso's native `simplify_color`/`simplify_metrics`, preserve
  unrelated pychete CG tensors, substitute unambiguous fixed-group constants,
  and decode simple native metrics back to registered pychete `del[...]` CG
  tensors. `SupertraceBlockTrace.simplify_index_algebra(...)`,
  `OneLoopSetup.simplify_index_algebra(...)`, and public
  `OneLoopMatchOptions.simplify_pychete_color_algebra=True` can now opt into
  this bridge.
- Threaded `simplify_pychete_color_algebra` through validation fixture preview
  and gap-report helpers, including the public `Theory.match(...)` gap-report
  path. This keeps fixture probing on the same API surface as ordinary
  one-loop matching.
- This slice still does not complete non-Abelian group-algebra simplification:
  expanded CG tensors can now lower through spenso and simple generator,
  Fierz, and structure-constant contractions can simplify through idenso, but
  broader supertrace fixture validation and multi-group edge cases remain to be
  improved.
- Validation so far: definitions/public-API tests pass with 37 tests from the
  earlier non-Abelian slice; after the SU(N) native-HEP bridge update, the
  focused spenso backend file passes with 22 tests, the selected one-loop
  native-HEP/non-Abelian covariant-derivative integration checks pass with 2
  tests, `python -m mypy` passes, and `git diff --check` passes. For the idenso
  colour bridge slice, focused idenso/spenso backend tests, selected matching
  idenso/native-HEP/pychete-colour tests, selected one-loop option tests, and
  public API tests pass locally; `python -m mypy` and `git diff --check` also
  pass.
- Targeted projected-condition probe with public match API, max trace order 1,
  internal minimal subtraction, registered/reference projection, and
  `simplify_pychete_color_algebra=True` shows unchanged counts versus the
  previous frontier:
  - `Singlet_Scalar_Extension`: 72/72 projected targets, 42 accepted, 30
    different; 39/64 Wilson targets accepted.
  - `E_VLL`: 72/72 projected targets, 27 accepted, 45 different; 25/64 Wilson
    targets accepted.
  - `S1S3LQs`: 72/72 projected targets, 12 accepted, 60 different; 12/64
    Wilson targets accepted.

## Current Validation Frontier

- Latest focused projected-condition probe for default models with
  `max_trace_order=1`, internal minimal subtraction, public `Theory.match(...)`,
  registered Wilson projection:
  - `Singlet_Scalar_Extension`: 72/72 projected targets, 42 accepted, 30
    different; 39/64 Wilson targets accepted.
  - `E_VLL`: 72/72 projected targets, 27 accepted, 45 different; 25/64 Wilson
    targets accepted.
  - `S1S3LQs`: 72/72 projected targets, 12 accepted, 60 different; 12/64
    Wilson targets accepted.
- Raising the Singlet Scalar Extension trace order from 1 to 3 did not change
  projected-condition acceptance. Enabling opt-in Abelian covariant-derivative
  expansion at order 3 also left the count at 42 accepted and 30 different.
- The representative Singlet differences are candidate-zero versus nonzero
  Matchete reference expressions for gauge-dependent and Higgs-sector
  conditions such as `mu2`, `lambda`, `cH`, `cHB`, `cHBox`, and `cHD`.

## Current Remaining Work

- Implement the broader covariant-derivative/group-algebra feature family:
  use the new idenso-backed pychete colour bridge on generated supertraces,
  extend it beyond the currently tested simple generator/Fierz/f-structure
  contractions where needed, then use targeted fixture probes to determine
  which projected Wilson gaps move.
- Continue improving Dirac/NCM simplification in generated supertraces through
  idenso-backed paths and Symbolica replacement rules.
- Extend EOM/on-shell reduction beyond exact linear target isolation where
  Matchete validation requires structured field redefinitions.
- Re-run targeted projected-condition validation only after a slice materially
  changes fixture matching behavior.
- Keep this live file compact. When it grows large again, move it unchanged to
  `one_shot_implementation_part_D.md` and replace it with a compact updated
  status note.
