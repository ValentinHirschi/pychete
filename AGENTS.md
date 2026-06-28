# pychete Agent Notes

## Non-Negotiable Sandbox Dispatch

This is the first shell-operating rule for this repository: never leave the
thread waiting on a sandbox approval prompt. The `exec_command` parameter
`sandbox_permissions: "require_escalated"` is banned for this repository. Do
not set it, do not request escalation, and do not ask the user for permission
through the tool approval path. The user has provided and started `listener.py`
specifically so sandbox-sensitive commands can be dispatched through the
`run.order`/`run.output` file protocol instead of blocking the one-shot matching
work.

Mechanical fail-closed guard before every shell tool call:

- The `sandbox_permissions` key must be absent from every `exec_command` call.
  Do not set it to `require_escalated`, and do not set it to `use_default`.
- Before sending a shell command, inspect the intended tool payload. If it
  contains `sandbox_permissions`, delete that key and re-plan the command.
- If the reason for adding `sandbox_permissions` would have been "this may need
  approval", do not run that command through escalation. Dispatch it through
  `listener.py` with `run.order`/`run.output` instead.
- Treat the current Codex approval policy as fail-closed: approval escalation is
  unavailable, so any payload containing `sandbox_permissions` is an invalid
  command plan for this repository.

Use this rule before every command that may touch sandbox-sensitive state:

- Ordinary read-only inspection commands and focused tests may run directly.
- Any command that is likely to write `.git` metadata or otherwise hit the
  known restricted-filesystem boundary must go through `listener.py` first.
  This includes `git commit`, `git rebase`, `git merge`, lock cleanup,
  repository maintenance, and any retry after `Operation not permitted`.
- Do not request or wait for a user approval prompt for these repository
  commands. Never retry them with `sandbox_permissions: "require_escalated"`.
  If a direct command unexpectedly fails with `Operation not permitted` or a
  read-only `.git` error, immediately queue the same command through
  `run.order` and inspect `run.output`.
- Queue one command at a time:

```sh
printf 'git commit -F /tmp/commit-message\n' > run.order
sleep 1
tail -200 run.output
```

The listener is only a sandbox-dispatch mechanism. Long or memory-sensitive
tests, matching previews, CDE/vakint probes, and validation fixtures must still
run through `scripts/run_with_memory_watch.py --limit-gb 30`.

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
When a first one-loop Wilson coefficient starts matching, add partial
integration coverage for the smallest meaningful operator subset rather than
jumping straight to all registered SMEFT conditions. Good regression surfaces
are selected trace families, selected Wilson coefficient names, selected
projection stages, and a few related operators sharing one generated source,
such as the Singlet `cHW/cHB/cHWB` Higgs-gauge subset. These tests should make
future mismatches cheap to reproduce and should identify whether a regression
belongs to source generation, backend evaluation, on-shell reduction, or
matching-condition projection.

Always use the managed virtual environment for pychete development and tests.
Do not use the ambient system Python when importing Symbolica, idenso, spenso,
or vakint.

Before running Python commands that import Symbolica, source `~/.bashrc` so the
local `SYMBOLICA_LICENSE` export is available:

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python -m pytest tests
```

Run tests or exploratory matching workloads that could grow large through the
project memory wrapper with a 30 GiB cap:

```sh
source "$HOME/.bashrc"
dependencies/.venv/bin/python scripts/run_with_memory_watch.py --limit-gb 30 -- \
  dependencies/.venv/bin/python -m pytest tests/integration/matching
