# One-Shot Port Implementation Notes

## Active Plan And Guidelines

- Continue the one-shot Matchete-style one-loop matching port on branch
  `one-shot-port`, targeting the default Matchete validation models first:
  `VLF_toy_model`, `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Keep the forward one-loop architecture Wilson-line-first. CDE remains a
  legacy/diagnostic route only; new parity work should extend explicit
  Wilson-line traces, Wilson-term expansion, idenso/spenso algebra, tensor
  reduction, vacuum-integral evaluation, and matching-condition projection.
- Keep operator-basis handling generic. SMEFT Warsaw is an optional built-in
  basis provider under `pychete.bases.smeft_warsaw`, not a core matching
  assumption.
- Runtime pychete and pytest remain Mathematica- and Matchete-independent.
  Wolfram scripts are optional tools for generating/debugging committed
  pychete-owned fixtures.
- Use Symbolica-native primitives, patterns, replacements, coefficient
  extraction, rational/polynomial tools, tensor canonicalization, and
  evaluators before adding Python symbolic logic. Use idenso for gamma, colour,
  metric, and abstract-index algebra; spenso for tensor-network/CG work; vakint
  for topology-independent tensor reduction and optional single-scale analytic
  cross-checks. pychete owns the Matchete-style analytic one-loop vacuum
  integral evaluator for single-scale, zero-mass, and mixed-mass cases.
- When a precise mismatch is identified, first inspect the corresponding
  Matchete Mathematica algorithm and compare stage semantics before patching
  pychete. Do not repair a disagreement from the final coefficient alone; use
  intermediate dumps/probes to locate the first semantic difference.
- Use larger coherent implementation slices. Run focused tests while building a
  slice, grouped targeted tests before a green milestone, and full/slow tests
  only when the milestone justifies the cost.
- Run memory-risk tests and exploratory matching workloads through
  `scripts/run_with_memory_watch.py --limit-gb 30 -- ...`.
- Never request sandbox permission escalation. The `sandbox_permissions` key is
  banned from shell tool calls. Use the user-started `listener.py`
  `run.order`/`run.output` route for `.git` metadata writes and for retries
  after `Operation not permitted`; otherwise run ordinary reads and focused
  tests directly.
- Commit and push coherent green milestones to `origin/one-shot-port`. Keep
  this live file current; when it grows too large again, archive it unchanged
  to `one_shot_implementation_part_G.md` and rewrite a compact live summary.

## History Files

- `implementation_notes/one_shot_implementation_part_A.md` keeps the first long
  implementation log unchanged.
- `implementation_notes/one_shot_implementation_part_B.md` records work through
  commit `e54615a`.
- `implementation_notes/one_shot_implementation_part_C.md` records Wilson
  projection, SMEFT Wilson metadata, internal integrals, on-shell/EOM
  reduction, final EFT truncation, and Abelian covariant-derivative expansion.
- `implementation_notes/one_shot_implementation_part_D.md` records
  non-Abelian infrastructure, idenso/spenso/vakint bridges, projection
  canonicalization, heavy-scalar dummy freshening, derivative/IBP projection,
  commutator lowering, CDE planning, and scalar CDE projection work.
- `implementation_notes/one_shot_implementation_part_E.md` records work through
  commit `c3cc55c`, including hybrid CDE composition, vakint tensor/CD decode,
  field-strength metric simplification, colour-chain decode,
  heavy-substituted projection, coupling mass-dimension filtering, Matchete
  coupling-dimension inference, and tensor-index canonicalization diagnostics.
- `implementation_notes/one_shot_implementation_part_F.md` preserves the long
  log through the latest Wilson-line author-feedback slices, explicit
  Wilson-line trace APIs, fermion/vector Wilson-line support, colour/idenso
  postprocessing, target-local filtering, evaluated-HBAR convention fixes,
  selected Singlet `cHW`/`cHB`/`cHWB` parity, and the first `cHD` frontier
  investigations.

## Current Verified Milestones

- The current explicit Wilson-line route has structured diagnostics through
  `WilsonLineTracePath`, `WilsonLineTraceExpansionTerm`,
  `s.WilsonLine`, and `s.WilsonTerm`. Public matching uses hybrid selected
  Wilson-line replacement: selected trace families are Wilson-line-expanded and
  the unselected interaction-power remainder stays in the source.
- CDE and Wilson-line public options are mutually exclusive. Validation preview
  helpers expose the same Wilson-line controls as public `Theory.match(...)`.
- Fermion Wilson-line slots use the fermionic propagator expansion; vector
  non-fermion slots carry the Matchete vector sign; generated closed fermion
  loop gamma traces are delegated to idenso.
- Generated Wilson-line numerators are postprocessed through NCM normalization,
  idenso Dirac/gamma simplification, loop-momentum metric contraction,
  field-strength metric/antisymmetry simplification, and optional generated
  colour simplification.
- The optional SMEFT Warsaw provider is registered through the generic
  operator-basis registry and is no longer exported from the package root.
- Heavy scalar solution substitution uses fresh dummy indices. Wilson-line
  target filtering is heavy-EOM-aware, so pre-EOM terms such as `H^2 phi` are
  preserved when they can become final light-field operators.
- Selected Singlet `hScalar-lScalar` Wilson-line validation now reproduces the
  Matchete fixture-level `cHW`, `cHB`, and `cHWB` coefficients with the
  evaluated-HBAR convention and internal minimal-subtraction backend.
- The latest focused code change adds registered-Wilson target-local Abelian
  gauge-EOM projection aliases. For a registered target such as `cHD`,
  projection now recognizes Higgs current times the Abelian vector EOM normal
  form `FieldStrength(B,{nu,mu},{},{nu})`, with weights computed by projecting
  the EOM-reduced current-current alias through the ordinary Symbolica
  projection path.
- Wilson-line target filtering now includes projection aliases in its atom
  requirements, so terms relevant only after target-local EOM/IBP aliases are
  not dropped just because the literal Warsaw operator lacks that intermediate
  atom family.
- pychete now has a bounded scalar-Laplacian IBP helper,
  `integrate_by_parts_scalar_laplacians(...)`, implementing the local
  Matchete `IdentitiesIBP` member
  `A * D_mu D_mu(phi) -> -D_mu(A) * D_mu(phi)`. The helper discovers tagged
  scalar Laplacian atoms with Symbolica patterns and extracts coefficients
  with native `Expression.coefficient(...)`. It is exported through the public
  API and wired only into the opt-in Wilson-line scalar-Green path, including
  the post-heavy-scalar-substitution preview/public matching stage.
- Registered Wilson/operator targets now also receive target-local scalar
  first-derivative IBP projection aliases. For a target factor
  `A * D_mu(phi)`, pychete adds the total-derivative-equivalent alias
  `-D_mu(A) * phi`, discovered with Symbolica field patterns and differentiated
  through `apply_cd(...)`. This is generic Green-basis projection support and
  not tied to the SMEFT `cHD` name.
- The scalar derivative-slot projection alias now covers the direct Matchete
  `IdentitiesIBP` member
  `A * D_mu D_rest(phi) -> -D_mu(A) * D_rest(phi)` for simple scalar
  derivative target monomials. It is bounded, uses Symbolica pattern discovery
  and native coefficient extraction, and skips additive/composite `CD` targets
  so it does not double count the existing scalar-box bilinear alias path.
- pychete now exposes `Theory.covariant_derivative_commutator_identities(expr)`
  as the Matchete `IdentitiesCDCommutation` identity-source boundary. Unlike
  `emit_covariant_derivative_commutators(..., mode="all_distinct")`, which is
  an equality-preserving one-pair expression rewrite, the new helper returns a
  separate identity for every adjacent distinct derivative pair on each
  differentiated field/field-strength atom. It uses Symbolica
  tag-restricted matches plus native `Expression.coefficient(...)` extraction,
  and deliberately skips nonlinear repeated atom occurrences until a true
  operator-class row-reduction representation owns them.
- pychete now has a first bounded Green-basis normal-form boundary:
  `linear_identity_normal_form(...)` and
  `Theory.covariant_derivative_commutator_normal_form(...)`. Composite
  operator monomials are encoded as temporary Symbolica variables, the linear
  relations are solved with native `Expression.solve_linear_system(...)`, and
  the result is decoded back to pychete expressions. The basis and preferred
  representatives remain explicit so this does not guess Matchete's full
  operator-class scoring rules in Python.
- pychete now also has a bounded automatic local-basis layer for this path:
  `linear_identity_basis_terms(...)`,
  `linear_identity_normal_form_from_identities(...)`, and
  `Theory.covariant_derivative_commutator_local_normal_form(...)`. These
  helpers collect operator monomials from an expression plus generated
  identities, strip scalar coefficients in the local Matchete
  `cpl * Operator[...]` sense, and still delegate row reduction to Symbolica.
  Preferred representatives remain explicit.
- pychete now has source-side scalar Green-basis identity helpers:
  `scalar_derivative_ibp_identities(...)` generates the scalar subset of
  Matchete `IdentitiesIBP`, and `scalar_derivative_green_normal_form(...)`
  combines scalar IBP and covariant-derivative commutator identities in a
  bounded local basis before delegating row reduction to Symbolica. The
  existing opt-in Wilson-line scalar derivative postprocess now uses this
  broader normal form, lowers any generated formal commutators, and then runs
  the existing field-strength exposure helper.
- When no explicit preference list is supplied, the scalar Green-basis normal
  form now applies a bounded scalar-local preferred-representative order based
  on the scalar-relevant Matchete `OpScore` pieces reviewed in
  `Simplifications.m`: prefer field-strength-like representatives, penalize
  explicit `CD(...)` wrappers and repeated derivative slots, and prefer
  derivative-balanced scalar factors over one-sided higher-derivative
  representatives. This closes a local representative-selection gap without
  porting Matchete's fermion/CG/Fierz scoring policy into Python.

## Current Frontier

- The closest full one-loop Matchete integration milestone remains the Singlet
  Scalar Extension selected Wilson-line trace family. The accepted subset is
  `hScalar-lScalar -> cHW/cHB/cHWB`; the first unresolved family is
  `hScalar-lScalar -> cHD` and related derivative/Higgs targets `cHBox` and
  `cH`.
- The latest cHD mismatch investigation followed the explicit Matchete
  algorithm before patching:
  `SaveValidationResults` simplifies saved trace results with
  `ContractCGs // MatchReduce // GreensSimplify`; `GreensSimplify` contracts
  group/index structures, maps terms to operator classes, builds IBP and
  covariant-derivative commutation identities through
  `ConstructOperatorIdentities`, row-reduces those identities, and returns
  preferred Green-basis representatives. `EOMSimplify` then performs systematic
  matter/vector field redefinitions; vector EOM normal form is
  `FieldStrength[V,{nu,mu},inds,{nu}]`, and `VectorShift` uses the gauge
  kinetic normalization.
