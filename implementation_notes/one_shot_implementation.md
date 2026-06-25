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
- Keep performance and scaling under active review for heavy symbolic stages:
  avoid mandatory global expansion when native factored coefficient extraction
  is sufficient, expose explicit controls for expensive projection/simplifier
  stages, and prefer algorithms that scale with selected targets where
  practical.
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

## Current Heavy-Scalar On-Shell Slice

- Added reusable heavy-scalar Symbolica replacement rules through
  `heavy_scalar_solution_replacements(...)`, reusing the existing
  `solve_heavy_scalar_eoms(...)` tree-level solver and `Replacement`
  callbacks instead of adding another Python expression traversal.
- Added `replace_heavy_scalar_solutions(...)` as the expression-level helper
  used by tree matching and the one-loop path.
- Added `OneLoopMatchOptions.substitute_heavy_scalar_solutions` and
  `OneLoopMatchOptions.heavy_scalar_solution_lagrangian`. When enabled,
  `match_one_loop(...)` solves heavy scalar EOMs from the selected Lagrangian,
  applies the resulting native Symbolica replacement rules to the on-shell
  one-loop EFT expression before optional user on-shell/EOM rules, final EFT
  truncation, and matching-condition projection, and records the rule/source
  counts in result metadata.
- The option is deliberately opt-in for now. A targeted Singlet Scalar
  Extension probe showed that applying this reduction before all 72 order-3
  SMEFT projection targets can cause large expression growth and slow native
  projection substantially. The mechanism is tested and available, but the
  default validation frontier remains unchanged until the projection path is
  optimized or the reduction is applied more selectively.
- Threaded `substitute_heavy_scalar_solutions` through the validation
  gap-report public-match path so future fixture probes can enable it
  deliberately.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_heavy_scalar_tree.py tests/integration/validation/test_validation_fixtures.py -k "heavy_scalar or forwards_pychete_color" -q`
  passed with 19 tests; an earlier broader focused run passed with 21 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed; `git diff --check`
  passed.

## Current Projection Scalability Slice

- Exposed `matching_condition_expand_source` on public `Theory.match(...)` and
  `match_one_loop(...)`, threading it through
  `MatchingResult.with_projected_matching_conditions(...)`. The default stays
  `True` for compatibility, but callers can now project from a less-expanded
  result expression with native `Expression.coefficient(...)` when factored
  forms scale better.
- Added `matching_condition_projection_expand_source` to validation fixture
  gap reports and forwarded it through both the public-match and lower-level
  preview projection paths. This makes performance-oriented projection probes
  possible without custom scripts.
- Recorded projection metadata as
  `matching_condition_projection_expand_source` in `MatchingResult.metadata`
  so reports and notebooks can tell whether matching conditions came from an
  expanded or factored source.
- Added `OneLoopMatchOptions.heavy_scalar_solution_expand`. The opt-in
  heavy-scalar solution substitution now applies its native Symbolica
  replacement rules without expanding immediately by default; users can still
  force expansion when desired. This keeps large-model exploratory matching
  from paying an avoidable expansion cost before projection strategy is
  chosen.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_heavy_scalar_tree.py tests/integration/validation/test_numeric_probes.py tests/integration/validation/test_validation_fixtures.py -k "heavy_scalar or project or forwards_pychete_color" -q`
  passed with 26 tests and 51 deselected.

## Current Target-Local EFT Projection Slice

- Added target-local EFT truncation to
  `MatchingResult.project_matching_conditions(...)` and
  `with_projected_matching_conditions(...)`. When `eft_order` is supplied, the
  implementation first extracts a target coefficient with native
  `Expression.coefficient(...)`, then applies `series_eft(...)` only to the
  smaller `coefficient * target` contribution before extracting the coefficient
  again. This preserves the total EFT-order semantics of a global truncation
  without expanding the full one-loop result.
- Exposed the path through public `Theory.match(...,
  matching_condition_truncate_eft=True)` and `match_one_loop(...)`; the
  one-loop API passes the requested `eft_order` and the active
  `OneLoopMatchOptions.heavy_field_dimension` into the target-local projection
  stage.
- Threaded `matching_condition_projection_truncate_eft` through validation
  fixture gap reports for both public-match and lower-level preview projection
  paths, so future Singlet/E_VLL/S1S3LQs probes can combine
  `matching_condition_projection_expand_source=False`,
  `matching_condition_projection_truncate_eft=True`, and
  `truncate_eft_result=False` where a target-local path is cheaper.
