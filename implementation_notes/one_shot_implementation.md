# One-Shot Port Implementation Notes

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
Mathematica, `wolframscript`, or a runnable Matchete installation. Development
helper Wolfram scripts may load the read-only Matchete checkout to generate
committed pychete-owned fixtures, but runtime code and tests must load only
those fixtures.

Keep the approved implementation plan copied into both
`implementation_notes/one_shot_user.md` and
`implementation_notes/one_shot_implementation.md`, and keep both copies updated
whenever the plan changes. Keep this implementation note continuously updated
with current progress, completed milestones, test status, backend/API
discoveries, dependency patches, blockers, and remaining work.

## Approved Plan

# One-Shot One-Loop Matching Port

## Summary

- Build a Pythonic pychete implementation of Matchete-style one-loop matching,
  prioritizing the default SMEFT UV matching models first, then all Matchete
  validation tests that map cleanly to pychete's architecture.
- Normal pytest must be Mathematica-independent. Development-only Wolfram
  scripts may load Matchete to generate serialized pychete fixtures under the
  repo, but tests load only those committed fixtures.
- Use Symbolica as the symbolic engine, idenso/spenso for gamma, colour,
  metric, and tensor algebra. Use pychete's own Matchete-style analytic backend
  for one-loop vacuum integral evaluation after tensor reduction, including
  single-scale, zero-mass, and mixed-mass cases. Use vakint for
  topology-independent tensor reduction and as an optional supported backend or
  cross-check for single-scale massive analytic evaluations.
- Compare results by pychete canonical equality, backed by Symbolica evaluator
  numeric probes for hard-to-canonicalize expressions.

## Key Changes

- Add `helper_mathematica_scripts/` with Wolfram scripts that load Matchete and
  export model definitions, validation expected outputs, supertraces, matching
  conditions, and selected unit-test fixtures into pychete-owned serialized
  assets. Keep optional top-level `scripts/` wrappers checked in for users who
  have Mathematica and want a convenient export/convert entry point, while
  keeping the maintained helper implementation and all normal pytest/runtime
  paths Matchete- and Mathematica-independent.
- Treat the direct Python Mathematica loader as a documented supported-subset
  loader for simple declarative model assets and saved-result snippets only.
  For complicated Mathematica models, use Wolfram/Matchete helper scripts to
  load the model, extract Matchete's parsed internal data, and emit equivalent
  pychete serialized state or Python fixture files that can be committed and
  used by tests and users.
- Add committed fixture assets for Matchete-independent pytest validation;
  never require `wolframscript` in normal tests.
- Extend pychete metadata with gauge groups, representations, CG tensors,
  charges, chiral fermions, ghosts, Goldstones, background fields, coupling
  symmetries, diagonal/unitary metadata, and SMEFT basis metadata using
  Symbolica symbol tags/data.
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

## Workflow

- During implementation, create and maintain
  `implementation_notes/one_shot_user.md` and
  `implementation_notes/one_shot_implementation.md`.
- Commit and push only green, coherent milestones to remote branch
  `one-shot-port`.
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

## Live Progress

- Current branch: `one-shot-port`.
- Current baseline commit at start of one-shot implementation: `a8abd5c`.
- The Matchete reference checkout exists under `Mathematica_reference/Matchete`
  and is treated as read-only.
- Completed the first implementation slice:
  - recorded the approved plan in both one-shot notes;
  - added a Mathematica-independent validation fixture loader backed by
    `PycheteState`;
  - added the default Matchete matching target manifest for
    `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`;
  - added development-only Mathematica helper script scaffolding for raw
    Matchete matching snapshots.
- Completed the second implementation slice:
  - added public `MatchingResult` as the structured carrier for UV Lagrangian,
    fluctuation operators, individual supertraces, off-shell EFT Lagrangian,
    on-shell EFT Lagrangian, matching conditions, and metadata;
  - added validation fixture support for reconstructing `MatchingResult` from
    committed JSON expression references;
  - kept `load_validation_fixture` out of the package-root public API while
    promoting `MatchingResult` as a public result object;
  - added Jupyter repr coverage for `MatchingResult`.
- Completed the third implementation slice:
  - added `pychete.validation.evaluator_probe_equal`, which compares two
    expressions through `Expression.evaluator_multiple` rather than Python-side
    substitution;
  - added `NumericProbeResult` to carry equality, maximum absolute difference,
    and per-sample differences;
  - added NumPy to the managed dependency bootstrap because Symbolica evaluator
    calls require the NumPy array API at runtime;
  - pinned the managed NumPy dependency to `numpy<2.5` because NumPy 2.5 stubs
    require Python 3.12 syntax while pychete's mypy target is Python 3.11.
- Completed the fourth implementation slice:
  - added `FieldChirality` and stored field chirality in Symbolica symbol data;
  - added field gauge-charge metadata stored in Symbolica symbol data;
  - added `Theory.group_charge(...)` for Pythonic U(1)-charge construction;
  - taught the supported Matchete model loader path to preserve simple
    `Charges`, `Indices`, and `Chiral` field options;
  - updated the VLF toy model Python asset so the Python and supported
    Mathematica assets agree on U(1) charge metadata.
- Completed the fifth implementation slice:
  - added the first committed pychete-owned fixture asset at
    `assets/validation/pychete/VLF_toy_model.model_fixture.json`;
  - added pytest coverage that loads this committed asset without Mathematica
    and compares it to the Python VLF model asset;
  - fixed `Theory.from_json_obj` so the group registry is restored alongside
    group symbols, which is required for `Theory.group_charge(...)` after
    loading fixtures or checkpoints.
- Completed the sixth implementation slice:
  - added Matchete-style coupling metadata to `CouplingDefinition` and
    Symbolica symbol data: indexed coupling representations, EFT order,
    boolean or permutation-valued self-conjugation, symmetry expressions,
    diagonal-coupling flags, thermal power counting, and unitary flags;
  - added central Symbolica heads for `SymmetricIndices`,
    `AntisymmetricIndices`, `SymmetricPermutation`,
    `AntisymmetricPermutation`, and `SymmetryOverride` through the
    `SymbolStore`;
  - taught `Theory.from_json_obj` to restore the new coupling metadata through
    the existing symbol-manifest-first checkpoint path;
  - added a coupling symbol-manifest normalization path so older committed
    fixtures that predate the new coupling keys load into the current
    structural symbol-data shape before expressions are parsed;
  - extended the supported Matchete model loader path to preserve
    `DefineCoupling` options instead of dropping them, including list-valued
    `DefineCoupling[{...}, ...]`.
- Completed the seventh implementation slice:
  - added pychete-owned model input assets for the remaining default one-loop
    matching targets: `Singlet_Scalar_Extension.m`, `E_VLL.m`, and
    `S1S3LQs.m`;
  - added the pychete-owned `SM.m` parent model asset required by those three
    default target files;
  - updated the default matching target manifest so every target points to a
    repository-owned `model_asset` and explicit `parent_assets` instead of
    requiring tests to read from `Mathematica_reference/Matchete`;
  - kept the status as `pending_matching_fixture` because the actual one-loop
    matching-result fixtures are still not generated.
- Completed the eighth implementation slice:
  - added metadata-only loading for the supported Matchete model subset through
    `load_matchete_model(..., include_lagrangian=False)`;
  - added parent-model expansion for `ParentModel["SM"]`, loading parent
    definitions into the child theory namespace before child-specific
    definitions;
  - added loader support for `ParameterDefault`, `DefineFlavorIndex`, optional
    `DefineGaugeGroup` arguments, `SU@N` group heads, quoted Mathematica
    strings in top-level splitters, broader Greek-name preprocessing, and
    `Bar@` / `CConj@` prefix application in metadata expressions;
  - added central `CConj` Symbolica head support;
  - generated committed metadata-only model-definition fixtures for `SM`,
    `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`;
  - updated the default matching target manifest to point at the committed
    model-definition fixtures for all default targets.
- Completed the ninth implementation slice:
  - extended the supported Mathematica expression normalizer for child target
    Lagrangians with integer factorials, simple implicit products, Mathematica
    list braces, and general `**` noncommutative chains;
  - changed parent expansion so child model expression loading uses parent
    metadata but does not attempt to parse or include the parent SM Lagrangian;
  - parsed and committed child-Lagrangian expressions for
    `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs` in their
    model-definition fixtures;
  - skipped local delayed helper definitions such as `tauSU2L[...] := ...`
    during direct parsing for now, leaving their calls as registered external
    heads until the CG adapter layer can lower them through spenso/idenso;
  - added tests proving those child Lagrangians parse from the pychete-owned
    model assets and restore from committed fixtures without Mathematica.
- Completed the tenth implementation slice:
  - added `pychete.backends.idenso` as a thin native delegation layer for
    `cook_function`, `cook_indices`, `dirac_adjoint`, `expand_bis`,
    `expand_color`, `expand_metrics`, `expand_mink`, `expand_mink_bis`,
    `list_dangling`, `simplify_color`, `simplify_gamma`,
    `simplify_metrics`, `to_dots`, `wrap_dummies`, and `wrap_indices`;
  - added `pychete.backends.spenso` as a thin native delegation layer for
    empty and HEP tensor libraries, tensor-network construction, execution,
    and scalar/tensor result extraction;
  - added `pychete.backends.vakint` as a thin native delegation layer for
    evaluation-method factories, engine construction/caching,
    `VakintExpression`, numerical-result conversion, canonicalization,
    tensor reduction, integral-only evaluation, and full integral evaluation;
  - routed the existing `pychete.group_algebra.idenso` shim through the new
    idenso adapter so older internal imports use the same native boundary;
  - added focused pytest coverage for native idenso delegation, cheap spenso
    tensor-library/network paths, and vakint delegation with a fake engine so
    tests do not instantiate vakint's expensive topology-processing engine.
- Completed the eleventh implementation slice:
  - added `parse_matchete_expression(...)` to lower Matchete saved-result
    syntax into pychete Symbolica heads, including `Field`, `Coupling`,
    `Index`, `FieldStrength`, `DiracProduct`, `GammaM`, `Proj`, `CG`,
    `Bar`, `Log`, dummy labels such as `d$$1`, and `\[CenterDot]`
    noncommutative chains;
  - added `helper_mathematica_scripts/convert_matchete_previous_results.py`,
    a Mathematica-independent converter for committed Matchete previous-result
    files into pychete `MatchingResult` fixtures;
  - generated and committed
    `assets/validation/pychete/VLF_toy_model.matching_fixture.json` from
    Matchete's previous VLF one-loop validation result;
  - updated the default matching target manifest so `VLF_toy_model` now points
    at a committed matching fixture while the other three default targets
    remain pending;
  - added pytest coverage for Matchete internal-head parsing and for loading
    the committed VLF matching fixture as a structured `MatchingResult` with
    13 supertraces and no Mathematica runtime.
- Completed the twelfth implementation slice:
  - extended `convert_matchete_previous_results.py` to lower nontrivial
    Matchete `Matching Conditions` rule lists into pychete fixture
    expressions;
  - matching-condition RHS expressions are stored in the fixture state and
    keyed by the canonical pychete expression for the Matchete rule left-hand
    side, preserving the rule target without adding a new fixture schema;
  - regenerated the VLF matching fixture with explicit matching-condition
    metadata and generated committed matching fixtures for the remaining
    default targets: `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`;
  - updated the default matching target manifest so all four initial models
    now point at committed pychete-owned matching fixtures;
  - added validation coverage that loads all four default matching fixtures
    without Mathematica and validates their structured `MatchingResult`
    expressions.
- Completed the thirteenth implementation slice:
  - added canonical `MatchingResult.compare_to(...)` support, returning a
    `MatchingResultComparison` with per-expression
    `MatchingExpressionComparison` entries;
  - comparison uses Symbolica-backed expansion plus canonical serialization so
    committed Matchete fixtures can serve as direct acceptance targets for
    future pychete one-loop matching output;
  - exported the comparison result types and
    `OneLoopMatchingNotImplementedError` through the public API;
  - added an explicit `loop_order` argument to `Theory.match(...)`, preserving
    the existing tree-level behavior for `loop_order=0`; later slices now route
    `loop_order=1` to an explicitly incomplete native-backed
    `MatchingResult`;
  - added tests that tree matching remains unchanged, one-loop requests cannot
    silently return tree-level results, and fixture comparisons report canonical
    mismatches.
- Completed the fourteenth implementation slice:
  - extended `MatchingResult.compare_to(...)` with optional Symbolica
    evaluator-backed numeric probes for expressions that fail canonical
    comparison;
  - kept canonical Symbolica comparison as the default and primary validation
    path, with numeric probes only running when callers provide both probe
    parameters and deterministic sample points;
  - attached numeric-probe evidence to each `MatchingExpressionComparison` so
    notebooks and tests can distinguish canonical equality from evaluator-backed
    equality;
  - exported `NumericProbeResult` and `evaluator_probe_equal` through the
    package-root public API now that comparison objects expose probe evidence;
  - added tests covering a trigonometric identity that is evaluator-equal but
    not canonically equal under the current Symbolica expansion policy.
- Completed the fifteenth implementation slice:
  - added public `FluctuationOperator` as the first structured one-loop
    pipeline carrier for quadratic fluctuation data;
  - added `Theory.fluctuation_operator(...)`, which extracts the algebraic
    Hessian for an explicit fluctuation basis by encoding selected field
    expressions as temporary Symbolica variables, applying native
    `Expression.derivative`, and decoding any residual temporary variables back
    to the original field expressions;
  - protected unselected barred fields with a Symbolica replacement-rule
    protector, while still allowing explicitly selected `Bar(Field(...))`
    entries to participate as independent basis variables;
  - exported `FluctuationOperator` through the package-root public API and
    added Jupyter-friendly repr hooks;
  - added tests for scalar Hessian entries, barred-field protection, explicit
    barred-field basis entries, duplicate-basis validation, and public API
    docstrings.
- Completed the sixteenth implementation slice:
  - added public `FluctuationBasis` as the first structured heavy/light
    fluctuation-sector carrier;
  - added `Theory.fluctuation_basis(...)`, which discovers field atoms with
    Symbolica `Expression.match` and `req_tag("field")` restrictions rather
    than Python tree walking;
  - classified discovered basis entries into heavy and light sectors from
    Symbolica field-label data via `field_mass_kind_from_label(...)`;
  - taught `Theory.fluctuation_operator(...)` to use the discovered basis when
    no explicit basis is supplied, while preserving the explicit-basis path;
  - added a theory-ownership guard so a `FluctuationBasis` cannot accidentally
    be reused with a different theory;
  - added tests that derivative-bearing fields are reduced to their base field
    entries, complex fields contribute barred and unbarred entries,
    unregistered/untagged field-like atoms are ignored, and automatic Hessian
    extraction uses the discovered basis.
- Completed the seventeenth implementation slice:
  - added public `FluctuationMode` records for each fluctuation-basis entry;
  - added public `FluctuationStatistics` enum values for bosonic and fermionic
    modes, avoiding stringly typed statistics metadata;
  - made `FluctuationBasis` derive `entries`, `heavy`, `light`,
    `heavy_modes`, and `light_modes` from structured modes rather than storing
    only raw field expressions;
  - added `FluctuationBasis.mode_for(...)` for deterministic metadata lookup;
  - populated mode metadata from Symbolica field-label data, including field
    type, mass kind, self-conjugacy, conjugation state, and boson/fermion
    supertrace sign;
  - added tests for scalar and fermion mode metadata, public API docstrings,
    and Jupyter repr hooks.
- Completed the eighteenth implementation slice:
  - added public `FluctuationSector` enum selectors for `all`, `heavy`, and
    `light` fluctuation sectors;
  - added public `FluctuationOperatorBlock` as a rectangular sector block of a
    fluctuation operator matrix;
  - taught `FluctuationOperator` to retain the `FluctuationMode` metadata used
    to build its basis, so later pipeline stages can address matrix entries by
    sector and mode;
  - added `FluctuationOperator.mode_for(...)` and
    `FluctuationOperator.block(...)`;
  - added tests for heavy-light and light-heavy block extraction, all-sector
    full-matrix blocks, invalid sector selectors, public API docstrings, and
    Jupyter repr hooks.
- Completed the nineteenth implementation slice:
  - added public `SupertracePlan` as the structured carrier for the four
    sector blocks that feed later one-loop supertrace generation:
    heavy-heavy, heavy-light, light-heavy, and light-light;
  - added `FluctuationOperator.supertrace_plan(...)`, which prepares the
    deterministic block data from existing fluctuation mode metadata without
    pretending to evaluate traces, tensor reductions, or loop integrals yet;
  - added heavy/light mode-count helpers and heavy-sector supertrace-sign
    aggregation so later supertrace terms can consume structured statistics
    metadata instead of rediscovering it;
  - exported `SupertracePlan` through the public API and added Jupyter-friendly
    repr hooks;
  - added tests for plan construction from sector blocks, expression-map export,
    public API docstrings, and Jupyter repr coverage.
- Completed the twentieth implementation slice:
  - added public `SupertraceBlockTrace` as a structured trace-kernel object for
    ordered products of fluctuation-operator blocks;
  - added `SupertracePlan.block_trace(...)`, which validates closed block
    chains, rejects mismatched adjacent sector blocks, and computes the weighted
    boson/fermion supertrace over the diagonal;
  - used Symbolica's native `Matrix.from_nested(...)` and `Matrix.__matmul__`
    for the matrix product, leaving only the unavoidable finite diagonal
    supertrace sum in Python because the stub exposes no matrix trace method;
  - kept this milestone at the block-kernel stage only: it does not claim to
    perform propagator expansion, loop-momentum reduction, tensor reduction, or
    vakint integration yet;
  - exported `SupertraceBlockTrace` through the public API and added
    Jupyter-friendly repr hooks;
  - added tests for heavy-heavy and heavy-light/light-heavy block traces,
    ordered sector-path metadata, expression-map export, invalid open or
    mismatched block chains, public API docstrings, and Jupyter repr coverage.
- Completed the twenty-first implementation slice:
  - added `SupertracePlan.closed_block_traces(...)`, which deterministically
    enumerates closed heavy/light sector paths at a requested block order and
    turns each path into a `SupertraceBlockTrace`;
  - kept the all-light closed path excluded by default, while allowing callers
    to include it explicitly for diagnostics or EFT-side comparison work;
  - used Python only for finite sector-path orchestration over the existing
    heavy/light blocks; each generated kernel still delegates its symbolic
    matrix product to the Symbolica Matrix path from the previous slice;
  - added tests for order-one and order-two closed paths, the light-only toggle,
    generated kernel expressions, order validation, and public API docstrings.
- Completed the twenty-second implementation slice:
  - added public `OneLoopSetup` as the current one-loop pipeline carrier before
    propagator expansion and loop integration;
  - added `Theory.one_loop_setup(...)`, which validates the UV Lagrangian,
    extracts the Symbolica-backed fluctuation operator, builds the supertrace
    plan, and generates closed block-trace kernels up to a requested order;
  - kept `Theory.match(..., loop_order=1)` unchanged and still failing loudly:
    the new setup API exposes real prepared inputs without returning a fake
    completed `MatchingResult`;
  - added deterministic expression-map helpers for setup outputs and generated
    supertrace kernels so future matching-result stages and validation fixtures
    can consume the same names;
  - exported `OneLoopSetup` through the public API and added Jupyter-friendly
    repr hooks;
  - added tests for one-loop setup construction, generated kernel names and
    expressions, expression-map export, invalid trace-order validation, public
    API docstrings, and Jupyter repr coverage.
- Completed the twenty-third implementation slice:
  - added `SupertraceBlockTrace.simplify_index_algebra(...)`, delegating kernel
    simplification to the native idenso adapter instead of adding local
    gamma/colour/metric/index algebra in Python;
  - added `OneLoopSetup.simplify_index_algebra(...)`, which returns an updated
    immutable setup with all generated block kernels simplified through idenso;
  - kept the fluctuation operator and supertrace plan shared across the
    simplified setup because only generated kernel expressions are transformed
    in this stage;
  - added tests that monkeypatch the idenso adapter boundary to prove
    generated kernels are routed through `pychete.backends.idenso` with the
    requested simplification options;
  - extended public API docstring coverage for the new simplification methods.
- Completed the twenty-fourth implementation slice:
  - added `SupertraceBlockTrace.canonicalize_integrals(...)`,
    `SupertraceBlockTrace.tensor_reduce_integrals(...)`, and
    `SupertraceBlockTrace.evaluate_integrals(...)`, delegating generated kernel
    transformations to the native vakint adapter;
  - added matching `OneLoopSetup` methods that return updated immutable setup
    objects with every generated kernel routed through vakint canonicalization,
    tensor reduction, or evaluation;
  - kept this as an explicit backend transformation stage only: the current
    setup kernels still need true loop-integral construction before these
    operations can produce final matching supertraces;
  - added tests using a fake vakint engine to prove the setup path delegates to
    `to_canonical`, `tensor_reduce`, and `evaluate` without constructing the
    expensive default native engine in normal pytest;
  - extended public API docstring coverage for the new vakint transformation
    methods.