- pychete now has a correct target-local Abelian vector-EOM projection alias,
  but that is not enough for the selected Singlet `cHD` coefficient. A
  filtered-versus-unfiltered selected `hScalar-lScalar` run with
  `wilson_line_max_total_order=4` and `wilson_line_max_slot_order=4` kept the
  same 16 Wilson-line terms in both cases, with nonzero plan entries
  `hScalar-lScalar#wilson0_o0_0`, `hScalar-lScalar#wilson5_o2_0`, and
  `hScalar-lScalar#wilson14_o4_0`. The on-shell aggregate still contained no
  detected `FieldStrength` atoms and projected the selected scalar-only source
  to zero for `cHD`.
- Therefore the current precise gap is not premature cHD target filtering and
  not direct coefficient extraction. It is the missing Matchete-style
  Green-basis scalar derivative reduction that turns the selected scalar
  derivative class into the preferred combination of pure `D^2H D^2H`,
  Higgs-current times `D·B`/`D·W`, and direct four-Higgs derivative-current
  operators before matching-condition extraction.
- The latest scalar-Laplacian IBP slice covers the direct
  `A * D^2 H -> D A * D H` source-side identity and projects a local
  four-Higgs derivative-current component with the expected sign. It does not
  complete the selected Singlet `cHD` mismatch: a bounded
  `wilson_line_max_total_order=0` smoke with heavy-scalar substitution and the
  new pass still projects `cHD` to zero. A max-order-4 debug with explicit
  commutator emission confirmed many generated `FieldStrength` atoms but still
  zero projected `cHD`; full source inspection of the `wilson14_o4_0` family is
  currently too expensive interactively. The remaining gap is therefore the
  higher-derivative Green-basis/commutator row-reduction piece, not this local
  scalar Laplacian identity alone.