- Matching-result metadata now records
  `matching_condition_projection_eft_order` and
  `matching_condition_projection_heavy_field_dimension`.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py tests/integration/matching/test_heavy_scalar_tree.py tests/integration/validation/test_validation_fixtures.py -k "project or heavy_scalar or forwards_pychete_color" -q`
  passed with 27 tests and 51 deselected.

## Current Native CG Round-Trip Slice

- Extended the spenso native-HEP lowering path so compatible built-in
  `builtin:del` CG tensors lower to native `TensorName.g()` metrics alongside
  the existing `gen` and `fStruct` lowering. This lets idenso contract pychete
  generator-delta expressions natively instead of leaving registered deltas as
  blockers next to native `spenso::chain(...)` generator output.
- Extended the idenso pychete-colour bridge to decode simple native colour
  tensors back to registered pychete CG atoms after native simplification:
  native metrics decode to `del`, native one-generator chains and direct
  generator tensors decode to `gen`, and native structure constants decode to
  `fStruct` with antisymmetric canonical ordering. Decoding only occurs when
  the originating pychete SU(N) group is unambiguous.
- Added focused backend tests for uncontracted generator round-tripping,
  generator-delta contraction, uncontracted structure-constant round-tripping,
  and native delta lowering.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_idenso_backend.py tests/unit/backends/test_spenso_backend.py -q`
  passed with 44 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "idenso or pychete_color or non_abelian or native_hep" -q`
  passed with 5 tests and 50 deselected; and
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py -k "pychete_color or forwards_pychete_color" -q`
  passed with 2 tests and 32 deselected. `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` and `git diff --check` also passed.
- A targeted Singlet Scalar Extension public-match probe with `max_trace_order=1`,
  internal minimal subtraction, pychete colour simplification,
  `matching_condition_projection_expand_source=False`, and
  `matching_condition_projection_truncate_eft=True` remains at the prior
  frontier: 42/72 accepted matching conditions, 30 different; 39/64 accepted
  Wilson conditions, 25 different.

## Current Vakint Namespace Decode Slice

- Found a correctness blocker in the internal one-loop path after native
  vakint tensor reduction: vakint rewrites pychete numerator atoms such as
  `Field(...)`, `Coupling(...)`, `Bar(...)`, `Index(...)`, populated/empty
  `List(...)`, and field-strength payloads into `vakint::...` wrappers. The
  scalar integral evaluation can still run, but matching-condition projection
  then sees no pychete fields/couplings and extracts zero coefficients.
- Added `pychete.backends.vakint.decode_pychete_namespace(theory, expr)`.
  It uses Symbolica replacement rules for the known native wrapper heads and
  theory-registry lookups for field, coupling, external, group, and
  representation labels. The implementation avoids a full Python expression
  traversal; Python only decodes the wildcard payloads passed by Symbolica's
  matcher. This keeps the boundary fix lightweight for larger expressions.
- Threaded the decoder through theory-aware vakint stage outputs in
  `SupertraceBlockTrace`, one-loop aggregate `power_type_*` and
  `interaction_power_type_*` methods, generated vakint expression maps, and
  named supertrace helpers. Raw generated expressions remain unchanged; native
  canonicalized, tensor-reduced, and evaluated stage outputs are decoded when
  a `Theory` is available.
- Added focused vakint backend tests proving synthetic wrappers and real
  native tensor-reduction output round-trip back to pychete fields,
  couplings, dummy indices, and registered SU(2) fundamental representations.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/backends/test_vakint_backend.py -q`
  passed with 27 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_heavy_scalar_tree.py tests/integration/validation/test_validation_fixtures.py -k "heavy_scalar or forwards_pychete_color" -q`
  passed with 19 tests and 33 deselected; `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` passed; and `git diff --check`
  passed.
- A targeted Singlet Scalar Extension public-match probe with the same
  performance-oriented options as the previous frontier still reports
  72/72 projected targets, 42 accepted, 30 different; 39/64 Wilson targets
  accepted. This confirms the namespace recovery fix does not by itself close
  the remaining physics-equivalence gaps. Continue with the broader
  covariant-derivative/group-algebra and on-shell/EOM feature families.

## Current Projection Index-Canonicalization Slice

- Added `canonize_indices` to `MatchingResult.project_matching_conditions(...)`
  and `with_projected_matching_conditions(...)`, enabled by default. The pass
  collects pychete `Index(...)` atoms from all requested projection targets
  and the source expression using Symbolica pattern matching, then applies
  native `Expression.canonize_tensors(...)` before native coefficient
  extraction. This makes alpha-equivalent contracted-index relabelings
  projectable without implementing a Python tensor matcher.
