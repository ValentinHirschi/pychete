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

Prefer grouped targeted tests during implementation slices, and reserve the
full suite for larger green milestones:

```sh
dependencies/.venv/bin/python -m pytest -m definitions tests/unit/definitions
dependencies/.venv/bin/python -m pytest -m functional tests/unit/functional
dependencies/.venv/bin/python -m pytest -m loaders tests/unit/loaders tests/integration/models
dependencies/.venv/bin/python -m pytest -m models tests/integration/models
dependencies/.venv/bin/python -m pytest -m backend tests/unit/backends
dependencies/.venv/bin/python -m pytest -m matching tests/integration/matching
dependencies/.venv/bin/python -m pytest -m validation tests/integration/validation
dependencies/.venv/bin/python -m pytest -m typing tests/test_static_typing.py
dependencies/.venv/bin/python -m pytest -m "not slow" tests
```

When a slice touches the slow validation fixtures, batch related work first and
then run the validation group once. Do not pay for the full suite after every
small local fix; use focused tests while building the slice, then a broader
targeted gate, and only then a full-suite gate when the milestone is large
enough to justify it.

For one-shot matching work, first identify a coherent implementation chunk
(for example: one model-loader parity gap, one backend normalization family,
or one supertrace/integral-evaluation feature family), implement the whole
chunk, and only then run the smallest pytest marker group that exercises that
chunk. Prefer smoke scripts and one or two focused tests during exploration;
promote them into regression tests once the design has settled. Run the broad
`not slow` gate only before a green milestone commit, and run slow validation
only when the batch materially changes fixture validation behavior.
Before starting a slice, review the remaining one-loop frontier and choose a
larger feature family that can be completed coherently. Do not run the whole
suite repeatedly while redesigning internals; reserve broad validation for the
end of the slice after focused checks pass.

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
For computationally heavy matching stages, keep scalability in view before
settling on an implementation shape: avoid mandatory full-expression expansion
when a factored/native coefficient route is available, expose explicit controls
for expensive projection or simplification stages, and prefer algorithms whose
cost grows with the selected targets or backend operation rather than the full
SMEFT expression whenever practical.
For matching-condition extraction from large one-loop expressions, prefer
`matching_condition_expand_source=False` plus
`matching_condition_truncate_eft=True` when appropriate. This projects each
target coefficient first with native `Expression.coefficient(...)`, then
applies `series_eft(...)` to only `coefficient * target`, preserving total
EFT-order semantics without forcing global expansion of the full result.

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
Public bosonic CDE matching requests must replace only the selected
interaction-supertrace families by their CDE-expanded aggregate and must keep
all unselected interaction-power trace families in the one-loop source. Use the
`interaction_bosonic_cde_hybrid_*` setup methods for public `Theory.match(...)`
and validation-fixture preview paths. The lower-level
`interaction_bosonic_cde_*` methods intentionally remain pure selected-CDE
diagnostics for inspecting generated kernels, terms, and backend expressions.
Fermion free inverse recognition must keep Dirac structure separate from scalar
propagator topology data. Use Symbolica replacement rules to mark
`Gamma(index) * LoopMomentum(index)` or
`DiracProduct(Gamma(index)) * LoopMomentum(index)`, then native
`coefficient_list(...)` extraction to recognize linear `slash(q) +/- m`
kinetic entries. The propagator metadata should expose the scalar denominator
`PropagatorDenominator(LoopMomentumSquared, m^2)`, while
`free_inverse_entry(...)` subtracts the original Dirac kinetic expression from
interaction blocks. Do not replace fermion free inverses by scalar
`LoopMomentumSquared - m^2` expressions inside the interaction matrix.
When a fermion kinetic entry also contains field-dependent gamma-current
pieces, such as Abelian gauge-current terms from `free_lag(...)`, recognize the
registered free inverse from the field-independent slash/mass part using
Symbolica replacement rules over tagged fields. The current term must remain in
`interaction_entry(...)`; do not fold vector- or scalar-dependent gamma terms
into the fermion mass slot.
Fluctuation-basis discovery must treat registered `FieldStrength(label, ...)`
atoms as occurrences of the owning vector field. Use `field_strength_pattern`
with the field-label tag/data supplied by `Theory.symbol`; do not parse label
names or require an explicit `Field(label, ...)` atom in free gauge-field
terms.
Vector free-kinetic extraction must also treat canonical field-strength
quadratics and field-strength bilinears as vector inverse-propagator data. Use
Symbolica matching and `Expression.coefficient` on
`FieldStrength(label, ...)^2` and `FieldStrength(label_a, ...) *
FieldStrength(label_b, ...)` terms, then lower the result to
differential/momentum operators through the same fluctuation-operator path as
scalar and fermion fields. Massive vector `free_lag(...)` terms follow the
current scalarized component convention and must produce
`LoopMomentumSquared - M^2` denominator metadata. When kinetic interactions are
present, extract the registered free inverse from the field-independent part of
the momentum entry and leave field-dependent or off-diagonal kinetic terms in
the interaction operator.
Abelian gauge charges in `Theory.free_lag(...)` must be resolved from the
registered group symbol data (`GROUP_KIND`, `GROUP_ABELIAN`, `GROUP_COUPLING`,
and `GROUP_FIELD`) rather than parallel Python lookup tables. In the current
scalarized vector convention, complex scalar and fermion free Lagrangians build
one combined Abelian connection from all gauged U(1) charges before expanding
the kinetic/current term. Global U(1) charges remain metadata only, and
non-Abelian covariant terms must wait for the idenso/spenso-backed group
algebra path rather than ad hoc Python expansion.
Keep free-Lagrangian conventions explicit with `FreeLagConvention`. The
default `FreeLagConvention.PYCHETE` uses canonical gauge kinetic terms and
expanded scalarized Abelian currents. The Matchete loader must use
`FreeLagConvention.MATCHETE`, where covariant-derivative interactions remain
implicit in derivative slots and gauge kinetic terms carry Matchete's
`1/g^2` normalization. Do not make `.m` loading silently depend on pychete's
canonical free-Lagrangian convention.
When a Matchete-style expression with implicit Abelian covariant derivatives
must be expanded for matching, use `Theory.expand_abelian_covariant_derivatives`
or `OneLoopMatchOptions.expand_abelian_covariant_derivatives`. This path is
implemented with Symbolica replacement rules over registered first-derivative
`Field` atoms and Symbolica symbol data for Abelian gauge groups. Do not
duplicate the expansion by hand in loaders or matching code. Non-Abelian
covariant derivatives must remain delegated to the planned idenso/spenso-backed
group-algebra path rather than an ad hoc scalarized Python implementation.
For non-Abelian covariant-derivative work, use
`Theory.expand_non_abelian_covariant_derivatives(...)` or
`OneLoopMatchOptions.expand_non_abelian_covariant_derivatives` for the opt-in
first-derivative expansion. Construct individual generator insertions through
`Theory.non_abelian_gauge_generator_insertion(...)` so the gauge coupling,
vector field, adjoint index, dual representation slot, and registered
`CG(gen, ...)` tensor come from theory-owned Symbolica metadata in one place.
Do not duplicate the `g * V * CG(gen) * field` expression shape manually in new
code. After such expansion, simplify/contract the generated CG tensors through
the spenso/idenso-backed group-algebra path rather than Python-side tensor
logic.
Public pychete expressions should keep full `Index(label, representation)`
metadata on CG-tensor arguments. The spenso adapter is responsible for
extracting the abstract labels for native `TensorStructure.index(...)`; do not
strip index metadata earlier just to satisfy backend parsing.
For HEP-compatible built-in SU(N) CG tensors, route `gen`, `fStruct`, and
`del` through the spenso/idenso bridge instead of Python tensor logic.
Compatible `del` tensors lower to native spenso metrics, and the idenso bridge
must decode simple native metrics, generators, structure constants, and
native generator `spenso::chain(...)` products back to registered pychete
`CG(...)` atoms before public matching output is exposed. Multi-generator
chains should decode to ordered products of registered generator CG tensors
with generated theory-owned internal index labels; do not replace them with
handwritten SU(N) identities in Python. Do not let simple native `spenso::t`,
`spenso::f`, `spenso::g`, or decodable `spenso::chain` forms leak into
pychete-facing results when the originating theory group is unambiguous.
Before native vakint engine calls, lower pychete loop-momentum numerator heads
with `pychete.backends.vakint.lower_pychete_loop_momentum_numerators(...)`.
This maps `LoopMomentum(index)` to native `vakint::k(loop_id, index)` and
`LoopMomentumSquared` to native `vakint::k(loop_id, 1)^2`, matching the
vakint tensor-reduction API.
After native vakint tensor reduction or analytic evaluation, decode any public
expression with `pychete.backends.vakint.decode_pychete_namespace(...)` before
projection, simplification, or user-facing output. This must convert recognized
`vakint::g(...)` metric wrappers and registered `vakint::CG(...)` tensor
wrappers back to theory-owned pychete `Metric(...)` and `CG(...)` heads through
Symbolica replacement rules. It must also decode native `vakint::CD(...)`
wrappers into pychete `CD(...)` after nested vakint namespace heads in their
bodies have been decoded, so derivative normalization and projection see the
standard pychete derivative operator. Native backend constants such as
`vakint::𝑖`, `vakint::I`, `vakint::𝜋`, and `vakint::π` must decode to
Symbolica's `Expression.I` and `Expression.PI`; pychete-owned analytic
evaluators should use those native Symbolica constants directly. Do not let
native vakint tensor, derivative, or number-constant wrappers leak into
matching-condition projection or public EFT Lagrangians.
Vakint topology expressions must collect propagators with identical
edge/momentum/mass signatures into a single `vakint::prop(...)` with the summed
power. Use `pychete.backends.vakint.collect_identical_propagators(...)` rather
than relying on repeated duplicate prop factors. This applies to all integer
propagator powers, including powered prop factors and numerator-induced
negative massless powers. Internal analytic evaluators must normalize topologies
again before extracting mass/power data, so direct user-supplied `vakint::topo`
expressions and native vakint outputs follow the same convention. Before
pychete's internal analytic integral evaluation, convert remaining scalar
native vakint factors
`vakint::k(loop_id, index)^(2*n)` into negative powers of the massless
propagator with
`pychete.backends.vacuum_integrals.absorb_vakint_scalar_loop_momentum_numerators(...)`.
Metric and Kronecker-delta contractions involving pychete loop momenta must go
through the idenso adapter. Use `simplify_pychete_loop_momentum_metrics(...)`
or `simplify_index_algebra(..., metrics=True)` so expressions like
`Metric(mu, nu) * LoopMomentum(mu) * LoopMomentum(nu)` reduce to
`LoopMomentumSquared` before vacuum-integral evaluation.
Field-strength Lorentz antisymmetry and metric contractions must also stay in
the backend simplification path. Use
`pychete.backends.idenso.simplify_pychete_field_strength_metrics(...)` or the
public `simplify_index_algebra(..., metrics=True)` pipeline so
`Metric(mu, nu) * FieldStrength(label, {mu, nu}, ...)` vanishes and contracted
slots are rewritten before EFT truncation or matching-condition projection.
Do not paper over these tensor identities with Wilson-specific projection
special cases.

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

