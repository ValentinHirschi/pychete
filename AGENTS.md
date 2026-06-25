# pychete Agent Notes

## Running Tests

Install the managed dependencies first:

```sh
python dependencies/install_dependencies.py
```

For a faster setup that skips the slow GammaLoop API build:

```sh
python dependencies/install_dependencies.py --no-gammaloop
```

Then run the test suite with pytest from the managed virtual environment:

```sh
source dependencies/.venv/bin/activate
python -m pytest tests
```

Equivalently, without activating the environment:

```sh
dependencies/.venv/bin/python -m pytest tests
```

The pytest suite includes a static typing check that runs `python -m mypy`.
To run it directly:

```sh
dependencies/.venv/bin/python -m mypy
```

Always use the managed virtual environment for pychete development and tests.
Do not use the ambient system Python when importing Symbolica, idenso, spenso,
or vakint.

Before running Python commands that import Symbolica, source `~/.bashrc` so the
local `SYMBOLICA_LICENSE` export is available:

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python -m pytest tests
```

## Logging And Progress Output

Use pychete's package logging layer for user-facing progress and debugging
output. Do not add ad hoc `print(...)` calls inside library code. Exported
helpers are available as:

```python
import pychete

pychete.configure_logging()
```

Use `pychete.logging.get_logger(...)` and `pychete.logging.progress(...)` from
implementation modules. Log high-level, notebook-friendly progress at `INFO`
for expensive matching, validation, tensor-reduction, and integral-evaluation
steps. Use `DEBUG` for lower-level internals. Never log full large Symbolica
expressions by default; log stage names, backend choices, counts, and timings.

## Dependency Policy

Using `sympy` and `scipy` is strictly forbidden in this project, including
importing them. All symbolic, algebraic, tensor, and integral work must be done
with Symbolica and the locally built community modules as much as possible.

Use:

- Symbolica for all symbolic and algebraic manipulations.
- idenso for gamma-matrix and colour algebra.
- spenso for tensor-network evaluations when needed.
- pychete's own Matchete-style analytic backend for one-loop vacuum integral
  evaluation, including single-scale, zero-mass, and mixed-mass cases after
  tensor reduction.
- vakint for topology-independent tensor reduction of vacuum-integral
  numerators, and as a supported optional backend/cross-check for single-scale
  massive analytic evaluations. Zero-mass or mixed-mass vacuum integral
  evaluation must not be delegated to vakint's numerical methods.

The installer builds the GammaLoop API against the local Symbolica checkout
with Symbolica's `gmp` feature enabled. GMP is an accepted dependency for this
project.

## Native Symbolica First

Performance matters. Symbolica is Rust-backed; handwritten Python symbolic
algorithms, tree walkers, replacement loops, simplifiers, derivative engines,
polynomial routines, tensor contractions, or integral reducers are forbidden
unless the local Symbolica/idenso/spenso/vakint/GammaLoop APIs have first been
checked and found insufficient for the specific operation.

Before adding or modifying symbolic code, explicitly inspect the Python stubs
and source listed below. Prefer native primitives even when a Python loop seems
small. If Python orchestration remains necessary, keep it at the boundary and
push the actual symbolic operation into Symbolica primitives.

When code starts checking atom types with `Expression.get_type()` or unpacking
children manually, stop and first try to express the operation with Symbolica
patterns: `Expression.match`, `Expression.matches`, `Expression.replace`,
`Expression.replace_multiple`, `Expression.replace_wildcards`, and
`Replacement`. Atom-type dispatch is acceptable only for narrow boundary code
such as external parsers or numeric coercions, or after a pattern-based attempt
has been shown not to express the required semantics.

Treat `Expression.match(pattern, restriction)` as the native way to collect
matching subexpressions: it yields every match from the expression, and the
matched subexpression can be reconstructed with `pattern.replace_wildcards`.
Do not add separate Python tree-walk collectors when a pattern match provides
the same data.

For derivatives, variations, and covariant-derivative-like operators, do not
hand-code sum/product/power rules in Python. Match the relevant pychete atoms
with Symbolica patterns, encode them as temporary Symbolica variables with
`Replacement` and `Expression.replace_multiple`, then use native Symbolica
operations such as `Expression.derivative` or a formal variation extracted with
`Expression.series` and `Expression.coefficient`.
Momentum lowering must keep derivative information symbolic rather than
dropping it. Contracted derivative pairs lower to `LoopMomentumSquared`; open
Lorentz derivative slots lower to explicit `LoopMomentum(index)` numerator
factors. Keep this lowering implemented as Symbolica replacement rules over
`DifferentialOperator(...)`, then hand tensor numerator reduction to vakint
where applicable.
Before native vakint engine calls, lower pychete loop-momentum numerator heads
with `pychete.backends.vakint.lower_pychete_loop_momentum_numerators(...)`.
This maps `LoopMomentum(index)` to native `vakint::k(loop_id, index)` and
`LoopMomentumSquared` to native `vakint::k(loop_id, 1)^2`, matching the
vakint tensor-reduction API.
Metric and Kronecker-delta contractions involving pychete loop momenta must go
through the idenso adapter. Use `simplify_pychete_loop_momentum_metrics(...)`
or `simplify_index_algebra(..., metrics=True)` so expressions like
`Metric(mu, nu) * LoopMomentum(mu) * LoopMomentum(nu)` reduce to
`LoopMomentumSquared` before vacuum-integral evaluation.

Internal pychete categories must not be stringly typed. Use explicit enum or
Symbolica constants such as `FieldMassKind`, `BuiltinIndexType`, and the
central `s` symbol store. Strings are acceptable only at external input
boundaries such as model parsers, JSON serialization, or user-facing API
compatibility shims, and must be normalized immediately.

Public API discoverability lives in `src/pychete/api.py`. Keep implementation
functions in their domain modules, but every function/class/enum intended for
users must be re-exported through `pychete.api` and package-root `pychete`.
Do not make users infer the public surface by browsing implementation files.
Every exported public object, and every user-facing method on exported classes,
must have a useful docstring at its implementation definition. These docstrings
are part of the interactive API: they should show up in `help(...)`, notebooks,
and editor hover tooltips such as VS Code/Pylance. When adding or promoting a
public API, update the public API docstring tests rather than leaving the
documentation requirement implicit.

Take full advantage of Symbolica symbol tags, attributes, and symbol data.
User-defined pychete symbols must be created through `Theory.symbol`, which
adds role tags such as `field`, `coupling`, `index`, `index_type`, `group`, and
`external`, plus symbol data for the owning theory and label. Pattern matching
over these symbols must use native Symbolica restrictions such as
`wildcard.req_tag(...)`, `wildcard.req_attr(...)`, `Expression.get_tags`, and
`Expression.get_symbol_data` where applicable. Do not enumerate all fields,
couplings, or indices in Python when a tag-restricted Symbolica pattern can
select the relevant expressions directly.
Imported names that are not registered fields, couplings, groups,
representations, or CG tensors must be registered through
`Theory.define_external(...)` and accessed through `Theory.external_handle(...)`.
This is the structural route for Matchete-derived Wilson-condition labels and
helper symbols: it preserves `external` Symbolica tags, symbol data, JSON
round-trips, and Jupyter-friendly metadata objects. Do not scatter direct
`Theory.symbol(..., role=SymbolRole.EXTERNAL)` calls in parsers or converters
unless you are maintaining the low-level registry primitive itself.
Known linear external helper functions, currently including Matchete-style
`Transp`, must receive the `external_linear_function` Symbolica tag and be
linearized through Symbolica replacement rules before variation extraction,
EFT marker extraction, or NCM coefficient selection. Do not allow EFT markers
or formal variation parameters to remain hidden inside tagged linear wrappers;
pull them outside with native `coefficient_list(...)`/`replace_multiple(...)`
logic before selecting operator dimensions or supertrace terms.
Matching-condition Wilson coefficients must be registered through
`Theory.define_wilson_coefficient(...)` before any expression containing that
symbol is parsed. Symbolica symbol data is fixed at creation time, so converters
must predeclare Wilson targets from the matching-condition left-hand side before
calling `parse_matchete_expression(...)`. Store basis metadata such as `SMEFT`,
target index expressions, and EFT order on the external label rather than in a
separate Python-only side table.

Group representation labels must be registered through
`Theory.define_representation(...)`. Model-specific labels such as Matchete's
`SU2L[quad]` must be theory-owned Symbolica symbols with `representation`
role tags and `representation_group`, `representation_dynkin`,
`representation_dimension`, and `representation_reality` symbol data, never
plain external symbols.

Clebsch-Gordan tensors must be registered through
`Theory.define_cg_tensor(...)`. Model-specific tensors such as Matchete's
`C4[i,j,k,M]` must become theory-owned `cg_tensor` labels used through the
central `CG(label, indices)` head, with `cg_representations`, optional
`cg_tensor`, and `cg_source` symbol data. Do not leave them as plain external
functions, and do not hand-roll contractions in Python; lower them through
spenso/idenso backend adapters. Use
`pychete.backends.spenso.representation_to_spenso(...)`,
`pychete.backends.spenso.cg_tensor_structure_to_spenso(...)`, and
`pychete.backends.spenso.indexed_cg_tensor_to_spenso(...)` as the standard
metadata bridge from pychete theory definitions to native spenso objects. Use
`pychete.backends.spenso.lower_cg_tensors_to_spenso(...)` and
`pychete.backends.spenso.evaluate_pychete_tensor_network(...)` when lowering
whole expressions; these functions use Symbolica's replacement engine with
`cg_tensor` tag restrictions and then delegate tensor-network work to spenso.
Use `pychete.backends.spenso.cg_tensor_library_tensor_to_spenso(...)`,
`pychete.backends.spenso.register_cg_tensor_in_spenso_library(...)`, and
`pychete.backends.spenso.cg_tensor_library_to_spenso(...)` when registering CG
tensors in native spenso libraries. Do not register empty sparse CG tensors as
placeholders: provide explicit component data, or opt into generated symbolic
components when a formal component-level tensor library is intended. For
supported built-in tensors, pass `builtin_components=True`; currently this is
only valid for finite `del[...]` identity tensors and `eps[...]` Levi-Civita
tensors. Do not invent component arrays for generators or structure constants;
use spenso/idenso native support or add a documented backend patch/adapter when
those components are needed. For compatible SU(3) colour tensors, pass
`native_hep_cg_builtins=True` so pychete lowers `gen[SU3[fund]]` and
`fStruct[SU3]` to spenso's native HEP `TensorName.t()` and `TensorName.f()`
objects with `Representation.cof(3)` / `Representation.coad(8)` and spenso's
HEP tensor library.
Built-in Matchete CG labels such as `gen[group[rep]]`, `eps[group]`,
`fStruct[group]`, `dSym[group]`, and `del[group[rep]]` must resolve to the
auto-registered theory-owned CG tensor labels, not to generic external
functions.

Every reusable pychete built-in symbol must be created through the central
`SymbolStore` so it receives pychete's custom Symbolica print callback. Human
printing should look good in `PrintMode.Symbolica`, `PrintMode.Latex`,
`PrintMode.Mathematica`, `PrintMode.Sympy`, and `PrintMode.Typst`; JSON and
checkpoint serialization must use `canonical_string(...)`, which disables
pretty callbacks through `custom_print_mode`.
Do not add convenience numeric constants such as `s.half` or
`s.twenty_fourth` to `SymbolStore`. Use ordinary Symbolica arithmetic like
`expr / 2`, `expr / 24`, `Expression.num(0)`, or `Expression.num(1)` for
numbers; the central symbol store is for pychete symbols and expression heads.

At minimum, check these exact Symbolica APIs before implementing anything
similar in Python:

- Constructors and parsing: `S`, `N`, `E`, `T`, `P`, `Expression.symbol`,
  `Expression.num`, `Expression.parse`, `Expression.load`, `Expression.save`.
- Formatting and export: `Expression.format`, `Expression.formatted`,
  `Expression.format_plain`, `Expression.to_latex`, `Expression.to_typst`,
  `Expression.to_sympy`, `Expression.to_mathematica`.
- Atom and symbol inspection: `Expression.get_type`, `Expression.get_name`,
  `Expression.get_tags`, `Expression.get_attributes`,
  `Expression.get_symbol_data`, `Expression.get_all_symbols`,
  `Expression.get_all_indeterminates`, `Expression.contains`.
  `Expression.to_atom_tree` is a low-level fallback only; prefer
  `get_type`, `get_name`, matching, and replacement primitives first.
- Elementary and special functions: `Expression.cos`, `Expression.sin`,
  `Expression.tan`, `Expression.cot`, `Expression.sec`, `Expression.csc`,
  `Expression.asin`, `Expression.acos`, `Expression.atan`,
  `Expression.acot`, `Expression.asec`, `Expression.acsc`,
  `Expression.sinh`, `Expression.cosh`, `Expression.tanh`,
  `Expression.coth`, `Expression.sech`, `Expression.csch`,
  `Expression.asinh`, `Expression.acosh`, `Expression.atanh`,
  `Expression.acoth`, `Expression.asech`, `Expression.acsch`,
  `Expression.exp`, `Expression.log`, `Expression.sqrt`,
  `Expression.abs`, `Expression.zeta`, `Expression.gamma`,
  `Expression.polygamma`, `Expression.polylog`, `Expression.bessel_j`,
  `Expression.bessel_y`, `Expression.bessel_i`, `Expression.bessel_k`,
  `Expression.conj`, `Expression.hold`, `Expression.to_float`,
  `Expression.rationalize`.
- Algebra and simplification: `Expression.map`,
  `Expression.set_coefficient_ring`, `Expression.expand`,
  `Expression.expand_num`, `Expression.collect`,
  `Expression.collect_symbol`, `Expression.collect_factors`,
  `Expression.collect_horner`, `Expression.collect_num`,
  `Expression.collect_by_coefficient`, `Expression.coefficient_list`,
  `Expression.coefficient`, `Expression.derivative`, `Expression.series`,
  `Expression.apart`, `Expression.together`, `Expression.cancel`,
  `Expression.factor`, `Expression.to_polynomial`,
  `Expression.to_rational_polynomial`, `Expression.canonize_tensors`.
- Matching and replacement: `Expression.match`, `Expression.matches`,
  `Expression.replace_iter`, `Expression.replace`,
  `Expression.replace_multiple`, `Expression.replace_wildcards`,
  `Replacement`, and callable right-hand sides in `Replacement`/`replace`.
  Do not write sequential Python replacement loops when `replace_multiple` or
  wildcard replacement rules can express the operation. Prefer callable
  replacement rules over "collect matching atoms, build exact replacements,
  then replace" when the replacement can be computed from wildcard bindings.
  If a match restriction needs custom logic after native tag/attribute/type
  restrictions are exhausted, use `PatternRestriction.req_matches`.
  Also check the wildcard restriction methods `Expression.req_len`,
  `Expression.req_tag`, `Expression.req_attr`, `Expression.req_type`,
  `Expression.req_contains`, `Expression.req_lit`, `Expression.req_cmp_lt`,
  `Expression.req_cmp_gt`, `Expression.req_cmp_le`, and
  `Expression.req_cmp_ge` before writing Python-side filtering.
- Solving and numerical evaluation: `Expression.solve_linear_system`,
  `Expression.nsolve`, `Expression.nsolve_system`, `Expression.evaluate`,
  `Expression.evaluator`, `Expression.evaluator_multiple`,
  `Evaluator.compile`, `Evaluator.evaluate`, `Evaluator.evaluate_complex`,
  `Evaluator.jit_compile`, `Evaluator.merge`, `Evaluator.dualize`.
- Transformer pipelines: `Transformer.if_then`, `Transformer.if_changed`,
  `Transformer.break_chain`, `Transformer.expand`, `Transformer.expand_num`,
  `Transformer.prod`, `Transformer.sum`, `Transformer.nargs`,
  `Transformer.sort`, `Transformer.cycle_symmetrize`,
  `Transformer.deduplicate`, `Transformer.from_coeff`, `Transformer.split`,
  `Transformer.linearize`, `Transformer.partitions`,
  `Transformer.permutations`, `Transformer.map`, `Transformer.map_terms`,
  `Transformer.for_each`, `Transformer.check_interrupt`,
  `Transformer.repeat`, `Transformer.chain`, `Transformer.derivative`,
  `Transformer.set_coefficient_ring`, `Transformer.collect`,
  `Transformer.collect_symbol`, `Transformer.collect_factors`,
  `Transformer.collect_horner`, `Transformer.collect_num`,
  `Transformer.collect_by_coefficient`, `Transformer.conjugate`,
  `Transformer.coefficient`, `Transformer.apart`, `Transformer.together`,
  `Transformer.cancel`, `Transformer.factor`, `Transformer.series`,
  `Transformer.replace`, `Transformer.replace_multiple`,
  `Transformer.print`, `Transformer.stats`.
- Polynomial/rational polynomial work: `Polynomial.parse`,
  `Polynomial.nterms`, `Polynomial.get_variables`, `Polynomial.degree`,
  `Polynomial.reorder`, `Polynomial.gcd`, `Polynomial.extended_gcd`,
  `Polynomial.resultant`, `Polynomial.factor_square_free`,
  `Polynomial.factor`, `Polynomial.derivative`, `Polynomial.integrate`,
  `Polynomial.content`, `Polynomial.primitive`, `Polynomial.monic`,
  `Polynomial.lcoeff`, `Polynomial.coefficient_list`,
  `Polynomial.groebner_basis`, `Polynomial.reduce`,
  `Polynomial.to_expression`, `Polynomial.evaluate`,
  `Polynomial.evaluate_complex`, `Polynomial.replace`,
  `Polynomial.interpolate`, `Polynomial.to_finite_field`,
  `Polynomial.to_number_field`, `Polynomial.adjoin`,
  `Polynomial.simplify_algebraic_number`, plus the corresponding
  `NumberFieldPolynomial`, `FiniteFieldPolynomial`, `RationalPolynomial`, and
  `FiniteFieldRationalPolynomial` methods.
- Series and streaming: `Series.get_coefficient`, `Series.to_expression`,
  `Series.sin`, `Series.cos`, `Series.exp`, `Series.log`, `Series.pow`,
  `Series.spow`, `Series.shift`, `Series.get_ramification`,
  `Series.get_trailing_exponent`, `Series.get_relative_order`,
  `Series.get_absolute_order`, `TermStreamer.load`, `TermStreamer.save`,
  `TermStreamer.push`, `TermStreamer.clear`, `TermStreamer.normalize`,
  `TermStreamer.to_expression`, `TermStreamer.map`,
  `TermStreamer.map_single_thread`, `TermStreamer.get_num_terms`,
  `TermStreamer.fits_in_memory`.
- Linear algebra, graph, and integer utilities: `Matrix.identity`,
  `Matrix.eye`, `Matrix.vec`, `Matrix.from_linear`, `Matrix.from_nested`,
  `Matrix.inv`, `Matrix.det`, `Matrix.solve`, `Matrix.solve_any`,
  `Matrix.row_reduce`, `Matrix.augment`, `Matrix.split_col`,
  `Matrix.content`, `Matrix.primitive_part`, `Matrix.map`,
  `Graph.generate`, `Graph.canonize`, `Graph.canonize_edges`,
  `Graph.is_isomorphic`, `Integer.prime_iter`, `Integer.is_prime`,
  `Integer.factor`, `Integer.totient`, `Integer.gcd`, `Integer.lcm`,
  `Integer.extended_gcd`, `Integer.chinese_remainder`,
  `Integer.solve_integer_relation`.
- Numerical integration utilities: `NumericalIntegrator.continuous`,
  `NumericalIntegrator.discrete`, `NumericalIntegrator.uniform`,
  `NumericalIntegrator.rng`, `NumericalIntegrator.import_grid`,
  `NumericalIntegrator.export_grid`,
  `NumericalIntegrator.get_live_estimate`, `NumericalIntegrator.probe`,
  `NumericalIntegrator.sample`, `NumericalIntegrator.merge`,
  `NumericalIntegrator.add_training_samples`, `NumericalIntegrator.update`,
  `NumericalIntegrator.integrate`, `Probe.discrete`, `Probe.continuous`,
  `Probe.uniform`, `RandomNumberGenerator.next`,
  `RandomNumberGenerator.next_float`, `RandomNumberGenerator.load`,
  `RandomNumberGenerator.save`.

For idenso, check and use these exact APIs for gamma, colour, metric, and index
algebra before writing Python fallbacks: `cook_function`, `cook_indices`,
`dirac_adjoint`, `expand_bis`, `expand_color`, `expand_metrics`,
`expand_mink`, `expand_mink_bis`, `list_dangling`, `simplify_color`,
`simplify_gamma`, `simplify_metrics`, `to_dots`, `wrap_dummies`,
`wrap_indices`.

For spenso, check and use these exact APIs for tensor objects and tensor-network
evaluation before writing Python tensor logic: `Representation`,
`Representation.bis`, `Representation.euc`, `Representation.mink`,
`Representation.cof`, `Representation.coad`, `Representation.cos`, `Slot`,
`TensorName`, `TensorName.g`, `TensorName.flat`, `TensorName.gamma`,
`TensorName.gamma5`, `TensorName.projm`, `TensorName.projp`,
`TensorName.sigma`, `TensorName.f`, `TensorName.t`, `TensorIndices`,
`TensorStructure`, `TensorStructure.symbolic`, `TensorStructure.index`,
`Tensor`, `Tensor.sparse`, `Tensor.dense`, `Tensor.one`, `Tensor.zero`,
`Tensor.evaluator`, `Tensor.scalar`, `LibraryTensor`,
`LibraryTensor.sparse`, `LibraryTensor.dense`, `LibraryTensor.one`,
`LibraryTensor.zero`, `TensorLibrary`, `TensorLibrary.construct`,
`TensorLibrary.register`, `TensorLibrary.hep_lib`,
`TensorLibrary.hep_lib_atom`, `TensorNetwork`, `TensorNetwork.one`,
`TensorNetwork.zero`, `TensorNetwork.replace`, `TensorNetwork.evaluate`,
`TensorNetwork.execute`, `TensorNetwork.result_tensor`,
`TensorNetwork.result_scalar`, `TensorEvaluator.evaluate`,
`TensorEvaluator.evaluate_complex`, `TensorEvaluator.compile`,
`CompiledTensorEvaluator.evaluate_complex`, `TensorFunctionLibrary`,
`initialize`.

For vakint, check and use these exact APIs for topology-independent tensor
reduction and optional single-scale massive vacuum integral cross-checks or
backend comparisons before writing Python logic: `Vakint`,
`Vakint.numerical_result_from_expression`,
`Vakint.numerical_evaluation`, `Vakint.numerical_result_to_expression`,
`Vakint.to_canonical`, `Vakint.tensor_reduce`, `Vakint.evaluate_integral`,
`Vakint.evaluate`, `VakintEvaluationMethod.new_alphaloop_method`,
`VakintEvaluationMethod.new_matad_method`,
`VakintEvaluationMethod.new_fmft_method`,
`VakintEvaluationMethod.new_pysecdec_method`, `VakintExpression`,
`VakintExpression.to_expression`, `VakintNumericalResult`,
`VakintNumericalResult.to_list`, `VakintNumericalResult.compare_to`.

## API Discovery

The local source checkouts under `dependencies/` are the primary API reference.
Inspect implementation details directly in:

- `dependencies/symbolica/src/`
- `dependencies/gammaloop/crates/idenso/`
- `dependencies/gammaloop/crates/spenso/`
- `dependencies/gammaloop/crates/spynso3/`
- `dependencies/gammaloop/crates/vakint/`
- `dependencies/gammaloop/crates/gammaloop-api/`

For Python-facing APIs, also inspect the generated/source stub files:

- `dependencies/symbolica-community/python/symbolica/core.pyi`
- `dependencies/symbolica-community/python/symbolica/community/idenso/__init__.pyi`
- `dependencies/symbolica-community/python/symbolica/community/spenso/__init__.pyi`
- `dependencies/symbolica-community/python/symbolica/community/vakint/__init__.pyi`
- `dependencies/symbolica-community/python/symbolica/community/example_extension/__init__.pyi`
- `dependencies/symbolica/symbolica.pyi`

For GammaLoop's Python API, inspect:

- `dependencies/gammaloop/crates/gammaloop-api/python/gammaloop/__init__.py`
- `dependencies/gammaloop/crates/gammaloop-api/src/python.rs`

## Matchete Reference

The checkout at `Mathematica_reference/Matchete` is the Mathematica reference
implementation. Treat it as read-only reference material: do not edit it, vendor
from it, import it, or otherwise use it directly in `pychete`.

You may run `wolframscript` against the original implementation when you need
to test or compare behavior. Load Matchete in Wolfram Language with:

```wolfram
<<Matchete`
```