- Threaded the option through public `match_one_loop(...)`,
  `Theory.match(...)`, and validation fixture gap reports as
  `matching_condition_canonize_indices` /
  `matching_condition_projection_canonize_indices`. Metadata now records
  `matching_condition_projection_canonize_indices`.
- The source expression is canonicalized term-locally, because generated
  one-loop sums can reuse the same dummy labels in different additive terms.
  Terms whose dummy structure is currently invalid for native tensor
  canonicalization are preserved rather than aborting projection. This keeps
  projection robust while documenting the next source-side normalization gap.
- Added regression coverage proving that a source term with a dummy SU(2)
  Higgs contraction projects onto a target using a different named SU(2)
  index only when index canonicalization is enabled.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -k "project" -q`
  passed with 6 tests and 21 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py -k "forwards_pychete_color" -q`
  passed with 1 test and 33 deselected; `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` passed; and `git diff --check`
  passed.
- A targeted Singlet Scalar Extension public-match probe remains at
  42/72 accepted matching conditions and 39/64 accepted Wilson targets; direct
  projection still finds 0 nonzero candidate conditions. The important new
  diagnostic is that relevant Higgs-sector source terms can contain
  over-contracted dummy indices, e.g. one SU(2) dummy appearing four times in
  a single product after heavy-scalar substitution. The next implementation
  slice should normalize those generated operator products at their source,
  preserving the physical pairings, before relying on tensor canonicalization.

## Current Fresh Heavy-Scalar Dummy Slice

- Implemented fresh dummy-index relabeling for one-loop heavy-scalar solution
  substitution. `heavy_scalar_solution_replacements(...)` now has an opt-in
  `fresh_dummy_indices` mode, and the public one-loop path enables it when
  `substitute_heavy_scalar_solutions=True`.
- Added power-aware Symbolica replacement rules for heavy scalar fields and
  conjugates. This avoids the old `S^2 -> replacement^2` shape where the same
  Higgs dummy contraction was squared and a single dummy label appeared four
  times in one product. In fresh mode each substituted occurrence receives its
  own deterministic dummy-label range.
- The implementation keeps performance in view: Symbolica still performs the
  matching/replacement work, and Python only relabels the compact solution
  expression for each matched heavy-field occurrence. This is deliberately
  narrower than a whole-expression Python tree rewrite.
- Metadata now records `heavy_scalar_solution_fresh_dummy_indices`. The reduced
  one-loop path reports four heavy-scalar replacement rules because it includes
  both atom and positive-integer-power rules for fields and conjugates.
- Added regression coverage proving that replacing `S^2` by a solution with a
  dummy Higgs contraction yields two distinct contracted-index pairs rather
  than one over-used dummy label.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_heavy_scalar_tree.py -k "fresh_dummy or substitutes_heavy_scalar" -q`
  passed with 2 tests and 17 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_heavy_scalar_tree.py tests/integration/validation/test_numeric_probes.py tests/integration/validation/test_validation_fixtures.py -k "fresh_dummy or substitutes_heavy_scalar or project or forwards_pychete_color" -q`
  passed with 16 tests and 64 deselected; `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` passed; and `git diff --check`
  passed.
- A targeted Singlet Scalar Extension diagnostic with public one-loop matching,
  internal minimal subtraction, trace order 1, no tensor reduction, combined
  terms, and heavy-scalar substitution reports
  `bad_term_count_sampled=0`, `heavy_scalar_solution_rule_count=4`, and
  `heavy_scalar_solution_fresh_dummy_indices=True`. The previous sampled
  over-contracted dummy-index pathology is fixed.
- The projected validation frontier did not move during the diagnostic pass:
  Singlet remains at 42/72 accepted matching conditions and 39/64 accepted
  Wilson targets. The next gaps are therefore not just alpha-renaming; they
  remain in operator-shape, derivative, group-algebra, and basis/on-shell
  reduction features.

## Current Derivative-Operator Projection Slice

- Added `functional.expand_cd_operators(...)`, an internal normalization helper
  that expands explicit pychete `CD(...)` wrappers into the canonical
  `Field(..., derivatives)` representation used by generated one-loop sources.
  The implementation is guarded by native Symbolica `matches(...)` and uses
  Symbolica replacement callbacks plus the existing `apply_cd(...)` variation
  machinery, rather than a Python expression walker.
