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
  `hScalar-lScalar -> cHW/cHB/cHWB`.
- The previous assumption that selected `hScalar-lScalar` also sources the
  unresolved Singlet `cHD` coefficient was rechecked against Matchete and is
  wrong. A target-aware Matchete prop-order-4 dump for `hScalar-lScalar`
  produced 18 raw four-derivative Higgs-bilinear terms, but the selected
  contribution becomes zero at the Matchete validation pipeline's
  `GreensSimplify` stage. Therefore `hScalar-lScalar -> cHD` is a useful
  Green-basis regression, not the immediate source of the nonzero saved
  Matchete `cHD` condition.
- Projecting the converted Matchete reference supertraces with pychete's
  registered `cHD` target identifies `hScalar-lScalar-lVector-lScalar` as the
  only currently observed nonzero reference supertrace source. Its projected
  contribution is
  `-3/2*hbar*log(mubar2/M^2)*A^2*gY^2/M^4
  -5/4*hbar*A^2*gY^2/M^4
  -3/2*hbar*A^2*gY^2/(epsilon*M^4)`. The full saved `cHD` condition is
  larger, so additional traces or tree/on-shell pieces still have to be
  identified after this selected trace is understood.
- The first precise mismatch in the four-slot trace was found before tensor
  reduction or projection: pychete's `FreeLagConvention.MATCHETE` scalar
  kinetic term kept Abelian covariant derivatives implicit but the fluctuation
  operator did not synthesize the corresponding scalar-vector X-blocks.
  Therefore every `lScalar-lVector`/`lVector-lScalar` path entry was zero and
  `hScalar-lScalar-lVector-lScalar` generated no pychete Wilson-line terms.
- The corresponding Matchete algorithm was reviewed before patching:
  `Matching.m:SetSubstitutions` uses
  `effLag = lag - KinOpLagrangian @@ allFieldLabels`, then computes
  `-FluctuationOperator[effLag, Bar@f1@i, f2@j]`, drops remaining quantum
  vector fields with `Field[_, _Vector, __] -> 0`, and lowers
  `OpenCD -> OpenCD - I LoopMom`. Thus scalar-vector X-terms from the charged
  scalar covariant kinetic current survive, while leftover vector-background
  pieces from connection-squared terms are removed.
- pychete now adds a bounded local implicit-Abelian scalar-vector contribution
  during fluctuation differential-entry construction when one basis entry is a
  registered scalar and the other is the registered Abelian vector for one of
  that scalar's gauge charges. The ordinary explicit entry is tried first; if
  it is already nonzero, pychete skips the implicit contribution to avoid
  double-counting explicitly expanded pychete lagrangians. A focused Singlet
  regression now confirms `hScalar-lScalar-lVector-lScalar` generates four
  zero-order Wilson-line terms carrying `gY^2`.
- The relevant downstream Matchete algorithm boundary remains:
  `PowerTypeSTr` iterates propagation orders, builds
  `GenericPropagatorExpansion`, enumerates `DeterminePowerInsertions`, and
  evaluates each insertion with `EvaluateSTr`; saved validation trace results
  are simplified through `ContractCGs // MatchReduce // GreensSimplify`.
  `GreensSimplify` builds operator classes, IBP identities, and
  covariant-derivative commutation identities, row-reduces them, and chooses
  preferred Green-basis representatives. `EOMSimplify` then applies matter and
  vector EOM redefinitions.
