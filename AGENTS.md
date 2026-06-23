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

## Dependency Policy

Using `sympy` and `scipy` is strictly forbidden in this project, including
importing them. All symbolic, algebraic, tensor, and integral work must be done
with Symbolica and the locally built community modules as much as possible.

Use:

- Symbolica for all symbolic and algebraic manipulations.
- idenso for gamma-matrix and colour algebra.
- spenso for tensor-network evaluations when needed.
- vakint for integration and pole identification of massive vacuum integrals.

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

Internal pychete categories must not be stringly typed. Use explicit enum or
Symbolica constants such as `FieldMassKind`, `BuiltinIndexType`, and the
central `s` symbol store. Strings are acceptable only at external input
boundaries such as model parsers, JSON serialization, or user-facing API
compatibility shims, and must be normalized immediately.

Public API discoverability lives in `src/pychete/api.py`. Keep implementation
functions in their domain modules, but every function/class/enum intended for
users must be re-exported through `pychete.api` and package-root `pychete`.
Do not make users infer the public surface by browsing implementation files.

Take full advantage of Symbolica symbol tags, attributes, and symbol data.
User-defined pychete symbols must be created through `Theory.symbol`, which
adds role tags such as `field`, `coupling`, `index`, `index_type`, `group`, and
`external`, plus symbol data for the owning theory and label. Pattern matching
over these symbols must use native Symbolica restrictions such as
`wildcard.req_tag(...)`, `wildcard.req_attr(...)`, `Expression.get_tags`, and
`Expression.get_symbol_data` where applicable. Do not enumerate all fields,
couplings, or indices in Python when a tag-restricted Symbolica pattern can
select the relevant expressions directly.

Every reusable pychete built-in symbol must be created through the central
`SymbolStore` so it receives pychete's custom Symbolica print callback. Human
printing should look good in `PrintMode.Symbolica`, `PrintMode.Latex`,
`PrintMode.Mathematica`, `PrintMode.Sympy`, and `PrintMode.Typst`; JSON and
checkpoint serialization must use `canonical_string(...)`, which disables
pretty callbacks through `custom_print_mode`.

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

For vakint, check and use these exact APIs for vacuum integral canonicalization,
tensor reduction, epsilon/pole extraction, and evaluation before writing Python
logic: `Vakint`, `Vakint.numerical_result_from_expression`,
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