- Threaded derivative-operator normalization through
  `MatchingResult.project_matching_conditions(...)`,
  `with_projected_matching_conditions(...)`, public `match_one_loop(...)`,
  `Theory.match(...)`, and validation fixture gap reports. It is enabled by
  default and can be disabled with
  `matching_condition_normalize_derivative_operators=False` or
  `matching_condition_projection_normalize_derivative_operators=False`.
- Matching-result metadata now records
  `matching_condition_projection_normalize_derivative_operators`.
- Added focused projection tests proving that a generated derivative-slot
  source projects against an explicit `CD(mu, ...)` target, and that additive
  product-rule targets such as `CD(List(mu, mu), phi*Bar(phi))` project when
  the source is kept factored with `expand_source=False`. This mirrors the
  performance-oriented projection path already used for larger SMEFT probes.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py -k "cd_targets or additive_cd or project" -q`
  passed with 8 tests and 21 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py -k "forwards_pychete_color" -q`
  passed with 1 test and 33 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/validation/test_numeric_probes.py tests/integration/validation/test_validation_fixtures.py -k "cd_targets or additive_cd or project or forwards_pychete_color" -q`
  passed with 12 tests and 51 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/functional/test_scalar_eom.py -q`
  passed with 14 tests. `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  and `git diff --check` also passed.
- A scoped Singlet Scalar Extension public-match report with the current
  performance-oriented validation options is unchanged by toggling derivative
  normalization: both modes report 42/72 accepted matching conditions and
  39/64 accepted Wilson targets. This confirms the next missing features are
  not merely explicit-`CD` versus derivative-slot normalization; the source
  still needs broader covariant-derivative/field-strength generation and
  on-shell/IBP basis reduction before the gauge and Higgs-derivative Wilson
  gaps can close.

## Current Covariant-Commutator Field-Strength Slice

- Added `Theory.covariant_derivative_commutator(field, left_index,
  right_index)` as the first explicit field-strength CDE primitive. It returns
  `[D_left, D_right]` acting on a concrete `Field(...)` or `Bar(Field(...))`
  atom using the existing pychete convention `D = partial - I * connection`.
  Unbarred fields receive `-I` times the gauge field-strength insertion;
  barred fields receive `+I` times the conjugate insertion.
- The primitive builds Abelian terms from registered Symbolica charge,
  coupling, and vector-field symbol data, and builds non-Abelian terms from
  registered representation metadata, generated adjoint/output indices, the
  registered `gen_<group>_<rep>` CG tensor, and a `FieldStrength(...)` atom
  carrying the adjoint index. Python is only used at the metadata boundary;
  no symbolic tree walking or handwritten simplification is introduced.
- Extended the generated-index helper with a `prefix` argument so commutator
  indices use a distinct deterministic `covariant_commutator_*` namespace and
  cannot accidentally collide with the existing first-derivative expansion
  indices in the same expression.
- Added focused tests for Abelian charged fields, barred-field sign
  conventions, non-Abelian SU(2) generator/field-strength insertions, and
  public `Theory` method docstring coverage.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/definitions/test_theory_definitions.py -k "commutator or non_abelian_gauge_generator or expand_non_abelian" -q`
  passed with 6 tests and 28 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/definitions/test_public_api.py -q`
  passed with 5 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/definitions/test_theory_definitions.py tests/unit/definitions/test_public_api.py -q`
  passed with 39 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/integration/matching/test_fluctuation_operator.py -k "non_abelian or field_strength or expands_abelian" -q`
  passed with 5 tests and 50 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests/unit/definitions/test_theory_definitions.py tests/unit/definitions/test_public_api.py tests/integration/matching/test_fluctuation_operator.py -k "commutator or non_abelian_gauge_generator or expand_non_abelian or non_abelian or field_strength or expands_abelian" -q`
  passed with 11 tests and 83 deselected; `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` and `git diff --check` also passed.
- This is not yet wired into the one-loop CDE expansion, so it does not claim
  to change the Singlet/E_VLL/S1S3LQs frontier. The next CDE slice should use
  this primitive to turn anti-symmetrized derivative products or commutator
  structures in generated supertraces into `FieldStrength(...)` operators,
  then simplify the resulting CG/field-strength tensors with the idenso/spenso
  adapters already in place.

## Current Formal Covariant-Commutator Expansion Slice

- Added the central Symbolica head `s.CovariantDerivativeCommutator(left,
  right, body)` plus dedicated wildcard symbols and pretty-print callbacks.
  This gives CDE code a compact formal marker for `[D_left, D_right]` without
  relying on string parsing or ad hoc Python expression shapes.
