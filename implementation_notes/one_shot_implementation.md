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
  metric, and tensor algebra, and vakint for vacuum integral canonicalization,
  tensor reduction, and evaluation.
- Compare results by pychete canonical equality, backed by Symbolica evaluator
  numeric probes for hard-to-canonicalize expressions.

## Key Changes

- Add `helper_mathematica_scripts/` with Wolfram scripts that load Matchete and
  export model definitions, validation expected outputs, supertraces, matching
  conditions, and selected unit-test fixtures into pychete-owned serialized
  assets.
- Add committed fixture assets for Matchete-independent pytest validation;
  never require `wolframscript` in normal tests.
- Extend pychete metadata with gauge groups, representations, CG tensors,
  charges, chiral fermions, ghosts, Goldstones, background fields, coupling
  symmetries, diagonal/unitary metadata, and SMEFT basis metadata using
  Symbolica symbol tags/data.
- Replace the current tiny Mathematica loader as a validation path with fixture
  loading; keep any direct Mathematica-input support explicitly secondary.

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
  tensor/CG contraction through spenso adapters, and vacuum integrals through
  vakint adapters.
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
    the existing tree-level behavior for `loop_order=0` and failing loudly for
    `loop_order=1` until the real one-loop engine is implemented;
  - added tests that tree matching remains unchanged, one-loop requests cannot
    silently return tree-level results, and fixture comparisons report
    canonical mismatches.
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
- `Theory.match(..., loop_order=1)` now has an explicit public contract but
  intentionally raises `OneLoopMatchingNotImplementedError`. This is preferable
  to returning a fake `MatchingResult`: the next matching-engine slices must
  fill the pipeline stages and satisfy `MatchingResult.compare_to(...)` against
  the committed default fixtures.
- `MatchingResult.compare_to(...)` now directly supports the approved fallback
  policy for hard-to-canonicalize expressions: canonical strings are compared
  first, and only canonical mismatches are optionally sent through
  `evaluator_probe_equal(...)`, which uses `Expression.evaluator_multiple`.
  The first regression test uses `sin(x)^2 + cos(x)^2` versus `1`, confirming
  the evaluator path can prove equality when canonical expansion does not.
- The first fluctuation-operator extraction layer now uses Symbolica native
  primitives only for symbolic work: `Expression.replace_multiple` for
  simultaneous field-to-variable encoding, `Expression.derivative` for Hessian
  entries, and `Expression.replace_multiple` again for decoding. The current
  scope is algebraic Hessian extraction over an explicit basis; assembling full
  differential operators from derivative-valued fields remains a later
  one-loop matching stage.
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
- Added `PowerTypeSupertraceContribution` and `OneLoopSetup.power_type_*`
  helpers. These expose cyclically unique power-type traces, prefactor-weighted
  numerators, EFT-truncated numerators through the existing Symbolica-backed
  `series_eft(...)`, and vakint topology expressions built from the truncated
  numerators. This is the first structured bridge from setup kernels toward
  final `MatchingResult.supertraces`, while `Theory.match(loop_order=1)` still
  correctly refuses to return an incomplete matching result.
- Added aggregate power-type inspection outputs on `OneLoopSetup`.
  `power_type_eft_lagrangian(...)` now sums the cyclically unique
  EFT-truncated power-type numerators into a single off-shell contribution, and
  `power_type_vakint_integral_sum(...)` sums the corresponding vakint topology
  expressions. The aggregation is intentionally thin Python orchestration over
  Symbolica expressions: the symbolic EFT truncation remains in
  `series_eft(...)`, the integral shape is built through the vakint adapter,
  and the final algebraic cleanup is delegated to Symbolica `Expression.expand`.
  This gives the future `MatchingResult.off_shell_eft_lagrangian` and
  `MatchingResult.supertraces` stages a concrete intermediate value without
  making `Theory.match(loop_order=1)` return a partial result.
- Added `OneLoopSetup.power_type_matching_preview(...)`, which builds an
  explicitly incomplete `MatchingResult` from the current one-loop setup
  stages. The preview carries the UV Lagrangian, fluctuation-operator map,
  individual power-type supertrace expressions, the aggregate off-shell
  power-type contribution, the aggregate vakint topology sum, and metadata
  marking `complete=False`, `stage="power_type_preview"`, and
  `on_shell_reduced=False`. This starts wiring the existing setup outputs into
  the final structured result surface while preserving the guard that
  `Theory.match(loop_order=1)` must not return until the full one-loop engine
  exists.
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

## Test Status

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

## Remaining Work

- Use the four committed default Matchete matching fixtures as acceptance
  targets for the pychete one-loop matching engine.
- Extend `FluctuationOperator` extraction from algebraic Hessians over explicit
  basis entries to full differential fluctuation operators, including
  derivative-valued fields and integration-by-parts conventions.
- Extend `FluctuationBasis` toward full one-loop degree-of-freedom metadata,
  including spin/statistics signs, real/complex counting, ghosts, Goldstones,
  background fields, and non-propagating fields.
- Consume `SupertracePlan` and `PropagatorPlan` to build real one-loop
  supertrace terms beyond the new neutral denominator-slot expressions and
  preliminary vakint one-loop topology lowering, including physical loop
  normalization and phase conventions, physical loop-momentum sign conventions,
  propagator insertion ordering for multi-mode blocks, tensor reductions, and
  validation against known native backend topologies.
- Add full SM/CG Lagrangian expression parsing to the model loader or replace
  direct source parsing for those expressions with generated pychete-owned state
  fixtures.
- Lower S1/S3 local CG helper heads and other tensor contractions through the
  new spenso/idenso adapter layer.
- Expand the converter/fixture path to additional mappable Matchete validation
  assets beyond the default matching targets.
- Use `evaluator_probe_equal` in fixture comparison tests when canonical
  equality is insufficient.
- Extend field metadata further for background fields, Goldstones, ghosts,
  representation reality, and SMEFT basis data.
- Extend theory metadata further for background fields, Goldstones, ghosts,
  representation reality, global groups, CG tensors, and SMEFT basis data.
- Extend the matching engine toward one-loop matching.