Useful read-only reference locations inside the checkout:

- Package files are in `Package/`.
- Current validation tests are in `Validation/Tests/`.
- Example model implementations are in `Models/`.

## Mathematica Loader Boundary

`src/pychete/loaders/mathematica.py` is an explicitly limited
Matchete/Wolfram-subset loader. It is acceptable for simple declarative model
fixtures and saved-result expression snippets, including supported heads such
as `ParentModel`, `ParameterDefault`, `DefineFlavorIndex`,
`DefineGaugeGroup`, `DefineGlobalGroup`, `DefineRepresentation`, `DefineCG`,
`DefineField`, and `DefineCoupling`.

Do not grow this Python loader into a general Wolfram Language parser. For
complicated Mathematica models, add or update optional Wolfram conversion
entry points under the top-level `scripts/` directory that load Matchete
itself, read Matchete's already-parsed internal data, and emit pychete-owned
serialized state or Python fixture files. Those emitted files may be committed
under `assets/` and used by tests and users. Normal pytest must continue to
consume only committed pychete fixtures and must not require `wolframscript`,
Mathematica, or a runnable Matchete checkout.

Keep optional user-facing entry points for this route under the top-level
`scripts/` directory, including `scripts/export_matchete_model_state.wls`,
`scripts/convert_matchete_model_state.wls`,
`scripts/convert_matchete_model_state.py`,
`scripts/export_matchete_matching_snapshots.wls`, and
`scripts/convert_matchete_previous_results.py`. These scripts are convenience
wrappers for users who already have Mathematica and Matchete available; they
must not be imported by pychete runtime code, required by pytest, or treated as
the canonical validation path. Supporting implementation code may live under
`helper_mathematica_scripts/`, but the discoverable user convenience route
must remain checked into `scripts/`.