- Added `covariant_derivative_commutator_pattern()` and
  `Theory.expand_covariant_derivative_commutators(...)`. The expansion is
  guarded by native `Expression.matches(...)` and uses a Symbolica replacement
  callback. Direct `Field(...)` and `Bar(Field(...))` bodies lower through the
  existing field-strength primitive; non-field bodies are preserved as formal
  commutators so future product-rule or basis-reduction stages can handle them
  deliberately.
- Factored the non-Abelian commutator implementation so direct public calls
  remain deterministic while bulk formal expansion uses one shared generated
  index counter. This prevents repeated non-Abelian commutator replacements
  from reusing the same `covariant_commutator_*` dummy labels inside a larger
  expression.
- Added `OneLoopMatchOptions.expand_covariant_derivative_commutators` and
  threaded it through `match_one_loop(...)`, `Theory.match(...)` via the
  options object, and validation fixture preview/gap-report helpers. The pass
  runs before fluctuation-operator setup when requested and records
  `covariant_derivative_commutators_expanded` in result metadata. The default
  remains `False`, matching the existing opt-in Abelian/non-Abelian derivative
  expansion controls.
- Performance note: the pass does no work when the formal head is absent, and
  the one-loop smoke test monkeypatches setup to validate ordering without
  paying for backend evaluation.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_pretty_printing.py
  tests/unit/definitions/test_public_api.py -k "commutator or builtin_pychete
  or public_api_methods" -q` passed with 7 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "expands_covariant or expands_abelian_covariant or
  expands_non_abelian_covariant" -q` passed with 3 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed; and
  `git diff --check` passed.

## Current Covariant-Derivative Commutator Emitter Slice

- Added `Theory.emit_covariant_derivative_commutators(...)` as the first CDE
  emitter using the Matchete `CommuteCDs` identity in pychete's derivative-slot
  representation. Registered `Field(...)` and `Bar(Field(...))` atoms with an
  adjacent covariant derivative pair out of canonical order are rewritten as
  the swapped derivative-slot atom plus a formal
  `CovariantDerivativeCommutator(left, right, body)` marker.
- The emitter is implemented through native Symbolica pattern matching and
  replacement callbacks. Barred fields are protected before unbarred field
  replacement, so conjugate fields keep the barred commutator sign convention
  instead of being rewritten through the unbarred inner field.