- Completed the twenty-fifth implementation slice:
  - added `SupertraceBlockTrace.evaluate_tensor_network(...)`, delegating
    generated kernel tensor/CG contraction to the native spenso adapter;
  - added `OneLoopSetup.evaluate_tensor_networks(...)`, which returns an
    updated immutable setup with every generated kernel evaluated through
    spenso and converted back through the adapter's scalar-result boundary;
  - kept this as an explicit backend transformation stage only: tensor-network
    evaluation is now wired into the setup path, but full one-loop matching
    still needs real propagator/integral construction before these kernels are
    physical supertrace contributions;
  - added tests that monkeypatch the spenso adapter boundary to prove generated
    kernels are routed through `pychete.backends.spenso` with caller-provided
    library, function-library, step, and mode options;
  - extended public API docstring coverage for the new spenso transformation
    methods.

## Backend/API Discoveries

- Symbolica state restoration already supports the structural guarantee needed
  for validation fixtures: `PycheteState.from_json_obj` restores registered
  theory symbols before parsing stored expressions.
- Existing idenso APIs include direct gamma, colour, metric, index wrapping, and
  dangling-index routines; these should be the first line for algebra adapters.
- Existing vakint APIs include `to_canonical`, `tensor_reduce`,
  `evaluate_integral`, and `evaluate`, which map directly onto the planned loop
  integral backend.
- Rescanned the Symbolica Python stub sections for `Expression.match`,
  `Expression.matches`, `Expression.evaluator`, and `Expression.evaluator_multiple`.
  The numeric-probe validation layer should use these evaluator APIs rather than
  Python substitution/evaluation.
- Directly tested `Expression.evaluator` and `Expression.evaluator_multiple` in
  the managed venv. Both return NumPy arrays; without NumPy installed the
  Symbolica evaluator path aborts before Python can raise a normal exception.
- Matchete `DefineField` stores `Charges`, `Indices`, and `Chiral` as first-class
  field options. The pychete representation now persists the first simple slice
  of that metadata through Symbolica symbol data and JSON checkpoints.
- The first committed fixture asset surfaced that restoring group symbols is not
  enough: the Python `Theory.groups` registry must also be restored before later
  code can build charges or inspect gauge-field metadata.
- Rescanned the Symbolica Python stub sections for symbol `data`, tags,
  `Expression.get_symbol_data`, and `Expression.get_tags`. Coupling metadata
  now stays on Symbolica symbols through the same structural data path as field
  mass/charge metadata.
- Matchete `DefineCoupling` stores `Indices`, `EFTOrder`, `SelfConjugate`,
  `Symmetries`, `DiagonalCoupling`, `ThermalPowerCounting`, and `Unitary`.
  It also requires unitary couplings to be square matrix couplings with
  `EFTOrder -> 0`; pychete now enforces the matching structural checks.
- Matchete `SuperTrace.m` uses a first grading convention in which scalar and
  vector propagator types carry sign `+1`, while fermion, ghost, and anti-ghost
  propagator types carry sign `-1`; it also introduces an explicit `1/2`
  compensation factor for `LeftHanded` and `RightHanded` chiral fermion fields
  in the log-type supertrace setup. pychete now exposes the corresponding mode
  metadata without prematurely multiplying it into the current matrix trace.
- Symbolica refuses to redefine an already-created symbol with different custom
  data. The fixture loader therefore normalizes older coupling manifest data to
  include the current default keys before registering theory symbols, preserving
  the structural guarantee that expressions parse only after the symbol registry
  has the intended data.
- The remaining default Matchete integration models all use `ParentModel["SM"]`.
  pychete now owns copies of those child model files and the SM parent input,
  but the loader still needs an explicit parent-model expansion path and CG
  function handling before these inputs can become full committed model-state
  fixtures.
- Parent-model expansion now works for metadata-only loading of the default
  targets. Full Lagrangian parsing for the SM-backed targets still requires the
  broader Mathematica expression subset around local CG helper definitions,
  implicit multiplication, noncommutative chains, and charge-conjugation
  expressions, or a Wolfram-generated pychete-owned fixture path for those
  expressions.
- Child-Lagrangian parsing now works for the three SM-backed default targets
  using parent metadata. The committed expressions intentionally do not include
  the SM parent Lagrangian yet; S1/S3 local CG helper calls are preserved as
  registered external Symbolica heads until they are routed through the planned
  spenso/idenso CG adapter layer.
- Rescanned and exercised the idenso/spenso/vakint Python stubs before adding
  backend adapters. Native idenso no-ops safely on plain Symbolica symbols for
  the covered simplifier/index wrappers, spenso can cheaply construct empty and
  HEP tensor libraries plus scalar tensor networks, and vakint method factories
  import cheaply while full `Vakint(...)` engine construction should remain a
  cached or caller-provided operation because it processes known topologies.
- Rescanned and directly probed Symbolica's function-attribute and transformer
  APIs for noncommutative-chain differentiation. `S(..., is_linear=True)` and
  `Transformer.linearize(...)` expand sums in function arguments, but native
  `Expression.derivative(...)` and `Expression.series(...)` still return
  formal `der(...)` heads for derivatives with respect to arbitrary function
  arguments. Therefore pychete's custom `NCM` head needs a narrow
  variation-time multilinear lowering before Symbolica coefficient extraction;
  this is backend-boundary glue for pychete's own head, not a replacement for
  Symbolica algebra.
- Rescanned the idenso and spenso Python stubs and local Rust source around
  `idenso.simplify_gamma`, `TensorLibrary.hep_lib`,
  `TensorName.projp`, and `TensorName.projm`. idenso already knows the chiral
  projector identities, but it expects native spenso projector tensors with
  bispinor endpoints. pychete therefore needs a lowering/decoding adapter for
  its compact `s.PR`/`s.PL` public symbols instead of Python-side projector
  simplification rules.
- Probed native idenso/spenso open-chain gamma behavior through
  `TensorLibrary.hep_lib()[S("spenso::gamma")]`, `projp`, and `projm`.
  Native idenso simplifies the identities needed by pychete's compact
  `DiracProduct` bridge, including same-chirality projector annihilation around
  a gamma matrix, chirality flips through a gamma matrix, contracted
  `gamma_mu gamma_mu`, and scalar-times-chain results such as
  `gamma_mu gamma_nu gamma_mu`. Unsupported native outputs with Lorentz metric
  factors are intentionally left undecoded until pychete has a full metric
  lowering policy for those forms.
- Symbolica's fixed-arity replacement rules remain the most practical native
  matching surface for mixed `NCM(...)` chains because the current public
  `Expression.match`/`replace_multiple` API does not expose a variadic sequence
  wildcard. The mixed-chain adapter therefore uses Symbolica to match bounded
  `NCM` arities, then applies native idenso only to contiguous Dirac subwords;
  all gamma/projector algebra still happens in idenso.
- Probed native vakint with `verify_numerator_identification=False` on
  coefficient-bearing one-loop topologies. Massive scalar topologies can be
  delegated, but a generated mixed massless/massive one-loop topology currently
  aborts the Python process inside native vakint while looking for a mass
  symbol. pychete therefore guards native vakint analytic evaluation calls for
  unsupported generated topologies and raises a Python `ValueError`; zero-mass
  and mixed-mass analytic evaluation belongs in pychete's separate
  Matchete-style integral backend rather than a local vakint patch. Native
  vakint tensor reduction remains usable because the numerator reduction is
  topology-independent.
- Matchete previous matching-result files store the stages pychete needs:
  `"UV Lagrangian"`, `"Off-shell EFT Lagrangian"`,
  `"On-shell EFT Lagrangian"`, `"SuperTraces"`, and
  `"Matching Conditions"`. VLF has `Matching Conditions -> None`, which made it
  the first practical committed matching fixture. The remaining default targets
  store nontrivial Wolfram rule lists with pattern indices, so the next
  converter slice must lower rule-list matching conditions before exporting
  those fixtures.
- Symbolica parses Wolfram `Log[...]` as native `symbolica::log`, and the
  Matchete parser now preserves it as a Symbolica built-in rather than creating
  a pychete external `log` head. Matchete's `I` parses as Symbolica's imaginary
  numeric atom, so no custom imaginary-unit handling was needed.
- The default Matchete matching-condition rule lists all lower through the
  current parser for the three non-VLF targets. Each of those fixtures carries
  72 matching conditions. The fixture key convention is intentionally canonical
  and machine-oriented; a later public presentation layer can display those
  left-hand sides using `display_string(...)` or `latex_string(...)`.
- `Theory.match(..., loop_order=1)` now has an explicit public contract. It
  returns the current native-backed, explicitly incomplete one-loop
  `MatchingResult` rather than a tree-level expression, with
  `metadata["complete"] == False`. The next matching-engine slices must fill
  the remaining pipeline stages and satisfy `MatchingResult.compare_to(...)`
  against the committed default fixtures before this can be considered a full
  one-loop implementation.
- `MatchingResult.compare_to(...)` now directly supports the approved fallback
  policy for hard-to-canonicalize expressions: canonical strings are compared
  first, and only canonical mismatches are optionally sent through
  `evaluator_probe_equal(...)`, which uses `Expression.evaluator_multiple`.
  The first regression test uses `sin(x)^2 + cos(x)^2` versus `1`, confirming
  the evaluator path can prove equality when canonical expansion does not.
- The first fluctuation-operator extraction layer initially used Symbolica
  `Expression.derivative` after field-to-variable encoding. That path was
  superseded for pychete heads such as `NCM`: algebraic Hessian entries now use
  `partial_functional_derivative(...)`, which normalizes pychete `Bar`, lowers
  multilinear `NCM` variations into ordered fragments, and still delegates
  coefficient extraction to Symbolica `series(...)` and `coefficient(...)`.
  Direct raw derivatives of opaque pychete heads are not suitable for
  noncommutative fermion chains because Symbolica correctly represents them as
  formal function derivatives.
- Automatic fluctuation-basis discovery now uses Symbolica pattern matching
  over `Field(...)` and `Bar(Field(...))` atoms with `req_tag("field")` on the
  field label wildcard. This keeps unregistered field-like test atoms out of
  the basis and makes heavy/light classification depend on Symbolica symbol
  data instead of name conventions.
- Fluctuation-basis entries now carry `FluctuationMode` metadata needed by
  later supertrace construction. The first statistics split distinguishes
  `s.Fermion` labels from all bosonic field types using Symbolica field-type
  data; full spin/multiplicity coefficients are still intentionally deferred
  until the degree-of-freedom metadata model is extended.
- `FluctuationOperator` now keeps mode metadata and can return deterministic
  heavy/light sector blocks. This is the first structural split needed for
  later supertrace generation, where heavy-heavy, heavy-light, light-heavy, and
  light-light blocks have distinct roles.
- `SupertracePlan` now makes those four heavy/light blocks explicit as a public
  pipeline object. The next one-loop matching stages should consume this object
  to construct real Symbolica/idenso/spenso/vakint supertrace contributions
  rather than rebuilding block selection logic elsewhere.
- Rescanned the Symbolica Matrix stub before adding block-kernel traces.
  `Matrix.from_nested(...)`, `Matrix.__mul__`, and `Matrix.__matmul__` are
  available and return matrix entries as `RationalPolynomial`, which can be
  converted back with `to_expression()`. No matrix trace method is exposed in
  the current Python stub, so pychete currently performs only the finite
  diagonal sum after native matrix multiplication.
- `SupertraceBlockTrace` is now the first concrete consumer of
  `SupertracePlan`: closed sector paths such as heavy-heavy and
  heavy-light/light-heavy can be turned into Symbolica expressions that later
  supertrace generation can decorate with propagators, statistics factors,
  momentum expansions, idenso/spenso tensor simplification, and vakint integral
  evaluation.
- `SupertracePlan.closed_block_traces(...)` now provides deterministic
  structural supertrace-kernel generation by block order. This is still only
  sector-path orchestration; the symbolic work for each generated trace remains
  native Symbolica Matrix multiplication, and future slices still need to add
  propagator insertion ordering, EFT truncation, tensor reduction, and vakint
  integral evaluation.
- `OneLoopSetup` is now the public way to inspect the current real one-loop
  pipeline inputs without pretending matching is complete. It connects the
  existing Symbolica-backed Hessian extraction, heavy/light block plan, and
  closed block-kernel generation into one structured object while leaving
  `Theory.match(..., loop_order=1)` reserved for the final end-to-end engine.
- Generated supertrace block kernels can now be sent through idenso with
  `SupertraceBlockTrace.simplify_index_algebra(...)` or
  `OneLoopSetup.simplify_index_algebra(...)`. This establishes the first
  explicit native backend simplification hook inside the one-loop setup path;
  later stages should add spenso tensor-network and vakint integral hooks in
  the same explicit adapter-driven style.
- Generated supertrace block kernels can now also be routed through vakint with
  canonicalization, tensor-reduction, and evaluation methods. These methods
  deliberately only delegate current expressions to vakint; later matching
  slices still need to construct the actual vacuum-integral expressions before
  the vakint stage can yield physical loop contributions.
- Generated supertrace block kernels can now be routed through spenso tensor
  networks with `evaluate_tensor_network(...)` and
  `evaluate_tensor_networks(...)`. The current method extracts scalar results
  through the existing adapter boundary, which is suitable for scalar
  supertrace kernels; future tensor-valued stages may need a sibling API that
  preserves tensor results instead of forcing scalar extraction.
- Completed the twenty-sixth implementation slice:
  - added `pychete.backends.spenso.representation_to_spenso(...)`, lowering
    registered pychete representation metadata to native spenso
    `Representation` objects with cached stable backend names;
  - added `pychete.backends.spenso.cg_tensor_structure_to_spenso(...)`,
    lowering registered `CGTensorDefinition` metadata into native spenso
    `TensorStructure` objects instead of leaving CG tensors as external heads;
  - added `pychete.backends.spenso.indexed_cg_tensor_to_spenso(...)`, lowering
    concrete pychete `CG(label, indices)` expressions to native spenso
    `TensorIndices`;
  - documented these adapter functions in `AGENTS.md` as the standard bridge
    from pychete theory metadata to native spenso objects;
  - added focused tests for complex, conjugate, pseudoreal, and dimensionless
    representation lowering plus built-in Matchete generator CG tensor
    lowering.
- Completed the twenty-seventh implementation slice:
  - added central `CGTensorLabelWildcard` and `CGTensorIndicesWildcard`
    Symbolica pattern symbols to the `SymbolStore`;
  - added `cg_tensor_pattern(...)` so registered pychete CG atoms can be found
    through Symbolica matching with `cg_tensor` tag restrictions;
  - added `pychete.backends.spenso.lower_cg_tensors_to_spenso(...)`, which uses
    Symbolica `Replacement` over the whole expression to replace only
    registered `CG(label, indices)` atoms by native spenso tensor expressions;
  - added `pychete.backends.spenso.evaluate_pychete_tensor_network(...)`, which
    applies that lowering before delegating tensor-network execution to the
    existing native spenso adapter;
  - routed `SupertraceBlockTrace.evaluate_tensor_network(...)` through the
    pychete-aware spenso helper, so one-loop setup kernels now get registered
    CG tensors lowered before network execution;
  - added focused backend and matching tests proving registered CG atoms lower,
    untagged `CG`-like atoms are ignored, and supertrace kernels reach spenso
    without pychete `CG` heads.
- Completed the twenty-eighth implementation slice:
  - added `pychete.backends.spenso.cg_tensor_library_tensor_to_spenso(...)`,
    creating native spenso `LibraryTensor` objects for registered pychete CG
    tensors from explicit component arrays or opt-in generated symbolic
    components;
  - added `pychete.backends.spenso.register_cg_tensor_in_spenso_library(...)`
    and `pychete.backends.spenso.cg_tensor_library_to_spenso(...)`, registering
    pychete CG tensors into native spenso `TensorLibrary` objects;
  - deliberately rejected registration without component data unless
    `symbolic_components=True`, avoiding the unsafe zero-tensor behavior that
    an empty sparse placeholder would imply;
  - threaded optional `cg_components_by_name` and `symbolic_cg_components`
    arguments through `evaluate_pychete_tensor_network(...)`,
    `SupertraceBlockTrace.evaluate_tensor_network(...)`, and
    `OneLoopSetup.evaluate_tensor_networks(...)`;
  - added focused tests for native library lookup, symbolic component
    generation, wrong-sized component rejection, and one-loop trace evaluation
    with a generated spenso CG library.
- Completed the twenty-ninth implementation slice:
  - added `pychete.backends.spenso.builtin_cg_tensor_components(...)` for the
    finite built-in invariant tensors that pychete can safely construct today:
    `builtin:del` identity tensors and `builtin:eps` Levi-Civita tensors;
  - extended CG tensor library registration with `builtin_components=True`,
    registering only supported built-ins and deliberately leaving generator,
    antisymmetric structure, and symmetric structure tensors unregistered until
    they are supplied by spenso/idenso-native support or explicit component
    data;
  - threaded `builtin_cg_components` through
    `evaluate_pychete_tensor_network(...)`,
    `SupertraceBlockTrace.evaluate_tensor_network(...)`, and
    `OneLoopSetup.evaluate_tensor_networks(...)`;
  - added focused tests for SU(2) epsilon components, fundamental delta
    components, selective built-in registration, and one-loop trace evaluation
    through a built-in spenso CG tensor library.
- Completed the thirtieth implementation slice:
  - added `pychete.backends.spenso.native_hep_representation_to_spenso(...)`,
    lowering compatible SU(3) `fund`/`Bar[fund]`/`adj` pychete
    representations to spenso's native HEP `Representation.cof(3)`,
    `dind(cof(3))`, and `Representation.coad(8)` objects;
  - added `pychete.backends.spenso.native_hep_cg_tensor_structure_to_spenso(...)`,
    lowering compatible built-in SU(3) `gen[group[fund]]` and
    `fStruct[group]` CG tensors to spenso's native `TensorName.t()` and
    `TensorName.f()` structures;
  - extended expression lowering and tensor-network evaluation with
    `native_hep_cg_builtins=True`, defaulting to spenso's atom-valued HEP
    tensor library when no library is supplied;
  - deliberately left non-SU(3) groups, adjoint generators, and `dSym` on the
    existing pychete/formal path until native support or explicit component
    data is supplied;
  - added focused backend and one-loop trace tests proving SU(3) generator
    atoms lower to `spenso::t(...)`, structure constants lower to
    `spenso::f(...)`, and the one-loop tensor-network route receives a native
    HEP tensor library.
- Completed the thirty-first implementation slice:
  - added `OneLoopSetup.power_type_matching_result(...)`, which packages the
    current native-backed power-type one-loop result as a `MatchingResult`;
  - the result uses the selected `power_type_vakint_integral_sum(...)` stage as
    both the off-shell and not-yet-reduced on-shell EFT Lagrangian, while
    retaining the EFT-truncated numerator sum as
    `supertraces["power_type_eft_lagrangian"]`;
  - kept `OneLoopSetup.power_type_matching_preview(...)` as a compatibility
    alias to the new result method, so fixture preview helpers now exercise the
    vakint-staged result path;
  - routed `Theory.match(..., loop_order=1)` and `match_one_loop(...)` to this
    incomplete native-backed result instead of raising
    `OneLoopMatchingNotImplementedError`;
  - preserved the explicit incompleteness contract through
    `metadata["complete"] == False`, `metadata["stage"] ==
    "power_type_vakint_result"`, and `metadata["on_shell_reduced"] == False`;
  - added tests proving the public one-loop match entry point returns a
    structured result, the result EFT Lagrangian is the vakint aggregate, and
    the older preview helper retains the numerator aggregate for inspection.
- Completed the thirty-second implementation slice:
  - added native Symbolica-backed vakint Laurent helpers:
    `pychete.backends.vakint.epsilon_symbol(...)`,
    `epsilon_coefficient(...)`, `pole_part(...)`, and `finite_part(...)`;
  - these helpers use Symbolica `Expression.coefficient_list(...)` over
    vakint's epsilon regulator and do not parse Laurent expressions in Python;
  - added `OneLoopSetup.power_type_vakint_epsilon_coefficient(...)`,
    `power_type_vakint_pole_part(...)`, and
    `power_type_vakint_finite_part(...)`, defaulting to the evaluated vakint
    stage where an epsilon Laurent series is expected;
  - extended evaluated `power_type_matching_result(...)` objects with
    `supertraces["power_type_vakint_pole_part"]` and
    `supertraces["power_type_vakint_finite_part"]`;
  - added focused tests for symbolic Laurent coefficient extraction, custom
    epsilon symbols, invalid pole-order validation, and one-loop setup/result
    pole extraction from a fake evaluated vakint Laurent series.