## Symbolica Expression Policy

Symbolica expressions are pychete's canonical physics representation. Encode
fields, couplings, indices, derivatives, conjugation, group tensors, and EFT
bookkeeping directly with stable Symbolica function heads whenever practical.
Use Python objects only for registries, validated metadata, orchestration, and
services that cannot reasonably live in an expression.

All reusable Symbolica symbols, function heads, and pattern wildcards must be
created once in pychete's central symbol registry and referenced from there.
Do not scatter calls such as `S("name")` through the codebase, and do not use
`E("...")` to construct reusable internal symbols, function heads, or pattern
wildcards. String parsing with `E("...")` or `Expression.parse("...")` is fine
for numeric coefficients and genuinely one-off literals such as `1/24`; the
centralization rule is about reusable pychete symbols and expression heads, not
about every rational number.

Prefer expression construction such as:

```python
s.phi(s.flavor(s.quark), S("b"))
```

over:

```python
E("phi(flavor(quark), b)")
```

Pattern placeholders follow the same rule and belong in the central registry.

Mathematica model files may be accepted as external input through a dedicated,
explicitly limited parser/adapter. Runtime pychete code and tests must never
import or read executable implementation code from the Matchete checkout.

Gamma-matrix, colour, and metric algebra should use idenso's existing routines
through a pychete adapter. Add Symbolica replacement-rule fallbacks under
`pychete/group_algebra/` only for behavior not supplied by idenso.