- The follow-up first-derivative target-local IBP alias now projects a
  registered `cHD` target from the full total-derivative-equivalent source
  `-D_mu(Bar[H] H D_mu H) Bar[H]`. The bounded selected Singlet order-zero
  smoke still returns zero, so the mismatch is not only projection of this
  first-derivative IBP family; the higher-derivative selected-source
  normal-form gap remains.
- The direct higher-derivative scalar derivative-slot projection alias closes
  a smaller structural mismatch with Matchete's `IdentitiesIBP`, but it is not
  a recursive/additive substitute for Matchete's row-reduced Green-basis
  identities. In particular, pychete still needs the explicit
  `IdentitiesCDCommutation` plus row-reduction semantics before interpreting
  partial pieces of total-derivative identities as selected Singlet `cHD`.
- The latest commutator-identity slice closes the identity-source mismatch:
  pychete can now generate all local adjacent-pair `CommuteCDs` identities for
  linear field-like atoms. These identities now have a Symbolica-backed
  explicit-basis solver boundary; what remains is the bounded automatic
  operator-class vector-space construction around them.
- The latest normal-form slices now feed local bases and generated commutator
  identities into Symbolica's linear solver. The new automatic local-basis
  builder is enough to reduce synthetic composite operator monomials such as
  `Bar(phi) D_a D_b phi` to preferred `Bar(phi) D_b D_a phi` plus commutator
  representatives without a hand-supplied basis list. The remaining cHD work
  is automatic operator-class discovery/scoring for larger local classes,
  basis construction for the higher-derivative Singlet source, and integration
  with the selected Wilson-line Green-basis stage.