- Completed the thirty-third implementation slice:
  - added `OneLoopSetup.power_type_minimal_subtraction_result(...)`, an
    explicitly incomplete finite-part result over the evaluated vakint
    aggregate;
  - the method evaluates the aggregate once, extracts the negative-power pole
    part and epsilon^0 finite part through the native Symbolica-backed vakint
    helpers, and records a minimal-subtraction-preview counterterm as
    `supertraces["power_type_vakint_ms_counterterm"]`;
  - the returned `MatchingResult` uses the finite part as both off-shell and
    not-yet-reduced on-shell EFT Lagrangians, while metadata records
    `stage="power_type_minimal_subtraction_result"`,
    `subtraction_scheme="minimal_subtraction_preview"`,
    `poles_subtracted=True`, and `complete=False`;
  - added focused tests proving the evaluated vakint aggregate is not evaluated
    more than once for this result path and that the pole, counterterm, finite
    part, and metadata are all exposed for future Matchete fixture comparisons.
- Completed the thirty-fourth implementation slice:
  - extended `FluctuationMode` with derived degree-of-freedom metadata:
    `index_representations`, `index_dimensions`, `internal_dimension`, and
    `supertrace_weight`;
  - dimensions are recovered from existing Symbolica symbol data on registered
    group representations and index-type symbols, so the mode metadata uses the
    same restored theory registry as the rest of pychete;
  - unknown index dimensions remain `None` and therefore produce
    `internal_dimension is None` and `supertrace_weight is None`, avoiding
    silent physics weights when backend metadata is missing;
  - added focused tests covering SU(3) x SU(2) x flavor dimensions for barred
    and unbarred fermion modes, unknown index dimensions, scalar unit
    multiplicity, signed supertrace weights, and public API docstring coverage.
- Completed the thirty-fifth implementation slice:
  - extended `FluctuationMode` with spin/Lorentz and reality-convention
    metadata: `chirality`, `conjugate_mode_count`,
    `spin_lorentz_dimension`, `chiral_supertrace_factor`, and
    `known_component_count`;
  - the metadata is derived from existing Symbolica field-label data and the
    Matchete `SuperTrace.m` convention for chiral fermion half-factors, keeping
    vectors' Lorentz multiplicity as `None` until idenso/spenso-backed metric
    contraction supplies the dimension-dependent trace;
  - added focused tests for Dirac and chiral fermions, gauge vectors, ghosts,
    complex scalar barred/unbarred basis entries, chiral half-factors, known
    spinor component counts, and public API docstring coverage.
- Completed the thirty-sixth implementation slice:
  - added a central `DifferentialOperator` Symbolica head and pretty-printer
    for derivative slots in fluctuation-operator entries;
  - extended `FluctuationOperator` with an optional Euler-Lagrange
    `differential_matrix`, a public `differential_entry(...)` accessor, and
    deterministic `fluctuation_operator_differential[...]` expression-map
    entries;
  - the differential matrix is assembled from existing Symbolica-backed
    `derive_eom(...)`, `partial_functional_derivative(...)`, pattern matches,
    `Expression.series(...)`, `Expression.coefficient(...)`, and
    `Expression.replace_multiple(...)`; the legacy algebraic Hessian matrix is
    kept unchanged for current supertrace previews;
  - added focused tests showing that scalar and barred complex-scalar free
    Lagrangians expose the kinetic operator as
    `-DifferentialOperator({d0, d0}) - m^2` while their algebraic Hessian entry
    remains the mass term.
- Completed the thirty-seventh implementation slice:
  - added `FluctuationOperator.momentum_entry(...)` and
    `momentum_expression_map(...)` for lowering contracted
    `DifferentialOperator` derivative pairs to loop-momentum powers;
  - the lowering uses a Symbolica `Expression.replace(...)` callable over the
    central `DifferentialOperator` head, mapping paired Lorentz derivative slots
    such as `{mu, mu}` to `-LoopMomentumSquared` and therefore scalar inverse
    operators to `q^2 - m^2`;
  - `OneLoopSetup.to_expression_map(...)` now includes the
    `fluctuation_operator_momentum` namespace alongside algebraic and
    differential operator entries;
  - added focused tests for real and barred complex scalar momentum entries,
    deterministic momentum expression maps, setup expression-map exposure, and
    public API docstring coverage.
- Completed the thirty-eighth implementation slice:
  - added `FluctuationOperator.propagator_denominator_entry(...)` and
    `propagator_denominator_expression_map(...)` to recognize scalar inverse
    operators of the form `LoopMomentumSquared - mass^2` as neutral
    `PropagatorDenominator(LoopMomentumSquared, mass^2)` expressions;
  - the recognizer uses native Symbolica `Expression.coefficient_list(...)` to
    verify a linear loop-momentum-squared coefficient and reject unsupported
    higher powers instead of decomposing terms by hand in Python;
  - denominator extraction requires agreement with registered field mass
    metadata by default, so interaction-dependent diagonal entries are not
    silently treated as free propagator masses; callers may opt out for
    inspection with `require_registered_mass=False`;
  - `OneLoopSetup.to_expression_map(...)` now exposes recognized denominators
    under the `fluctuation_operator_denominator` namespace;
  - added focused tests for free real scalars, barred complex scalars,
    deterministic denominator maps, interaction-mass rejection, opt-out
    inspection, and public API docstring coverage.
- Completed the thirty-ninth implementation slice:
  - added `FluctuationOperator.propagator_denominator_for_mode(...)` so a basis
    mode can recover its free propagator denominator directly from the
    momentum-lowered fluctuation operator, including off-diagonal barred/
    unbarred complex-scalar kinetic entries;
  - added `OneLoopSetup.operator_propagator_denominator_chain(...)`,
    `operator_propagator_mass_squared_chain(...)`,
    `operator_propagator_expression(...)`,
    `supertrace_operator_propagator_expression_map(...)`,
    `operator_vakint_integral_expression(...)`, and
    `operator_vakint_integral_expression_map(...)` to align recognized free
    denominators with each closed supertrace path and lower those operator-
    derived mass slots to vakint topologies;
  - the mode-level lookup first uses the strict denominator recognizer and then
    uses native Symbolica `Expression.coefficient_list(...)` through the shared
    unit-linear loop-momentum check to recover the registered free mass when a
    diagonal entry also contains interaction insertions such as `q^2 - m^2 -
    H*y`;
  - bulk expression maps skip unrecognized traces by default so algebraic toy
    setups without kinetic terms still export stable preview data, while direct
    chain/integral methods and `skip_unrecognized=False` keep the operator path
    strict for matching workflows;
  - `OneLoopSetup.to_expression_map(...)` now includes recognized
    `supertrace_operator_propagator_kernel` and `operator_vakint_integral`
    namespaces when inverse-operator denominators are available;
  - added focused tests for complex scalar mode denominator recovery,
    operator-derived scalar propagator insertion chains, decorated kernels,
    vakint topology lowering, setup expression-map exposure, and public API
    docstring coverage.
- Completed the fortieth implementation slice:
  - added `FluctuationOperator.free_inverse_entry(...)`,
    `interaction_entry(...)`, `interaction_expression_map(...)`,
    `interaction_block(...)`, and `interaction_supertrace_plan(...)` so the
    momentum-lowered fluctuation operator can be split into free inverse
    propagation plus interaction insertions;
  - added `OneLoopSetup.interaction_supertrace_plan(...)`,
    `interaction_block_traces(...)`, and
    `interaction_supertrace_expression_map(...)` to expose closed traces built
    from interaction-only heavy/light blocks without changing the legacy
    power-type preview path yet;
  - free inverse subtraction is restricted to the valid real or barred/
    unbarred complex kinetic column and reuses the existing operator-derived
    propagator denominator lookup; the denominator is converted back to
    `LoopMomentumSquared - mass^2`, so diagonal entries such as `q^2 - m^2 -
    H*y` leave only the insertion `-H*y`;
  - `OneLoopSetup.to_expression_map(...)` now includes
    `fluctuation_operator_interaction` and `interaction_supertrace_kernel`
    namespaces for inspecting this propagator-expansion input stage;
  - added focused tests proving that free real scalar diagonal entries vanish
    in the interaction operator, interaction-dependent diagonal entries remain,
    heavy-light interaction traces keep the expected `y^2 phi^2` insertion, and
    the public API docstring coverage includes the new methods.
- Completed the forty-first implementation slice:
  - added `OneLoopSetup.interaction_power_type_traces(...)`,
    `interaction_power_type_contributions(...)`,
    `interaction_power_type_expression_map(...)`,
    `interaction_power_type_eft_lagrangian(...)`,
    `interaction_power_type_vakint_integral_sum(...)`, and
    `interaction_power_type_matching_result(...)` as the first contribution
    path built from the interaction-only fluctuation operator instead of the
    legacy full fluctuation blocks;
  - refactored cyclic trace selection through the shared
    `_cyclically_unique_traces(...)` helper so the legacy and interaction-power
    paths use the same deterministic sector-cycle filtering;
  - the interaction-power aggregate reuses `PowerTypeSupertraceContribution`,
    Symbolica-backed EFT truncation, and the existing native vakint staging
    (`raw`, `canonical`, `tensor_reduced`, `evaluated`) rather than adding any
    Python-side symbolic expansion logic;
  - `OneLoopSetup.to_expression_map(...)` now includes
    `interaction_power_type_supertrace`,
    `interaction_power_type_eft_lagrangian`, and
    `interaction_power_type_vakint_integral_sum` entries so this insertion-only
    contribution path is inspectable next to the legacy preview;
  - added focused tests showing that the interaction-power path keeps only the
    heavy-light insertion contribution for the scalar toy setup, delegates
    canonicalization to the vakint engine, exposes an
    `interaction_power_type_vakint_result` `MatchingResult`, and carries
    explicit `uses_interaction_operator` plus
    `interaction_power_type_contribution_count` metadata.
- Completed the forty-second implementation slice:
  - routed `match_one_loop(...)` and therefore
    `Theory.match(..., loop_order=1)` to
    `OneLoopSetup.interaction_power_type_matching_result(...)`, making the
    public one-loop entry point use the free-propagator/interaction-insertion
    split instead of the legacy full-block power preview;
  - kept `OneLoopSetup.power_type_matching_preview(...)` and
    `power_type_matching_result(...)` available as explicit legacy inspection
    paths, so earlier diagnostics remain accessible while the public matching
    API moves toward the physically relevant propagator expansion;
  - updated `ValidationFixture.one_loop_preview(...)` to build the current
    interaction-power preview from committed model fixtures, preserving the
    Mathematica-independent fixture workflow while exposing
    `metadata["uses_interaction_operator"] == True`;
  - updated focused public-entry tests to assert
    `metadata["stage"] == "interaction_power_type_vakint_result"` and the
    `interaction_power_type_vakint_integral_sum` expression namespace for both
    direct `Theory.match(..., loop_order=1)` and fixture-backed previews.
- Completed the forty-third implementation slice:
  - added interaction-power counterparts to the evaluated-vakint Laurent
    helpers:
    `OneLoopSetup.interaction_power_type_vakint_epsilon_coefficient(...)`,
    `interaction_power_type_vakint_pole_part(...)`, and
    `interaction_power_type_vakint_finite_part(...)`;
  - extended `OneLoopSetup.interaction_power_type_matching_result(...)` so an
    evaluated vakint result records
    `interaction_power_type_vakint_pole_part` and
    `interaction_power_type_vakint_finite_part` in the `MatchingResult`
    supertrace map, matching the legacy power-type inspection surface, and
    corrected its legacy `power_type_contribution_count` metadata to report
    the legacy contribution count separately from
    `interaction_power_type_contribution_count`;
  - added
    `OneLoopSetup.interaction_power_type_minimal_subtraction_result(...)`, an
    explicitly incomplete finite-part result over the interaction-power vakint
    aggregate that records the pole, minimal-subtraction-preview counterterm,
    finite part, `uses_interaction_operator=True`, and
    `subtraction_scheme="minimal_subtraction_preview"`;
  - kept the symbolic extraction in the existing `pychete.backends.vakint`
    helpers, which use Symbolica `Expression.coefficient_list(...)` over
    vakint's epsilon regulator, so this slice adds orchestration around native
    Symbolica/vakint-backed operations rather than Python Laurent parsing;
  - added focused tests covering the new interaction-power epsilon
    coefficient, pole part, finite part, evaluated matching-result exposure,
    minimal-subtraction result metadata, and public API docstring coverage.
- Completed the forty-fourth implementation slice:
  - rescanned Matchete `Package/SuperTrace.m` and `Package/LoopIntegration.m`
    for the power-type prefactor convention: `PowerTypeSTr` applies
    `-I hbar/2` for bosonic propagator classes and the opposite sign for
    fermionic/ghost classes, while `hbar` is documented as the loop-order
    marker understood as the final `1/(16 pi^2)` factor;
  - rescanned the Symbolica Python stubs and used the native `Expression.I`
    and `Expression.PI` constants for the normalization factors instead of
    parsing or string-building constants;
  - added central `s.HBar` Symbolica symbol support, with custom print output
    as `hbar`, `\hbar`, and Mathematica-style `\[HBar]` across pychete's
    output modes;
  - added public `OneLoopNormalization` and
    `one_loop_normalization_factor(...)`, covering the current unnormalized
    preview factor, Matchete's explicit `I*hbar` supertrace factor relative to
    pychete's local `-1/2` contribution convention, and the final
    `I/(16*pi^2)` loop-factor replacement;
  - added
    `OneLoopSetup.interaction_power_type_normalized_matching_result(...)`,
    which preserves the raw interaction-power vakint aggregate for inspection
    while returning off-shell/on-shell EFT Lagrangians scaled by the selected
    loop factor and recording normalized pole/finite pieces when the selected
    vakint stage is evaluated;
  - exported the new normalization enum/helper through `pychete.api` and the
    package root, and added focused coverage for public docstrings, hbar pretty
    printing, raw-vs-normalized result storage, and evaluated normalized
    pole/finite extraction.
- Completed the forty-fifth implementation slice:
  - added `MatchingFixtureGapReport` and
    `ValidationFixture.one_loop_preview_gap_report(...)` so committed
    pychete-owned Matchete fixtures can now be used as explicit acceptance
    targets even while the current interaction-power result is still
    incomplete;
  - the report compares the current one-loop preview result's exposed
    supertrace and matching-condition names to a reference `MatchingResult`,
    records candidate/reference counts, common names, candidate-only names,
    and missing Matchete reference names, and provides JSON plus Jupyter
    `_repr_html_`/`_repr_latex_` output;
  - added a Mathematica-independent integration test over the four default
    Matchete matching targets (`VLF_toy_model`,
    `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`) proving the current
    candidate exposes the three top-level expression stages by common name but
    still lacks all Matchete-named supertrace keys and all nonzero matching
    conditions;
  - this is deliberately a gap-reporting milestone, not an acceptance pass:
    the report makes the remaining validation surface measurable so later
    slices can turn missing-reference counts into canonical or evaluator-backed
    equality checks as the matching engine catches up.
- Completed the forty-sixth implementation slice:
  - added Matchete-style supertrace category names derived from existing
    Symbolica-backed field metadata, so traces now use labels such as
    `hScalar`, `hScalar-lScalar`, `hFermion-lFermion`, and
    `hScalar-lFermion` instead of only heavy/light sector paths;
  - kept the old `SupertracePlan.closed_block_traces(...)` sector diagnostic
    path intact, and added `SupertracePlan.closed_category_traces(...)` plus
    category-restricted blocks for the matching pipeline;
  - routed `one_loop_setup(...)` and interaction-power trace generation through
    the category trace path, including interaction-only plans, so free
    propagation subtraction is preserved while light scalar, fermion, and
    vector paths are no longer collapsed into a single `light` block;
  - exposed raw per-contribution vakint topology expressions directly in
    `MatchingResult.supertraces` under their Matchete-style path names, while
    preserving the existing diagnostic
    `interaction_power_type_supertrace[...]` and aggregate vakint entries;
  - updated the four default fixture gap reports: the current candidate now has
    real shared supertrace keys with the Matchete fixtures
    (`VLF_toy_model`: 5, `Singlet_Scalar_Extension`: 6, `E_VLL`: 6,
    `S1S3LQs`: 9), but this remains a naming/surface-coverage milestone, not
    an equality pass over Matchete's final supertrace expressions.
- Completed the forty-seventh implementation slice:
  - added an explicit `named_supertrace_stage` option to the power-type and
    interaction-power matching-result builders so direct Matchete-style
    supertrace entries can be kept raw or individually sent through native
    vakint canonicalization, tensor reduction, or evaluation;
  - kept aggregate `vakint_stage` separate from the direct-name
    `named_supertrace_stage`, allowing validation code to canonicalize shared
    per-path entries without changing the aggregate off-shell/on-shell preview
    expression;
  - threaded the same option through `ValidationFixture.one_loop_preview(...)`
    and `one_loop_preview_gap_report(...)`, preserving the
    Mathematica-independent fixture workflow while making staged per-name
    comparisons possible;
  - the implementation delegates staged per-name entries to the same native
    `vakint.to_canonical`, `vakint.tensor_reduce`, and `vakint.evaluate`
    adapter functions used elsewhere; no Python integral canonicalization or
    expression rewriting was added.
- Completed the forty-eighth implementation slice:
  - extended `MatchingFixtureGapReport` from name coverage into canonical
    shared-supertrace coverage, adding
    `canonical_equal_common_supertrace_names` and
    `canonical_different_common_supertrace_names` plus JSON and notebook repr
    count output;
  - the report uses the existing `MatchingResult.compare_to(...)` path over
    shared supertrace names, so canonical comparison remains Symbolica-backed
    through the matching result comparison machinery rather than a separate
    validation-only tree walker;
  - recorded the current canonical-equality frontier for the four default
    Matchete targets: `VLF_toy_model` has 0/5 equal shared supertraces,
    `Singlet_Scalar_Extension` has 0/6, `E_VLL` has 3/6, and `S1S3LQs` has
    3/9;
  - this turns future matching-engine work into a measurable acceptance target:
    later slices should move names from the canonical-different set into the
    canonical-equal set while reducing missing-reference counts.
- Completed the forty-ninth implementation slice:
  - removed formal Symbolica `der(...)` artifacts from noncommutative fermion
    variation paths by routing the algebraic fluctuation matrix through
    `partial_functional_derivative(...)` instead of differentiating opaque
    pychete heads directly;
  - added a derivative-safe pychete `Bar` normalizer for variation extraction
    so conjugated Yukawa terms such as `Bar[-y phi NCM[bar(psi), PR, Psi]]`
    expose `bar(y)`, self-conjugate scalar fields, reversed
    noncommutative chains, and the expected `PR <-> PL` conjugation before
    coefficient extraction;
  - added NCM multilinearization for both functional-variation and
    covariant-derivative variation parameters: Symbolica still performs the
    coefficient extraction through `series(...)` and `coefficient(...)`, while
    pychete only lowers the custom `NCM` head into first-order ordered chain
    fragments because native Symbolica derivatives of arbitrary function
    arguments intentionally produce formal `der(...)` heads;
  - removed the old temporary-variable Hessian helpers
    `_fluctuation_variable`, `_encode_fluctuation_basis`, and
    `_decode_fluctuation_basis`, which were the source of the opaque-function
    derivative artifacts;
  - added regression coverage for a VLF-like fermion/scalar Yukawa interaction
    proving that algebraic, differential, momentum-lowered, and interaction
    fluctuation entries contain no formal `der(...)` artifacts and that the
    direct/conjugated `P_R`/`P_L` coefficients are extracted as ordered
    noncommutative fragments;
  - checked the live `VLF_toy_model` one-loop preview after the change:
    all 47 candidate named supertraces are now free of formal `der(...)`
    artifacts, though canonical equality against Matchete remains unchanged at
    0/5 shared supertraces because Dirac-chain normalization, phase/sign
    conventions, and vakint evaluation are still future slices.
- Completed the fiftieth implementation slice:
  - added `pychete.backends.idenso.simplify_pychete_dirac_projectors(...)` as
    a narrow backend-boundary bridge for pychete's compact `P_R`/`P_L` symbols;
  - the bridge lowers projector-only words to native spenso
    `spenso::projp`/`spenso::projm` tensors from `TensorLibrary.hep_lib()`,
    delegates the algebra to native `idenso.simplify_gamma(...)`, and decodes
    only simple scalar/projector outputs back to pychete symbols;
  - mixed products such as `P_R P_L` and `P_L P_R` are also resolved by the
    native idenso bridge rather than by handwritten Python zero rules;
  - `simplify_index_algebra(...)` now runs this projector bridge before and
    after the native idenso pipeline, and
    `PowerTypeSupertraceContribution.numerator_expression` applies it before
    EFT numerator truncation and vakint lowering;
  - added unit and integration coverage proving that powers such as `P_R^3`
    and `P_L^2` collapse to single projectors, mixed products collapse to
    zero, and a VLF-like one-loop numerator no longer exposes
    `pychete::PR^2`/`pychete::PL^2` before vakint lowering;
  - the live VLF `hFermion-lFermion` preview numerator now uses linear
    `P_R`/`P_L` factors instead of projector powers, but canonical equality
    against Matchete remains unchanged at 0/5 shared supertraces because
    conjugation/orientation, full open Dirac-chain lowering, and final vakint
    evaluation are still unresolved.