- The next precise comparison is now downstream of source generation:
  Wilson-term expansion, tensor reduction/integration, heavy-scalar
  substitution, Green-basis normal form, and registered-Wilson projection for
  the nonzero four-slot source. A full debug dump currently reaches a
  pychete scalar Green-basis size frontier, so the next slice should keep
  target-local dumps bounded while comparing Matchete stages.

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
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py -k
  "reference_chd_records" -q` passed (`1 passed, 48 deselected`). This is a
  fast partial regression for the Matchete `EOMSimplify` delta on the Singlet
  `cHD` matching condition and does not require Mathematica at pytest time.
- Watchdog-wrapped `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "higgs_gauge_subset or singlet_selected_wilson_line_chd_four_slot" -q`
  passed (`2 passed, 114 deselected`). These are the current targeted
  one-loop Wilson-coefficient regressions: selected `hScalar-lScalar` for
  `cHW/cHB/cHWB`, and selected four-slot `cHD`.
- `PYTHONPATH=src dependencies/.venv/bin/python -m py_compile
  scripts/debug_pychete_singlet_wilson_trace.py
  scripts/compare_singlet_wilson_debug.py` passed after the target-aware
  diagnostic edits.
- Watchdog-wrapped `wolframscript -file
  helper_mathematica_scripts/debug_singlet_wilson_trace.wls --target cHD
  --prop-order 0 ...` produced a Matchete order-zero dump whose saved
  reference `cHD` condition is nonzero.
- Watchdog-wrapped Matchete `hScalar-lScalar --target cHD --prop-order 4`
  showed the selected two-slot contribution vanishes after
  `GreensSimplify`, despite 18 raw four-derivative Higgs-bilinear terms before
  validation simplification.
- A converted-reference supertrace projection probe showed the only current
  nonzero `cHD` supertrace projection is
  `hScalar-lScalar-lVector-lScalar`; this replaces the older two-slot
  selected-trace assumption for the next mismatch slice.
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "charged_scalar or implicit_abelian" -q` passed (`2 passed`), covering the
  Matchete-convention implicit Abelian scalar-vector X-terms and preserving
  the existing explicit charged-scalar gauge-interaction behavior.
- Watchdog-wrapped `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_fluctuation_operator.py -k
  "four_slot_scalar_vector_trace" -q` passed (`1 passed`), confirming the
  Singlet `hScalar-lScalar-lVector-lScalar` zero-order Wilson-line source now
  generates four `gY^2` terms.
- Watchdog-wrapped direct Singlet source probe confirmed
  `hScalar-lScalar-lVector-lScalar` has `48` paths, `4` nonzero paths, and
  `4` zero-order Wilson-line terms after the implicit-Abelian X-term patch.
- A watchdog-wrapped full pychete `cHD` debug dump for that trace was stopped
  after it became too slow in downstream evaluation/projection. A broader
  selected `cHW` regression probe then exposed a separate scalar Green-basis
  solver limitation: some Wilson-line terms hand Symbolica's linear solver
  complex coefficients such as `5*i/18` together with nontrivial backend
  coefficient factors. The current solver patch now strips common scalar
  identity prefactors and encodes complex numeric row coefficients through an
  internal symbolic `i` placeholder before delegating to
  `Expression.solve_linear_system(...)`; focused unit tests cover both a
  shared imaginary prefactor and a relative `i/epsilon` row. This removes the
  selected `cHW` solver crash, but the selected coefficient still disagrees,
  so the patch is not yet a green milestone.
- Watchdog-wrapped selected `hScalar-lScalar -> cHW` now reaches projection.
  With `mu_R^2` left symbolic it gives
  `hbar*A^2*gL^2/M^4*(log(mu_R^2)/6 - log(M)/3 + 25/72)`, and with
  `mu_R^2=M^2` it gives `25/72*hbar*A^2*gL^2/M^4` instead of Matchete's saved
  `1/12`. Disabling scalar Green-basis exposure gives zero projection, so the
  mismatch is in scalar Green-basis/commutator exposure and finite-shift
  handling rather than source generation.
- A bounded Matchete `hScalar-lScalar -> cHW` prop-order-4 dump confirms the
  saved validation condition is
  `hbar*A^2*gL^2/(12*M^4)`. Matchete's reliable pre-`GreensSimplify`
  `validation_match_reduce` samples have the same derivative-word families as
  pychete. A pychete pre-Green finite probe at `mu_R^2=M^2` shows unbarred
  Higgs derivative-bilinear coefficients `-7/9`, `11/9`, and `-5/18`, while
  Matchete samples show the corresponding finite constants `-7/18`, `11/18`,
  and `-5/36` on barred derivatives as part of a symmetric barred/unbarred
  pair before simplification. Finite-first exploratory Green exposure gives
  `7/144`, pre-finite Green exposure gives `50/144`, and Matchete expects
  `12/144`; the next patch must therefore model Matchete's d-dimensional
  operator identity and finite-shift handling more faithfully, not just adjust
  an overall prefactor.