- Prefix derivatives are preserved as explicit `CD(List(...), commutator)`
  wrappers around the emitted marker. This mirrors Matchete's `TakeDev[prefix,
  GAction[...]]` structure while avoiding mandatory global expansion; later
  passes can call the existing `expand_cd_operators(...)` machinery when they
  need the full product rule.
- Added `OneLoopMatchOptions.emit_covariant_derivative_commutators` and
  threaded it through public `match_one_loop(...)` plus validation fixture
  preview/gap-report helpers. The one-loop ordering is now: optional Abelian
  first-derivative expansion, optional non-Abelian first-derivative expansion,
  optional commutator emission, optional formal commutator expansion to
  `FieldStrength(...)`, then fluctuation-operator setup. Result metadata records
  `covariant_derivative_commutators_emitted`.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_public_api.py -k "commutator or
  public_api_methods" -q` passed with 8 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "covariant_derivative_commutators" -q` passed with 2 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed; and
  `git diff --check` passed.

## Current Bounded Commutator-Emission Canonicalization Slice

- Extended `Theory.emit_covariant_derivative_commutators(...)` with an
  explicit `max_passes` bound. The default remains one adjacent commute, while
  larger values can canonicalize longer derivative-slot lists through repeated
  Symbolica replacement passes without introducing an unbounded expression-growth
  loop.
- Existing formal `CovariantDerivativeCommutator(...)` markers are protected
  during each emitter pass with a dedicated central temporary head
  `s.CovariantDerivativeProtectedCommutator(...)`. This prevents repeated
  canonicalization from recursively rewriting fields inside already-emitted CDE
  payloads; later lowering/product-rule stages stay explicit and opt-in.
- Added `OneLoopMatchOptions.emit_covariant_derivative_commutator_passes` and
  forwarded it through public `match_one_loop(...)` plus validation fixture
  preview/gap-report helpers. Result metadata records
  `covariant_derivative_commutator_emit_passes`, using `0` when emission is not
  requested.
- Added tests for one-pass versus repeated three-pass canonicalization of
  derivative slots, protection of existing formal commutator markers, rejection
  of negative pass counts, pretty-print registration for the protected marker,
  and one-loop option metadata.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_pretty_printing.py
  tests/unit/definitions/test_public_api.py -k "commutator or builtin_pychete
  or public_api_methods" -q` passed with 11 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "covariant_derivative_commutators" -q` passed with 2 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed; and
  `git diff --check` passed.

## Current FieldStrength Commutator-Emission Slice

- Added reusable `FieldStrength(...)` derivative-slot helpers in
  `src/pychete/expr.py` so field-strength atoms can be manipulated through the
  same central pychete expression API as fields instead of open-coded child
  indexing at call sites.
- Generalized `Theory.emit_covariant_derivative_commutators(...)` so registered
  `FieldStrength(...)` and `Bar(FieldStrength(...))` atoms participate in the
  same native Symbolica replacement pass as `Field(...)` atoms. The pass still
  protects already-emitted `CovariantDerivativeCommutator(...)` markers first,
  protects barred payloads before unbarred replacement, and keeps prefix
  derivatives as explicit `CD(List(...), commutator)` wrappers.
- Extended `Theory.expand_covariant_derivative_commutators(...)` and direct
  `Theory.covariant_derivative_commutator(...)` calls to handle
  `FieldStrength(...)` and `Bar(FieldStrength(...))` bodies. Abelian
  field-strength bodies lower to zero, while non-Abelian field-strength bodies
  lower through the registered `gen_<group>_<rep>` CG tensor acting on each
  matching gauge-group index. For adjoint gauge field strengths this uses the
  existing `gen_<group>_adj` metadata, leaving later spenso/idenso passes free
  to simplify the generated adjoint-generator algebra.
- Extended the idenso pychete-colour bridge with a native pre-normalization
  step for registered adjoint generators:
  `gen_<group>_adj(...) -> -I fStruct_<group>(...)`, matching Matchete's
  `CG[gen[group[adj]], indices] := -I CG[fStruct[group], indices]` identity.
  This lets field-strength commutator output flow through the existing native
  `fStruct` simplification and round-trip decoding path instead of preserving
  generic adjoint-generator CG tensors.
- Performance note: the emitter now checks for both tagged field and tagged
  field-strength matches before building temporary protection replacements, and
  it does not force expression expansion.
- Validation so far for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py -k "commutator" -q`
  passed first with 12 tests and later, after field-strength commutator
  lowering was added, with 15 tests and 32 deselected. The grouped milestone
  gate also passed after the lowering extension:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_pretty_printing.py -k "commutator or
  builtin_pychete" -q` with 16 tests and 41 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "covariant_derivative_commutators" -q` with 2 tests and 55 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/backends/test_idenso_backend.py tests/unit/backends/test_spenso_backend.py -q`
  with 46 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "covariant_derivative_commutators or pychete_color" -q` with 3 tests and 54
  deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed; and
  `git diff --check` passed.

## Current CD FieldStrength Product-Rule Slice

- Extended `functional.apply_cd(...)` so its Symbolica variation replacement
  pass treats registered `FieldStrength(...)` and `Bar(FieldStrength(...))`
  atoms as derivative-carrying pychete atoms, not as constants. Derivatives are
  appended to the field-strength derivative slot using the central expression
  helpers.
- Extended the same native replacement pass to formal
  `CovariantDerivativeCommutator(left, right, body)` markers. Prefix
  derivatives now propagate into the commutator body through `apply_cd(...)`
  and rewrap the derivative as a commutator, rather than leaving emitted
  commutator payloads opaque.
- This specifically fixes the source path
  `CD(List(prefix), CovariantDerivativeCommutator(...))` emitted by bounded
  commutator canonicalization: after formal commutators lower to
  `FieldStrength * field`, `expand_cd_operators(...)` now applies the native
  product rule to both the generated field strength and the field atom.
- Performance note: the implementation still avoids a Python derivative tree
  walker. Symbolica performs matching, replacement, series expansion, and
  coefficient extraction; Python only supplies callback construction for the
  matched pychete atoms.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_scalar_eom.py -k "cd" -q` passed with 8 tests and
  9 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/matching/test_fluctuation_operator.py -k "commutator or
  covariant_derivative" -q` passed with 22 tests and 82 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed; and
  `git diff --check` passed.
- A targeted Singlet Scalar Extension public-match probe with
  `max_trace_order=1`, internal minimal subtraction, no tensor reduction,
  combined terms, registered Wilson projection, commutator emission plus
  expansion, and pychete colour simplification remains at the current
  validation frontier: 72/72 projected targets, 42 accepted, 30 different;
  39/64 Wilson targets accepted. The slice is therefore a correctness fix for
  emitted/lowered commutator derivative semantics, not yet a projected
  SMEFT-coverage improvement.