- Completed the fifty-first implementation slice:
  - extended the idenso bridge from projector-only products to compact pychete
    `DiracProduct(...)` words and all-Dirac `NCM(...)` words containing
    `P_R`, `P_L`, and one-index `Gamma(...)` factors;
  - the new `simplify_pychete_dirac_algebra(...)` helper first applies the
    projector bridge, then uses Symbolica replacement rules over fixed-arity
    `DiracProduct` and pure-Dirac `NCM` patterns, lowers matched words to
    native spenso `gamma`/`projp`/`projm` tensors, delegates to
    `idenso.simplify_gamma(...)`, and decodes only supported native chain,
    spinor-identity, scalar, sum, and product outputs back to pychete
    expressions; the fixed replacement-rule tuples and native HEP tensor
    lookups are cached so repeated simplification does not rebuild that
    backend boundary metadata;
  - verified native-backed identities including `P_R gamma_mu P_R -> 0`,
    `P_L gamma_mu P_L -> 0`, `P_R gamma_mu P_L -> gamma_mu P_L`,
    `gamma_mu gamma_mu -> 4`, and
    `gamma_mu gamma_nu gamma_mu -> -2 gamma_nu`;
  - replacement ordering now simplifies nested `DiracProduct(...)` factors
    inside mixed noncommutative chains without rewriting the surrounding
    non-Dirac operands;
  - `simplify_index_algebra(...)` and
    `PowerTypeSupertraceContribution.numerator_expression` now use the broader
    pychete Dirac-algebra bridge rather than the projector-only helper;
  - the default Matchete validation frontier remains unchanged, which means
    the next equality-moving slice must handle full field-endpoint open-chain
    orientation/conjugation and remaining vakint normalization rather than only
    compact `DiracProduct` identities.
- Completed the fifty-second implementation slice:
  - extended `simplify_pychete_dirac_algebra(...)` with a mixed-`NCM`
    contiguous-subword pass: Symbolica replacement rules match bounded
    `NCM(...)` arities, the adapter identifies contiguous runs of pychete
    Dirac factors inside the chain, and each run is lowered to native
    spenso/idenso for the actual gamma/projector simplification;
  - supported native outputs are reinserted carefully into the surrounding
    noncommutative chain: zero Dirac subwords annihilate the whole chain,
    scalar outputs such as `gamma_mu gamma_mu -> 4` are extracted as
    commutative coefficients, and non-scalar supported outputs are kept as
    compact `DiracProduct(...)` operands;
  - unsupported native outputs are left untouched, preserving the original
    mixed `NCM(...)` chain until pychete has a full Lorentz-metric and
    field-endpoint lowering policy;
  - added focused backend tests for `NCM(left, P_R, gamma_mu, P_R, right) -> 0`,
    `NCM(left, P_R, gamma_mu, P_L, right) ->
    NCM(left, DiracProduct(gamma_mu, P_L), right)`, and scalar extraction from
    `NCM(left, gamma_mu, gamma_mu, right)`;
  - added an integration-level test proving
    `PowerTypeSupertraceContribution.numerator_expression` applies this mixed
    `NCM` bridge before EFT truncation, so the one-loop matching path benefits
    from the backend adapter rather than only direct backend callers.
- Completed the fifty-third implementation slice:
  - added a pychete-side preflight guard around native vakint
    `to_canonical(...)`, `tensor_reduce(...)`, `evaluate_integral(...)`, and
    `evaluate(...)` calls for generated one-loop topologies with zero-mass
    propagators;
  - this guard was added after a managed-venv probe showed that native vakint
    can abort the Python process, rather than raising a catchable exception,
    for a mixed massless/massive generated topology even when
    `verify_numerator_identification=False` is passed to the native engine;
  - the guard uses Symbolica matching to find `vakint::topo(...)` subexpressions
    and only inspects the matched `vakint::prop(..., mass_squared, ...)` mass
    slots at the backend boundary; no integral reduction or symbolic
    integration logic was implemented in Python;
  - added unit coverage proving unsafe massless topologies raise `ValueError`
    before a fake native engine is called, preserving the existing delegation
    behavior for massive topologies.
- `OneLoopSetup` now exposes `propagator_plan(...)` and `propagator_count`,
  backed by `FluctuationPropagator` and `PropagatorPlan`. Heavy and optional
  light propagator metadata recover mass expressions through Symbolica
  field-label data via `field_mass_expr_from_label(...)`, so no Python field
  enumeration or name convention is used to find masses. This is still a
  planning layer: future slices must use these mass and mass-squared
  expressions to build real loop-momentum denominators and EFT propagator
  expansions.
- Rescanned the Symbolica Python stubs for `Expression.series`,
  `Expression.coefficient`, `Expression.collect`, `Expression.derivative`,
  `Expression.match`, `Expression.matches`, `Expression.replace_multiple`, and
  `Transformer.series` before extending the propagator stage. The current slice
  adds central Symbolica heads `LoopMomentumSquared`,
  `PropagatorDenominator`, and `SupertraceKernel`; it deliberately does not
  choose a Minkowski/Euclidean sign convention yet.
- `FluctuationPropagator.denominator(...)` now builds neutral Symbolica
  denominator expressions, and `SupertraceBlockTrace` can expose
  `propagator_denominator_chain(...)` plus `propagator_expression(...)`.
  `OneLoopSetup.supertrace_propagator_expression_map(...)` provides all
  generated trace kernels decorated with denominator slots, so the next vakint
  lowering slice has explicit Symbolica input rather than implicit Python-side
  bookkeeping.
- Rescanned vakint's Python stub and local Rust source for the accepted
  integral shape. vakint expects sums of numerator terms times
  `vakint::topo(vakint::prop(...)*...)`, with tensor reduction and evaluation
  delegated through `Vakint.to_canonical`, `Vakint.tensor_reduce`, and
  `Vakint.evaluate`.
- `pychete.backends.vakint` now has explicit Symbolica constructors for
  `vakint::k`, `vakint::edge`, `vakint::prop`, `vakint::topo`, one-loop
  vacuum topologies, and one-loop vacuum integrals. The one-loop setup can now
  lower each supertrace block trace into that vakint topology form with
  `SupertraceBlockTrace.vakint_integral_expression(...)` and
  `OneLoopSetup.vakint_integral_expression_map(...)`.
- `OneLoopSetup` also exposes native-delegating map methods for canonicalizing,
  tensor-reducing, and evaluating those lowered vakint integral expressions.
  This is still a structural lowering stage: the expressions use the current
  denominator-slot ordering and need subsequent physics work for final
  propagator sign conventions, EFT expansion, and known-topology validation.
- Rescanned Matchete's `SuperTrace.m` power-type trace construction. Matchete
  deduplicates power traces under cyclic permutations and applies a common
  `-I hbar/2` prefactor, with the boson/fermion grading carried separately by
  the propagating type. pychete's current block trace already carries the
  grading sign in the Symbolica matrix supertrace, so the new contribution
  layer uses a convention-local `-1/2` prefactor and keeps the missing loop
  normalization/phase explicit as remaining work.
- Rescanned Matchete's `LoopIntegration.m` convention for `hbar`. Matchete
  documents `hbar` as the loop-order marker understood as the final
  `1/(16 pi^2)` factor, while the scalar-integral prefactors carry their own
  factors of `I`. pychete now exposes both explicit Symbolica normalization
  choices: `OneLoopNormalization.MATCHETE_HBAR` gives `I*s.HBar`, and
  `OneLoopNormalization.MATCHETE_LOOP_FACTOR` gives
  `I/(16*Expression.PI**2)`. Future fixture comparisons must still validate
  the backend integral phase against vakint output before promoting either
  normalized preview to a complete matching result.
- Added `PowerTypeSupertraceContribution` and `OneLoopSetup.power_type_*`
  helpers. These expose cyclically unique power-type traces, prefactor-weighted
  numerators, EFT-truncated numerators through the existing Symbolica-backed
  `series_eft(...)`, and vakint topology expressions built from the truncated
  numerators. This is the first structured bridge from setup kernels toward
  final `MatchingResult.supertraces`.
- Added aggregate power-type inspection outputs on `OneLoopSetup`.
  `power_type_eft_lagrangian(...)` now sums the cyclically unique
  EFT-truncated power-type numerators into a single off-shell contribution, and
  `power_type_vakint_integral_sum(...)` sums the corresponding vakint topology
  expressions. The aggregation is intentionally thin Python orchestration over
  Symbolica expressions: the symbolic EFT truncation remains in
  `series_eft(...)`, the integral shape is built through the vakint adapter,
  and the final algebraic cleanup is delegated to Symbolica `Expression.expand`.
  This gives the future `MatchingResult.off_shell_eft_lagrangian` and
  `MatchingResult.supertraces` stages a concrete intermediate value.
- Added `OneLoopSetup.power_type_matching_preview(...)`, which builds an
  explicitly incomplete `MatchingResult` from the current one-loop setup
  stages. Later slices promoted the vakint topology sum to the result EFT
  Lagrangian, but the result remains marked `complete=False` until full
  on-shell reduction and matching-condition extraction are implemented.
- Added public `VakintIntegralStage` selectors and routed aggregate power-type
  vakint sums through the native vakint adapter. `power_type_vakint_integral_sum`
  now supports raw, canonical, tensor-reduced, and evaluated stages, delegating
  non-raw work to `vakint.to_canonical`, `vakint.tensor_reduce`, and
  `vakint.evaluate` respectively. `power_type_matching_preview(...)` can carry
  a selected aggregate vakint stage and records the stage in metadata, giving
  the future one-loop result pipeline an explicit native-backend hook without
  creating a default vakint engine unless the user requests a non-raw stage.
- Rescanned Symbolica's `Matrix` stub and confirmed that the native matrix type
  is rational-polynomial based. `SupertracePlan` now keeps the native
  `Matrix.from_nested(...)`/matrix-product path as the default, but falls back
  to expression-matrix multiplication only when Symbolica rejects entries that
  cannot be converted to rational polynomials. This fallback is intentionally
  narrow and exists to unblock indexed/backend-function expressions in real
  model fixtures; it is not a replacement for native Symbolica matrix algebra.
- The four committed default Matchete model fixtures now all build the first
  `heavy-heavy` one-loop setup kernel without Mathematica. This validates the
  fixture-to-setup path for `VLF_toy_model`, `Singlet_Scalar_Extension`,
  `E_VLL`, and `S1S3LQs` at the current setup depth. At this point, broader
  preview generation exposed a later EFT-series truncation bottleneck.
- Rescanned Symbolica's `Expression.coefficient_list` and `Expression.series`
  APIs for EFT truncation. `series_eft(...)` now uses the same native
  marker-coefficient extraction for inclusive and exact EFT-order selection,
  instead of asking Symbolica to build a full formal series for the inclusive
  path. This remains native Symbolica algebra over the `EFTExpansionParameter`
  marker but avoids the large-series bottleneck observed when building
  power-type previews for real model fixtures.
- With coefficient-list EFT truncation, the four committed default Matchete
  model fixtures now build the first incomplete one-loop
  `power_type_matching_preview(...)` without Mathematica. The preview is still
  explicitly marked incomplete, but this moves the default target fixtures one
  stage further along the actual pychete one-loop result surface.
- Added `ValidationFixture.one_loop_preview(...)` as the fixture-backed entry
  point for building the current incomplete one-loop preview from committed
  pychete assets. This keeps normal pytest Mathematica-independent while giving
  future Matchete acceptance tests a stable path from fixture state to candidate
  `MatchingResult`. The default target model fixtures now build
  `power_type_matching_preview(...)` through this helper at
  `max_trace_order=3`, covering eleven generated kernels and six cyclically
  unique power-type contributions per model.
- Rescanned vakint's one-loop examples and parser tests for propagator power
  conventions. `pychete.backends.vakint.one_loop_vacuum_topology(...)` now
  combines repeated equal mass-squared denominator slots into a single vakint
  propagator with summed power, e.g. two identical one-loop denominators become
  `vakint::prop(..., mass_squared, 2)` rather than two duplicate propagator
  factors. This makes current power-type lowering closer to vakint's native
  topology representation for repeated single-scale denominators.
- Rescanned the spenso Python stubs for `Representation`, `TensorName`,
  `TensorStructure`, and `TensorIndices`, and exercised the constructors in the
  managed venv. Native spenso representations are globally registered by name;
  constructing the same name with incompatible duality can abort the Python
  process from Rust, so pychete now uses stable dimension/reality-qualified
  backend names plus an adapter-side cache when lowering representations.
- Rescanned Symbolica's `Expression.replace`, `Expression.replace_multiple`,
  and `Replacement` stubs before adding expression-wide CG lowering. Callable
  replacements receive wildcard bindings and are suitable for lowering matched
  atoms to backend-native expressions, while Symbolica owns the traversal over
  the larger expression.
- Rescanned spenso's `LibraryTensor` and `TensorLibrary` stubs and exercised
  `LibraryTensor.dense(...)`, `LibraryTensor.sparse(...)`, and
  `TensorLibrary.register(...)` in the managed venv. `LibraryTensor.sparse(...)`
  creates an initially zero sparse tensor, so pychete must not use it as an
  unknown-component placeholder. Dense tensors with explicit or generated
  symbolic entries are the safe formal registration path for now.
- For built-in CG components, `del[...]` and `eps[...]` are finite component
  tensors that can be constructed deterministically from representation
  dimensions and handed to spenso as dense `LibraryTensor` objects. Generator
  and structure-constant tensors are not constructed locally in Python in this
  slice; they still need idenso/spenso-native support or explicit component
  input.
- Rescanned spenso's HEP tensor APIs and exercised `TensorName.t()`,
  `TensorName.f()`, `Representation.cof(3)`, `Representation.coad(8)`, and
  `TensorLibrary.hep_lib_atom()` in the managed venv. The native HEP library
  exposes `spenso::t` with rank `8 x 3 x 3bar` and `spenso::f` with adjoint
  rank `8 x 8 x 8`; `TensorName.f()` may canonicalize index order with an
  antisymmetric sign. pychete now maps only compatible SU(3) built-ins to
  those native names.
- Rescanned vakint's Python stubs and Rust implementation around epsilon
  handling. Native vakint stores/returns Laurent data in the configured
  epsilon regulator and `VakintNumericalResult.to_list()` exposes
  `(epsilon exponent, complex coefficient)` pairs. Symbolica
  `Expression.coefficient_list(epsilon)` also directly returns symbolic
  Laurent powers, including negative powers such as `epsilon^-1`, so pychete's
  symbolic pole helpers now use that native coefficient extraction instead of
  a parser or tree walker.

## Test Status

- `dependencies/.venv/bin/python -m pytest
  tests/unit/backends/test_idenso_backend.py::test_idenso_pipeline_simplifies_pychete_projectors_through_native_bridge
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_simplifies_projector_words_before_vakint_lowering
  -q` passed after the projector bridge slice: 2 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the projector bridge
  slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  -q` passed after the projector bridge slice: 1 passed.
- `dependencies/.venv/bin/python -m pytest tests/unit/backends
  tests/integration/matching tests/integration/validation -q` passed after
  the projector bridge slice: 90 passed.
- `dependencies/.venv/bin/python -m pytest tests -q` passed after the
  projector bridge slice: 163 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `git diff --check` passed after the projector bridge slice.
- The default-target canonical frontier remains unchanged after the projector
  bridge slice: VLF has 0/5 equal shared supertraces, Singlet has 0/6,
  E_VLL has 3/6, and S1S3LQs has 3/9. The VLF
  `hFermion-lFermion` numerator no longer contains `P_R^2`/`P_L^2`.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/backends/test_idenso_backend.py -q` passed after the compact
  DiracProduct bridge slice: 7 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the compact
  DiracProduct bridge slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  -q` passed after the compact DiracProduct bridge slice: 1 passed. The
  default-target canonical frontier remains unchanged by this slice.
- `dependencies/.venv/bin/python -m pytest tests -q` passed after the compact
  DiracProduct bridge slice: 165 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `git diff --check` passed after the compact DiracProduct bridge slice.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/backends/test_idenso_backend.py
  tests/integration/matching/test_fluctuation_operator.py::test_power_type_numerator_simplifies_mixed_ncm_dirac_subwords_before_eft_truncation
  -q` passed after the mixed `NCM` contiguous-subword bridge slice: 9 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the mixed `NCM`
  contiguous-subword bridge slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  -q` passed after the mixed `NCM` contiguous-subword bridge slice: 1 passed.
  The default-target canonical frontier remains unchanged by this slice.
- `dependencies/.venv/bin/python -m pytest tests -q` passed after the mixed
  `NCM` contiguous-subword bridge slice: 167 passed, 1 skipped. The skip is
  the existing GammaLoop API import check because GammaLoop was not requested
  in the current dependency manifest.
- `git diff --check` passed after the mixed `NCM` contiguous-subword bridge
  slice.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/backends/test_vakint_backend.py -q` passed after the native-vakint
  zero-mass topology guard slice: 11 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the native-vakint
  zero-mass topology guard slice: no issues found in 24 source files.
- A direct managed-venv probe of
  `vakint.to_canonical(vakint.one_loop_vacuum_integral(num, (0, m^2)), engine=vakint.create_engine(verify_numerator_identification=False))`
  now raises a catchable Python `ValueError` before entering native vakint.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  -q` passed after the native-vakint zero-mass topology guard slice: 1 passed.
- `dependencies/.venv/bin/python -m pytest tests -q` passed after the
  native-vakint zero-mass topology guard slice: 171 passed, 1 skipped. The skip
  is the existing GammaLoop API import check because GammaLoop was not
  requested in the current dependency manifest.
- `git diff --check` passed after the native-vakint zero-mass topology guard
  slice.
- `dependencies/.venv/bin/python -m pytest tests/integration/validation/test_validation_fixtures.py`
  passed: 3 passed.
- `dependencies/.venv/bin/python -m mypy` passed: no issues found in 18 source
  files.
- `dependencies/.venv/bin/python -m pytest tests` passed: 58 passed, 1 skipped.
  The skip is the existing GammaLoop API import check because GammaLoop was not
  requested in the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed: 10 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the `MatchingResult`
  slice: no issues found in 18 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  `MatchingResult` slice: 60 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py` passed: 3 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the numeric-probe slice:
  no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the numeric-probe
  slice: 63 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_public_api.py` passed after the field metadata
  slice: 16 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the field metadata slice:
  no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the field
  metadata slice: 64 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/definitions/test_theory_definitions.py` passed after the committed
  fixture slice: 14 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the committed fixture
  slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the committed
  fixture slice: 65 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py` passed after the coupling
  metadata slice: 16 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the coupling metadata
  slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the coupling
  metadata slice: 69 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py` passed after the
  default model asset slice: 6 passed.