```

Use this wrapper for broad pytest groups, slow validation fixtures, CDE/vakint
matching smokes, and any workload that might approach machine RAM limits.
The wrapper also polls `stop.order` in the current working directory by
default. For long exploratory commands, prefer this file-based stop mechanism
over process-management commands that may require sandbox approval: remove any
stale `stop.order` before launching the workload, and create/touch
`stop.order` to ask the wrapper to terminate the wrapped process group.

## Sandbox And Listener Workflow

Do not let work stall on sandbox approval prompts. The expected workflow is:

1. Run ordinary read-only shell commands and ordinary tests directly.
2. For commands that may touch `.git` metadata or another known
   restricted-filesystem boundary, use the user-started `listener.py` route
   immediately. If any other necessary direct command fails with
   `Operation not permitted`, a sandbox write restriction, or the known
   read-only `.git` metadata failure, retry it through the listener rather
   than stalling on an approval prompt.
3. Queue exactly one command by writing it to `run.order`, then read
   `run.output` for its exit code and output. The listener clears `run.order`
   itself and appends history to `run.log`.

Typical listener usage:

```sh
printf 'git commit -F /tmp/commit-message\n' > run.order
sleep 1
tail -200 run.output
```

Use the listener for any `.git` metadata writes that fail in the sandbox,
including `git commit`, `git rebase`, `git merge`, lock cleanup, and similarly
blocked repository-maintenance commands. For long or memory-sensitive
Python/test/matching workloads, still use
`scripts/run_with_memory_watch.py --limit-gb 30`; the listener is a
sandbox-dispatch fallback, not a replacement for the memory watchdog.

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
For Matchete-parity validation, keep loop-convention symbols theory-owned.
When using `OneLoopNormalization.MATCHETE_HBAR` against converted Matchete
fixtures, pass `OneLoopMatchOptions.hbar` as the registered external `hbar`
symbol, or let `ValidationFixture.one_loop_preview_gap_report(...)` resolve it
from the active theory. Do not compare converted Matchete conditions containing
`external_hbar` against package-level `s.HBar` without an explicit convention
choice. Use `OneLoopNormalization.MATCHETE_HBAR` for raw, unevaluated vakint
supertrace expressions. Use `OneLoopNormalization.MATCHETE_EVALUATED_HBAR` for
evaluated internal/vakint finite expressions that already contain the explicit
`i/(16*pi^2)` factor; this applies the central
`+16*pi^2*i*hbar` conversion to Matchete's external `hbar` loop-counting
convention. The sign is fixed by Matchete's scalar/vector power-type
supertrace prefactor `-I hbar/2` together with pychete's evaluated-backend
integral convention, where the scalar integral has already supplied the loop
`+I/(16*pi^2)` factor. Do not reintroduce the old negative evaluated-hbar
bridge sign, and do not repair this convention later with Wilson-specific
projection replacements.
Before calling native `Expression.coefficient(...)` on large composite
matching targets, prefilter candidate source terms with Symbolica pattern
matches over registered field and field-strength labels. The filter must be
conservative: keep all terms whose field/field-strength label content can
match one additive target term, reject terms with extra dynamical labels, and
then delegate the actual coefficient extraction to Symbolica. Do not replace
this with string filtering or a Python symbolic matcher. Cache the source term
tuple and each term's field/field-strength label counts inside the projection
extractor, because many Wilson targets filter the same source. Do not expand
the filtered source subset just to hand it to native coefficient extraction;
let the subsequent `Expression.coefficient(...)`, `collect_factors(...)`, and
`factor(...)` fallbacks do the symbolic work on the smaller selected source.
Do not call native `Expression.collect_factors()` or `Expression.factor()` on
large filtered projection sources: even Rust-backed global collection and
factorization can dominate matching-condition projection. Gate these fallbacks
with Symbolica's native expression size information, such as `len(expr)` and
`Expression.get_byte_size()`, and fall through to the indexed wildcard
projection path when the filtered source is too large. This is a performance
guard around native fallbacks, not an excuse to add Python-side algebra. A
similarly guarded target-local `Expression.expand()` fallback is allowed only
after native coefficient, collect, and factor routes fail; its purpose is to
expose small hidden additive factors introduced by replacement-rule outputs
such as order-by-order heavy scalar solutions while preserving
`matching_condition_expand_source=False` for the full matching source.
After a target-local tensor-canonicalized projection source is built, use
separate term/byte guards for bounded termwise exact projection and generic
full-source projection. A bounded termwise pass may run before the stricter
generic fallback guard because it only applies native coefficient extraction
term by term; this is needed for registered Wilson targets whose projection
aliases broaden the canonicalization family, such as post-EOM scalar
commutator-bilinear `cHD` terms. If raw exact projection, powered-index
wildcard projection, target-local tensor canonicalization, and the bounded
termwise exact pass do not expose a match, return zero for that oversized
target-local source rather than letting one Wilson condition trigger
unbounded native collection or coefficient extraction. This is a temporary
performance frontier marker, not a claim that the missing Wilson coefficient
has been physically shown to vanish.
For simple registered `Coupling(label, indices, order)` matching targets, also
prefilter source terms with a native Symbolica `Coupling(label, _, _)` pattern
before coefficient extraction. This is a conservative label-presence filter:
it must not try to infer polynomial powers or coupling algebra in Python, and
the final coefficient must still come from Symbolica's
`Expression.coefficient(...)`/collect/factor path.
Registered Wilson-coefficient projection targets with stored operator metadata
are allowed to use target-local integration-by-parts projection aliases
automatically, because the stored operator is already a basis-level projection
instruction. Raw expression targets must remain exact unless
`normalize_ibp_scalar_bilinears=True` is requested. When aliases are present,
first try native exact `Expression.coefficient(...)` extraction with wildcard
index fallback disabled. This exact fast path may skip tensor canonicalization
only when `coefficient * target` exhausts the conservatively filtered
target-local source; otherwise it would drop alpha-equivalent dummy-index
terms. If exact extraction does not exhaust that source, canonicalize only the
filtered target-local source, target, and alias expressions together through
one shared Symbolica `Expression.canonize_tensors(...)` index-spec path before
any wildcard-index fallback. Do not canonicalize the full matching source just
to handle one target or target-local alias family.
For target-local coefficient extraction, drop derivative-slot branches that
cannot match the projection target before expensive extraction fallbacks. Use
Symbolica pattern replacements over registered `Field(...)`,
`Bar(Field(...))`, `FieldStrength(...)`, and `Bar(FieldStrength(...))` atoms to
replace source atoms whose derivative-slot signature is absent from the target
by zero. This is essential after order-by-order heavy-scalar substitution:
irrelevant derivative branches can otherwise remain hidden inside additive
solution factors and block projection of non-derivative Wilson targets such as
`cH`. Keep this target-local and label-scoped; do not globally delete
derivative operators from the matching source.
When truncating registered Wilson-coefficient projections, enforce coefficient
canonical mass dimension only from explicit coupling symbol data. Store known
coupling dimensions through `Theory.define_coupling(..., mass_dimension=...)`
and `SymbolDataKey.DIMENSION`; heavy/light field mass couplings have dimension
one and gauge/Yukawa/quartic couplings should be explicitly dimensionless when
known. Use Symbolica tag-restricted coupling matches and
`Expression.to_rational_polynomial(...)` to read numerator and denominator
powers, so inverse heavy-mass powers are handled natively and masses inside
non-rational functions such as logarithms are not counted as polynomial
powers. If any coupling dimension in a coefficient term is unknown, retain the
term rather than guessing. Do not implement Wilson coefficient dimension cuts
by string parsing, ad hoc scans of `M` names, or Python-side assumptions about
which couplings are masses.
For Matchete-derived model-state conversion, infer missing coupling
mass-dimension metadata with `infer_coupling_mass_dimensions(theory,
lagrangian)` in a temporary probe theory before constructing the final theory
that will be serialized. This keeps the final `Theory.define_coupling(...)`
calls structurally safe: Symbolica symbol data is fixed at symbol creation
time, so converters must not parse lagrangians with dimensionless placeholders
and then try to mutate coupling symbol metadata afterwards.
For any equality/projection question where only dummy-index names differ, use
`Expression.canonize_tensors(...)` with grouped pychete `Index(...)` specs and
the returned canonical expression, external-index list, and dummy-index list.
Treat that returned payload as the authoritative index-replacement map for
aligning dummy indices; do not infer the same map by rescanning strings or
expression trees. Do not compare raw canonical strings before this
normalization, and do not write a Python dummy-index canonicalizer when
Symbolica can provide the canonical replacements. Public comparison diagnostics
such as `MatchingExpressionComparison` should keep these returned payloads
attached when they used tensor-index canonicalization, so debugging and
notebook output can show which native canonical dummy labels were compared.

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
Do not treat the covariant-derivative expansion (CDE) implementation as the
forward core architecture for one-loop matching. Matchete used CDE in its early
v0.1/paper route, but the current Matchete direction uses explicit Wilson-line
trace handling because it generalizes better to higher loops. pychete's CDE
code may remain as an opt-in legacy diagnostic, validation, and regression
route, but new core matching work should move toward explicit Wilson-line
style functional traces and should not deepen SMEFT-specific or CDE-specific
coupling in the main pipeline.
This is direct feedback from the Matchete authors, not only a local preference:
do not spend new implementation slices trying to complete one-loop parity by
making the legacy CDE path more central. If a planned task can be expressed
through either CDE or explicit Wilson-line traces, choose the Wilson-line route
and leave CDE as a comparison/diagnostic route unless the task is explicitly
about preserving old CDE behavior.
When Matchete parity is the objective, treat CDE agreement as a legacy
cross-check only. Do not add new CDE-first planners, public controls, or
projection shortcuts unless they are explicitly preserving old behavior. New
one-loop implementation slices should instead extend the explicit Wilson-line
path, including fermion-loop closure, Wilson-term expansion, index/gamma/group
algebra, tensor reduction, integral evaluation, and matching-condition
projection from the Wilson-line representation.
Whenever a precise Matchete-parity mismatch is identified, first review the
corresponding Matchete Mathematica algorithm and the relevant pychete algorithm
side by side before patching pychete. Use intermediate-stage dumps and focused
probes to locate the first semantic difference. Do not infer the fix only from
the final Wilson coefficient, and do not add model- or Warsaw-specific
coefficient patches when the mismatch belongs to a generic stage such as
Wilson-line expansion, Green-basis reduction, EOM simplification, tensor
reduction, or projection.
For every sustained Matchete/pychete disagreement, actively generate and
inspect focused Matchete intermediate data with debug WolframScripts whenever
Mathematica is available. Dump as many relevant Matchete stages as practical
for the narrowed trace, insertion, propagation order, target, or simplification
stage: raw `EvaluateSTr`, insertion replacements, `ActWithOpenCDs`,
`GatherLoopMomenta`, `WilsonExpand`, loop integration,
`ContractCGs // MatchReduce // GreensSimplify`, `EOMSimplify`, and saved
matching-condition projections as applicable. Pair those dumps with bounded
pychete probes at the same semantic boundaries, then patch the first differing
generic algorithm. Keep useful dump scripts under `helper_mathematica_scripts/`
and commit Mathematica-independent JSON/pychete fixtures when they become
regression evidence. Runtime pychete and pytest must remain Mathematica
independent.
This Matchete-side dissection is the default parity workflow, not a last
resort. During active one-shot matching work, keep running or refreshing
focused debug WolframScripts often enough that any mismatch is compared against
a current Matchete stage dump for the same trace, target, propagation order,
and simplification boundary before changing pychete. If Mathematica is
unavailable, record that limitation in the implementation notes and continue
with the closest committed Matchete-derived fixtures.
Make this a regular cadence during mismatch work, not an occasional audit:
after each nontrivial pychete/Matchete disagreement, dump the narrowest
Matchete stages available, inspect them side by side with bounded pychete
probes, and keep adding intermediate checkpoints until the first divergence is
localized. The implementation notes should explicitly say which WolframScript
dump was refreshed, which pychete probe was compared, and what the next generic
Matchete algorithm boundary is.
For the active one-loop frontier, treat debug WolframScript runs and Matchete
intermediate dissection as routine engineering work, not exceptional
diagnostics. When pychete and Matchete disagree, refresh the narrowest relevant
Matchete dump first, compare it with a bounded pychete probe, and only then
patch the generic pychete algorithm that first diverges from Matchete's stage
semantics.
When reporting progress on a mismatch, state which Matchete dump/checkpoint
and which bounded pychete probe were compared. A statement that a coefficient
"does not match" is not actionable enough for this port unless it is tied to a
specific stage boundary such as source generation, Wilson expansion, loop
integration, Green-basis simplification, EOM reduction, or projection.
For every continuation or status update during mismatch work, explicitly
confirm the paired-debug workflow in concrete terms: name the current Matchete
WolframScript/fixture checkpoint, name the bounded pychete probe or fixture
being compared to it, and state the stage boundary currently under suspicion.
If no fresh WolframScript run was possible, say which committed Matchete dump is
being used instead and record that limitation in the implementation notes.
Do this repeatedly while the mismatch is active: run or refresh focused
debug WolframScripts as often as needed, dissect Matchete's intermediate
objects stage by stage, and keep comparing them against bounded pychete probes
until the first semantic divergence is narrow. This confirmation is a working
requirement, not a one-time note.
Treat this as a hard acceptance gate for mismatch-driven runtime patches:
there must be an explicit, current Matchete intermediate dump or committed
Matchete-derived fixture, a bounded pychete probe at the same semantic stage,
and a recorded first-differing boundary before the patch is considered ready.
Keep running or refreshing focused debug WolframScripts during mismatch work
until that boundary is narrow enough to justify a generic port of Matchete's
algorithm.
Every mismatch-fix note should explicitly name the Matchete dump or
WolframScript checkpoint used, the corresponding bounded pychete probe, and the
first generic algorithm boundary where they differ. This keeps the port aligned
with Matchete's algorithms while still implementing them through Symbolica,
idenso, spenso, and vakint rather than final-coefficient patching.
Before accepting any pychete patch motivated by a Matchete disagreement,
complete this mismatch checklist in the implementation notes: identify the
Matchete debug script or committed fixture used, identify the matching bounded
pychete probe or pytest fixture, state the first stage boundary where the two
objects differ, and explain why the patch ports a generic Matchete algorithm
rather than repairing a single coefficient. If the checklist cannot yet be
completed, add more Matchete-side dumps or finer pychete probes before changing
runtime code.
Treat the repeated debug-WolframScript workflow as an active obligation during
all mismatch work. If a pychete result disagrees with Matchete, assume the next
engineering step is to dump more Matchete intermediate state, not to guess from
the final coefficient. Run or refresh focused WolframScripts often, dissect
Matchete's stage objects, and compare them with bounded pychete probes until
the first divergence is localized. Status updates and implementation notes
must explicitly name the Matchete dump/checkpoint, the pychete probe, and the
suspected stage boundary so the port keeps following Matchete's algorithms,
implemented through Symbolica/idenso/spenso/vakint, rather than drifting into
coefficient-specific fixes.
For the current Singlet `cHD` frontier and later one-loop frontiers, assume the
first useful debugging artifact is a Matchete-side intermediate dump, not
another final-coefficient probe. When a pychete coefficient disagrees with
Matchete, run or refresh focused WolframScript dumps as often as practical and
dissect the Matchete stages until there are enough checkpoints to compare
against pychete: insertion metadata, Xterm replacements, open-derivative
action, Wilson expansion, tensor/integral stages, Green simplification,
EOM/field redefinition, and final projection. Only after the first stage
boundary is identified should runtime pychete code be changed, and the change
must be a generic Symbolica/idenso/spenso/vakint port of that Matchete
algorithm.
For selected Wilson-line trace disagreements, decompose the comparison by
Matchete propagation order and pychete Wilson-line total order before touching
projection code. The Singlet `hScalar-lScalar-lVector-lScalar -> cHD` frontier
showed why this is mandatory: Matchete's saved selected trace is the sum of
propagation orders 0, 1, and 2, and the first two runtime fixes came from
stage-local comparisons against
`debug_singlet_wilson_trace.wls` prop-order dumps, not from the final
coefficient. The generic rules found there are now part of the port:
loop-symmetry pruning must count explicit `LoopMomentum(...)` factors and
uncontracted `DifferentialOperator(...)` slots term-by-term, and closed
Lorentz metric traces from tensor reduction must be contracted as
`d = 4 - 2*epsilon` before finite Laurent extraction so epsilon-suppressed
trace pieces multiply loop poles correctly.
For the active Singlet `cHD` EOM/on-shell frontier, keep
`helper_mathematica_scripts/debug_singlet_eom_simplify.wls` and its committed
JSON fixture current as the Matchete `EOMSimplify`/`FieldRedef.m`
checkpoint. That dump should record the real package-scope Matchete stages,
including `FieldsToShift`, the prepared EOM-term list, field-specific
`ScalarShift`/`FermionShift`/`VectorShift` data when relevant, and the saved
off-shell/on-shell projection delta. When extending this or similar
WolframScript dumps, qualify Matchete package-scope heads such as
``Matchete`PackageScope`EoM``, ``Matchete`PackageScope`Operator``,
``Matchete`PackageScope`TermsToList``,
``Matchete`PackageScope`InternalSimplify``, and
``Matchete`PackageScope`$FieldAssociation``; otherwise the script may create
inert lookalike symbols and report misleading checkpoints. Pair each refreshed
Matchete EOM dump with a bounded pychete probe of the corresponding
source/EOM/field-redefinition boundary before changing runtime code.
The current narrowed Singlet `cHD` EOM boundary is the internal-simplified
source replay through Matchete `PerformSystematicFieldRedefs`: matter
renormalization and shifts through `after_shift_dim6_dev4` leave the `cHD`
projection unchanged, while `after_shift_dim6_dev3` produces the full
off-shell-to-on-shell delta. Treat this as evidence that the next runtime
implementation should port generic scalar/matter `DetermineShifts`,
`ScalarShift`, and source-scoped `ShiftLagrangian` behavior before adding any
coefficient-specific alias.
Use `scalar_eom_field_redefinition_delta(...)` /
`Theory.scalar_eom_field_redefinition_delta(...)` as the bounded pychete
consumer for explicit formal scalar `EOM(Field(...))` and
`EOM(Bar(Field(...)))` terms. That helper intentionally assumes a prior
Green/InternalSimplify-style exposure stage has already produced formal EOM
atoms; do not pretend it handles arbitrary derivative sources by itself.
The first bounded exposure stage is `scalar_eom_identities(...)` plus
`scalar_derivative_green_normal_form(..., include_eom=True,
eom_lagrangian=...)`, optionally routed through
`OneLoopMatchOptions.wilson_line_expose_scalar_eom_terms`. It discovers scalar
Laplacian atoms with Symbolica patterns, extracts coefficients with native
`Expression.coefficient(...)`, and exposes formal EOM atoms for the subsequent
field-redefinition consumer. Keep validating this against the Matchete
`debug_singlet_eom_simplify.wls` / `singlet_eom_cHD.debug.json` checkpoints
before using it as evidence for full Singlet `cHD` on-shell parity.
Use `expose_abelian_vector_eom_currents(...)` /
`Theory.expose_abelian_vector_eom_currents(...)` only as a bounded exact
source-side bridge for Abelian vector-EOM current-current products. It
discovers charged scalar first-derivative currents with Symbolica patterns and
then uses direct `Expression.coefficient(...)` plus the shared Symbolica-backed
projection extractor for expanded composite factors. The current Singlet
`cHD` pychete probe showed zero exposed vector-EOM divergences from this exact
bridge, so do not treat it as the missing `InternalSimplify`/field-redefinition
solution for that frontier; the remaining port must cover broader
Green-representative conversion and scalar/matter shift preparation.
Latest user reinforcement, 2026-06-28: when a Matchete/pychete mismatch is
active, repeatedly run or refresh focused debug WolframScripts, dump as many
Matchete intermediate stages as practical, and compare them against bounded
pychete probes until the first semantic divergence is located. Confirm this
paired-debug cadence in progress notes; do not move from a final coefficient
mismatch directly to a runtime patch.
Latest explicit confirmation, 2026-06-28: during active mismatch work the
expected working loop is to run focused Matchete WolframScripts often, dissect
their intermediate objects, and compare those objects against bounded pychete
probes at the same stage before changing runtime code. Keep naming the exact
Matchete script or committed dump, the paired pychete probe, and the suspected
algorithm boundary in status updates and implementation notes so the port
closely follows Matchete's algorithms while translating them to
Symbolica/idenso/spenso/vakint.
Represent current-Matchete-style Wilson-line trace work through
`WilsonLineTracePath`, `WilsonLineTraceExpansionTerm`, `s.WilsonLine`, and
`s.WilsonTerm`. Build these objects from the ordered entry paths returned by
`_supertrace_block_entry_paths(...)`, before `SupertraceBlockTrace.expression`
has summed over the matrix-trace entries and lost the individual
propagator/insertion ordering. The propagator mass slots follow the Matchete
`GenericPropagatorExpansion` convention: after each interaction insertion,
record the next fluctuation mode, and close the path by a Wilson line for the
final mode back to the initial mode. Do not bolt a Wilson-line placeholder onto
an already summed trace and call it equivalent. Public diagnostics that expose
the current Matchete route should use
`WilsonLineTracePath.propagator_expansion_terms(...)` and
`OneLoopSetup.interaction_wilson_line_expansion_*` rather than adding new
CDE-named public surfaces. Reusing the tested bosonic covariant propagator
expansion primitive internally is allowed, but that primitive is an
implementation detail, not the conceptual architecture.
Wilson-line propagator expansion must respect the fluctuation statistics of
each propagator slot. Bosonic slots use the `PropBosonExpand`-style
`bosonic_covariant_propagator_expansion_terms(...)`; fermionic slots use
`fermionic_covariant_propagator_expansion_terms(...)`, mirroring Matchete's
`PropFermionExpand` as `(slash(k)+M) Helper[n] + i gamma(mu) OpenCD(mu)
Helper[n-1]`. Generated slash/open-derivative Lorentz labels must be
theory-owned pychete `Index(...)` expressions, and compact gamma/projector
cleanup must remain delegated to idenso after Wilson-term expansion. Do not
use the bosonic expansion for fermion Wilson-line slots.
Within the non-fermion branch, vector propagator slots must carry Matchete's
extra `PropExpand[Vector] = -PropBosonExpand[...]` sign. Detect this from
`FluctuationMode.field_type`/registered field metadata, never from trace names
such as `hVector`, and keep the sign on the covariant propagator term
prefactor so downstream Wilson-line termwise vakint/internal evaluation sees
the same topology and numerator structure as scalar slots.
Public one-loop matching can opt into the same selected-trace route with
`OneLoopMatchOptions.wilson_line_expansion_indices_by_trace`,
`wilson_line_act_open_derivatives`, and
`wilson_line_max_derivative_order`. For generated derivative-order plans, use
the Wilson-line-native `wilson_line_trace_names`,
`wilson_line_max_total_order`, `wilson_line_max_slot_order`, and
`wilson_line_index_prefix` controls, or
`OneLoopSetup.interaction_wilson_line_expansion_plan(...)`. Do not reach for
`bosonic_cde_max_total_order` just because it is convenient. These options are
intentionally separate from `bosonic_cde_*`; requesting both CDE and
Wilson-line expansion in one match is an API error until an explicit comparison
policy is designed. The public
`Theory.match(...)` Wilson-line route must be hybrid by default: selected trace
families are replaced by their Wilson-line-expanded aggregate while all
unselected interaction-power traces remain in the source. Keep pure selected
Wilson-line result methods available for diagnostics, not as the default public
matching route.
Validation-facing one-loop preview and gap-report helpers must expose the same
`wilson_line_*` controls as `Theory.match(...)`, including generated
Wilson-line plans and target-local Wilson-line term filtering for direct
fixture previews. New Matchete parity probes should prefer these Wilson-line
controls over legacy `bosonic_cde_*` controls unless the purpose of the test is
explicitly to preserve or compare the old CDE route.
For target-local Wilson-line parity probes, use
`wilson_line_filter_terms_by_matching_targets=True` together with projected
matching-condition targets. This conservative label-level filter may drop
Wilson-line expansion terms whose numerators cannot contain any requested
field/field-strength target before tensor reduction/evaluation, but final
coefficient extraction must still be delegated to the ordinary Symbolica
projection path. Do not add CDE-only filtering or SMEFT-name-specific filtering
for new frontier checks.
For field-strength projection targets such as `cHW`, the Wilson-line filter
must remain conservative with respect to Matchete's later reduction stages:
raw Matchete `EvaluateSTr` output can be derivative-only, with explicit
`FieldStrength(...)` atoms appearing only after `ContractCGs`, `MatchReduce`,
and `GreensSimplify`. Therefore do not require explicit field-strength atoms
inside generated Wilson-line numerators when charged fields and enough
derivative order can generate the requested field strengths through
covariant-derivative commutators.
Future `WilsonTerm` expansion must use Symbolica replacement rules/patterns
and the idenso/spenso algebra path for field-strength, colour, and tensor
simplification; do not implement it as a Python tree walker. Open covariant
derivatives acting on a closing `WilsonTerm(...)` must append to its derivative
slot through `apply_cd`/Symbolica replacement rules before
`expand_wilson_terms(...)` lowers the supported cases.
Use `expand_wilson_terms(theory, expr)` as the public Wilson-line expansion
boundary. Its first supported cases are the coincidence-limit identity
transporter, the vanishing one-derivative term, and the two-derivative
field-strength term for scalar/fermion representations, plus
Matchete-style derivative-sublist partitions up to the requested
`max_derivative_order` (default four). Before derivative-sublist expansion,
keep the current Matchete cleanup stage that drops symmetry-vanishing Wilson terms:
call `remove_symmetry_vanishing_wilson_terms(...)` or rely on
`expand_wilson_terms(...)` doing so before lowering supported `WilsonTerm`
atoms. This stage must use Symbolica pattern matches over
`SymmetricLorentzInds(...)` markers and `WilsonTerm(...)` atoms; do not expand
or inspect the full expression tree manually just to find these cases. A
Wilson term vanishes if its two derivative indices are equal, or if its
derivative-index list contains a symmetric Lorentz-index group generated by
loop integration.
When the Wilson-line path still delegates tensor reduction to vakint, use
`remove_loop_momentum_symmetry_vanishing_wilson_terms(...)` with the explicit
loop-momentum index metadata from the generated propagator-expansion terms.
That helper first drops odd-rank loop-momentum terms, matching Matchete's
`LoopMoms[...]` symmetry rule before Wilson expansion. For even nonzero rank it
temporarily annotates the term with `SymmetricLorentzInds(...)`, applies the
Wilson-term vanishing rule, then strips the marker so public numerators keep
their original `LoopMomentum(...)` factors for backend tensor reduction. Do not
replace those loop momenta by a Python angular-average formula in this path.
Derivative-sublist expansion should keep
using Symbolica replacement callbacks over `WilsonTerm(...)` and theory-owned
gauge metadata; Python may enumerate derivative-index partitions, but it must
not inspect expression trees to do group algebra. Matchete-style Wilson-line
field strengths are coupling-free at this boundary: do not multiply generated
`FieldStrength(...)` insertions by explicit gauge couplings during
`WilsonTerm(...)` lowering or generated CDE/Wilson-line commutator lowering.
Warsaw/operator targets and matching-condition normalizations carry their own
gauge-coupling factors separately. Non-Abelian vector
`WilsonTerm` expansion has bounded support through the vector field's implicit
adjoint gauge transporter and the Lorentz endpoint metric; Abelian vector
derivative terms with no gauge charge lower to zero. `WilsonTerm` atoms above
the requested derivative order must remain formal until their combinatoric
coverage is explicitly requested and tested.
Generated Wilson-line numerators must normalize pychete noncommutative chains
before backend simplification. Use `normalize_ncm_chains(...)` to flatten
nested `NCM(...)` operands and hoist only commutative scalar coefficients, then
delegate compact projector/gamma words to
`idenso.simplify_pychete_dirac_algebra(...)` before scalarizing commutative
chains. This mirrors Matchete's `NCM`/`DiracProduct` cleanup while keeping the
actual gamma algebra in the native backend; do not leave generated
Wilson-line terms with `NCM(..., NCM(...), ...)` nesting that blocks idenso.
Before applying open covariant derivatives, Wilson-line symmetry pruning, or
target-local filtering to generated `NCM(...)` chains, linearize additive
operands with `distribute_ncm_additions(...)`. Matchete's noncommutative
products are effectively processed termwise in these stages; pychete's custom
`NCM` head is not native multiplication, so `NCM(A + B, OpenCD(mu), X)` must
be represented as the sum of separate ordered chains before pruning/filtering.
Keep this as bounded Symbolica replacement-rule orchestration and do not
replace it with a global Python expression walker.
When `OneLoopMatchOptions.simplify_pychete_color_algebra` is enabled, generated
Wilson-line numerators must also pass through
`idenso.simplify_pychete_color_algebra(...)` after supported `WilsonTerm`
expansion and Dirac/NCM postprocessing. Setup-level colour simplification runs
before generated Wilson-line terms exist, so it is not sufficient for
Wilson-line-generated CG structures. Keep this as explicit option plumbing into
`WilsonLineTracePath.propagator_expansion_terms(...)`; do not silently simplify
raw Wilson-line diagnostics by default.
For explicit Wilson-line traces, open covariant derivatives act only on factors
to their right in the ordered chain ending with the closing `WilsonTerm(...)`.
Do not use the cyclic closed-chain wrapping mode from the legacy CDE path in
`WilsonLineTracePath.propagator_expansion_terms(...)`; wrapping derivatives
back onto earlier insertions creates non-Matchete Wilson-line source terms.
Generated Wilson-line postprocessing must also simplify pychete loop-momentum
metric contractions and field-strength metric/antisymmetry relations through
the idenso adapter before vakint/internal integral evaluation. Closed Dirac
traces can introduce `Metric(mu,nu)` factors that must contract with
`LoopMomentum(mu) LoopMomentum(nu)` to `LoopMomentumSquared`; do not leave
those contractions for a Python-side vacuum-integral parser or projection-time
special cases.
The remaining Singlet `cHW` frontier is not solved by target filtering,
post-result heavy-scalar substitution, or additive `NCM` linearization alone.
Pure `A^2` `hScalar-lScalar` Wilson-line terms reach the pre-commutator stage
as loop-momentum tensors multiplying four covariant derivatives on a charged
Higgs. The missing Matchete-parity step is loop-symmetric multi-commutator
lowering tied to tensor-reduced/symmetric loop-momentum structures, capable of
producing two field strengths from those four derivatives. Implement that as a
native Symbolica/idenso/vakint-backed stage, using Matchete's
`EvaluateSymmetricLorentzInds`/`CommuteCDs` behavior as reference; do not
paper over it with SMEFT-specific `cHW` replacements or coefficient patches.
For local covariant-derivative commutator emission, use
`Theory.emit_covariant_derivative_commutators(..., mode="inversions")` for the
stable canonical-order rewrite and
`Theory.emit_covariant_derivative_commutators(..., mode="all_distinct")` only
for the bounded Matchete `CommuteCDs` adjacent-pair identity. The
`all_distinct` mode intentionally supports one pass only; do not run it in a
repeat-to-fixed-point loop, because adjacent derivative swaps would otherwise
commute the same pair back and grow the expression. Public Wilson-line parity
probes should select it through
`OneLoopMatchOptions.wilson_line_covariant_derivative_commutator_mode`.
When reproducing Matchete `IdentitiesCDCommutation` or building future
Green-basis row reduction, use
`Theory.covariant_derivative_commutator_identities(expr)` rather than treating
`emit_covariant_derivative_commutators(..., mode="all_distinct")` as a complete
identity source. The emitter rewrites one eligible adjacent pair per atom and
is an equality-preserving expression transform; Matchete's simplifier
generates a separate identity for every adjacent distinct derivative pair on
each differentiated field/field-strength atom. The identity helper mirrors
that source with Symbolica pattern discovery and native coefficient
extraction, while deliberately skipping nonlinear repeated atom occurrences
until a full operator-class row-reduction representation owns that case.
For bounded Green-basis normal-form experiments, use
`linear_identity_normal_form(...)` or
`Theory.covariant_derivative_commutator_normal_form(...)` when the local basis
is explicit. Use `linear_identity_basis_terms(...)`,
`linear_identity_normal_form_from_identities(...)`, or
`Theory.covariant_derivative_commutator_local_normal_form(...)` when the local
basis should be collected from the source plus generated identities. These
helpers encode operator-basis monomials as temporary Symbolica variables and
delegate the linear solve to Symbolica's native
`Expression.solve_linear_system(...)`; do not implement row reduction or
Gaussian elimination in Python. The automatic collector only separates local
operator factors from scalar coefficients in a bounded expression/identity
neighborhood. Preferred representatives remain explicit by design: do not
guess Matchete's full operator-class scoring from strings or ad hoc global
expression walks.
For scalar derivative Green-basis work, use
`scalar_derivative_ibp_identities(...)` as the local scalar
`IdentitiesIBP` source and `scalar_derivative_green_normal_form(...)` as the
combined bounded IBP/commutator normal-form boundary. These helpers discover
tagged scalar field atoms with Symbolica patterns, extract coefficients with
native `Expression.coefficient(...)`, close the local identity neighborhood
under explicit bounds, and delegate row reduction to the Green-basis Symbolica
solver. Do not add more target-specific scalar IBP projection aliases until
this generic source-side normal form has been checked against the relevant
Matchete operator class.
When no explicit scalar Green-basis preferred representatives are supplied,
`scalar_derivative_green_normal_form(...)` applies only the scalar-relevant
pieces of Matchete's `OpScore`: prefer field-strength-like representatives,
penalize explicit `CD(...)` wrappers and repeated derivative slots on the same
scalar field, and prefer derivative-balanced scalar factors over one-sided
higher-derivative representatives. Do not extend this local score to
fermion/CG/Fierz structures without first reviewing Matchete's corresponding
scoring algorithms and native idenso/spenso capabilities.
For scalar derivative-bilinear normal forms, use the generic
`expose_scalar_derivative_commutator_bilinears(theory, expr, ...)` helper
rather than adding projection-specific replacements. It collects tagged scalar
field atoms with Symbolica patterns, extracts exact bilinear coefficients with
native `Expression.coefficient(...)`, and exposes Matchete
`GreensSimplify`-checked field-strength components through theory-owned
`CovariantDerivativeCommutator(...) * CovariantDerivativeCommutator(...)`
lowering. Current supported local scalar cases include two two-derivative
factors and one-sided four-derivative factors. For a target normalized as
`Bar[H] H F_W^2/gL^2`, the committed Matchete probe weights are
`Bar[D_mu D_nu H] D_mu D_nu H -> 1/4*gL^2`,
`Bar[D_mu D_nu H] D_nu D_mu H -> 1/8*gL^2`,
`Bar[D_mu D_nu D_mu D_nu H] H -> 1/8*gL^2`,
`Bar[D_mu D_mu D_nu D_nu H] H -> 0`, and
`Bar[D_mu D_nu D_nu D_mu H] H -> 1/4*gL^2`. In Wilson-line internal,
vakint, and validation preview routes this is available through
`OneLoopMatchOptions.wilson_line_expose_scalar_derivative_commutator_bilinears`
and remains opt-in while the broader Matchete-normal-form layer is validated.
For current-Matchete Wilson-line parity, apply this exposure after scalar
vacuum-integral evaluation and finite-part extraction. Do not run
`scalar_derivative_green_normal_form(...)` or its row-reduction identities on
pre-integral Wilson-line numerators as part of the default matching pipeline:
that changes the finite constants for the selected Singlet
`hScalar-lScalar -> cHW` probe. Keep pre-integral scalar Green-basis normal
form as an explicit diagnostic comparison path only, and use
`_apply_wilson_line_post_integral_scalar_commutator_bilinears(...)` for the
default internal/vakint/validation Wilson-line exposure boundary.
`WilsonLineTracePath.wilson_term_expanded_template_expression(...)` and
`WilsonLineTracePath.wilson_term_expanded_kernel_expression(...)` are
structural bridge methods; do not wire them into the default one-loop result
pipeline until their higher-order coverage is validated against committed
Matchete-independent fixtures.
Public bosonic CDE matching requests must replace only the selected
interaction-supertrace families by their CDE-expanded aggregate and must keep
all unselected interaction-power trace families in the one-loop source. Use the
`interaction_bosonic_cde_hybrid_*` setup methods for public `Theory.match(...)`
and validation-fixture preview paths. The lower-level
`interaction_bosonic_cde_*` methods intentionally remain pure selected-CDE
diagnostics for inspecting generated kernels, terms, and backend expressions.
Power-type supertrace prefactors must keep the cyclic-orbit factor after cyclic
de-duplication. Use `SupertraceBlockTrace.power_type_log_prefactor` for both
ordinary interaction-power terms and selected bosonic CDE replacement terms.
Periodic words such as `hScalar-hScalar` and `hScalar-hScalar-hScalar` carry
`-1/(2*n)`, while full-orbit words such as `hScalar-lScalar` keep effective
`-1/2`. Do not hard-code a universal `-1/2`, and do not omit the logarithmic
prefactor in CDE-generated replacement terms.
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
Closed fermion-loop Dirac traces generated by the explicit Wilson-line path
must be delegated to the idenso bridge. Use
`pychete.backends.idenso.trace_pychete_closed_dirac_chains(...)` on pure
compact pychete `NCM(...)` gamma/projector words in Wilson-line supertrace
numerators, then decode native `spenso::g(mink(...), mink(...))` wrappers back
to `pychete::Metric(...)` before tensor reduction or projection. If native
idenso cannot reduce a projector-only closed word, keep it formal; do not
patch over that gap with handwritten Python gamma-trace identities. For
fermion-loop terms with no compact Dirac factors and no registered fermion
fields, apply the Dirac identity trace factor at the Wilson-line postprocess
boundary. Open chains with registered fermion endpoints must remain open.
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
For barred/conjugate fields, the generator must act on the conjugate slot as
`CG(gen, adjoint, input, output_dual) * Bar(field(output))`; do not reuse the
unbarred `CG(gen, adjoint, output, input_dual)` orientation because that hides
fund/dual contractions from native idenso/spenso colour algebra.
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
For the SMEFT-relevant SU(2) Higgs/gauge CDE structures, use
`pychete.backends.idenso.simplify_su2_field_strength_generator_bilinears(...)`
to project symmetric `Bar(H_j) H_i T^A_{i k} T^B_{k j} W^A W^B` structures to
the singlet `Bar(H_i) H_i W^A W^A`. The singlet coefficient must be computed
from an idenso-simplified generator trace and applied with Symbolica
replacement rules; do not add Wilson-specific projection hacks for `cHW`.
For mixed SU(2)-U(1) Higgs/gauge CDE structures, use
`pychete.backends.idenso.simplify_su2_u1_field_strength_generator_bilinears(...)`
to canonicalize `H_i Bar(H_j) T^A_{i j} W^A B` source terms into the registered
Warsaw `cHWB` orientation. The U(1) charge and gauge couplings must remain in
the surrounding Symbolica coefficient; the helper is only an index-orientation
normalization over registered theory metadata.
When projecting indexed targets with conjugate-representation label pairs, use
the `MatchingResult` projection path rather than direct ad hoc coefficient
calls. Its final fallback must use Symbolica's `Expression.canonize_tensors`
return values: first get the canonical target expression together with the
returned canonical external and dummy index lists, then replace those
canonical target indices by linked wildcards and extract the temporary marker
coefficient natively. This covers CG targets such as `cHWB`, where
`Index(label, rep)` and `Index(label, Bar(rep))` must alpha-match together,
without inventing a separate Python-side dummy-index canonicalizer.
Before native vakint engine calls, lower pychete loop-momentum numerator heads
with `pychete.backends.vakint.lower_pychete_loop_momentum_numerators(...)`.
This maps `LoopMomentum(index)` to native `vakint::k(loop_id, index)` and
`LoopMomentumSquared` to native `vakint::k(loop_id, 1)^2`, matching the
vakint tensor-reduction API. If `index` is a full pychete `Index(...)`
expression, the vakint adapter must map it to a flat backend-safe symbol before
calling native vakint/FORM and decode returned native metric wrappers back to
the original `Index(...)` through `decode_pychete_namespace(...)`. Do not hand
nested pychete `Index(...)` wrappers to native loop-vector slots.
For CDE-generated internal analytic evaluation, reduce and evaluate each
generated `BosonicCDETraceExpansionTerm` independently before summing the
result. Do not first build one monolithic CDE topology sum and then ask vakint
to tensor-reduce the whole expression; multi-insertion traces such as
`hScalar-hScalar` scale much better when the backend boundary is the generated
CDE term.
The same termwise rule applies to selected CDE aggregates at native vakint
stages: raw diagnostic sums may stay raw, but canonicalized, tensor-reduced, or
evaluated native CDE aggregates must process each generated term independently
and only then sum decoded outputs. Keep native vakint wrapper constructors
attribute-compatible with the Rust backend before import; for example
`vakint::g` must be created as symmetric when Python code needs the wrapper
before native vakint has been imported.
Freshen dummy indices independently on every ordered CDE trace-entry operand
before multiplying the entry chain. Repeated trace insertions are independent
index sums; reusing one dummy label across all insertions creates an invalid
over-contracted source and breaks Symbolica's `canonize_tensors(...)` and
registered Wilson projection. Use `relabel_dummy_indices(...)` at the trace
entry boundary rather than a Wilson-specific projection workaround.
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
Generated Wilson-line/CDE Lorentz index labels are pychete dummy-index data,
not vakint-owned public symbols. When vakint or native tensor reduction emits
labels such as `vakint::wilson_line_*`, `vakint::cde_*`, or metric aliases
such as `index_wilson_line_*`/`index_cde_*`, normalize them to one pychete
generated namespace before idenso metric contraction or matching projection.
The normalization belongs in backend decode/simplification adapters through
Symbolica replacement rules; do not preserve `vakint::wilson_line_*` labels in
public pychete expressions, and do not compensate later with Wilson-specific
projection hacks.
Before any tensor-reduced Wilson-line expression is handed back to
`Theory`-owned derivative routines, generated `pychete::wilson_line_*` and
`pychete::cde_*` Lorentz labels must be restored to theory-owned
`Theory.symbol(..., role=SymbolRole.INDEX)` labels. Use this restored form for
`Theory._validate_registered_expression(...)`,
`emit_covariant_derivative_commutators(...)`, and
`expand_covariant_derivative_commutators(...)`; otherwise backend-generated
dummy labels can trip the structural symbol-data guarantees.
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