- `scripts/debug_pychete_singlet_wilson_trace.py` now has a `--source-only`
  mode for bounded four-slot trace diagnostics. Watchdog-wrapped source-only
  `hScalar-lScalar-lVector-lScalar -> cHD` completed quickly and reported
  four nonempty order-zero terms in preaction, prefinal, runtime-internal, and
  post-final grouped source summaries.
- Watchdog-wrapped `scripts/debug_pychete_singlet_wilson_trace.py --target
  cHD --max-total-order 0 --max-slot-order 0
  --substitute-heavy-scalar-solutions ...` produced a pychete dump retaining
  the two EOM-aware selected rows but still projecting zero after heavy
  substitution and scalar Green normal form.
- `git diff --check` passed.

## Next Work

- Continue target-aware Matchete and pychete debug comparisons for the exact
  four-slot trace `hScalar-lScalar-lVector-lScalar -> cHD`, now that pychete
  source generation is nonzero. Start with bounded per-entry/per-stage dumps
  rather than full aggregate evaluation, because the current pychete debug
  script becomes too slow downstream.
- Compare Matchete's `SuperTrace.m` stages for this trace against pychete's
  generated Wilson-line entries after the scalar-vector X-term fix. In
  particular, check insertion enumeration, cyclic/log prefactors, light-vector
  gauge-coupling factors, vector-slot signs, open-derivative action,
  symmetry-vanishing Wilson terms, Wilson expansion, tensor
  reduction/integration, heavy-scalar substitution, and final
  Green-basis/projection stages.
- If the first mismatch is still in Green-basis simplification, continue from
  the already reviewed Matchete `Simplifications.m` algorithms around
  `MatchOperatorPatterns`, `ConstructOperatorIdentities`, `IdentitiesIBP`,
  `IdentitiesCDCommutation`, `IBPSimplify`, `OperatorToNormalForm`, and
  `OpScore`. Keep the patch generic and Symbolica/idenso-backed rather than
  adding a Warsaw-specific `cHD` shortcut.
- The next scalar Green-basis work should continue beyond the fixed solver
  crash and compare Matchete's d-dimensional simplification semantics. In
  `Simplifications.m`, `Operator[...]` pulls prefactors free of
  `Field|FieldStrength|CG|LCTensor` outside the operator object,
  `SeparateInteractionTerm` returns `{coefficient, operator}`, and
  `ConstructOperatorIdentities` row-reduces the operator vector space.
  However, Matchete also keeps dimensional-regulator effects through
  `IBPSimplify`/`EpsExpand` and its evanescent treatment. pychete must capture
  the corresponding finite shifts generically before the selected `cHW`
  regression can be treated as a stable first Green-basis milestone.

## Latest Slice In Progress

- A direct Matchete-vs-pychete stage comparison for selected Singlet
  `hScalar-lScalar -> cHW` showed that applying pychete's scalar
  Green-basis normal form before scalar integral evaluation is the wrong
  ordering for the current Wilson-line path. Keeping the pre-integral
  Wilson/tensor/integral expression unexposed, taking the finite evaluated
  result, and only then applying scalar derivative commutator-bilinear
  exposure gives the Matchete coefficient `1/12` in the focused probe.
- The implementation is being adjusted so
  `wilson_line_expose_scalar_derivative_commutator_bilinears` means
  post-evaluation/post-finite exposure for internal, vakint, public matching,
  and validation preview routes. The older
  `_apply_wilson_line_scalar_green_normal_form(...)` remains available only as
  an explicit diagnostic comparison path.