- `dependencies/.venv/bin/python -m pytest tests` passed after the default
  model asset slice: 69 passed, 1 skipped. The skip is the existing GammaLoop
  API import check because GammaLoop was not requested in the current dependency
  manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/models/test_model_loaders.py
  tests/integration/validation/test_validation_fixtures.py` passed after the
  parent-model metadata fixture slice: 14 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the parent-model metadata
  fixture slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  parent-model metadata fixture slice: 72 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in the
  current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/models/test_model_loaders.py
  tests/integration/validation/test_validation_fixtures.py` passed after the
  child-Lagrangian fixture slice: 15 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the child-Lagrangian
  fixture slice: no issues found in 19 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  child-Lagrangian fixture slice: 73 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest tests/unit/backends` passed after
  the backend-adapter slice: 10 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the backend-adapter
  slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  backend-adapter slice: 83 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/loaders/test_mathematica_result_parser.py
  tests/integration/validation/test_validation_fixtures.py` passed after the
  VLF matching-fixture slice: 10 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the VLF
  matching-fixture slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the VLF
  matching-fixture slice: 86 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/loaders/test_mathematica_result_parser.py` passed after the
  default matching-fixture conversion slice: 10 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the default
  matching-fixture conversion slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the default
  matching-fixture conversion slice: 86 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_heavy_scalar_tree.py
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/definitions/test_public_api.py` passed after the matching API
  comparison slice: 20 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the matching API
  comparison slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the matching API
  comparison slice: 89 passed, 1 skipped. The skip is the existing GammaLoop
  API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py
  tests/unit/definitions/test_public_api.py
  tests/integration/validation/test_validation_fixtures.py` passed after the
  comparison-probe slice: 18 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the comparison-probe
  slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  comparison-probe slice: 91 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the fluctuation-operator slice: 9 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the fluctuation-operator
  slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  fluctuation-operator slice: 95 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the fluctuation-basis slice: 12 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the fluctuation-basis
  slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  fluctuation-basis slice: 98 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the fluctuation-mode metadata slice: 13 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the fluctuation-mode
  metadata slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  fluctuation-mode metadata slice: 99 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the fluctuation-sector block slice: 16 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the fluctuation-sector
  block slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  fluctuation-sector block slice: 102 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the supertrace-plan slice: 17 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the supertrace-plan
  slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  supertrace-plan slice: 103 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the supertrace-block-trace slice: 19 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  supertrace-block-trace slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  supertrace-block-trace slice: 105 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the closed-supertrace-path slice: 19 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  closed-supertrace-path slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  closed-supertrace-path slice: 106 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the one-loop-setup slice: 21 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the one-loop-setup
  slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  one-loop-setup slice: 107 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the idenso-kernel-simplification slice: 21 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  idenso-kernel-simplification slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  idenso-kernel-simplification slice: 108 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the vakint-kernel-transformation slice: 22 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  vakint-kernel-transformation slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  vakint-kernel-transformation slice: 109 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the spenso-kernel-evaluation slice: 23 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  spenso-kernel-evaluation slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  spenso-kernel-evaluation slice: 110 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the propagator-planning slice: 25 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  propagator-planning slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  propagator-planning slice: 111 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py`
  passed after the supertrace-denominator-chain slice: 32 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  supertrace-denominator-chain slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  supertrace-denominator-chain slice: 112 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/backends/test_vakint_backend.py
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the vakint-topology-lowering slice: 28 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  vakint-topology-lowering slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  vakint-topology-lowering slice: 113 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks`
  passed after the power-type-contribution slice: 25 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  power-type-contribution slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  power-type-contribution slice: 113 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the power-type-aggregation slice: 24 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  power-type-aggregation slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  power-type-aggregation slice: 113 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the power-type-preview-result slice: 24 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  power-type-preview-result slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  power-type-preview-result slice: 113 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/unit/definitions/test_public_api.py`
  passed after the power-type-vakint-stage slice: 24 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  power-type-vakint-stage slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  power-type-vakint-stage slice: 113 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/definitions/test_public_api.py`
  passed after the expression-matrix-supertrace-fallback slice: 35 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  expression-matrix-supertrace-fallback slice: no issues found in 24 source
  files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  expression-matrix-supertrace-fallback slice: 115 passed, 1 skipped. The skip
  is the existing GammaLoop API import check because GammaLoop was not
  requested in the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/eft/test_eft_counting.py
  tests/integration/validation/test_validation_fixtures.py
  tests/integration/matching/test_fluctuation_operator.py`
  passed after the coefficient-list-EFT-truncation slice: 35 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  coefficient-list-EFT-truncation slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  coefficient-list-EFT-truncation slice: 115 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py
  tests/unit/eft/test_eft_counting.py
  tests/integration/matching/test_fluctuation_operator.py`
  passed after the fixture-one-loop-preview-helper slice: 35 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  fixture-one-loop-preview-helper slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  fixture-one-loop-preview-helper slice: 115 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `dependencies/.venv/bin/python -m pytest
  tests/unit/backends/test_vakint_backend.py
  tests/integration/matching/test_fluctuation_operator.py`
  passed after the powered-vakint-denominator slice: 26 passed.
- `dependencies/.venv/bin/python -m mypy` passed after the
  powered-vakint-denominator slice: no issues found in 24 source files.
- `dependencies/.venv/bin/python -m pytest tests` passed after the
  powered-vakint-denominator slice: 116 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- Added the field-role metadata slice needed for Matchete-style one-loop field
  classification:
  - introduced public `FieldRole` enum values `PHYSICAL`, `GHOST`,
    `ANTI_GHOST`, `GOLDSTONE`, and `BACKGROUND`;
  - added field-label Symbolica symbol data keys for `field_role`,
    `propagating`, and `zero_mode`, plus field-role/propagation/zero-mode
    Symbolica tags created directly on the theory-owned field symbols;
  - made `Theory._restore_symbol_manifest(...)` normalize restored tag names
    and augment older manifests with field-role tags from restored symbol data,
    while still requiring all manifest-declared tags to be present;
  - exposed role/progression metadata through `FieldDefinition.role`,
    `is_ghost`, `is_goldstone`, `is_background`, `is_propagating`, and
    `is_zero_mode`;
  - taught the Matchete loader to preserve `Ghost`, `AntiGhost`,
    `GoldstoneBoson`, `BackgroundField`, `ZeroMode`, and explicit
    `Propagating`/`NonPropagating` field metadata;
  - kept fluctuation-basis discovery Symbolica-pattern based, but now filters
    non-propagating/background fields through field-label symbol data and
    grades ghost/anti-ghost modes with the fermionic supertrace sign.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py
  tests/integration/matching/test_fluctuation_operator.py'`
  passed after the field-role metadata slice: 44 passed.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m mypy'`
  passed after the field-role metadata slice: no issues found in 24 source
  files.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests'` passed after the field-role metadata slice: 120 passed, 1 skipped.
  The skip is the existing GammaLoop API import check because GammaLoop was not
  requested in the current dependency manifest.
- Added the global-group metadata slice required for Matchete model/theory
  coverage:
  - introduced public `GroupKind` enum values `GAUGE` and `GLOBAL`;
  - added group-label Symbolica symbol data keys for `group_kind` and
    `group_abelian`, plus `group_kind_*` and abelian/non-abelian tags on
    theory-owned group symbols;
  - extended gauge group metadata to record explicit kind and abelian status
    while preserving coupling and vector-field information;
  - added `Theory.define_global_group(...)` for global symmetry groups with no
    gauge coupling or vector field;
  - made JSON restore normalize older gauge-only group entries and reconstruct
    group-kind tags from restored Symbolica symbol data;
  - taught the Matchete loader to parse `DefineGlobalGroup[grName, lieGroup]`,
    so global-group representations such as `SU2F[fund]` and global U(1)
    charges can be stored in field metadata.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_public_api.py'` passed after the global-group
  metadata slice: 28 passed.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m mypy'`
  passed after the global-group metadata slice: no issues found in 24 source
  files.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests'` passed after the global-group metadata slice: 122 passed, 1 skipped.
  The skip is the existing GammaLoop API import check because GammaLoop was not
  requested in the current dependency manifest.
- Added the representation metadata slice needed by Matchete models using
  `DefineRepresentation[Group[label], Group, Dynkin]`:
  - introduced public `RepresentationReality` and `RepresentationDefinition`
    objects, exported through `pychete.api` and the package root;
  - added `Theory.define_representation(...)` for gauge/global group
    representations, preserving central built-ins `fund` and `adj` while
    turning model-specific labels such as `quad` into theory-owned Symbolica
    symbols;
  - stored representation metadata directly on model-specific Symbolica labels
    through `representation_group`, `representation_dynkin`,
    `representation_dimension`, and `representation_reality` symbol data, plus
    `representation_group_*` and `representation_reality_*` tags;
  - serialized the representation registry in theory checkpoints and restored
    it after the symbol manifest and group registry, before field/coupling
    metadata that may reference representation expressions;
  - taught the Matchete loader to parse `DefineRepresentation[...]`, including
    `G[rep]` and `G@rep` representation names, so field/coupling index
    expressions such as `SU2L[quad]` use the registered Symbolica label rather
    than an untagged external symbol;
  - kept backend-computed representation dimensions and Frobenius-Schur
    indicators as explicit metadata for now. Loader-defined representations
    preserve Dynkin coefficients and use `RepresentationReality.UNKNOWN`
    when no native or conservative pychete inference path is available.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_public_api.py'` passed after the representation
  metadata slice: 30 passed.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m mypy'`
  passed after the representation metadata slice: no issues found in 24 source
  files.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests'` passed after the representation metadata slice: 124 passed, 1
  skipped. The skip is the existing GammaLoop API import check because
  GammaLoop was not requested in the current dependency manifest.
- Added a follow-up representation-metadata inference slice after checking the
  spenso/idenso Python stubs for native group-theory support:
  - spenso exposes tensor-network `Representation` objects once dimension and
    self-duality are known, but the current Python stub does not expose
    Dynkin-to-dimension or Frobenius-Schur-indicator computation;
  - idenso exposes gamma/colour/metric/index simplification functions, but not
    representation-dimension or representation-reality inference;
  - pychete now conservatively auto-registers built-in `fund` and `adj`
    representations when non-Abelian gauge/global groups are registered;
  - for `SU(N)` built-ins, pychete records fundamental dimension `N`, adjoint
    dimension `N^2 - 1`, real adjoint reality, complex `SU(N>2)`
    fundamentals, and pseudoreal `SU(2)` fundamentals;
  - for explicit `SU(2)` Dynkin labels such as Matchete's scalar quadruplet
    `DefineRepresentation[SU2L[quad], SU2L, {3}]`, pychete records dimension
    `n + 1` and real/pseudoreal parity from the Dynkin coefficient;
  - explicit user-provided dimension/reality metadata continues to override
    inference, and unsupported representations remain
    `RepresentationReality.UNKNOWN`.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_public_api.py'` passed after the
  representation-inference slice: 30 passed.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m mypy'`
  passed after the representation-inference slice: no issues found in 24 source
  files.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests'` passed after the representation-inference slice: 124 passed, 1
  skipped. The skip is the existing GammaLoop API import check because
  GammaLoop was not requested in the current dependency manifest.
- Added the conjugate-representation lookup slice needed by models such as
  `S1S3LQs`, where fields carry `Bar@SU3c[fund]` index representations:
  - added `Theory.representation_definition(...)`,
    `Theory.representation_dimension(...)`,
    `Theory.representation_reality(...)`, and
    `Theory.is_conjugate_representation(...)`;
  - direct registered representation expressions resolve normally, and
    syntactic `Bar(rep)` wrappers resolve through the underlying registered
    representation metadata without adding duplicate registry entries;
  - the `S1S3LQs` loader test now verifies that the leptoquark colour index is
    recognized as a conjugate `SU3c[fund]` representation with dimension `3`
    and complex reality.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_public_api.py'` passed after the
  conjugate-representation lookup slice: 31 passed.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m mypy'`
  passed after the conjugate-representation lookup slice: no issues found in
  24 source files.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests'` passed after the conjugate-representation lookup slice: 125 passed,
  1 skipped. The skip is the existing GammaLoop API import check because
  GammaLoop was not requested in the current dependency manifest.
- Added the CG tensor metadata and loader slice needed by Matchete models such
  as `Scalar_quadruplet` and later CG-manipulation validation tests:
  - checked the spenso Python stub and confirmed it exposes `Representation`,
    `Slot`, `TensorName`, `TensorStructure`, `TensorLibrary`, and
    `TensorNetwork` APIs suitable for later tensor-network lowering, while
    this slice only preserves model metadata and symbolic atoms;
  - introduced public `CGTensorDefinition` and `CGTensorHandle`, exported
    through `pychete.api` and the package root;
  - added `Theory.define_cg_tensor(...)` and `Theory.cg_tensor_handle(...)`;
  - created theory-owned `cg_tensor` labels with `cg_representations`,
    optional `cg_tensor`, and `cg_source` Symbolica symbol data, plus
    rank tags such as `cg_tensor_rank_3`;
  - serialized and restored `cg_tensors` after groups/representations and
    before fields/couplings, so named CG tensors survive state reloads before
    lagrangian expressions reference them;
  - taught the Matchete loader to parse `DefineCG[name, reps, source]` and to
    lower named calls such as `C4[i,j,M]` into the central
    `CG(cg_tensor_C4, List(i,j,M))` head instead of untyped external functions;
  - intentionally stored unsupported Mathematica tensor-generation calls such
    as `First@InvariantTensors[...]` as source text for now. Actual component
    tensor construction and contraction remain a spenso/idenso backend adapter
    task.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_public_api.py'` passed after the CG tensor
  metadata slice: 33 passed.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m mypy'`
  passed after the CG tensor metadata slice: no issues found in 24 source
  files.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests'` passed after the CG tensor metadata slice: 127 passed, 1 skipped.
  The skip is the existing GammaLoop API import check because GammaLoop was not
  requested in the current dependency manifest.
- Added the built-in Matchete CG tensor label slice:
  - non-Abelian group registration now auto-registers built-in CG tensors for
    `gen[group[fund]]`, `gen[group[adj]]`, `fStruct[group]`, `dSym[group]`,
    `del[group[fund]]`, `del[group[adj]]`, and `eps[group]` when the
    fundamental dimension is known;
  - the loader now recognizes built-in `CG[...]` first-argument labels and
    lowers `CG[eps[SU2L], {...}]`, `CG[gen[SU2L[fund]], {...}]`, and
    `CG[fStruct[SU2L], {...}]` to registered theory-owned CG labels instead of
    external functions;
  - standalone group symbols in parsed expressions now resolve to the
    theory-owned group symbol, which is needed by CG labels such as
    `eps[SU2L]`;
  - this is still metadata/lowering only. Actual contractions and tensor
    algebra remain delegated to the future spenso/idenso adapter.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py
  tests/unit/definitions/test_public_api.py'` passed after the built-in CG
  tensor label slice: 34 passed.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m mypy'`
  passed after the built-in CG tensor label slice: no issues found in 24 source
  files.
- `bash -lc 'source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest
  tests'` passed after the built-in CG tensor label slice: 128 passed, 1
  skipped. The skip is the existing GammaLoop API import check because
  GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/backends/test_spenso_backend.py
  tests/unit/definitions/test_theory_definitions.py
  tests/integration/models/test_model_loaders.py -q'` passed after the spenso
  metadata bridge slice: 36 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the spenso metadata bridge slice: no issues found in
  24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the spenso metadata bridge slice: 131
  passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/backends/test_spenso_backend.py
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_pretty_printing.py::test_all_builtin_pychete_symbols_have_pretty_print_callbacks
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_routes_generated_kernels_through_spenso
  tests/integration/matching/test_fluctuation_operator.py::test_supertrace_block_trace_lowers_registered_cg_tensors_before_spenso
  -q'` passed after the CG-to-spenso expression lowering slice: 28 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the CG-to-spenso expression lowering slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the CG-to-spenso expression lowering
  slice: 134 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/backends/test_spenso_backend.py
  tests/integration/matching/test_fluctuation_operator.py::test_supertrace_block_trace_lowers_registered_cg_tensors_before_spenso
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_routes_generated_kernels_through_spenso
  -q'` passed after the spenso CG library registration slice: 14 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the spenso CG library registration slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the spenso CG library registration slice:
  138 passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/backends/test_spenso_backend.py
  tests/integration/matching/test_fluctuation_operator.py::test_supertrace_block_trace_lowers_registered_cg_tensors_before_spenso
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_routes_generated_kernels_through_spenso
  -q'` passed after the built-in delta/epsilon CG component slice: 17 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the built-in delta/epsilon CG component slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the built-in delta/epsilon CG component
  slice: 141 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/backends/test_spenso_backend.py
  tests/integration/matching/test_fluctuation_operator.py::test_supertrace_block_trace_can_use_native_hep_spenso_builtins
  tests/integration/matching/test_fluctuation_operator.py::test_supertrace_block_trace_lowers_registered_cg_tensors_before_spenso
  -q'` passed after the native SU(3) HEP CG lowering slice: 21 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the native SU(3) HEP CG lowering slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the native SU(3) HEP CG lowering slice:
  146 passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_heavy_scalar_tree.py
  tests/integration/matching/test_fluctuation_operator.py::test_theory_one_loop_setup_prepares_current_matching_pipeline_inputs
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_propagator_plan_recovers_masses_from_symbol_data
  tests/integration/validation/test_validation_fixtures.py::test_default_model_fixtures_build_order_three_one_loop_preview_without_mathematica
  tests/unit/definitions/test_public_api.py -q'` passed after the one-loop
  power-type result entry-point slice: 14 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the one-loop power-type result entry-point slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the one-loop power-type result entry-point
  slice: 146 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/backends/test_vakint_backend.py
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_extracts_evaluated_vakint_poles_with_symbolica_coefficients
  tests/unit/definitions/test_public_api.py -q'` passed after the vakint
  epsilon-pole extraction slice: 12 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the vakint epsilon-pole extraction slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the vakint epsilon-pole extraction slice:
  149 passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_extracts_evaluated_vakint_poles_with_symbolica_coefficients
  tests/unit/definitions/test_public_api.py -q'` passed after the power-type
  minimal-subtraction result slice: 5 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the power-type minimal-subtraction result slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the power-type minimal-subtraction result
  slice: 149 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_basis_modes_carry_statistics_and_mass_metadata
  tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_modes_carry_internal_representation_dimensions
  tests/unit/definitions/test_public_api.py -q'` passed after the fluctuation
  mode degree metadata slice: 6 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the fluctuation mode degree metadata slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the fluctuation mode degree metadata slice:
  150 passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_basis_modes_carry_statistics_and_mass_metadata
  tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_modes_expose_spin_lorentz_and_reality_conventions
  tests/unit/definitions/test_public_api.py -q'` passed after the fluctuation
  mode spin/Lorentz metadata slice: 6 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the fluctuation mode spin/Lorentz metadata slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the fluctuation mode spin/Lorentz metadata
  slice: 151 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_exposes_euler_lagrange_differential_entries
  tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_differential_entries_handle_barred_complex_scalars
  tests/unit/definitions/test_public_api.py -q'` passed after the fluctuation
  differential-operator matrix slice: 6 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the fluctuation
  differential-operator matrix slice: 36 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the fluctuation differential-operator matrix slice:
  no issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the fluctuation differential-operator
  matrix slice: 153 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_exposes_euler_lagrange_differential_entries
  tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_differential_entries_handle_barred_complex_scalars
  tests/integration/matching/test_fluctuation_operator.py::test_theory_one_loop_setup_prepares_current_matching_pipeline_inputs
  tests/unit/definitions/test_public_api.py -q'` passed after the
  fluctuation-operator momentum-lowering slice: 7 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the
  fluctuation-operator momentum-lowering slice: 36 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the fluctuation-operator momentum-lowering slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the fluctuation-operator momentum-lowering
  slice: 153 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_exposes_euler_lagrange_differential_entries
  tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_differential_entries_handle_barred_complex_scalars
  tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_denominator_extraction_rejects_interaction_masses
  tests/unit/definitions/test_public_api.py -q'` passed after the
  fluctuation-operator denominator extraction slice: 7 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the
  fluctuation-operator denominator extraction slice: 37 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the fluctuation-operator denominator extraction slice:
  no issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the fluctuation-operator denominator
  extraction slice: 154 passed, 1 skipped. The skip is the existing GammaLoop
  API import check because GammaLoop was not requested in the current
  dependency manifest.