- The source-side scalar IBP/commutator normal-form slice adds the next local
  identity layer and is wired into the opt-in Wilson-line scalar-Green path.
  A watchdog-wrapped order-zero selected Singlet `hScalar-lScalar -> cHD`
  smoke still preserved two EOM-aware Wilson-line terms but produced no
  projected matching condition, so this does not yet complete the `cHD`
  milestone. The remaining gap is the larger Matchete operator-class scoring
  and preferred-representative policy for higher-derivative scalar classes,
  not just generation of the first local IBP/commutator identities.
- The scalar-local preferred-representative score now maps a focused crossed
  one-sided four-derivative scalar bilinear to the balanced two-derivative
  bilinear in unit tests. The selected Singlet order-zero `cHD` smoke remains
  unchanged, so the next mismatch investigation still has to compare
  Matchete's full operator-class normal-form/evaluation path against pychete's
  bounded local scalar normal form before another patch.
- The diagnostic scripts now support target-aware `cHD` comparison. The
  Matchete Singlet Wilson-line dump accepts `--target` and records the saved
  reference matching condition for that target. The pychete Singlet debug dump
  uses the requested target for filtering/projection, can apply the public
  heavy-scalar solution replacement stage, and reports aggregate projections
  after heavy substitution and after the scalar Green normal form. A
  watchdog-wrapped order-zero `cHD` run with EOM-aware target filtering kept
  the two expected `hScalar-lScalar#wilson0_o0_0` rows, but the aggregate
  projection remained zero before substitution, after substitution, and after
  scalar Green normal form. This localizes the next parity comparison away
  from order-zero filtering and toward the higher-derivative
  `wilson14_o4_0` operator-class row reduction.