For comparisons and projections involving contracted tensor or field indices,
use Symbolica's native `Expression.canonize_tensors(contracted_indices)`. It
returns the canonical expression together with the external and ordered dummy
indices appearing in that canonical expression; use that native output to align
alpha-equivalent dummy-index contractions before comparing or projecting. Do
not hand-roll Python dummy-index renaming or rely on raw string equality when
`canonize_tensors(...)` can make the index structure canonical. In pychete
code, prefer `tensor_index_specs(...)` to build the grouped pychete
`Index(...)` specs and `canonize_tensor_indices(...)` to preserve Symbolica's
returned canonical expression, external-index list, and dummy-index list. Use
`TensorCanonization.canonical_indices` when building wildcard patterns from the
canonical form; do not rescan the canonical expression to infer the same index
mapping. When Symbolica exposes canonical index replacements or equivalent
external/dummy index payloads, keep those payloads attached to comparison and
projection results so later code can line up dummy indices without another
Python-side collection pass.
Validation fixture gap reports must leave `comparison_canonize_indices=True`
unless a test is explicitly measuring raw non-canonical behavior; otherwise
alpha-equivalent dummy contractions in common supertraces or matching
conditions will be reported as false validation gaps.
Target-local CDE term filters must stay conservative and label-level: use
Symbolica pattern matches to require the requested field/field-strength atoms,
but do not try to line up dummy indices inside the filter. Leave
dummy-index alignment to the existing projection/comparison path based on
`Expression.canonize_tensors(...)` and its returned canonical index payload.
For Matchete fixture frontier work, combine CDE filtering with
`ValidationFixture.one_loop_preview_gap_report(...,
matching_condition_projection_names=...)` so expensive public matching runs can
project only the Wilson family currently under investigation. Projection names
may be canonical condition names or external Wilson names such as `cHW`; use
`"wilson"` only when all Wilson conditions are intentionally needed.
Before projection/canonicalization, normalize powers of indexed field and
field-strength atoms with Symbolica replacement rules into fresh-index products
so shorthand terms such as `H[i]^3*Bar(H[i])^3` or `F[mu,nu,A]^2` can project
against Warsaw-basis operators written with independent dummy contractions.
Keep this normalization target-local to matching-condition projection; do not
globally rewrite user expressions just for display.
Also keep projection-local scalar derivative bilinears from reusing one
field-index contraction across every factor. Terms such as
`H[i] * D(mu, H[i]) * Bar(H[i]) * Bar(D(mu, H[i]))` must be split with
Symbolica replacement rules into independent dummy contractions before tensor
canonization, so `cHBox`-style IBP aliases can be projected without changing
the stored tree-level expression globally.
When counting EFT order for explicit `CD(...)` wrappers, a list-form derivative
index such as `CD({mu, mu}, body)` carries one derivative per listed index.
Do not count the whole list as a single derivative; otherwise Wilson
mass-dimension filtering drops valid dimension-six targets like `cHBox`.