- `git diff --check` passed after the fluctuation-operator denominator
  extraction slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_differential_entries_handle_barred_complex_scalars
  tests/integration/matching/test_fluctuation_operator.py::test_theory_one_loop_setup_prepares_current_matching_pipeline_inputs
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_propagator_plan_recovers_masses_from_symbol_data
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_operator_derived_propagator_insertions
  tests/unit/definitions/test_public_api.py -q'` passed after the
  operator-derived propagator insertion slice: 8 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the operator-derived
  propagator insertion slice: 38 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the operator-derived propagator insertion slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the operator-derived propagator insertion
  slice: 155 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the operator-derived propagator insertion
  slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_operator_derived_propagator_insertions
  tests/unit/definitions/test_public_api.py -q'` passed after the
  interaction-only fluctuation-operator slice: 6 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the interaction-only
  fluctuation-operator slice: 39 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the interaction-only fluctuation-operator slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the interaction-only fluctuation-operator
  slice: 156 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the interaction-only fluctuation-operator
  slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
  tests/unit/definitions/test_public_api.py -q'` passed after the
  interaction-power contribution slice: 5 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the interaction-power
  contribution slice: 39 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the interaction-power contribution slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the interaction-power contribution slice:
  156 passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the interaction-power contribution slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_request_returns_incomplete_native_backed_result
  tests/integration/validation/test_validation_fixtures.py::test_default_model_fixtures_build_order_three_one_loop_preview_without_mathematica
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
  -q'` passed after the public one-loop interaction-power routing slice:
  3 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the public one-loop interaction-power routing slice:
  no issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the public one-loop
  interaction-power routing slice: 39 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the public one-loop interaction-power
  routing slice: 156 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `git diff --check` passed after the public one-loop interaction-power routing
  slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_extracts_evaluated_vakint_poles_with_symbolica_coefficients
  tests/unit/definitions/test_public_api.py -q'` passed after the
  interaction-power pole/minimal-subtraction slice: 6 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the
  interaction-power pole/minimal-subtraction slice: 39 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the interaction-power pole/minimal-subtraction slice:
  no issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the interaction-power
  pole/minimal-subtraction slice: 156 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `git diff --check` passed after the interaction-power
  pole/minimal-subtraction slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_extracts_evaluated_vakint_poles_with_symbolica_coefficients
  tests/unit/definitions/test_public_api.py
  tests/unit/definitions/test_pretty_printing.py::test_loop_hbar_symbol_prints_cleanly_in_all_symbolica_modes
  tests/unit/definitions/test_pretty_printing.py::test_all_builtin_pychete_symbols_have_pretty_print_callbacks
  -q'` passed after the interaction-power normalization slice: 8 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the interaction-power normalization slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the interaction-power
  normalization slice: 39 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/definitions -q'` passed after the interaction-power
  normalization slice: 44 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the interaction-power normalization
  slice: 157 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the interaction-power normalization slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  tests/integration/validation/test_validation_fixtures.py::test_default_model_fixtures_build_order_three_one_loop_preview_without_mathematica
  -q'` passed after the default-target gap-report slice: 2 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the default-target gap-report slice: no issues found
  in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/validation -q'` passed after the
  default-target gap-report slice: 16 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/models -q'` passed after the default-target
  gap-report slice: 13 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the default-target gap-report slice: 158
  passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the default-target gap-report slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py -q'`
  passed after the Matchete-style supertrace-category naming slice: 33 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_model_fixtures_build_order_three_one_loop_preview_without_mathematica
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  -q'` passed after the category naming slice: 2 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the category naming slice: no issues found in 24
  source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching tests/integration/validation -q'`
  passed after the category naming slice: 56 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/definitions/test_public_api.py -q'` passed after the
  category naming slice: 4 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/unit/definitions/test_pretty_printing.py::test_pychete_objects_expose_jupyter_repr_hooks
  -q'` passed after switching the repr-hook one-loop fixture to a heavy scalar
  setup: 1 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the category naming slice: 159 passed, 1
  skipped. The skip is the existing GammaLoop API import check because
  GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the Matchete-style supertrace-category naming
  slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
  -q'` passed after the staged named-supertrace slice: 1 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_stage_named_supertraces_with_vakint_engine
  -q'` passed after the staged named-supertrace slice: 1 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the staged named-supertrace slice: no issues found in
  24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching tests/integration/validation -q'`
  passed after the staged named-supertrace slice: 57 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the staged named-supertrace slice: 160
  passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the staged named-supertrace slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  -q'` passed after the canonical shared-supertrace gap-report slice: 1
  passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the canonical shared-supertrace gap-report slice: no
  issues found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/validation -q'` passed after the canonical
  shared-supertrace gap-report slice: 17 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the canonical shared-supertrace gap-report
  slice: 160 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the canonical shared-supertrace gap-report
  slice.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/matching/test_fluctuation_operator.py::test_fluctuation_operator_linearizes_noncommutative_fermion_chains_without_formal_derivatives
  -q'` passed after the NCM/Bar variation-linearization slice: 1 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching -q'` passed after the NCM/Bar
  variation-linearization slice: 41 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the NCM/Bar variation-linearization slice: no issues
  found in 24 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest
  tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
  tests/integration/validation/test_validation_fixtures.py::test_default_model_fixtures_build_order_three_one_loop_preview_without_mathematica
  -q'` passed after the NCM/Bar variation-linearization slice: 2 passed.
- A direct managed-venv probe of
  `assets/validation/pychete/VLF_toy_model.model_fixture.json` confirmed that
  the order-three one-loop preview still has 47 candidate named supertraces and
  now has zero candidate supertraces whose canonical string contains
  `der(...)`.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching tests/integration/validation -q'`
  passed after tightening the direct `Bar(Field)` protection semantics: 58
  passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the NCM/Bar
  variation-linearization slice: 161 passed, 1 skipped. The skip is the
  existing GammaLoop API import check because GammaLoop was not requested in
  the current dependency manifest.
- `git diff --check` passed after the NCM/Bar variation-linearization slice.
- Current backend design update: native vakint tensor reduction is
  topology-independent and may be used on numerator structures before analytic
  integration, including for zero-mass or mixed-mass topologies. pychete should
  own the Matchete-style one-loop analytic vacuum-integral evaluator for
  single-scale, zero-mass, and mixed-mass cases. Native vakint analytic
  evaluation remains useful as an optional supported backend and cross-check
  for single-scale massive integrals, but zero-mass and mixed-mass analytic
  evaluation must not be delegated to vakint's numerical methods.
- Completed the vakint tensor-reduction/evaluation boundary slice:
  - added a generic managed dependency-patch workflow to
    `dependencies/install_dependencies.py`, including idempotent `git apply`
    handling and manifest discovery for future dependency patches;
  - removed the planned local vakint zero-mass propagator patch because the
    correct architecture is pychete-side analytic evaluation for one-loop
    vacuum integrals, with vakint kept as a single-scale optional backend and
    cross-check;
  - tightened `pychete.backends.vakint` analytic evaluation/canonicalization
    calls so they inspect matched `vakint::topo(...)` / `vakint::prop(...)`
    expressions with Symbolica pattern matching and raise before entering
    native vakint unless every generated topology has one nonzero mass scale;
  - kept `pychete.backends.vakint.tensor_reduce(...)` delegating to native
    vakint for zero-mass and mixed-mass topology expressions because numerator
    tensor reduction is topology-independent;
  - added tests proving zero-mass and mixed-mass topologies are rejected before
    analytic engine calls, delegated for tensor reduction, and repeated
    equal-mass topologies still delegate to the native vakint engine.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/dependencies/test_install_dependencies.py
  tests/unit/backends/test_vakint_backend.py -q'` passed after the vakint
  tensor-reduction/evaluation boundary slice: 18 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_fluctuation_operator.py -q'`
  passed after updating mixed-mass integration expectations for the vakint
  tensor-reduction/evaluation boundary slice: 36 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the vakint tensor-reduction/evaluation
  boundary slice: 178 passed, 1 skipped. The skip is the existing GammaLoop API
  import check because GammaLoop was not requested in the current dependency
  manifest.
- `git diff --check` passed after the vakint tensor-reduction/evaluation
  boundary slice.
- Completed the internal single-scale vacuum-integral comparison slice:
  - added `pychete.backends.vacuum_integrals` with
    `evaluate_one_loop_single_scale_vacuum_integral(...)`, pychete's first
    internal Matchete-style analytic one-loop tadpole evaluator;
  - the current evaluator covers the one-loop, one-propagator, power-one,
    finite-through-pole single-scale massive tadpole in the same MSbar
    convention used by vakint when `number_of_terms_in_epsilon_expansion=2`;
  - re-exported the evaluator through `pychete.api` and package-root
    `pychete`;
  - added a real native-vakint comparison test proving the internal pychete
    result equals `vakint.evaluate(...)` for the same single-scale topology.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/backends/test_vacuum_integrals_backend.py
  tests/unit/backends/test_vakint_backend.py
  tests/unit/definitions/test_public_api.py -q'` passed after the internal
  single-scale comparison slice: 21 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the internal single-scale comparison
  slice: 179 passed, 1 skipped. The skip is the existing GammaLoop API import
  check because GammaLoop was not requested in the current dependency manifest.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the internal single-scale comparison slice: no issues
  found in 25 source files.
- `git diff --check` passed after the internal single-scale comparison slice.
- Completed the first code-organization refactor slice:
  - extracted structured matching result/comparison types from
    `src/pychete/matching.py` into `src/pychete/matching_results.py`;
  - extracted one-loop option enums and normalization helpers into
    `src/pychete/matching_options.py`;
  - kept compatibility imports through `pychete.matching` while updating
    internal imports and public API ownership to use the new focused modules;
  - reduced `matching.py` from roughly 3,400 lines to roughly 3,150 lines
    without changing the public API surface.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/definitions/test_public_api.py
  tests/integration/validation/test_numeric_probes.py
  tests/integration/validation/test_validation_fixtures.py -q'` passed after
  extracting matching results: 21 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/definitions/test_public_api.py
  tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
  -q'` passed after extracting matching options: 5 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the first refactor slice: no issues found in 27
  source files.
- Added explicit loader-boundary guidance after the Mathematica-model parsing
  design update:
  - `src/pychete/loaders/mathematica.py` now documents the direct loader as a
    supported subset for simple declarative Matchete/Wolfram assets and saved
    validation-result snippets only;
  - `AGENTS.md`, `helper_mathematica_scripts/README.md`, and the copied
    one-shot plan now require complicated Mathematica models to be loaded by
    development-only Wolfram/Matchete helper scripts that emit pychete-owned
    serialized state or Python fixtures;
  - normal pytest remains Mathematica-independent and consumes only committed
    pychete fixtures.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/definitions/test_public_api.py
  tests/integration/models/test_model_loaders.py
  tests/integration/validation/test_validation_fixtures.py -q'` passed after
  the refactor and loader-boundary documentation slice: 29 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the refactor and loader-boundary documentation slice:
  no issues found in 27 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the refactor and loader-boundary
  documentation slice: 179 passed, 1 skipped. The skip is the existing
  GammaLoop API import check because GammaLoop was not requested in the current
  dependency manifest.
- `git diff --check` passed after the refactor and loader-boundary
  documentation slice.
- Completed the second code-organization refactor slice:
  - extracted tree-level heavy-scalar matching into
    `src/pychete/tree_matching.py`, including `HeavyScalarSolution`,
    `solve_heavy_scalar_eoms(...)`, and `match_tree(...)`;
  - updated `Theory.solve_heavy_scalar_eoms(...)`,
    `Theory.match(loop_order=0)`, and `pychete.api` to use the new focused
    module as the canonical owner;
  - kept compatibility imports from `pychete.matching` so existing callers that
    import `HeavyScalarSolution`, `solve_heavy_scalar_eoms`, or `match_tree`
    from the older module continue to work;
  - reduced `matching.py` further by moving the tree-matching tail out of the
    one-loop fluctuation/supertrace module.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/integration/matching/test_heavy_scalar_tree.py
  tests/unit/definitions/test_pretty_printing.py
  tests/unit/definitions/test_public_api.py -q'` passed after the tree
  matching extraction: 20 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the tree matching extraction: no issues found in 28
  source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the tree matching extraction: 179 passed,
  1 skipped. The skip is the existing GammaLoop API import check because
  GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the tree matching extraction.
- Completed the third code-organization refactor slice:
  - extracted theory metadata enums, type aliases, Symbolica symbol-data
    accessors, registered definition dataclasses, and lightweight handles into
    `src/pychete/theory_metadata.py`;
  - kept compatibility re-exports through `src/pychete/theory.py` while making
    `pychete.api`, `matching.py`, `functional.py`, `eft.py`, the Mathematica
    loader, `tree_matching.py`, and the spenso bridge import metadata from the
    new focused module;
  - reduced `theory.py` from roughly 1,990 lines to roughly 1,040 lines so it
    now focuses on the `Theory` registry/orchestration class, JSON
    restoration, and public theory methods;
  - added an explicit `theory_metadata.__all__` for discoverability of the
    metadata surface.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/definitions
  tests/integration/models/test_model_loaders.py
  tests/integration/validation/test_validation_fixtures.py
  tests/integration/matching/test_heavy_scalar_tree.py -q'` passed after the
  theory metadata extraction: 76 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after the theory metadata extraction: no issues found in 29
  source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after the theory metadata extraction: 179
  passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- `git diff --check` passed after the theory metadata extraction.
- Implemented the initial loaded-Matchete-model export path for complicated
  Mathematica models:
  - added `helper_mathematica_scripts/export_matchete_model_state.wls`, a
    development-only Wolfram script that calls Matchete `LoadModel[...]` and
    exports post-load model metadata from Matchete getters/associations
    (`GetFields[]`, `GetCouplings[]`, `GetGaugeGroups[]`,
    `GetGlobalGroups[]`, `GetFlavorIndices[]`, `GetRepresentations[]`, and CG
    metadata) into a neutral `matchete_loaded_model_state` RawJSON contract;
  - added `helper_mathematica_scripts/convert_matchete_model_state.py`, which
    converts that RawJSON contract into normal pychete `model_definition`
    fixtures built through `Theory`, `PycheteState`, and the existing
    Matchete-expression lowering helpers;
  - documented the two-step export/convert workflow in
    `helper_mathematica_scripts/README.md`;
  - added a Mathematica-independent unit test with a synthetic loaded-model
    state JSON that proves the converter emits a normal pychete fixture
    loadable by `load_validation_fixture(...)`.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/loaders/test_matchete_model_state_converter.py -q'`
  passed after adding the model-state exporter/converter: 2 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests/unit/loaders tests/integration/models/test_model_loaders.py
  tests/integration/validation/test_validation_fixtures.py -q'` passed after
  adding the model-state exporter/converter: 29 passed.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m mypy'` passed after adding the model-state exporter/converter: no issues
  found in 29 source files.
- `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python
  -m pytest tests -q'` passed after adding the model-state exporter/converter:
  181 passed, 1 skipped. The skip is the existing GammaLoop API import check
  because GammaLoop was not requested in the current dependency manifest.
- Regenerated the four default model-definition fixtures from a real
  Matchete-loaded state using the optional Wolfram exporter/converter path:
  - ran `export_matchete_model_state.wls` through local `wolframscript` for
    `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`;
  - converted the resulting `matchete_loaded_model_state` RawJSON files into
    committed pychete `model_definition` fixtures with no converter warnings;
  - the refreshed fixture counts are:
    `VLF_toy_model` fields/couplings/groups/representations/CG tensors =
    4/4/1/0/0,
    `Singlet_Scalar_Extension` = 10/13/3/4/16,
    `E_VLL` = 10/10/3/4/16, and `S1S3LQs` = 11/17/3/4/16;
  - the three SM-parent fixtures now carry Matchete-derived representation and
    CG tensor metadata instead of the earlier direct-loader subset fixtures;
  - the current order-three one-loop preview from all four refreshed fixtures
    exposes 25 kernels, 11 interaction-power contributions, and 47 named
    supertraces, while remaining explicitly incomplete.
- Added optional top-level `scripts/` wrappers for the Mathematica conversion
  route:
  - `scripts/export_matchete_model_state.wls` delegates to the maintained
    helper Wolfram exporter;
  - `scripts/convert_matchete_model_state.py` delegates to the maintained
    Python converter;
  - `scripts/README.md` documents this as a convenience-only workflow for
    users with Mathematica, not a pychete runtime or pytest dependency.
- Extended the pychete-owned one-loop vacuum-integral backend for
  single-scale massive topologies:
  - `evaluate_one_loop_single_scale_vacuum_integral(...)` now supports
    positive integer propagator powers through the finite-order convention
    matched to native vakint with
    `number_of_terms_in_epsilon_expansion=2`;
  - added
    `evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared(...)`
    for direct evaluation of vakint-style mass-squared slots, preserving
    vakint's `log(mursq) - log(mass_squared)` convention and the
    `M^2 -> 2 log(M)` presentation where the mass slot is a literal square;
  - added `evaluate_one_loop_single_scale_vakint_expression(...)`, which uses
    Symbolica pattern matching and replacement over `vakint::topo(...)` atoms
    to evaluate scalar single-scale massive topology factors after optional
    tensor reduction, while rejecting zero-mass and mixed-mass topologies;
  - added `OneLoopSetup.power_type_internal_integral_sum(...)` and
    `interaction_power_type_internal_integral_sum(...)` so the one-loop
    pipeline can use native vakint for topology-independent tensor reduction
    and pychete's internal analytic evaluator for the scalar single-scale
    integral evaluation stage;
  - added tests comparing internal results to real native vakint evaluation
    for powers 1 through 5 and for bare mass-squared slots, plus setup-level
    tests proving optional tensor-reduction delegation before internal
    evaluation.
- Extended the internal scalar one-loop vacuum-integral evaluator beyond
  single-scale massive topologies:
  - read Matchete `Package/LoopIntegration.m`, especially
    `SingleScaleIntegral[...]`, `MultiScaleIntegral[...]`, and
    `EvaluateLoopFunctionsInternal[...]`;
  - added `evaluate_one_loop_vakint_expression(...)`, a generic internal
    scalar evaluator for one-loop `vakint::topo(...)` factors after tensor
    reduction;
  - the evaluator treats zero-mass propagators as powers of `1/k^2`, returns
    zero for scaleless all-massless topologies, combines repeated nonzero
    masses, and follows Matchete's multiscale formula that reduces mixed-mass
    topologies to derivatives of single-scale integrals with respect to
    mass-squared variables;
  - Symbolica performs the derivative and replacement work; Python is used only
    for the finite topology bookkeeping over propagator powers;
  - switched `OneLoopSetup.power_type_internal_integral_sum(...)` and
    `interaction_power_type_internal_integral_sum(...)` to this generic
    evaluator, so mixed heavy/light scalar topologies now have a pychete-owned
    analytic path after optional native vakint tensor reduction;
  - kept `evaluate_one_loop_single_scale_vakint_expression(...)` as the strict
    single-scale massive helper and added tests for two-mass, massless/massive,
    and all-massless scalar topology cases.
- Ported two concrete Matchete `Validation/Tests/LoopIntegration.wl`
  scalar-evaluation cases into the pychete-owned internal integral backend:
  - `Prop[m]^2 Prop[0]^2`, where the zero-mass denominator contributes a
    massless propagator power and the result is proportional to
    `-I/m^4 * (1/epsilon + log(mu^2/m^2) + 2)` in pychete's explicit
    `1/(16*pi^2)` normalization convention;
  - `Prop[m]^2 Prop[0]^-2`, where the negative zero-mass power represents a
    loop-momentum numerator power after tensor reduction and the result is
    proportional to `I*m^4 * (3/epsilon + 3 log(mu^2/m^2) + 2)`;
  - the generic internal scalar evaluator now accepts negative zero-mass
    propagator powers, continues to reject non-integer powers, and keeps
    massive propagator powers strictly positive;
  - the optional top-level conversion scripts remain checked in under
    `scripts/` as convenience wrappers over `helper_mathematica_scripts/`, and
    pychete runtime code plus normal pytest continue to consume committed
    pychete fixtures only.
- Verification for the Matchete massless-power loop-integration slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_vacuum_integrals_backend.py
    tests/integration/matching/test_fluctuation_operator.py
    tests/unit/definitions/test_public_api.py -q'` passed: 53 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 193 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Added the first pychete-side coverage of Matchete
  `SimplifyMassFunction`-style finite loop-function cancellation:
  - rescanned the Symbolica stubs for `Expression.together()` and used that
    native common-denominator primitive rather than adding a Python LF/IBP
    reducer;
  - added an opt-in `combine_terms=True` path to
    `evaluate_one_loop_single_scale_vakint_expression(...)`,
    `evaluate_one_loop_vakint_expression(...)`,
    `OneLoopSetup.power_type_internal_integral_sum(...)`, and
    `OneLoopSetup.interaction_power_type_internal_integral_sum(...)`;
  - ported the Matchete
    `SimplifyMassFunction: 2 mass complicated sum full reduction` validation
    case through pychete's vakint-topology representation, where the evaluated
    and combined result is pychete's explicit loop normalization times
    `1/(6 Md^2 Mq^2)`;
  - left the default evaluated form expanded for compatibility with existing
    tests and callers, so expensive common-denominator combination remains an
    explicit request.
- Verification for the native loop-function combination slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_vacuum_integrals_backend.py
    tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_can_evaluate_single_scale_integrals_internally
    -q'` passed: 14 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 194 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Promoted pychete's internal analytic vacuum-integral evaluator into the
  structured one-loop result surface:
  - added public `OneLoopIntegralBackend` selectors for fixture previews, with
    `vakint` preserving the existing raw/native-vakint path and `internal`
    selecting pychete's internal analytic scalar integral backend;
  - added `OneLoopSetup.interaction_power_type_internal_matching_result(...)`,
    returning a `MatchingResult` whose off-shell/on-shell EFT Lagrangians are
    the internally evaluated interaction-power aggregate rather than raw
    `vakint::topo(...)` placeholders;
  - named supertraces in this result are evaluated through the same internal
    backend after optional topology-independent native vakint tensor
    reduction, so individual Matchete-style supertrace keys can now carry
    evaluated scalar integrals;
  - the result records the raw vakint topology aggregate, the internal
    evaluated aggregate, and Symbolica-backed pole/finite parts, while
    retaining `complete=False` until on-shell reduction and matching-condition
    extraction are implemented;
  - `ValidationFixture.one_loop_preview(...)` and gap reports can now opt into
    the internal backend without Mathematica or Matchete runtime dependencies.
- Verification for the internal analytic result-backend slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_internal_integral_backend_without_mathematica
    tests/unit/definitions/test_public_api.py -q'` passed: 6 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 195 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Moved the public one-loop matching entry point onto the internal analytic
  result backend:
  - `Theory.match(..., loop_order=1)` and `match_one_loop(...)` now return
    `OneLoopSetup.interaction_power_type_internal_matching_result(...)`
    instead of the raw/native-vakint topology-sum result;
  - the public result therefore exposes internally evaluated scalar
    one-loop integrals by default, with `metadata["integral_backend"] ==
    "pychete_internal"`, `tensor_reduce == False`, and `combine_terms == True`;
  - the raw/native-vakint `interaction_power_type_matching_result(...)` path
    remains available on `OneLoopSetup` for diagnostics, explicit native
    backend staging, and comparisons against earlier placeholders.