SMEFT Warsaw-basis Wilson coefficients with known pychete operator monomials
must be registered through `src/pychete/smeft.py` helpers such as
`define_smeft_wilson_coefficient`. Do not scatter ad hoc Wilson-to-operator
maps in converters, fixtures, or matching code; keep the central registry as
the source of truth. The default Matchete SMEFT validation fixtures expect the
full 64-name `SMEFTWilsonCoefficients[]` set from `SMEFT_Warsaw.m` to have
pychete-native operator metadata.

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
Generated fermion traces must not leave powers such as `NCM(...)^2` in symbolic
numerators. Before Dirac/idenso simplification and vakint lowering, use the
central idenso adapter path, which first applies
`pychete.backends.idenso.expand_pychete_ncm_powers(...)` to bounded positive
integer powers of `NCM` and then delegates compact Dirac/projector words to the
native idenso gamma simplifier. Do not try to reconstruct the ordering of
arbitrary products of distinct `NCM` factors after Symbolica has seen them as
commutative multiplication; only expand powers where the repeated
noncommutative order is unambiguous.
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
those components are needed. For compatible SU(N) fundamental/adjoint tensors,
pass `native_hep_cg_builtins=True` so pychete lowers `gen[SU(N)[fund]]` and
`fStruct[SU(N)]` to spenso's native HEP `TensorName.t()` and `TensorName.f()`
objects with `Representation.cof(N)` / `Representation.coad(N^2 - 1)` and
spenso's HEP tensor library. This applies to SMEFT-relevant `SU2L` as well as
`SU3c`; do not hard-code a colour-only SU(3) path when the registered group
metadata already identifies a compatible `SU(N)` representation.
Built-in Matchete CG labels such as `gen[group[rep]]`, `eps[group]`,
`fStruct[group]`, `dSym[group]`, and `del[group[rep]]` must resolve to the
auto-registered theory-owned CG tensor labels, not to generic external
functions.
For symbolic colour/group simplification of registered pychete CG tensors, use
`pychete.group_algebra.simplify_pychete_color(...)` or the low-level
`pychete.backends.idenso.simplify_pychete_color_algebra(...)`. This bridge must
lower only spenso-native HEP-compatible `gen` and `fStruct` tensors, delegate
the SU(N) algebra to idenso's native `simplify_color`, use native
`simplify_metrics` only on controlled pure-native metric inputs, and decode
simple native metrics and native generator chains back to registered pychete
`CG(...)` tensors.
Do not lower every registered CG tensor to a generic spenso tensor when calling
idenso; unrelated pychete `del`, `eps`, `dSym`, and model-specific CG tensors
must stay in pychete representation unless a backend-native simplification
explicitly handles them. Public one-loop matching can opt into this bridge with
`OneLoopMatchOptions.simplify_pychete_color_algebra=True`.
For public post-result CDE expressions containing generated pychete derivative
and Lorentz structures, do not run the global native colour simplifier over the
whole expression. Use `pychete.backends.idenso.decode_native_color_wrappers(...)`
to decode already-native `spenso::g`, `spenso::t`, `spenso::f`, and
`spenso::chain` wrappers back to pychete `CG(...)` atoms, and apply full native
colour simplification only to controlled colour-bearing kernels or isolated
subexpressions.

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