- The focused regression to close first is now the selected Higgs-gauge
  subset test
  `test_singlet_selected_wilson_line_higgs_gauge_subset_matches_matchete_coefficients`.
  Once it is stable, rerun the Singlet source-generation regressions and then
  return to the four-slot `hScalar-lScalar-lVector-lScalar -> cHD` source.
- Focused validation after the patch:
  `tests/integration/matching/test_fluctuation_operator.py -k higgs_gauge_subset`
  passes, and
  `tests/integration/validation/test_validation_fixtures.py -k
  "singlet_wilson_line_gap_report_accepts_selected_higgs_gauge_targets and
  cHW"` passes under the 30 GiB watchdog. This establishes selected
  `hScalar-lScalar -> cHW` one-loop Wilson-line parity against the saved
  Matchete fixture, but not full-model SMEFT matching parity.

## Latest cHD Four-Slot Slice

- Continued the selected Singlet
  `hScalar-lScalar-lVector-lScalar -> cHD` Matchete parity investigation with
  insertion-level Matchete debug output instead of final-condition guessing.
  The useful Matchete checkpoint is insertion 1: after `WilsonExpand` and
  loop integration it has the paired structure
  `Bar[H_i] D_mu H_i D_mu Bar[H_j] H_j` with coefficient proportional to
  `A^2 gY^2`, `Prop[0]^3 Prop[M]`, and the expected
  `Log[mubar2/M^2]` finite part.
- Found and fixed two generic pychete mismatches before projection:
  pre-Wilson tensor reduction was not seeing loop momenta hidden inside
  generated `NCM(...)` chains, and internal light-vector propagator slots in
  longer Wilson-line paths were missing the Lorentz endpoint metric. The
  pre-Wilson path now scalarizes commutative `NCM` chains before collecting
  loop momenta, inserts the internal vector Lorentz metric, and delays
  symmetric-Lorentz metric contraction until after `WilsonTerm` expansion.
- Found and fixed the next generic mismatch in the pychete/idenso delta
  bridge. Matchete's `ContractDelta // ContractCGs // ContractDelta` contracts
  deltas through barred scalar field indices; pychete's generic
  `Delta * rest` fallback could leave or drop the delta before identifying
  the neighboring `Bar(Field(...))`. The idenso adapter now has bounded
  Symbolica replacement rules for `Delta(...) * Field(...)` and
  `Delta(...) * Bar(Field(...))` before the generic closed-dummy fallback.
- Result: selected pre-heavy `hScalar-lScalar-lVector-lScalar -> cHD`
  projection is now nonzero and matches the Matchete-selected finite
  coefficient
  `hbar*A^2*gY^2/M^4*(log(M) - log(vakint::mursq)/2 - 1/2)` using the
  registered Wilson target and EOM-aware target filtering. This is a second
  selected-trace Wilson-line coefficient milestone, not yet a full Singlet
  model integration-test reproduction.
- Latest registered-projection fix: a bounded pychete probe compared the raw
  and registered `cHD` paths at each projection stage after heavy-scalar
  substitution and post-finite scalar commutator-bilinear exposure. The first
  mismatch was not tensor reduction, vakint evaluation, normalization, or
  mass-dimension truncation. It was the registered projection path: Wilson
  aliases broadened the target-local canonicalization family enough to trip
  the generic-projection size guard before a cheap termwise exact native
  coefficient pass could run. The guard now allows a separately bounded
  termwise exact pass before blocking the expensive generic full-source
  fallback.
- Result: selected `hScalar-lScalar-lVector-lScalar -> cHD` now keeps the
  Matchete-selected finite coefficient
  `hbar*A^2*gY^2/M^4*(log(M) - log(vakint::mursq)/2 - 1/2)` through
  heavy-scalar substitution and post-finite scalar commutator-bilinear
  exposure using the registered Wilson target. This is still a selected-trace
  milestone, not yet a full Singlet model integration-test reproduction.