- Verification for the public one-loop internal-result switch:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_request_returns_incomplete_internal_integral_result
    tests/unit/definitions/test_public_api.py -q'` passed: 5 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 195 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Extended the optional top-level Matchete conversion route:
  - added `scripts/export_matchete_matching_snapshots.wls` as a convenience
    wrapper over the maintained raw matching-snapshot helper;
  - added `scripts/convert_matchete_previous_results.py` as a convenience
    wrapper over the maintained previous-result-to-fixture converter;
  - updated `scripts/README.md`, `AGENTS.md`, and the copied user notes to
    make clear that both model-state and matching-result conversion wrappers
    should remain committed for users with Mathematica, while pychete runtime
    code and normal pytest remain fully Matchete- and Mathematica-independent;
  - added pytest coverage that checks the top-level wrappers are present and
    delegate to maintained helper implementations instead of becoming runtime
    dependencies.
- Verification for the top-level optional conversion-script slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/loaders/test_matchete_model_state_converter.py -q'` passed:
    3 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 196 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Added an internal-backend minimal-subtraction result path for the public
  interaction-power one-loop pipeline:
  - added
    `OneLoopSetup.interaction_power_type_internal_minimal_subtraction_result(...)`,
    which reuses `interaction_power_type_internal_matching_result(...)` and
    Symbolica-backed `vakint.pole_part(...)` / `vakint.finite_part(...)`
    extraction rather than adding new symbolic traversal;
  - the result keeps the internally evaluated aggregate, pole part, finite
    part, and new
    `interaction_power_type_internal_integral_ms_counterterm` diagnostic in
    `MatchingResult.supertraces`;
  - the current off-shell/on-shell EFT Lagrangians are the epsilon^0 finite
    part, while metadata records
    `stage == "interaction_power_type_internal_minimal_subtraction_result"`,
    `subtraction_scheme == "minimal_subtraction_preview"`,
    `poles_subtracted == True`, `integral_backend == "pychete_internal"`,
    and the selected tensor-reduction / term-combination settings;
  - added the method to the public API docstring coverage and extended the
    interaction-power integration test to verify the finite result, pole part,
    and counterterm against the existing internal analytic evaluator.
- Verification for the internal minimal-subtraction slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
    tests/unit/definitions/test_public_api.py -q'` passed: 5 passed.
- Final verification for the internal minimal-subtraction slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_fluctuation_operator.py::test_one_loop_setup_builds_interaction_only_fluctuation_traces
    tests/unit/definitions/test_public_api.py -q'` passed: 5 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 196 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Promoted the public one-loop entry point to the internal minimal-subtraction
  preview:
  - `match_one_loop(...)` and therefore
    `Theory.match(..., loop_order=1)` now call
    `OneLoopSetup.interaction_power_type_internal_minimal_subtraction_result(...)`
    with `tensor_reduce=False` and `combine_terms=True`;
  - the public result's off-shell/on-shell EFT Lagrangians are now the
    epsilon^0 finite part of the internally evaluated interaction-power
    aggregate rather than the unrenormalized pole-plus-finite aggregate;
  - lower-level diagnostic builders remain available:
    `interaction_power_type_internal_matching_result(...)` still exposes the
    unrenormalized internal integral result, and
    `interaction_power_type_matching_result(...)` still exposes raw/native
    vakint staging;
  - updated the public one-loop tree/integration test to assert
    `stage == "interaction_power_type_internal_minimal_subtraction_result"`,
    the minimal-subtraction metadata, the internal counterterm diagnostic, and
    finite-part EFT Lagrangians.
- Verification for the public one-loop minimal-subtraction switch so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_request_returns_incomplete_internal_minimal_subtraction_result
    tests/unit/definitions/test_public_api.py -q'` passed: 5 passed.
- Final verification for the public one-loop minimal-subtraction switch:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_heavy_scalar_tree.py::test_one_loop_match_request_returns_incomplete_internal_minimal_subtraction_result
    tests/unit/definitions/test_public_api.py -q'` passed: 5 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 196 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Extended the Mathematica-independent validation fixture preview layer to
  target the public finite MS stage:
  - added `OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION` with the
    user-facing selector string `"internal_minimal_subtraction"`;
  - `ValidationFixture.one_loop_preview(...)` and
    `one_loop_preview_gap_report(...)` can now call
    `OneLoopSetup.interaction_power_type_internal_minimal_subtraction_result(...)`
    while preserving the existing `vakint` and unrenormalized `internal`
    preview paths;
  - the fixture preview exposes the same finite-part off-shell/on-shell EFT
    Lagrangians, internal pole diagnostics, and MS counterterm diagnostic as
    the public `Theory.match(..., loop_order=1)` path, while remaining fully
    Mathematica- and Matchete-independent;
  - added validation coverage that exercises both the enum selector and the
    user-facing string selector through preview and gap-report calls against
    committed VLF fixtures.
- Verification for the validation fixture MS selector so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_internal_integral_backend_without_mathematica
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_internal_minimal_subtraction_backend_without_mathematica
    -q'` passed: 2 passed.
- Final verification for the validation fixture MS selector:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_internal_integral_backend_without_mathematica
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_internal_minimal_subtraction_backend_without_mathematica
    -q'` passed: 2 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 197 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Extended fixture gap reports with Symbolica evaluator probe accounting:
  - `ValidationFixture.one_loop_preview_gap_report(...)` now accepts
    `probe_parameters`, `probe_samples`, and probe tolerances, forwarding them
    to the existing `MatchingResult.compare_to(...)` evaluator-backed
    comparison path;
  - `MatchingFixtureGapReport` now records
    `numeric_probe_equal_common_supertrace_names` and
    `numeric_probe_different_common_supertrace_names` separately from
    canonical equality, so reports can state that two shared supertraces are
    still canonically different while numeric probes agree;
  - this uses Symbolica's `Expression.evaluator_multiple(...)` through
    `evaluator_probe_equal(...)`; no Python substitution or ad hoc numeric
    evaluation was added;
  - added focused validation coverage where `sin(x)^2 + cos(x)^2` and `1`
    remain canonically different in a synthetic shared supertrace but are
    accepted by the evaluator probe and recorded in the gap report JSON.
- Verification for the gap-report numeric-probe slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed:
    6 passed.
- Final verification for the gap-report numeric-probe slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_use_internal_minimal_subtraction_backend_without_mathematica
    -q'` passed: 7 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 198 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Added four-target fixture coverage for the current public finite/MS preview:
  - added an integration test that builds
    `integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION`
    gap reports for `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and
    `S1S3LQs` at `max_trace_order=3` using only committed pychete fixtures;
  - each report now tracks the same public stage as
    `Theory.match(..., loop_order=1)`,
    `interaction_power_type_internal_minimal_subtraction_result`, with
    `internal_tensor_reduce=False` and `internal_combine_terms=True`;
  - the observed candidate supertrace surface is 50 names for each default
    target, including `interaction_power_type_internal_integral_sum` and
    `interaction_power_type_internal_integral_ms_counterterm`; common
    Matchete-style supertrace names remain the same as the raw/vakint preview
    frontier;
  - canonical agreement remains unchanged at this stage: E_VLL has the same
    three equal shared fermion-chain names as before, S1S3LQs has the same
    three equal shared scalar/fermion names as before, and VLF plus the singlet
    scalar extension still have zero canonically equal shared supertraces.
- Verification for the four-target internal-MS fixture coverage so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_internal_ms_one_loop_coverage
    -q'` passed: 1 passed.
- Final verification for the four-target internal-MS fixture coverage:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_current_one_loop_coverage
    tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_gap_reports_track_internal_ms_one_loop_coverage
    -q'` passed: 2 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 199 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Added selective evaluator-probe targeting for validation comparisons:
  - `MatchingResult.compare_to(...)` now accepts `probe_names`, allowing
    numeric probes to be restricted to selected compared expressions while all
    expressions still receive canonical equality checks;
  - `ValidationFixture.one_loop_preview_gap_report(...)` forwards
    `probe_supertrace_names` to that comparison layer, so concrete Matchete
    fixture reports can probe only supertraces with suitable deterministic
    sample points instead of trying to evaluate every shared symbolic object;
  - added tests showing that one canonical-different trigonometric identity is
    accepted by Symbolica's evaluator probe while a second canonical-different
    identity remains unprobed and reported as canonical-only different;
  - this keeps the validation policy honest: canonical equality remains the
    primary metric, and numeric probes are an explicit, per-expression fallback.
- Verification for the selective evaluator-probe targeting slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed:
    7 passed.
- Final verification for the selective evaluator-probe targeting slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed:
    7 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 200 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Added explicit pychete-side coverage for the remaining finite two-mass
  `SimplifyMassFunction` cases in Matchete
  `Validation/Tests/LoopIntegration.wl`:
  - checked the two simple two-mass reductions,
    `LF[{M1, M3}, {1, 1, 1}] + LF[{M1, M3}, {2, 1, 0}] -
    LF[{M3, M1}, {2, 1, 0}] -> 2 LF[{M1, M3}, {2, 1, 0}]` and
    `LF[{M1, M3}, {1, 1, 1}] - LF[{M1, M3}, {2, 1, 0}] +
    LF[{M3, M1}, {2, 1, 0}] -> 2 LF[{M1, M3}, {1, 2, 0}]`,
    by evaluating both sides through pychete's Symbolica-backed analytic
    one-loop evaluator;
  - checked Matchete's partial-reduction case against the explicit two-term
    Matchete reference shape
    `-2 LF[{Mq, Mu}, {4, 1, -1}] + 2 LF[{Mq, Mu}, {5, 1, -2}]`,
    again comparing evaluated pychete expressions rather than depending on
    Matchete's unevaluated `LF[...]` placeholder representation;
  - no runtime Wolfram/Matchete dependency was added to pytest, and no new
    handwritten simplifier was introduced because the existing implementation
    already performs the required reduction with Symbolica's native
    `Expression.derivative(...)` and `Expression.together()`.
- Verification for the expanded Matchete loop-integration coverage slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_vacuum_integrals_backend.py -q'` passed:
    15 passed.
- Added an endpoint-aware open Dirac-chain simplification pass in the idenso
  bridge:
  - `pychete.backends.idenso.simplify_pychete_open_dirac_chains(...)` matches
    `NCM(Bar(Field(..., Fermion, ...)), dirac..., Field(..., Fermion, ...))`
    with Symbolica field-label tag restrictions, so it only applies to
    theory-registered pychete fermion fields and skips untagged
    `Field(...)` lookalikes;
  - the matched Dirac middle word is still lowered to native spenso
    `gamma`/`projp`/`projm` tensors and simplified through
    `idenso.simplify_gamma(...)`; the pychete field endpoints remain in the
    public Symbolica representation;
  - `simplify_pychete_dirac_algebra(...)` now runs this endpoint-aware pass
    before the generic mixed-`NCM` contiguous-subword pass, so VLF-like
    `bar(psi) ** P_R ** gamma(mu) ** P_L ** Psi` chains get the explicit
    field-endpoint route where possible;
  - added focused tests for vanishing same-chirality open chains, surviving
    `gamma(mu) P_L` open chains, contracted `gamma(mu) gamma(mu)` open chains,
    and tag-restricted rejection of unregistered field labels.
- Verification for the endpoint-aware idenso open-chain slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_idenso_backend.py -q'` passed: 10 passed.
- Final verification for the endpoint-aware idenso open-chain slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_idenso_backend.py -q'` passed: 10 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_fluctuation_operator.py -q'` passed:
    37 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 204 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Extended the loaded-Matchete-model converter to preserve internal coupling
  symmetry associations:
  - inspected Matchete's live `GetCouplings[...][Symmetries]` output for
    synthetic symmetric and antisymmetric couplings; the exported internal
    shape is a signed permutation association such as
    `<|{1, 2} -> 1, {2, 1} -> -1|>`;
  - `helper_mathematica_scripts/convert_matchete_model_state.py` now parses
    both `<|...|>` and `Association[...]` forms and converts each non-identity
    signed permutation into explicit pychete metadata expressions:
    `s.SymmetricPermutation(...)` for sign `+1` and
    `s.AntisymmetricPermutation(...)` for sign `-1`;
  - unsupported association entries now produce a targeted warning rather than
    dropping all internal symmetry metadata silently;
  - added a converter fixture test that round-trips symmetric and
    antisymmetric Matchete internal associations through pychete state
    serialization and verifies the resulting coupling symbol data.
- Verification for the internal coupling-symmetry converter slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/loaders/test_matchete_model_state_converter.py -q'` passed:
    3 passed.
- Final verification for the internal coupling-symmetry converter slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/loaders/test_matchete_model_state_converter.py
    tests/integration/models/test_model_loaders.py -q'` passed: 16 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 204 passed,
    1 skipped. The skip is the existing GammaLoop API import check because
    GammaLoop was not requested in the current dependency manifest.
- Started a CG tensor payload-preservation slice for the loaded-Matchete-model
  converter and spenso bridge:
  - kept the optional Mathematica conversion route committed through the
    top-level `scripts/` wrappers while preserving the rule that pychete
    runtime code and normal pytest runs are Matchete- and
    Mathematica-independent;
  - inspected the committed loaded-model fixtures and confirmed that non-native
    `tFundf_*` CG tensors were still preserved only as opaque
    `SparseArray[...]` source strings, while built-in delta/epsilon support
    already had native component fallback coverage;
  - added `pychete.backends.spenso.cg_tensor_component_expression(...)` and
    `cg_tensor_components_from_expression(...)` to encode/decode dense
    row-major CG component payloads as pychete-owned Symbolica metadata;
  - added `stored_cg_tensor_components(...)` and taught spenso library
    registration to consume stored CG component metadata before falling back to
    generated formal symbolic components;
  - extended `helper_mathematica_scripts/convert_matchete_model_state.py` to
    decode Matchete's compressed four-argument `SparseArray[...]` shape into
    dense pychete CG tensor metadata when possible, while retaining the raw
    source string for provenance and warning/falling back to source-only
    preservation if the sparse shape is unsupported;
  - fixed the supported Mathematica expression converter so `Sqrt[...]` is
    converted to Symbolica's native square-root primitive instead of an
    external `sqrt` symbol, which is required for exact CG component values
    such as `Sqrt[3]/4`;
  - added focused tests for stored CG tensor metadata registration through
    spenso and for sparse CG tensor decoding through the optional Matchete
    model-state converter.
- Verification for the CG sparse-tensor payload slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_spenso_backend.py
    tests/unit/loaders/test_matchete_model_state_converter.py'` passed:
    24 passed.
- Final verification for the CG sparse-tensor payload slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 206 passed,
    1 skipped in 147.12s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Extended the sparse-CG tensor payload slice into the committed default
  Matchete model fixtures:
  - populated stored dense `cg_tensor` metadata for the non-native
    `tFundf_SU2L` and `tFundf_SU3c` tensors in
    `Singlet_Scalar_Extension.model_fixture.json`, `E_VLL.model_fixture.json`,
    and `S1S3LQs.model_fixture.json`, deriving the payloads from the existing
    Matchete `SparseArray[...]` source strings without requiring Mathematica at
    test time;
  - stored each payload in both the high-level `cg_tensors` registry entry and
    the Symbolica symbol manifest data, preserving the symbol-manifest-first
    checkpoint safety invariant;
  - added a restore-time normalization in `Theory.from_json_obj(...)` so legacy
    or hand-edited checkpoints that have a `cg_tensors[name]["tensor"]` payload
    but stale symbol-manifest data backfill the complete `cg_tensor` symbol
    data before any theory-owned symbols are created;
  - added a legacy-manifest unit test for this restore path;
  - added an integration regression that loads the three default model fixtures
    without Mathematica, verifies stored `tFundf_*` component counts, and
    registers those tensors in a native spenso `TensorLibrary` directly from
    fixture metadata.
- Verification for the committed default-fixture sparse-CG payload slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_theory_definitions.py
    tests/integration/models/test_model_loaders.py -q'` passed: 32 passed.
- Final verification for the committed default-fixture sparse-CG payload slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_theory_definitions.py
    tests/integration/models/test_model_loaders.py -q'` passed: 32 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 208 passed,
    1 skipped in 148.01s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Expanded the supported Mathematica model-loader subset for local CG helper
  functions used by the default S1/S3 leptoquark model:
  - inspected the current parsed `S1S3LQs` Lagrangian and found opaque
    `external_tauSU2L`, `external_epsilonSU2L`, and `external_fSU2L` helper
    heads coming from local `Module` definitions such as
    `tauSU2L[J_, i_, j_] := 2 CG[gen[SU2L[fund]], {...}]`;
  - added a parser-boundary `_LocalFunction` environment for simple
    Mathematica `SetDelayed` function definitions inside `Module`, binding
    actual call arguments to the stored pattern parameters and evaluating the
    original body through the existing pychete/Symbolica conversion path;
  - retained the previous conservative behavior for unsupported delayed
    assignments by skipping non-call `:=` statements rather than growing the
    direct Python loader toward full Wolfram syntax;
  - the direct `S1S3LQs.m` asset now parses those helpers into registered
    `CG(...)` atoms: 5 `gen_SU2L_fund`, 4 `eps_SU2L`, and 1
    `fStruct_SU2L` occurrences in the canonical Lagrangian, with no remaining
    local helper external heads;
  - added focused tests for a synthetic local CG helper and for the real
    `S1S3LQs` model asset.
- Verification for the local CG helper expansion slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/models/test_model_loaders.py -q'` passed: 16 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
- Final verification for the local CG helper expansion slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/models/test_model_loaders.py -q'` passed: 16 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 210 passed,
    1 skipped in 147.70s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Extended the spenso tensor-network path to use stored CG tensor components
  automatically:
  - `pychete.backends.spenso.has_stored_cg_tensor_components(...)` now reports
    whether a theory has decodable dense CG component metadata;
  - `evaluate_pychete_tensor_network(...)` now builds a native
    `TensorLibrary` from stored CG component metadata when the caller has not
    supplied another library or component strategy, so committed model fixtures
    with stored `tFundf_*` payloads can route directly through spenso without
    requiring explicit `cg_components_by_name`, `builtin_cg_components=True`,
    or `symbolic_cg_components=True`;
  - explicit component maps, built-in component registration, native HEP
    builtins, and symbolic component fallback remain opt-in paths;
  - added backend and `SupertraceBlockTrace.evaluate_tensor_network(...)`
    regressions using a custom stored finite SU(2) CG tensor to prove the
    automatic path is driven by stored metadata, not by built-in epsilon
    special cases.
- Verification for the stored-CG automatic spenso library slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_spenso_backend.py
    tests/integration/matching/test_fluctuation_operator.py -q'` passed:
    59 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
- Final verification for the stored-CG automatic spenso library slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/backends/test_spenso_backend.py
    tests/integration/matching/test_fluctuation_operator.py -q'` passed:
    59 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 212 passed,
    1 skipped in 145.35s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Added a one-command optional top-level Wolfram conversion wrapper for users
  with Mathematica:
  - `scripts/convert_matchete_model_state.wls` now exports loaded Matchete
    model state through the existing top-level
    `scripts/export_matchete_model_state.wls` wrapper and then invokes
    `scripts/convert_matchete_model_state.py` with `PYTHONPATH=src`;
  - the wrapper defaults to `dependencies/.venv/bin/python` when available,
    falls back to `python3`, and supports `--python`, `--raw-out`,
    `--fixtures-dir`, `--models`, and `--no-lagrangian`;
  - `scripts/README.md`, `AGENTS.md`, and the copied user notes now explicitly
    keep this route as optional user convenience tooling under `scripts/`;
  - no runtime pychete import path, normal pytest path, or committed fixture
    dependency on Mathematica, `wolframscript`, or Matchete was introduced.
- Verification for the one-command optional conversion-wrapper slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/loaders/test_matchete_model_state_converter.py -q'` passed:
    4 passed.
- Final verification for the one-command optional conversion-wrapper slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/loaders/test_matchete_model_state_converter.py -q'` passed:
    4 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 212 passed,
    1 skipped in 144.53s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Added an opt-in spenso tensor-network evaluation hook to the
  Mathematica-independent validation preview path:
  - rescanned the local spenso Python stub around `TensorLibrary`,
    `TensorNetwork.execute(...)`, and `TensorNetwork.result_scalar(...)`
    before adding the hook;
  - `ValidationFixture.one_loop_preview(...)` can now call
    `OneLoopSetup.evaluate_tensor_networks(...)` before building the
    interaction-power preview, with pass-through controls for explicit CG
    component maps, built-in CG components, native HEP builtins, symbolic
    components, an existing native library, function libraries, step limits,
    and execution mode;
  - `ValidationFixture.one_loop_preview_gap_report(...)` mirrors those options
    so current-vs-Matchete fixture comparisons can opt into the same native
    spenso route;
  - preview metadata now records whether tensor networks were evaluated and
    which CG component source was used (`explicit`, `builtin`, `symbolic`,
    `stored`, `native_hep`, or `library`);
  - added a focused integration test on the committed `S1S3LQs` model fixture
    proving the validation preview can route generated kernels through spenso,
    automatically build a native `TensorLibrary` from stored Matchete sparse-CG
    component metadata, and remove `pychete::CG` atoms before native tensor
    execution, while keeping default previews unchanged.