## Latest Validation

- `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed with no issues.
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_scalar_green_bilinears.py -q` passed
  (`20 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_public_api.py -q` passed (`8 passed`).
- Watchdog-wrapped `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "scalar_derivative" -q` passed (`3 passed`).
- Watchdog-wrapped `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py -k
  "wilson_line_scalar_derivative_bilinear_option" -q` passed (`1 passed`).
- Watchdog-wrapped `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py -k
  "pre_eom_terms_for_derivative_higgs_target" -q` passed (`1 passed`).
- Watchdog-wrapped selected Singlet order-zero `hScalar-lScalar -> cHD` probe
  with the new scalar Green normal form preserved `2` Wilson-line terms in
  `hScalar-lScalar#wilson0_o0_0` and still produced no projected matching
  condition.
- `PYTHONPATH=src dependencies/.venv/bin/python -m py_compile
  scripts/debug_pychete_singlet_wilson_trace.py
  scripts/compare_singlet_wilson_debug.py` passed after the target-aware
  diagnostic edits.
- Watchdog-wrapped `wolframscript -file
  helper_mathematica_scripts/debug_singlet_wilson_trace.wls --target cHD
  --prop-order 0 ...` produced a Matchete order-zero dump whose saved
  reference `cHD` condition is nonzero.
- Watchdog-wrapped `scripts/debug_pychete_singlet_wilson_trace.py --target
  cHD --max-total-order 0 --max-slot-order 0
  --substitute-heavy-scalar-solutions ...` produced a pychete dump retaining
  the two EOM-aware selected rows but still projecting zero after heavy
  substitution and scalar Green normal form.
- `git diff --check` passed.

## Next Work

- Continue the next generic, bounded scalar Green-basis reduction slice. Start
  from the Matchete `Simplifications.m` algorithms around
  `MatchOperatorPatterns`, `ConstructOperatorIdentities`, `IdentitiesIBP`,
  `IdentitiesCDCommutation`, `IBPSimplify`, and `OperatorToNormalForm`; do not
  add another Warsaw-specific `cHD` shortcut.
- Use Symbolica pattern/replacement/coefficient/tensor-canonicalization
  primitives and idenso metric/group simplification as the pychete boundary.
  A small Python orchestrator may enumerate candidate scalar derivative classes,
  but the symbolic transformations should stay native.
- The next concrete target is the higher-derivative scalar class behind
  `hScalar-lScalar#wilson14_o4_0`: reproduce Matchete's adjacent
  `CommuteCDs` plus row-reduced Green-basis representative for the local
  four-derivative scalar terms, then rerun a reduced selected-trace cHD smoke
  under the 30 GiB watchdog.
- Use the target-aware Matchete/pychete debug dumps for the next precise
  comparison, and inspect Matchete's `ConstructOperatorIdentities`/`IBPSimplify`
  behavior for the exact derivative-class samples before changing runtime
  matching code.
- With bounded scalar IBP/commutator normal form now available and wired into
  the opt-in Wilson-line scalar-Green route, the next implementation step is
  to port more of Matchete's operator-class scoring/preferred-representative
  policy for the higher-derivative scalar classes. The immediate target is a
  generic preference strategy that can select the same Green-basis
  representatives Matchete uses for the selected Singlet `cHD`/`cHBox`/`cH`
  derivative-Higgs family, without hard-coding Warsaw coefficients.