## Current Open-CD CDE Building-Block Slice

- Confirmed by diagnostic that the Singlet Scalar Extension input Lagrangian
  contains explicit `B`, `W`, and `G` `FieldStrength(...)` kinetic terms, but
  the generated one-loop source currently contains no field-strength atoms.
  This means the gauge Wilson gaps such as `cHB`, `cHW`, and `cHWB` are
  operator-generation gaps, not projection/canonicalization-only gaps.
- Re-read Matchete's `SuperTrace.m` and `CovariantDerivative.m` CDE logic.
  The key missing pychete stage is Matchete's open-covariant-derivative
  expansion: propagator expansions emit `OpenCD[...]` operators in
  non-commutative chains; `ActWithOpenCDs` lets the rightmost open derivative
  act on all factors to its right; later `GAction`/commutator logic creates
  field-strength insertions. pychete's current
  `DifferentialOperator -> LoopMomentum` lowering skips this stage.
- Added central `s.OpenCD(...)` support and a new internal `pychete.cde`
  helper module with `open_covariant_derivative(...)` and
  `act_with_open_covariant_derivatives(...)`. The action pass uses bounded
  arity Symbolica replacement patterns over `NCM(...)` chains, matching the
  strategy already used for non-commutative variation linearization. Python
  only orchestrates one matched chain callback; `apply_cd(...)` still delegates
  symbolic derivative semantics to Symbolica replacement/series/coefficient
  machinery.
- This slice is deliberately not wired into the default one-loop pipeline yet.
  It establishes a tested representation and action primitive for the next CDE
  propagator-expansion slice, where open derivatives must be generated before
  loop-momentum/tensor-reduction lowering.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_cde.py tests/unit/definitions/test_pretty_printing.py
  -k "open_covariant or supertrace_denominator" -q` passed with 6 tests and 9
  deselected; `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional -q` passed with 22 tests.

## Current Bosonic CDE Propagator Expansion Slice

- Added `BosonicCovariantPropagatorExpansionTerm` and
  `bosonic_covariant_propagator_expansion_terms(...)` in `pychete.cde`. This
  mirrors the numerator/operator part of Matchete's `PropBosonExpand` for
  `[(q + P)^2 - M^2]^-1`: loop-momentum numerators and open covariant
  derivative operands are generated, while the scalar propagator denominator
  power is stored separately for the existing vakint/internal topology
  machinery.
- The expansion terms keep `open_cd_operands` split from the commutative
  prefactor and loop-momentum numerator. Callers can splice these operands into
  a larger non-commutative supertrace chain before calling
  `act_with_open_covariant_derivatives(...)`, which is necessary for Wilson
  line/X-term action and later field-strength generation.
- Performance note: symbolic work remains in Symbolica expressions and the
  open-CD action pass. Python only performs finite expansion-order
  combinatorics around Matchete's integer-set/variable-partition bookkeeping;
  reusable bounded replacement rules and integer compositions are cached.
- This is still an internal CDE building block, not the default one-loop path.
  The next slice should connect these expansion terms to interaction-power
  supertrace kernels so propagator expansion can happen before loop-momentum
  tensor reduction.
- Validation for this slice so far:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_cde.py -q` passed with 9 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional -q` passed with 26 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_pretty_printing.py -k "supertrace_denominator"
  -q` passed with 1 test and 9 deselected; `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` passed; and `git diff --check`
  passed.

## Current CDE Supertrace Integration Slice

- Connected the bosonic CDE propagator expansion building block to selected
  interaction-power supertrace kernels without changing the default one-loop
  matching path. `SupertraceBlockTrace.bosonic_cde_expansion_terms(...)`
  expands one ordered trace by splicing each propagator slot's `OpenCD(...)`
  operands into the non-commutative block-entry chain before optional
  `act_with_open_covariant_derivatives(...)`.
- Added `BosonicCDETraceExpansionTerm` as the structured public result object
  for one expanded term. It carries the numerator, mass-squared slots, and
  propagator powers separately, exposes a diagnostic `SupertraceKernel(...)`
  expression, and lowers directly to the existing vakint topology expression
  with explicit powers.
- Added selected-trace setup helpers:
  `OneLoopSetup.interaction_bosonic_cde_kernel_expression_map(...)` and
  `OneLoopSetup.interaction_bosonic_cde_vakint_integral_expression_map(...)`.
  Both require an explicit map from trace name to expansion-index sequences,
  so exploratory CDE work scales with requested traces/orders instead of
  globally expanding every generated trace.