Selected bosonic CDE trace requests must stay target-local. When
`bosonic_cde_trace_names` or explicit CDE expansion maps select a trace family,
build only the requested interaction category blocks and reuse identical
category-pair blocks within that selected trace. Do not construct the full
interaction supertrace plan just to throw away unselected trace names.

Matchete-style one-loop matching conditions contain both tree-level matching
pieces and one-loop threshold pieces. Public one-loop previews keep the
historical loop-only default for diagnostics, but parity probes that compare
full matching conditions should enable `OneLoopMatchOptions.include_tree_level_matching`.
The tree-level matched EFT source must be added after loop normalization so
loop prefactors never multiply tree terms.
When tree-level matching is included, preserve separate loop-only and
tree-level projection sources and project matching conditions source-by-source
with `MatchingResult.project_matching_conditions_from_sources(...)` or the
automatic one-loop staged projection path. Do not project full tree+loop
matching conditions only from the summed on-shell source: a direct loop
coefficient of an additive target can otherwise stop native coefficient
extraction before target-local IBP aliases recover the independent tree
contribution. Keep the staged sources updated through on-shell replacement
rules and EFT truncation so they still add up to the final public source.

Public API discoverability lives in `src/pychete/api.py`. Keep implementation
functions in their domain modules, but every function/class/enum intended for
users must be re-exported through `pychete.api` and package-root `pychete`,
except optional basis-provider helpers such as SMEFT Warsaw, which live under
`pychete.bases` plus any explicit compatibility shim.
Do not make users infer the public surface by browsing implementation files.
Every exported public object, and every user-facing method on exported classes,
must have a useful docstring at its implementation definition. These docstrings
are part of the interactive API: they should show up in `help(...)`, notebooks,
and editor hover tooltips such as VS Code/Pylance. When adding or promoting a
public API, update the public API docstring tests rather than leaving the
documentation requirement implicit.