- Added a Matchete debug checkpoint for the next full-model `cHD` boundary:
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` writes
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`, recording the
  saved Singlet reference off-shell projection, on-shell projection, and
  `EOMSimplify` delta for the registered `cHD` operator. The coefficient shift
  is
  `-hbar*A^2*gY^2/(6*epsilon*M^4) -
  17*hbar*A^2*gY^2/(36*M^4) -
  hbar*A^2*gY^2*log(mubar2/M^2)/(6*M^4)`. Existing pychete
  Green-basis/EOM helpers do not reproduce this full on-shell shift from the
  saved reference; the remaining full-model blocker is a generic
  Matchete-style `EOMSimplify`/field-redefinition implementation, not the
  selected Wilson-line coefficient path.
- Added the Mathematica-independent regression
  `test_singlet_reference_chd_records_matchete_eom_simplify_delta`, which
  projects `cHD` from the committed off-shell and on-shell Singlet matching
  fixtures and checks the off-shell coefficient, the on-minus-off
  `EOMSimplify` delta, and the stored on-shell matching condition separately.
  The test uses the theory-owned `epsilon` and `mubar2` external symbols rather
  than fresh global Symbolica symbols, preserving the structural state-loading
  safety rule around symbol metadata.
- Fixed the first concrete prerequisite for a generic Matchete-style
  `EOMSimplify` implementation: `Theory.free_lag(...)` now instantiates every
  field with its declared internal dummy indices before constructing scalar,
  fermion, mass, and Abelian-current terms. Previously indexed complex fields
  such as the SMEFT Higgs were treated as unindexed in free kinetic terms,
  which made indexed light-field EOM extraction impossible.
- Fixed complex exact-field EOM variation for indexed fields. Passing
  `H[i]` to `derive_eom(...)` now uses the conjugate variation `Bar[H[i]]`
  when the field is not self-conjugate, matching the field-handle behavior and
  allowing `eom_replacement_rule(...)` /
  `eom_replacement_rules_for_expression(...)` to isolate indexed scalar
  Laplacians with Symbolica coefficient extraction.
- Added unit coverage for indexed complex scalar free kinetic terms and
  indexed complex scalar EOM replacement rules, plus a Singlet fixture
  regression proving the model Lagrangian now generates two Higgs EOM rules
  for the committed off-shell reference Laplacians. Applying those rules to
  the already-Greens-simplified off-shell reference does not produce the
  Matchete `cHD` on-shell delta; this confirms the remaining blocker is still
  the raw-Lagrangian field-redefinition loop, not this indexed-EOM
  prerequisite.
- Added a deliberately partial first-success integration regression for the
  selected Singlet Higgs-gauge Wilson subset. The former single `cHW`
  selected-trace test now projects only `cHW`, `cHB`, and `cHWB` from one
  generated `hScalar-lScalar` Wilson-line source and checks the Matchete
  coefficients `1/12`, `1/12`, and `1/6`. This gives fast regression scoping
  for the first matching Wilson coefficients without paying for all registered
  SMEFT conditions.
- Focused validation passed:
  `tests/unit/backends/test_idenso_backend.py -k "pychete_delta" -q`
  (`5 passed`), and watchdog-wrapped
  `tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line_vector_slots_use_matchete_propagator_sign or
  singlet_four_slot_scalar_vector_trace_has_implicit_abelian_xterms or
  higgs_gauge_subset or
  singlet_selected_wilson_line_chd_four_slot" -q` (`4 passed`).
- Latest focused validation for the indexed-EOM prerequisite passed:
  `tests/unit/functional/test_scalar_eom.py
  tests/unit/definitions/test_theory_definitions.py -q` (`84 passed`);
  `tests/integration/validation/test_validation_fixtures.py -k
  "reference_chd_records or higgs_eom_rules" -q` (`2 passed`);
  `tests/integration/matching/test_heavy_scalar_tree.py -k
  "generates_eom_replacements" -q` (`1 passed`); and watchdog-wrapped
  `tests/integration/matching/test_fluctuation_operator.py -k
  "higgs_gauge_subset or singlet_selected_wilson_line_chd_four_slot or
  four_slot_scalar_vector_trace" -q` (`3 passed`).