- Verification for the validation-preview spenso hook so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_evaluate_tensor_networks_with_stored_cg_components
    -q'` passed: 1 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed:
    16 passed.
- Final verification for the validation-preview spenso hook:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed:
    16 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 213 passed,
    1 skipped in 164.18s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Added the first generic matching-condition projection API on structured
  `MatchingResult` objects:
  - inspected Symbolica's `Expression.coefficient(...)` stub and checked that
    it projects literal products such as `C*O` natively before adding pychete
    wrapper code;
  - `MatchingResult.project_matching_conditions(...)` now extracts a
    dictionary of condition values from any named result expression stage,
    defaulting to `on_shell_eft_lagrangian`, using native Symbolica
    coefficients rather than Python term walkers;
  - `MatchingResult.with_projected_matching_conditions(...)` returns a new
    result carrying those projected conditions, preserving or replacing
    existing conditions according to the `merge` option and recording
    projection metadata;
  - iterable targets are keyed by canonical pychete strings, while mappings can
    provide stable public condition names. `drop_zero=True` removes conditions
    whose native coefficient is zero;
  - this does not complete SMEFT matching-condition extraction, but it gives the
    one-loop result pipeline a real reusable native-Symbolica coefficient
    projection step for future SMEFT basis maps.
- Verification for the matching-condition projection slice so far:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py tests/unit/definitions/test_public_api.py
    -q'` passed: 12 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
- Final verification for the matching-condition projection slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py tests/unit/definitions/test_public_api.py
    -q'` passed: 12 passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 214 passed,
    1 skipped in 163.10s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Extended the validation gap-report layer from matching-condition presence
  counts to actual canonical matching-condition expression comparisons:
  - `MatchingFixtureGapReport` now records canonical-equal and
    canonical-different shared matching-condition names and JSON counts;
  - `_gap_report(...)` compares shared matching-condition expressions through
    the existing `MatchingResult.compare_to(...)` path, so canonical equality
    remains the primary validation mechanism;
  - `ValidationFixture.one_loop_preview_gap_report(...)` can now opt into
    `project_reference_matching_conditions=True`, which parses the reference
    fixture's canonical matching-condition keys through the registered theory
    state and uses native Symbolica coefficient projection to populate
    candidate conditions before comparison;
  - this keeps default gap reports unchanged, but gives Matchete fixture
    comparisons a concrete route from the current one-loop preview Lagrangian
    to the 72 committed SMEFT-style reference condition names;
  - on the committed `Singlet_Scalar_Extension` fixture with
    `max_trace_order=1`, opt-in condition projection exposes all 72 reference
    condition keys on the candidate and currently yields 39 canonical-equal and
    33 canonical-different matching conditions.
- Confirmed the optional Mathematica conversion route remains committed under
  the top-level `scripts/` directory for users with Mathematica, while this
  validation-comparison slice keeps pychete runtime code and normal pytest
  fully Matchete- and Mathematica-independent.
- Final verification for the matching-condition gap-report slice:
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_can_project_reference_matching_conditions_without_mathematica
    -q'` passed: 10 passed.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed: 17
    passed in 165.74s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 216 passed, 1
    skipped in 174.51s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Extended selective evaluator-probe reporting from supertraces to projected
  matching conditions:
  - `MatchingFixtureGapReport` now records numeric-probe-equal and
    numeric-probe-different shared matching-condition names and JSON counts;
  - `ValidationFixture.one_loop_preview_gap_report(...)` and `_gap_report(...)`
    accept `probe_matching_condition_names`, keeping condition probes opt-in so
    supertrace probe samples do not accidentally evaluate every projected
    matching condition;
  - the implementation reuses `MatchingResult.compare_to(...)` and
    `Expression.evaluator_multiple(...)`, preserving the Symbolica-first
    evaluator policy for non-canonical but numerically equivalent validation
    expressions.
- Final verification for the matching-condition evaluator-probe slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed: 10
    passed in 0.07s.
  - `git diff --check` passed.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed: 17
    passed in 166.02s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 217 passed, 1
    skipped in 174.16s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Added deterministic Symbolica-backed numeric probe planning for future
  fixture comparisons:
  - `NumericProbePlan`, `deterministic_probe_samples(...)`, and
    `build_numeric_probe_plan(...)` are now public pychete APIs, with
    parameter discovery delegated to native `Expression.get_all_symbols(...)`;
  - `ValidationFixture.one_loop_preview_gap_report(...)` and `_gap_report(...)`
    can opt into `auto_probe_samples=True` for selected
    `probe_supertrace_names` and/or `probe_matching_condition_names`, building
    evaluator parameters and deterministic sample rows from the selected
    candidate/reference expressions;
  - automatic probe sampling intentionally requires explicit probe-name
    selectors and refuses explicit `probe_parameters`/`probe_samples` in the
    same call, preventing broad accidental numerical evaluation of every large
    Matchete fixture expression.
- Final verification for the deterministic probe-plan slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed: 12
    passed in 0.08s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_public_api.py -q'` passed: 4 passed in 0.02s.
  - `git diff --check` passed.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py
    tests/unit/definitions/test_public_api.py -q'` passed: 16 passed in 0.06s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed: 17
    passed in 167.06s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 219 passed, 1
    skipped in 172.01s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Added canonical-or-probe acceptance reporting to fixture gap reports:
  - `MatchingFixtureGapReport` now exposes accepted shared supertrace and
    matching-condition names/counts, where accepted means either canonical
    Symbolica equality or successful Symbolica evaluator probe fallback;
  - the report also exposes the remaining shared names that are still
    different after enabled probes, giving Matchete fixture comparisons a
    direct view of "accepted by validation policy" versus "still unresolved";
  - JSON output and Jupyter-friendly HTML/LaTeX summaries now surface accepted
    counts, while the raw canonical and numeric-probe split remains available
    for diagnosis.
- Final verification for the canonical-or-probe acceptance-report slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed: 12
    passed in 0.07s.
  - `git diff --check` passed.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed: 12
    passed in 0.05s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed: 17
    passed in 167.77s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 219 passed, 1
    skipped in 173.61s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Expanded the Mathematica-independent matching-condition acceptance frontier
  over all four default Matchete one-loop matching targets:
  - `tests/integration/validation/test_validation_fixtures.py` now projects
    reference matching-condition keys for `VLF_toy_model`,
    `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs` from current pychete
    preview Lagrangians and checks accepted/unresolved counts through the new
    canonical-or-probe report fields;
  - current `max_trace_order=1` projected matching-condition frontier is
    `VLF_toy_model` 0/0, `Singlet_Scalar_Extension` 39/72 accepted,
    `E_VLL` 25/72 accepted, and `S1S3LQs` 12/72 accepted;
  - this keeps pytest fully Mathematica-independent while making the default
    SMEFT-oriented matching-condition target gap explicit for future one-loop
    matching slices.
- Final verification for the default projected matching-condition frontier
  slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_default_matching_target_projected_matching_condition_frontier_without_mathematica
    -q'` passed: 1 passed in 37.62s.
  - `git diff --check` passed.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed: 17
    passed in 196.03s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 219 passed, 1
    skipped in 203.12s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Hardened automatic evaluator probe parameter discovery for pychete function
  atoms:
  - `build_numeric_probe_plan(...)` now keeps the default `symbols` parameter
    discovery mode for ordinary Symbolica numerical functions, preserving
    probes such as `sin(x)^2 + cos(x)^2 == 1`;
  - added `parameter_mode="indeterminates"`, which delegates to native
    `Expression.get_all_indeterminates(enter_functions=False)` so custom
    pychete function applications such as `Coupling(...)`, `Index(...)`, and
    stored `log(...)` applications can become evaluator parameters instead of
    causing Symbolica evaluator construction failures;
  - `ValidationFixture.one_loop_preview_gap_report(...)` and `_gap_report(...)`
    thread this through as `probe_parameter_mode`, and focused tests cover the
    custom-function path.
- Added a real default-fixture regression that probes the first unresolved
  `Singlet_Scalar_Extension` matching condition with
  `probe_parameter_mode="indeterminates"`. This confirms the automatic
  Symbolica evaluator path works on committed Matchete-derived expressions
  containing pychete `Coupling(...)` applications and stored logarithms, not
  only on synthetic function atoms.
- Development probe of the first five canonical-different projected matching
  conditions in each of `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`
  with `probe_parameter_mode="indeterminates"` produced no additional
  numeric-probe equalities; the current acceptance frontier remains 39/72,
  25/72, and 12/72 respectively.
- Final verification for the probe parameter-mode slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed: 13
    passed in 0.08s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_default_matching_condition_probe_accepts_fixture_function_indeterminates
    -q'` passed: 1 passed in 15.43s.
  - `git diff --check` passed.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py -q'` passed: 13
    passed in 0.07s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_public_api.py -q'` passed: 4 passed in 0.02s.
  - After the final import-format cleanup, `git diff --check` and `bash -lc
    'source "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m
    mypy'` passed again, and `bash -lc 'source "$HOME/.bashrc" &&
    PYTHONPATH=src dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_numeric_probes.py
    tests/unit/definitions/test_public_api.py -q'` passed: 17 passed in
    0.07s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed: 17
    passed in 199.55s.
  - After adding the real default-fixture regression, `bash -lc 'source
    "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py -q'` passed: 18
    passed in 210.73s.
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed finally on the
    current tree: 220 passed, 1 skipped in 201.51s. The skip is the existing
    GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
  - After adding the real default-fixture regression, `bash -lc 'source
    "$HOME/.bashrc" && PYTHONPATH=src dependencies/.venv/bin/python -m pytest
    tests -q'` passed: 221 passed, 1 skipped in 217.42s. The skip is the
    existing GammaLoop API import check because GammaLoop was not requested in
    the current dependency manifest.
- Exposed matching-condition projection through the public one-loop matching
  API:
  - `Theory.match(..., loop_order=1, matching_condition_targets=...)` now
    forwards requested targets to `match_one_loop(...)`;
  - `match_one_loop(...)` returns a projected `MatchingResult` by delegating to
    `MatchingResult.with_projected_matching_conditions(...)`, so coefficient
    extraction stays on the native Symbolica `Expression.coefficient(...)`
    path rather than adding a Python expression walker;
  - tree-level `Theory.match(..., loop_order=0)` now rejects
    `matching_condition_targets` explicitly, keeping the expression-returning
    tree API unchanged and preventing silent ignored projection requests;
  - added integration coverage for requested nonzero projection,
    `drop_zero=True`, metadata bookkeeping, and tree-level rejection.
- Reconfirmed the optional Mathematica conversion route should stay committed
  under the top-level `scripts/` directory for users with Mathematica,
  including `scripts/convert_matchete_model_state.wls`. This remains
  convenience tooling only: pychete runtime code, normal pytest, and committed
  fixture consumption remain completely Matchete- and Mathematica-independent.
- Verification for the public one-loop matching-condition projection slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_heavy_scalar_tree.py -q'` passed: 9
    passed in 0.23s;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_public_api.py -q'` passed: 4 passed in
    0.02s;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 223 passed, 1
    skipped in 216.49s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Added a public one-loop matching options object and routed an opt-in fixture
  validation path through the public `Theory.match(...)` API:
  - introduced `OneLoopMatchOptions` as a package-root public API export for
    `Theory.match(..., loop_order=1)`, keeping advanced backend/trace/order
    controls discoverable without adding a large keyword surface directly to
    `Theory.match`;
  - `match_one_loop(...)` now dispatches through `OneLoopIntegralBackend`
    options to the existing vakint, internal analytic, or internal
    minimal-subtraction preview backends, while preserving the previous public
    defaults (`internal_minimal_subtraction`, `tensor_reduce=False`,
    `combine_terms=True`);
  - `ValidationFixture.one_loop_preview_gap_report(...,
    use_public_match_api=True)` can now build the candidate through
    `Theory.match(..., one_loop_options=..., matching_condition_targets=...)`
    and therefore tests public one-loop projection directly against committed
    Matchete-derived fixtures;
  - the default fixture preview route remains unchanged so fixture-local
    tensor-network evaluation and broader preview knobs are still available
    without pretending they are part of the public `Theory.match` surface yet;
  - added Mathematica-independent tests for options-driven backend/trace-order
    selection, loop-order option rejection in tree matching, and projected
    Singlet Scalar Extension matching-condition comparison through the public
    match path.
- Final verification for the public one-loop options slice:
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_heavy_scalar_tree.py -q'` passed: 10
    passed in 0.27s;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_can_project_conditions_through_public_match_api
    -q'` passed: 1 passed in 9.07s;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_public_api.py -q'` passed: 4 passed in
    0.02s;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 225 passed, 1
    skipped in 226.54s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Promoted spenso tensor-network evaluation to the public one-loop match path:
  - extended `OneLoopMatchOptions` with the existing tensor-network controls:
    `evaluate_tensor_networks`, explicit CG component mappings, builtin/native
    HEP/symbolic CG component modes, tensor-network library, function library,
    step count, and execution mode;
  - `match_one_loop(...)` now applies
    `OneLoopSetup.evaluate_tensor_networks(...)` before backend integral
    evaluation when requested, preserving the native spenso route through
    pychete's `backends.spenso.evaluate_pychete_tensor_network(...)` adapter;
  - public one-loop `MatchingResult.metadata` now records
    `tensor_networks_evaluated`, `tensor_network_cg_component_source`, and
    `tensor_network_native_hep_cg_builtins`, matching the fixture preview
    metadata conventions;
  - `ValidationFixture.one_loop_preview_gap_report(...,
    use_public_match_api=True, evaluate_tensor_networks=True)` now routes the
    same tensor-network options through `Theory.match(...)` instead of
    rejecting that combination;
  - added Mathematica-independent tests proving public `Theory.match` can
    route generated kernels through spenso, forward library/function/step/mode
    options, and automatically use stored sparse CG tensor components from the
    committed `S1S3LQs` fixture.
- Final verification for the public tensor-network one-loop options slice:
  - inspected the spenso Python stubs for native `TensorLibrary.register`,
    `TensorLibrary.hep_lib`, `TensorLibrary.hep_lib_atom`,
    `TensorNetwork.execute`, and `TensorNetwork.result_scalar`;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_heavy_scalar_tree.py -q'` passed: 11
    passed in 0.28s;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_public_one_loop_match_can_evaluate_fixture_tensor_networks_with_stored_cg_components
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_can_project_conditions_through_public_match_api
    -q'` passed: 2 passed in 32.22s;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_public_api.py -q'` passed: 4 passed in
    0.02s;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 227 passed, 1
    skipped in 252.05s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.
- Exposed existing interaction-power vakint loop normalization through the
  public one-loop matching options:
  - extended `OneLoopMatchOptions` with `normalization`, defaulting to
    `OneLoopNormalization.PREVIEW` so previous public behavior is unchanged;
  - `match_one_loop(...)` now delegates non-preview vakint normalization to
    `OneLoopSetup.interaction_power_type_normalized_matching_result(...)`,
    preserving the existing Symbolica-native `Expression.I`, `Expression.PI`,
    and `Expression.expand()` path for scaled EFT Lagrangians and pole/finite
    pieces;
  - non-preview normalization is rejected for the pychete internal analytic
    backends for now, because those backends already carry explicit analytic
    vacuum-integral normalization and need a separate convention decision
    before accepting additional loop factors;
  - `ValidationFixture.one_loop_preview(...)` and
    `one_loop_preview_gap_report(...)` now accept the same normalization option
    and route it through either direct fixture preview or public
    `Theory.match(...)` preview when requested;
  - added Mathematica-independent tests proving public `Theory.match` can
    return a normalized vakint result with the unnormalized aggregate retained,
    and proving fixture previews can request Matchete-hbar normalization
    without invoking Mathematica.
- Final verification for the public one-loop normalization option slice:
  - inspected the Symbolica Python stubs for native `Expression.expand`,
    `Expression.collect`, `Expression.coefficient`, and `Expression.together`,
    and confirmed this slice reuses the existing native normalization helper
    rather than adding Python algebra;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/matching/test_heavy_scalar_tree.py -q'` passed: 12
    passed in 0.33s;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_preview_can_apply_vakint_normalization_without_mathematica
    -q'` passed: 1 passed in 0.29s;
  - `git diff --check` passed;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest
    tests/unit/definitions/test_public_api.py -q'` passed: 4 passed in
    0.02s;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m mypy'` passed: no issues found in 29
    source files;
  - `bash -lc 'source "$HOME/.bashrc" && PYTHONPATH=src
    dependencies/.venv/bin/python -m pytest tests -q'` passed: 229 passed, 1
    skipped in 247.22s. The skip is the existing GammaLoop API import check
    because GammaLoop was not requested in the current dependency manifest.

## Remaining Work

- Continue using the four committed default Matchete matching fixtures as
  acceptance targets for the pychete one-loop matching engine; current tests
  cover both raw/vakint and public finite/MS preview gap reports, but final
  Matchete equivalence is still incomplete.
- Extend the new loaded-model-state exporter/converter beyond the current
  initial contract, especially richer vector/zero-mode metadata and
  complicated Matchete models that exceed the direct Python loader's documented
  subset. Internal coupling-symmetry associations are now preserved as
  explicit signed pychete permutation metadata, and the default loaded-model
  fixtures now store supported compressed `SparseArray[...]` CG tensors as
  dense Symbolica component metadata consumable by spenso.
- Extend the new paired-derivative momentum lowering beyond scalar contracted
  derivative pairs into open derivative slots, vector/gauge Lorentz structures,
  full propagator expansion beyond the new scalar operator-derived denominator,
  interaction-insertion, public interaction-power contribution chain, and
  integration-by-parts convention validation against Matchete fixtures.
- Extend `FluctuationBasis` degree-of-freedom metadata beyond the new internal
  and spin/Lorentz mode metadata into backend-evaluated vector Lorentz traces,
  real/complex coefficient placement in actual supertrace kernels, and later
  model-specific SMEFT basis classifications.
- Extend the new spenso metadata bridge from native `Representation`,
  `TensorStructure`, `TensorIndices`, and expression-wide CG replacement into
  remaining generator/structure support outside native SU(3) HEP tensors,
  contractions, simplifications, and invariant-tensor construction, using
  idenso where gamma/colour/index algebra is the right backend.
- Extend the current public interaction-power internal minimal-subtraction
  preview into a fully physical one-loop matching result, including phase
  conventions, loop-momentum sign conventions, propagator insertion ordering
  for multi-mode blocks, tensor reductions, scheme-specific renormalization
  beyond the current minimal-subtraction preview, and validation against
  Matchete fixtures and known native backend topologies.
- Extend the pychete-owned analytic vacuum-integral backend beyond the covered
  scalar one-loop zero/mixed/single-scale and finite two-mass
  `LoopIntegration.wl` cases into broader loop-function behavior: canonical
  LF-style simplification when an unevaluated placeholder API is actually
  needed, higher numerator structures after tensor reduction, and
  near-degenerate expansion policies. Native vakint remains available for
  topology-independent tensor reduction and supported single-scale massive
  analytic evaluation cross-checks.
- Extend the new endpoint-aware Dirac bridge into full pychete field-endpoint
  open-chain lowering. Current VLF previews no longer contain `der(...)`
  artifacts, bare `P_R^2`/`P_L^2` powers in the covered numerator path, or
  unsupported compact `DiracProduct` gamma/projector identities; registered
  `NCM(bar(field), dirac..., field)` chains now have an explicit tag-restricted
  native idenso middle-word route. The remaining gap is proper field-endpoint
  orientation, conjugation normalization, native spinor-index endpoint
  lowering, and final vakint evaluation before pychete can canonically agree
  with Matchete's saved `DiracProduct[...]` expressions.
- Add full SM/CG Lagrangian expression parsing to the model loader or replace
  direct source parsing for those expressions with generated pychete-owned state
  fixtures. The direct loader now expands the local S1/S3 CG helper definitions
  used by the default `S1S3LQs.m` asset into registered `CG(...)` atoms, but
  broader Wolfram helper syntax should still use the optional Mathematica
  exporter route.
- Lower remaining tensor contractions through the spenso/idenso adapter layer.
- Expand the converter/fixture path to additional mappable Matchete validation
  assets beyond the default matching targets.
- Apply the selective evaluator-probe gap-report plumbing to concrete Matchete
  fixture comparisons once suitable deterministic sample points and per-name
  probe eligibility are available for each model's free parameters and
  singularity constraints.
- Extend field metadata further for representation reality and SMEFT basis data.
- Extend theory metadata further for representation reality, CG tensors, and
  SMEFT basis data.
- Extend the matching engine toward one-loop matching.