Operator-basis metadata must be generic. Register known Wilson coefficient
operators through `OperatorBasis` and
`define_wilson_coefficient_from_basis(...)`, or register a provider with
`register_operator_basis(...)` and consume it through
`registered_operator_basis(...)` /
`define_wilson_coefficient_from_registered_basis(...)`. Specialized helpers such as
`define_smeft_wilson_coefficient(...)` must be thin convenience wrappers over
that generic basis machinery. SMEFT Warsaw is an optional built-in validation
and user-convenience basis, not a core matching assumption. Its implementation
lives under `pychete.bases.smeft_warsaw`; `pychete.smeft` is only a
compatibility shim for older fixtures/scripts. Root-level SMEFT exports must
not be added: optional basis providers are available through `pychete.bases`
and compatibility shims, while the package-root API stays generic. New engine
code must consume generic `OperatorBasis`/Wilson metadata and must not import
`pychete.smeft`, import `pychete.bases.smeft_warsaw`, or branch on Warsaw
names. Do not scatter ad hoc Wilson-to-operator maps in converters, fixtures,
matching code, or basis-specific modules outside `pychete.bases`. Raw
`Theory.define_wilson_coefficient(...)` calls must stay basis-unassigned by
default; use `define_wilson_coefficient_from_basis(...)` or a thin
basis-specific convenience wrapper to attach `"SMEFT"` or any other named
basis deliberately. The default Matchete SMEFT
validation fixtures expect the full 64-name `SMEFTWilsonCoefficients[]` set
from `SMEFT_Warsaw.m` to have pychete-native operator metadata, but the
matching pipeline must remain basis-agnostic.
Matchete-author feedback specifically warned against shaping pychete as a
SMEFT-specific matching tool. Treat the bundled Warsaw provider as fixture and
convenience data behind the generic operator-basis registry; do not use it as a
template for engine control flow, backend simplification decisions, or public
root API design.

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