- Latest on-shell EOM slice: `eom_replacement_rules_for_expression(...)` now
  also collects Abelian vector field-strength divergence targets with
  Symbolica pattern matches, not only scalar Laplacian targets. For registered
  Abelian gauge vectors it builds the charged complex-scalar current from
  theory metadata and applies the Matchete-normalized vector EOM
  `D_nu F_{nu mu} -> -g^2 J_mu`, with the opposite sign for the reversed
  field-strength orientation. This is intentionally bounded to scalar
  Abelian currents for now; fermion currents and non-Abelian vector EOMs
  remain part of the larger Matchete-style `EOMSimplify`/field-redefinition
  frontier.
- Added unit tests for both Abelian vector field-strength divergence
  orientations and a public `Theory.match(..., loop_order=1)` regression
  proving that generated EOM rules reduce a loop-source vector divergence
  before projection. This closes a direct prerequisite for the full Singlet
  `cHD` on-shell shift, while still leaving the raw-Lagrangian iterative
  field-redefinition loop open.
- The selected Singlet Higgs-gauge Wilson coefficient regression is now split
  into parametrized partial integration tests for `cHW`, `cHB`, and `cHWB`.
  They reuse one cached selected `hScalar-lScalar` Wilson-line source inside
  the pytest process, so failures identify the exact coefficient subset
  without recomputing the expensive source three times. The selected four-slot
  `cHD` check remains a separate single-coefficient partial regression.
- Latest focused validation for this slice passed:
  `tests/unit/functional/test_scalar_eom.py -q` (`22 passed`);
  `tests/integration/matching/test_heavy_scalar_tree.py -k
  "vector_eom_replacements or generates_eom_replacements" -q` (`2 passed`);
  and watchdog-wrapped `tests/integration/matching/test_fluctuation_operator.py
  -k "higgs_gauge_coefficient_matches_matchete_subset or
  singlet_selected_wilson_line_chd_four_slot or
  singlet_four_slot_scalar_vector_trace_has_implicit_abelian_xterms" -q`
  (`5 passed`). `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` also
  passed with no issues.
- Latest field-redefinition slice: reviewed Matchete
  `Package/FieldRedef.m` before patching. The key missing vector-EOM piece was
  not another projection alias: Matchete's `DummyGaugeShift` shifts both
  Abelian field strengths and the charged covariant derivatives. pychete's
  previous replacement-only path accounted for the
  `D_nu F_{nu mu}` replacement but missed the scalar-current companion from
  shifting charged scalar `CD` slots.
- Added `abelian_vector_eom_field_redefinition_delta(...)` and
  `Theory.abelian_vector_eom_field_redefinition_delta(...)`. The helper uses
  the same Symbolica pattern collection, native `Expression.coefficient(...)`,
  and Symbolica `Replacement` application as the EOM replacement pass. It is
  deliberately bounded to Abelian gauge vectors and charged scalar currents;
  fermion currents, non-Abelian vectors, kinetic mixing, Jacobian/anomaly
  terms, and full iterative scalar/fermion field redefinitions remain open.
- Added the opt-in public one-loop option
  `OneLoopMatchOptions.on_shell_eom_abelian_vector_field_redefinition`. When
  enabled together with `on_shell_eom_lagrangian`, pychete computes the
  Abelian vector companion from the pre-reduction source, applies the ordinary
  EOM replacements, then adds the companion as a named diagnostic stage.
- Important checkpoint: applying the committed Singlet model Lagrangian to the
  committed Matchete off-shell reference with the vector EOM replacement plus
  this new companion now reproduces the saved Matchete `cHD` on-shell matching
  coefficient exactly. The previous vector replacement alone moved only half
  of the required off-shell-to-on-shell shift.