- The denominator mass/power alignment follows the ordered closed trace after
  each block entry. This preserves the open-derivative ordering needed before
  loop-momentum tensor reduction and still lowers repeated propagators as
  single vakint props with the accumulated power.
- Exported `BosonicCDETraceExpansionTerm` through `pychete.api` and package
  root `pychete`, keeping the new CDE diagnostic surface discoverable.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py -k "interaction_bosonic_cde or
  public_api" -q` passed with 6 tests and 57 deselected;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_cde.py -q` passed with 9 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed; and
  `git diff --check` passed.

## Current Opt-In CDE Matching-Result Slice

- Added `OneLoopMatchOptions.bosonic_cde_expansion_indices_by_trace` and
  `OneLoopMatchOptions.bosonic_cde_act_open_derivatives`. Supplying the trace
  expansion map explicitly switches `match_one_loop(...)` from the older
  interaction-power aggregate to the selected CDE-expanded interaction
  aggregate, while preserving the existing backend selection, normalization,
  on-shell/EOM reduction, final EFT truncation, and matching-condition
  projection pipeline.
- Added CDE aggregate/result helpers on `OneLoopSetup`:
  `interaction_bosonic_cde_expansion_terms_by_trace(...)`,
  `interaction_bosonic_cde_expansion_terms(...)`,
  `interaction_bosonic_cde_vakint_integral_sum(...)`,
  `interaction_bosonic_cde_internal_integral_sum(...)`,
  `interaction_bosonic_cde_matching_result(...)`,
  `interaction_bosonic_cde_internal_matching_result(...)`,
  `interaction_bosonic_cde_internal_minimal_subtraction_result(...)`, and
  `interaction_bosonic_cde_minimal_subtraction_result(...)`.
- The new result methods expose named CDE kernels, named CDE vakint
  topologies, aggregate sums, pole/finite pieces where applicable, and
  metadata recording CDE trace/term counts and whether open derivatives were
  acted. Internal evaluation still delegates tensor reduction to vakint when
  requested and scalar topology evaluation to pychete's analytic one-loop
  backend.
- Threaded the same explicit CDE options through validation fixture preview
  and public-match gap-report helpers, so fixture diagnostics can exercise the
  new path without Mathematica or custom scripts.
- Performance/scaling note: there is still no global automatic CDE expansion.
  Callers must select trace names and expansion-index sequences explicitly, so
  exploratory CDE work scales with the requested trace/order subset. Automatic
  expansion-order planning remains a later matching-stage feature.
- Validation for this slice:
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py::test_interaction_bosonic_cde_expansion_maps_selected_trace_to_kernel_and_vakint
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_bosonic_cde_expansion_without_mathematica
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_forwards_pychete_color_to_public_match_api
  tests/unit/definitions/test_public_api.py::test_public_api_methods_have_docstrings
  -q` passed with 4 tests;
  `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_cde.py tests/unit/definitions/test_public_api.py
  tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_validation_fixtures.py -k "cde or
  public_api or forwards_pychete_color or
  preview_can_use_internal_integral_backend" -q` passed with 18 tests and 89
  deselected; `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed;
  and `git diff --check` passed.

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
- Add automatic CDE expansion-order planning for selected trace families, then
  integrate the commutator emitter/lowering pair into the generated CDE stages
  that produce the gauge Wilson structures needed by `cHB`, `cHW`, `cHWB`,
  and related fermionic Higgs-current coefficients.
- Add an on-shell/IBP basis-reduction strategy for derivative-slot Higgs
  operators so generated derivative distributions can project onto Warsaw
  basis targets such as `cH`, `cHBox`, and `cHD`.
- Optimize the opt-in heavy-scalar solution substitution/projection path so it
  can be safely enabled for larger order-3 SMEFT target sets without causing
  avoidable expression growth. Candidate directions: apply heavy-field
  replacement before expansion where possible, project smaller target groups,
  and use Symbolica collection/coefficient primitives on less-expanded stages.
- Use the new `matching_condition_expand_source=False` and
  `matching_condition_truncate_eft=True` controls, together with
  `heavy_scalar_solution_expand=False`, in targeted order-3 Singlet probes
  once the next backend feature slice materially changes the projected EFT
  expression.
- Re-run targeted projected-condition validation only after a slice materially
  changes fixture matching behavior.
- Keep this live file compact. When it grows large again, move it unchanged to
  `one_shot_implementation_part_D.md` and replace it with a compact updated
  status note.