- Latest focused validation for this slice passed:
  `tests/unit/functional/test_scalar_eom.py -q` (`23 passed`);
  `tests/integration/matching/test_heavy_scalar_tree.py -k
  "vector_eom_replacements" -q` (`1 passed`);
  `tests/integration/validation/test_validation_fixtures.py -k
  "reference_chd_vector_eom_field_redefinition or reference_chd_records or
  higgs_eom_rules" -q` (`3 passed`);
  `tests/unit/definitions/test_public_api.py -q` (`8 passed`);
  and `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed with no
  issues.
- Latest validation-plumbing slice: `ValidationFixture.one_loop_preview(...)`
  and `ValidationFixture.one_loop_preview_gap_report(...)` now expose the
  on-shell EOM controls that the public matcher uses, including
  `on_shell_eom_lagrangian`, field filters, derivative-order/strict/repeat
  settings, and the bounded
  `on_shell_eom_abelian_vector_field_redefinition` companion. Fixture
  expression names are resolved before either the direct-preview route or the
  `use_public_match_api=True` route is called, so committed Matchete-independent
  gap reports can exercise the same Singlet `cHD` on-shell checkpoint without
  custom test-only postprocessing.
- Focused validation for the plumbing slice passed:
  `tests/integration/validation/test_validation_fixtures.py -k
  "preview_applies_abelian_vector_eom_field_redefinition or
  forwards_pychete_color_to_public_match_api or
  forwards_heavy_scalar_options_to_direct_preview" -q` (`3 passed`);
  `tests/integration/validation/test_validation_fixtures.py -k
  "reference_chd_vector_eom_field_redefinition or reference_chd_records or
  higgs_eom_rules" -q` (`3 passed`);
  and `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed with no
  issues.
- Latest partial Wilson-coefficient scoping slice: the first selected
  one-loop Wilson-coefficient successes now live in the dedicated integration
  module `tests/integration/matching/test_singlet_selected_wilson_coefficients.py`
  instead of the broad fluctuation-operator test file. The `cHW`, `cHB`, and
  `cHWB` checks remain separate parametrized cases, sharing one cached
  selected `hScalar-lScalar` Wilson-line source inside the pytest process.
  The selected four-slot `cHD` contribution remains a separate single-target
  regression. This gives future regressions fast node IDs for individual
  Wilson coefficients while preserving the existing first-success coverage.
- Focused validation for the test-scoping slice passed under the 30 GiB
  watchdog: `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -q` (`4 passed`). The edited broad file also passed collection:
  `tests/integration/matching/test_fluctuation_operator.py --collect-only -q`
  (`114 tests collected`).
- Latest public-route coefficient slice: the first successful selected
  Singlet Wilson coefficients now also pass through the public
  `Theory.match(...)` path as exercised by
  `ValidationFixture.one_loop_preview_gap_report(..., use_public_match_api=True)`.
  The new slow partial integration test projects the selected
  `hScalar-lScalar` Wilson-line subset for `cHW`, `cHB`, and `cHWB` in one
  report, with target filtering, pre-Wilson tensor reduction, internal
  minimal subtraction, evaluated-HBAR normalization, and registered-Wilson
  matching-condition projection all enabled. All three projected coefficients
  match the committed Matchete fixture.
- A bounded probe of the order-one full-model `cHD` report with the new
  on-shell EOM options still disagrees, and the metadata shows no vector-EOM
  rule or Abelian field-redefinition delta applied at that truncation. This
  keeps the full Singlet `cHD` frontier honest: the selected four-slot
  coefficient and reference off-shell-to-on-shell reduction are green, but the
  full generated model source still needs additional trace/source coverage
  before the public full-model `cHD` condition can pass.
- Focused validation for this slice passed under the 30 GiB watchdog:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -q`
  (`5 passed`).
- Latest public selected-`cHD` slice: the public `Theory.match(...)` route now
  also reproduces the selected Singlet
  `hScalar-lScalar-lVector-lScalar -> cHD` coefficient with Wilson-line target
  filtering enabled. The mismatch was in the pre-generation Wilson-line entry
  filter: it rewrote individual insertion entries whenever any projection
  alias involved a field strength. Registered `cHD` has field-strength EOM
  aliases, but also has a pure field/derivative target group; heavy-mediated
  terms must be allowed to combine across the whole Wilson-line path before
  generated-term filtering. The entry rewrite is now restricted to target
  requirement sets where every requirement group is field-strength-local.
  The path-level impossible-entry guard and generated-term filter remain in
  place.
- Added a public selected-four-slot `cHD` regression to
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py`.
  It calls `Theory.match(...)` with selected
  `hScalar-lScalar-lVector-lScalar`, target filtering, pre-Wilson tensor
  reduction, internal minimal subtraction, evaluated-HBAR normalization, and
  registered-Wilson projection. It checks the Matchete-selected coefficient
  `hbar*A^2*gY^2/M^4*(log(M) - log(vakint::mursq)/2 - 1/2)`.
- Focused validation for this slice passed under the 30 GiB watchdog:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -q`
  (`6 passed`), and
  `tests/integration/matching/test_fluctuation_operator.py -k
  "wilson_line_target_filter or singlet_wilson_line_target_prefilter or
  public_wilson_line_can_filter_terms_by_matching_targets" -q`
  (`3 passed, 111 deselected`). `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` also passed.
- Latest source-map scoping slice: `MatchingResult` now exposes
  `project_matching_conditions_by_source(...)`, a diagnostic projection view
  that projects the same target set independently from each named supertrace
  or staged source. The method is intentionally orchestration only: each
  coefficient still goes through the existing Symbolica-backed
  `project_matching_conditions(...)` path with the same tensor
  canonicalization, derivative normalization, EFT truncation, and projection
  aliases.
- Added the partial integration regression
  `test_singlet_reference_chd_source_map_is_single_four_slot_supertrace`.
  It projects the committed Matchete Singlet reference fixture for registered
  `cHD` source by source, proves the only nonzero supertrace contribution is
  `hScalar-lScalar-lVector-lScalar`, and checks that this contribution equals
  the full committed off-shell reference projection. This keeps future
  regressions localized: a failure can distinguish wrong generated selected
  coefficient, wrong Matchete source decomposition, and wrong on-shell EOM
  delta.
- Focused validation for this slice passed:
  watchdog-wrapped `tests/integration/validation/test_validation_fixtures.py
  -k "singlet_reference_chd" -q` (`3 passed, 50 deselected`);
  watchdog-wrapped `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -q` (`6 passed`); `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  passed; and `git diff --check` passed.
- Latest insertion-checkpoint slice: generated and committed the Matchete
  debug fixture
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.debug.json`
  for the Singlet
  `hScalar-lScalar-lVector-lScalar -> cHD` propagator-order-zero trace. The
  dump records 88 Matchete insertion replacements, the `(-1/2*I)*hbar`
  power-log prefactor, and detailed insertion-level bilinear coefficients.
  Its first detailed insertion validates a single `-1/4` cHD-type quarter
  contribution after Matchete's Wilson expansion and loop integration stages.
- Added partial integration regressions that project only individual pychete
  Wilson-line paths 0 and 26 for the same selected four-slot trace. Each path
  independently reproduces the Matchete quarter coefficient
  `hbar*A^2*gY^2/M^4*(log(M)/2 - log(vakint::mursq)/4 - 1/(4*epsilon) - 1/4)`.
  This is intentionally narrower than the selected aggregate coefficient:
  pychete currently finds two such quarter-path contributions, while the
  committed Matchete off-shell source has the equivalent of six. The next
  frontier is therefore localized to missing scalar-vector Xterm/GaugeCTerm
  insertion families or Green-basis projection coverage, not to the basic
  path-level loop integration/projection machinery.
- Focused validation for this insertion-checkpoint slice passed under the
  30 GiB watchdog:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -k "quarter_paths or selected_chd_four_slot_wilson_coefficient" -q`
  (`4 passed, 4 deselected`).
