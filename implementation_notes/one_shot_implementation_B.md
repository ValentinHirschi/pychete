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
- For sustained Matchete/pychete disagreements, actively run focused debug
  WolframScripts and dump as many relevant Matchete intermediate stages as
  practical for the narrowed trace, insertion, propagation order, target, and
  simplification stage. Compare those dumps against bounded pychete probes at
  the same semantic boundaries before patching the first differing generic
  algorithm. Keep pytest Mathematica-independent by committing only derived
  JSON/pychete fixtures when they become regression evidence.
- Treat those Matchete-side debug dumps as the default parity workflow during
  active one-shot matching work. If a mismatch has no recent compatible
  Matchete dump for the same trace, target, propagation order, and stage,
  create or refresh one before changing pychete whenever Mathematica is
  available; otherwise record that limitation explicitly.
- For each mismatch-fix slice, record the specific Matchete debug
  WolframScript/dump consulted, the corresponding bounded pychete probe, and
  the first generic algorithm boundary where they diverged. The goal is to
  port the relevant Matchete algorithm through Symbolica/idenso/spenso/vakint,
  not to infer fixes from final Wilson-coefficient disagreement.
- Before accepting a patch motivated by a Matchete disagreement, complete the
  mismatch checklist in these notes: name the Matchete debug script or
  committed fixture, name the bounded pychete probe or pytest fixture, state
  the first stage boundary that differs, and explain why the runtime change is
  a generic Matchete-algorithm port rather than a coefficient-specific repair.
- User reinforcement, 2026-06-28: for every current and future
  Matchete/pychete disagreement, keep running or refreshing focused debug
  WolframScripts and dissect Matchete intermediates until the first mismatching
  semantic boundary is located. Record the Matchete stage dump, the bounded
  pychete probe, and the stage comparison before accepting runtime changes.
- User reinforcement, 2026-06-28: this must be an active cadence during
  mismatch work, not a retrospective audit. Keep dumping as many relevant
  Matchete intermediate stages as practical for the narrowed
  trace/target/stage, compare them directly with bounded pychete probes, and
  add checkpoints until the first divergence is located before patching
  runtime pychete.
- Latest user reinforcement, 2026-06-28: every mismatch continuation/status
  must explicitly name the Matchete WolframScript or committed fixture
  checkpoint, the bounded pychete probe or fixture being compared, and the
  current suspected stage boundary. The active cadence is to keep running or
  refreshing debug WolframScripts often, dissect Matchete intermediates as far
  as needed, and only patch the first generic algorithm divergence through
  Symbolica/idenso/spenso/vakint.
- Latest user reinforcement, 2026-06-28: this paired-debug cadence is an
  acceptance gate, not only a reporting style. Whenever pychete and Matchete
  disagree, keep refreshing focused Matchete WolframScript dumps and comparing
  them with bounded pychete probes until the first differing semantic boundary
  is explicit in these notes. Runtime changes motivated by the disagreement
  should only port that generic Matchete algorithm boundary.
- Latest user reinforcement, 2026-06-28: explicitly confirm that mismatch work
  is using repeated debug WolframScripts and Matchete intermediate dissection,
  not final-coefficient guessing. For every active disagreement, keep dumping
  as many relevant Matchete stages as practical, compare those checkpoints with
  bounded pychete probes at the same semantic boundary, and record the first
  divergence before patching runtime code.
- Latest explicit confirmation, 2026-06-28: the active mismatch workflow is to
  run focused Matchete WolframScripts often, dissect their intermediate stage
  objects, and compare them against bounded pychete probes before changing
  runtime code. Progress notes should keep naming the exact Matchete
  script/fixture, the paired pychete probe, and the suspected generic
  algorithm boundary so runtime changes remain true Symbolica/idenso/spenso/
  vakint ports of Matchete algorithms.
- Latest mismatch-debugging objective, 2026-06-28: a mismatching Wilson
  coefficient is never enough information to patch runtime pychete. For each
  mismatch, add or refresh the smallest useful Matchete WolframScript dump,
  dissect the Matchete intermediates for the narrowed trace/target/order
  boundary, add the matching bounded pychete probe, and identify the first
  semantic stage where they diverge. Runtime work should then port that
  Matchete algorithmic stage through Symbolica/idenso/spenso/vakint primitives,
  not encode a coefficient-specific repair.
- Current concrete objective reminder: the active Singlet `cHD`
  EOM/on-shell frontier must keep
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` and
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json` current as
  Matchete `EOMSimplify`/`FieldRedef.m` evidence. Any runtime patch motivated
  by this frontier should first compare a refreshed Matchete dump with a
  bounded pychete probe at the same source/EOM/field-redefinition boundary.
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
- Latest paired source/path checkpoint: the pychete-side boundary fixture now
  records the Matchete quarter insertion rows from
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`
  next to pychete's path-level selected projections. The Matchete dump has
  eight target-contributing quarter insertions
  `[1, 3, 12, 14, 45, 47, 56, 58]`, while pychete has four nonzero
  Wilson-line paths `{0, 2, 24, 26}`. Paths `0`, `2`, and `26` project with
  the expected `-1/4` sign, path `24` projects with the opposite sign, and the
  aggregate remains the recorded `-1/2` pole/log weight instead of Matchete's
  `-3/2`. The next generic comparison should therefore focus on
  insertion/source coverage and scalar-vector branch signs before EOM, not on
  final-condition repair.
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
- Latest scalar-vector frontier slice: extended the development-only
  `helper_mathematica_scripts/debug_singlet_wilson_trace.wls` dump so the
  selected Singlet `cHD` debug fixtures now record Matchete's scalar-vector
  Xterm order metadata and explicit replacement values for `{H,B}`, `{B,H}`,
  `{Conj[H],B}`, `{B,Conj[H]}`, and `GaugeCTerm[B]`. The regenerated compact
  fixture keeps the first 12 detailed insertions, while the new full fixture
  records all 88 insertion replacements for the same selected prop-order-zero
  trace.
- The full Matchete insertion fixture shows that the selected four-slot
  `cHD` source has 44 nonzero detailed insertions, including 20 nonzero
  `A^2 gY^2` scalar-vector insertion variants and eight explicit `-1/4`
  quarter-insertion checkpoints. The scalar-vector Xterm replacements confirm
  that Matchete keeps both `LoopMom` and `OpenCD` branches for the
  `{H,B}`/`{B,H}` entries. This sharpens the remaining pychete mismatch:
  the selected pychete Wilson-line path projection is still green for the two
  already-known quarter paths, but the missing source families live in the
  scalar-vector Xterm/open-derivative decomposition and/or its later
  Green-basis projection, not in the committed Matchete reference source map.
- A direct runtime prototype that replaced pychete selected Wilson-line
  scalar-vector entries with a first-pass Matchete-style open-derivative
  decomposition was tested and deliberately not kept: it reduced the selected
  aggregate `cHD` coefficient to one quarter of the previous selected value,
  whereas Matchete's committed off-shell source is larger. The next
  implementation attempt should therefore compare the exact placement and
  orientation of `FuncNCM[field, OpenCD]`, `LoopMom`, and differentiated-field
  terms against pychete's `act_with_open_covariant_derivatives` semantics
  before changing runtime source generation.
- Added a fast Mathematica-independent fixture regression in
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py`
  that parses the full Matchete JSON and checks the scalar-vector Xterm
  metadata, the 20 nonzero `A^2 gY^2` insertion variants, and the eight
  quarter-insertion indices. Focused validation passed under the 30 GiB
  watchdog:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -k "matchete_fixture_records_scalar_vector_frontier or chd_four_slot" -q`
  (`5 passed, 4 deselected`), and the full selected coefficient file passed
  (`9 passed`).
- Latest OpenCD/scoped-coefficient slice: reviewed Matchete's
  `ActWithOpenCDs` boundary and `FuncNCM` flattening semantics before editing
  pychete. `act_with_open_covariant_derivatives(...)` now normalizes nested
  pychete `NCM(...)` chains before applying the bounded Symbolica replacement
  rules for open covariant derivatives. This keeps generated scalar-vector
  `FuncNCM[field, OpenCD]`-style terms visible to the OpenCD action even when
  they are embedded inside a larger Wilson-line chain.
- Added a focused CDE unit regression proving that
  `NCM(phi, NCM(chi, OpenCD(mu)), eta)` is flattened before acting and
  produces `NCM(phi, chi, D_mu eta)`, matching the relevant Matchete
  noncommutative-product behavior without adding a Python expression walker.
- The first successful selected one-loop Wilson coefficients are now also
  scoped as genuinely single-target partial integration tests. The
  `hScalar-lScalar -> cHW/cHB/cHWB` checks request and project one Wilson
  coefficient at a time, and assert the exact filtered Wilson-line source
  shape: `cHW` and `cHB` each keep one nonzero plan entry with 10 terms, while
  `cHWB` keeps two nonzero plan entries with 14 terms. The slower public
  all-three check remains as the broader route guard, but future regressions
  can now reproduce one coefficient/source-filter mismatch directly.
- Focused validation for this slice passed: `tests/unit/functional/test_cde.py
  -q` (`14 passed`); watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -q` (`9 passed`); `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  passed; and `git diff --check` passed.
- Latest scalar-vector OpenCD source slice: after comparing the committed
  Matchete `Xterm[..., 1, 1, 1]` fixture values to pychete path entries,
  pychete now generates the missing implicit Abelian scalar-vector OpenCD
  branch. The branch is derived locally from each first-order
  `DifferentialOperator(mu)` coefficient with Symbolica pattern matching and
  native `Expression.coefficient(...)`: if `C*DifferentialOperator(mu)` would
  lower to the loop-momentum branch, pychete also adds
  `-C*NCM(field, OpenCD(mu))`, matching Matchete's
  `OpenCD -> OpenCD - I LoopMom` relation. This keeps the existing loop and
  differentiated-field pieces intact.
- Focused source regressions now check both orientations of the implicit
  Abelian scalar-vector entry and assert that the selected Singlet
  `hScalar-lScalar-lVector-lScalar` zero-order source contains four generated
  terms with explicit `OpenCD` branches. A direct probe shows all four
  nonzero scalar-vector paths (`0`, `2`, `24`, and `26`) now carry OpenCD in
  their pre-Wilson numerators.
- The selected pre-heavy `cHD` coefficient remains green, and the already
  matched path-level quarter checkpoints for paths `0` and `26` still pass.
  However, once the more complete OpenCD branch is included, the old
  post-heavy/post-commutator selected `cHD` checkpoint cancels to zero under
  pychete's current bounded Green-basis normalization. This is now recorded as
  the next downstream frontier rather than hidden by the earlier
  source-incomplete checkpoint: paths `2` and `24` have source terms but still
  need broader Matchete-style Green/projection handling to contribute.
- Focused validation for this slice passed:
  `tests/integration/matching/test_fluctuation_operator.py -k
  "implicit_abelian_scalar_kinetic or four_slot_scalar_vector_trace" -q`
  (`2 passed, 112 deselected`); watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -q` (`9 passed`); `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  passed; and `git diff --check` passed.
- Latest public partial-test scoping slice: the public
  `Theory.match(...)`/`ValidationFixture.one_loop_preview_gap_report(...)`
  selected Singlet Higgs-gauge route now has per-coefficient pytest nodes for
  `cHW`, `cHB`, and `cHWB`, backed by one cached public selected-source run.
  The broad all-three public-route guard remains, but future regressions now
  identify the failing public Wilson coefficient directly without paying for
  three independent public matching runs.
- Focused validation for this slice passed under the 30 GiB watchdog:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -q` (`12 passed`). `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  also passed with no issues.
- Latest selected-`cHD` aggregate projection slice: a bounded path/stage probe
  showed that Wilson-line paths `0` and `26` still project to the expected
  quarter contribution after heavy-scalar substitution, while projecting the
  aggregate post-heavy source returned zero. The mismatch was therefore a
  target-local projection linearity/guard issue, not a physical cancellation
  in the generated selected source.
- `MatchingResult.project_matching_conditions(...)` now has a bounded
  chunked termwise exact fallback after target-local tensor canonicalization.
  If the canonicalized source is too large for the old single-pass termwise
  byte guard but still below explicit chunked term/byte caps, pychete projects
  exact coefficients in small chunks and sums them. This keeps the expensive
  global collect/factor fallback disabled while preserving linearity for
  selected Wilson-line aggregates.
- The selected Singlet
  `hScalar-lScalar-lVector-lScalar -> cHD` regression now verifies that the
  post-heavy/post-commutator aggregate selected source keeps the Matchete
  selected coefficient
  `hbar*A^2*gY^2/M^4*(log(M) - log(vakint::mursq)/2 - 1/2)`.
  Remaining full-model `cHD` parity is still a broader source/EOM coverage
  problem, not this aggregate projection bug.
- Focused validation for this slice passed:
  `tests/integration/validation/test_numeric_probes.py -k
  "canonized_sources or chunked_termwise" -q` (`2 passed`);
  watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py
  -q` (`12 passed`);
  `tests/integration/validation/test_numeric_probes.py -k "projection" -q`
  (`25 passed`); and `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  passed with no issues.
- Latest user-guidance reinforcement: the persistent goal objective and
  `AGENTS.md` now explicitly require focused Matchete debug WolframScript
  dumps for sustained Matchete/pychete disagreements whenever Mathematica is
  available. The expected workflow is to dump Matchete stages such as raw
  `EvaluateSTr`, insertion replacements, `ActWithOpenCDs`,
  `GatherLoopMomenta`, `WilsonExpand`, loop integration,
  `ContractCGs // MatchReduce // GreensSimplify`, `EOMSimplify`, and saved
  projections, compare them to bounded pychete probes at the same semantic
  boundaries, and patch the first differing generic algorithm rather than a
  final-coefficient shortcut.
- Latest selected-`cHD` path-map diagnostic: the current slice followed the
  Matchete-first debugging workflow. The Matchete full insertion and
  scalar-vector `Xterm` dumps for selected
  `hScalar-lScalar-lVector-lScalar -> cHD` were compared with bounded pychete
  probes for paths `0`, `2`, `24`, and `26`, which located the first mismatch
  before tensor reduction or final projection.
- Two generic Wilson-line source mismatches were fixed. `_MAX_OPEN_CD_CHAIN_ARITY`
  is now `16`, so `ActWithOpenCDs` reaches the longer four-slot Wilson-line
  `NCM` chains and no acted selected four-slot numerator retains formal
  `OpenCD`. The implicit Abelian scalar-vector `OpenCD` companion now follows
  Matchete's `Xterm` orientation: barred scalar atoms carry `+C`, unbarred
  scalar atoms carry `-C`.
- The selected path-map regression now records the corrected signs: paths `0`,
  `2`, and `26` project to the finite Matchete quarter coefficient after
  heavy-scalar substitution, while path `24` carries the compensating opposite
  sign. The aggregate public selected `cHD` coefficient remains
  `hbar*A^2*gY^2/M^4*(log(M) - log(vakint::mursq)/2 - 1/2)`. This is a
  selected-trace milestone; full-model `cHD` parity still needs broader
  Matchete-style source/EOM coverage beyond this trace.
- Focused validation for this slice passed:
  `tests/integration/matching/test_fluctuation_operator.py -k
  "implicit_abelian_scalar_kinetic"` (`1 passed, 113 deselected`);
  `tests/unit/functional/test_cde.py -q` (`14 passed`);
  `tests/integration/matching/test_fluctuation_operator.py -k
  "implicit_abelian_scalar_kinetic or four_slot_scalar_vector_trace"` (`2
  passed, 112 deselected`); watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "path_projection_map or public_match_selected_chd_four_slot"` (`2 passed, 11
  deselected`); watchdog-wrapped full selected Wilson coefficient file (`13
  passed`); and `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed
  with no issues.
- Latest public-route `cHD`/EOM projection slice: a focused public selected
  `cHD` probe showed that the order-zero four-slot source now generates and
  projects correctly, but vector EOM reduction does not fire there because the
  expression contains no Abelian field-strength divergence. A source-only
  order-four `hScalar-lScalar -> cHD` pychete dump then showed that registered
  target filtering keeps the field-strength candidate families, including the
  heavy-scalar-relaxed `phi + B` requirement group.
- The next mismatch was localized to the Green/IBP representative used by
  Matchete: generated order-four sources can expose undifferentiated Abelian
  field strengths multiplied by differentiated scalar currents,
  schematically `F_{nu mu} D_nu J_mu`, while the existing registered Wilson
  projection alias only handled the already-integrated form
  `J_mu D_nu F_{nu mu}`. `MatchingResult` now adds the target-local IBP alias
  `-D_nu J_mu F_{nu mu}` for registered Abelian vector EOM projections and
  computes the coefficient with the same Symbolica-backed alias projection
  path. The alias path now filters a bounded target-local candidate source and
  delegates additive alias coefficient extraction to native
  `_ProjectionCoefficientExtractor.coefficient(...)` instead of the older
  termwise additive-alias shortcut.
- `scripts/debug_pychete_singlet_wilson_trace.py` now resolves target names
  such as `cHD` to theory-registered Wilson coefficient expressions when
  available, so development dumps keep stored Wilson operator metadata and
  EOM/IBP projection aliases. Raw Warsaw operator expressions remain the
  fallback for unregistered targets.
- Added focused regressions for the registered `cHD` vector-EOM IBP alias and
  for the registered `cHD` target-filter requirement groups. This advances the
  full-model `cHD` frontier by covering the Matchete-style `F * D current`
  representative, but it is not yet a complete full Singlet on-shell match;
  remaining work is to run the larger public order-four/full-model `cHD`
  route and patch the next post-evaluation/EOM or finite Green-basis mismatch.
- Focused validation for this slice passed:
  `tests/integration/validation/test_numeric_probes.py -k
  "abelian_gauge_eom"` (`2 passed, 61 deselected`);
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "registered_chd_filter_requirements"` (`1 passed, 13 deselected`);
  `tests/integration/validation/test_numeric_probes.py -k "projection"` (`26
  passed, 37 deselected`); watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -q`
  (`14 passed`); and `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  passed with no issues.
- Latest user reinforcement: continue running focused debug WolframScripts and
  dissecting Matchete intermediate stages whenever a Matchete/pychete mismatch
  appears. Future mismatch entries must identify the Matchete dump, the paired
  pychete probe, and the first differing generic algorithm boundary before a
  pychete fix is accepted.
- Latest confirmation: this remains the active debugging workflow for the
  current Singlet `cHD` frontier. New mismatch progress reports should name
  the exact Matchete stage dump/checkpoint and bounded pychete probe compared,
  so the next fixes keep following Matchete algorithms ported through
  Symbolica/idenso/spenso/vakint rather than final-coefficient guesses.
- Latest full-public `cHD` performance slice: the current comparison reused
  the committed Matchete checkpoints
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`,
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`, and the saved
  `Singlet_Scalar_Extension.matching_fixture.json` condition. The paired
  watchdog-wrapped pychete probe ran the full generated order-zero Wilson-line
  public route for registered `cHD` with the internal non-minimal backend,
  heavy-scalar substitution, target filtering, and `mubar2`/`epsilon`
  symbols.
- Found the first practical blocker in that full public route before any new
  Matchete algorithm patch: the heavy-scalar substitution stage expanded one
  scalar-only source from 16 terms to 62,584 terms before Green/projection.
  `heavy_scalar_solution_replacements(...)` now accepts `max_order`, powered
  heavy-field replacements respect summed solution order, and
  `replace_heavy_scalar_solutions_eft_limited(...)` chooses a conservative
  per-term cap from the requested EFT order while still delegating the actual
  rewrite to Symbolica `replace_multiple(...)`. Public `Theory.match(...)`
  uses this bounded path when matching targets are projected with EFT
  truncation, and it also updates staged on-shell projection sources.
- The full public internal `cHD` probe now completes. It generates 32
  Wilson-line terms over 64 planned entries and records
  `heavy_scalar_solution_eft_limited=True`. The remaining mismatch is now
  exposed cleanly: after factoring out `hbar*A^2*gY^2/M^4`, pychete gives
  `-1/(2 epsilon) - 1/2 - 1/2 log(mubar2) + log(M)`, while the Matchete
  reference gives
  `-5/(3 epsilon) - 31/18 - 5/3 log(mubar2/M^2)`. The next slice should
  compare Matchete source/EOMSimplify/field-redefinition stages against
  target-local pychete probes for the missing `-7/(6 epsilon)` and associated
  finite/log pieces, not revisit the heavy-scalar substitution performance
  issue.
- Focused validation for this slice passed:
  `tests/integration/matching/test_heavy_scalar_tree.py -q` (`23 passed`);
  watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "public_match_selected_chd_four_slot_wilson_coefficient" -q` (`1 passed, 13
  deselected`); and `PYTHONPATH=src dependencies/.venv/bin/python -m mypy`
  passed with no issues. `git diff --check` and `py_compile` for the touched
  Python modules also passed.
- Latest user reminder recorded again: the active mismatch workflow is to keep
  running focused debug WolframScripts and dissecting Matchete intermediate
  results, not to infer fixes from final Wilson coefficients. For the current
  Singlet `cHD` frontier, the next comparisons should name the refreshed
  Matchete dump/checkpoint, the paired bounded pychete probe, and the first
  stage boundary that differs before any pychete algorithm patch is made.
- Latest `cHD` boundary probe: refreshed the pychete public generated-source
  check against the committed Matchete `cHD` insertion/EOM fixtures. The
  watchdog-wrapped pychete probe for the full generated order-zero Wilson-line
  public route still projects
  `-1/(2 epsilon) - 1/2 - 1/2 log(mubar2/M^2)`, and its post-heavy source has
  zero differentiated `FieldStrength(B, ..., {nu})` atoms, so pychete derives
  zero Abelian vector EOM replacement rules and zero field-redefinition delta.
  Turning on Wilson-line commutator emission/expansion for the same probe did
  not change this. By contrast, the converted Matchete reference off-shell
  source contains differentiated `FieldStrength(B)` and `FieldStrength(W)`
  atoms, produces one Abelian vector EOM rule, and has a nonzero vector
  field-redefinition delta. The first current semantic gap is therefore
  Wilson-line Green/commutator source exposure into Matchete's
  field-strength-divergence/current representative, not a final projection or
  EOM-rule plumbing bug.
- Added a focused Matchete fixture regression on the new
  `validation_simplified_target_coefficient_input_form` fields emitted by
  `helper_mathematica_scripts/debug_singlet_wilson_trace.wls`: the full
  four-slot `cHD` dump records eight insertion-level `GetOperatorCoefficient`
  quarter checkpoints at insertion indices `1, 3, 12, 14, 45, 47, 56, 58`,
  while the selected prop-order aggregate coefficient remains `$Failed` in
  Matchete's direct debug script. This keeps the next source-generation patch
  tied to Matchete insertion-level evidence.
- Focused validation for this documentation/debug-fixture slice passed:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "matchete_fixture_records_scalar_vector_frontier"` (`1 passed, 13
  deselected`); watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "matchete_fixture_records_scalar_vector_frontier or quarter_paths"` (`3
  passed, 11 deselected`); and `git diff --check` passed.
- Latest Matchete-mismatch checklist for the scalar Green source-exposure
  slice: the Matchete evidence is the committed
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`
  insertion dump plus `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`
  showing differentiated field-strength representatives and vector-EOM
  machinery. The paired bounded pychete probes were
  `/tmp/probe_singlet_chd_source_structure.py`,
  `/tmp/probe_singlet_chd_derivative_terms.py`, and
  `/tmp/probe_singlet_chd_eom_boundary_safe.py`. The first semantic boundary
  was source exposure after Wilson-line/integral evaluation and scalar Green
  representative selection: pychete had three-plus-one scalar derivative
  bilinears but did not lower them into Matchete's
  `J_mu D_nu F_{nu mu}`/`F_{nu mu} D_nu J_mu` family.
- Implemented the generic part of that boundary in
  `expose_scalar_derivative_commutator_bilinears(...)`: bounded
  three-plus-one scalar derivative monomials are now sent through the existing
  Symbolica-backed Green normal-form/commutator exposure path rather than a
  coefficient-specific repair. A watchdog rerun of
  `/tmp/probe_singlet_chd_eom_boundary_safe.py` now shows two differentiated
  Abelian `FieldStrength(B)` atoms and two vector EOM rules in the full
  generated public `cHD` source. The public projected coefficient is still the
  previous `-1/2` pole/log result, and applying the current vector
  field-redefinition delta naively produces an `A*muphi` contribution, so the
  next mismatch boundary is the larger Matchete-style source scoping and
  EOM/field-redefinition ordering, not this local Green exposure itself.
- Focused validation for this slice passed:
  `tests/unit/functional/test_scalar_green_bilinears.py -q` (`22 passed`);
  watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "public_match_selected_chd_four_slot_wilson_coefficient or selected_chd_four_slot_wilson_coefficient" -q`
  (`2 passed, 12 deselected`); `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` passed; and `git diff --check`
  passed.
- Latest user reminder captured for the active objective: while the selected
  `cHD` public coefficient still disagrees with Matchete, the next
  implementation slices must continue the Matchete-first debug loop. The
  immediate comparisons should use the committed
  `singlet_hScalar_lScalar_lVector_lScalar_cHD` insertion dumps plus any
  refreshed focused WolframScript checkpoints needed to compare
  source-generation, Wilson expansion, loop integration, Green simplification,
  EOM/field-redefinition, and projection boundaries against bounded pychete
  probes.
- Latest Matchete EOMSimplify checkpoint: refreshed
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` and
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json` so the dump now
  records ``Matchete`PackageScope`FieldsToShift[offShell]``. For the saved
  Singlet off-shell result Matchete reports
  `{{d, 4}, {e, 4}, {H, 4}, {l, 4}, {q, 4}, {u, 4}}`, i.e. the systematic
  field-redefinition frontier includes the Higgs and fermion matter fields but
  does not list the Abelian vector `B` as a field-to-shift at this checkpoint.
  This is important for the next `cHD` slice: pychete's bounded vector-EOM
  replacement/delta helper remains useful for the committed off-shell
  reference, but the full generated-source mismatch should now be treated as a
  missing Matchete-style matter-field redefinition/source-scoping algorithm,
  not as a naive reorder of the vector-only EOM pass.
- Bounded pychete probes paired with that Matchete checkpoint:
  `/tmp/probe_singlet_chd_public_eom_after_patch.py` confirms the public route
  currently applies zero EOM rules because scalar commutator-bilinear exposure
  happens after the EOM pass, while `/tmp/probe_singlet_chd_eom_boundary_safe.py`
  confirms the exposed aggregate source has two differentiated Abelian
  field-strength atoms and two vector EOM rules. Applying the current bounded
  vector companion naively projects an `A*muphi*gY^2` family, not Matchete's
  saved `A^2*gY^2` on-shell `cHD` delta. The first semantic boundary is
  therefore EOMSimplify/source-scoped field redefinitions after Greens
  simplification, not a final-coefficient normalization issue.
- Runtime projection fix from the same checklist: registered-Wilson Abelian
  vector-EOM projection aliases are now scoped to on-shell projection sources
  (`on_shell_eft_lagrangian`, loop-only on-shell, or tree-level on-shell).
  They remain available to Wilson-line target filtering as conservative
  requirements, but explicit off-shell projections and source-map diagnostics
  no longer absorb EOM/on-shell aliases. This restores the committed Matchete
  off-shell `cHD` coefficient while keeping on-shell alias coverage for
  generated or reduced on-shell sources.
- Focused validation for this slice passed:
  watchdog-wrapped
  `tests/integration/validation/test_validation_fixtures.py -k
  "reference_chd_records or fields_to_shift or
  reference_chd_vector_eom_field_redefinition" -q` (`3 passed`);
  watchdog-wrapped
  `tests/integration/validation/test_validation_fixtures.py -k
  "singlet_reference_chd" -q` (`4 passed, 50 deselected`);
  watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "chd_four_slot or higgs_gauge" -q` (`13 passed, 1 deselected`);
  watchdog-wrapped
  `tests/integration/validation/test_numeric_probes.py -k
  "on_shell_scoped or gauge_eom_current_alias or gauge_eom_ibp_alias" -q`
  (`3 passed, 61 deselected`); `PYTHONPATH=src
  dependencies/.venv/bin/python -m mypy` passed; and `git diff --check`
  passed.
- Latest debug-fixture refinement: the Singlet `cHD` EOMSimplify
  WolframScript now qualifies package-scope Matchete symbols when reproducing
  `FieldRedef.m` internals, including ``Matchete`PackageScope`EoM``,
  ``Matchete`PackageScope`Operator``,
  ``Matchete`PackageScope`TermsToList``, and
  ``Matchete`PackageScope`$FieldAssociation``. Without those qualifications
  the script can create inert lookalike symbols and report misleading EOM
  counts. The regenerated JSON fixture now records six prepared EOM terms with
  field labels `{d, e, l, q, u, H}` and a Higgs `ScalarShift` checkpoint with
  one Higgs EOM term. This confirms the next generic frontier is systematic
  matter-field redefinition/source scoping, especially the Higgs/matter path,
  not a final `cHD` coefficient patch.
- Latest Matchete replay boundary: extended the same debug fixture to replay
  private `FieldRedef.m` stages on two saved Matchete artifacts, the saved
  `Off-shell EFT Lagrangian` and the sum of saved simplified `SuperTraces`.
  For both inputs, `RenormalizeMatterFields`, `GaugeFieldNormalization`, and
  every `ShiftLagrangian` loop through dimension six leave the registered
  `cHD` projection unchanged from the off-shell coefficient. This is now a
  committed Mathematica-independent checkpoint:
  `field_redefinition_replay_off_shell` and
  `field_redefinition_replay_supertrace_sum` both have zero
  `delta_from_off_shell_input_form` at every recorded stage. Therefore the
  saved Matchete on-shell `cHD` delta is generated from the original
  unsimplified `LagrangianEFT` boundary used by
  `EOMSimplify[LagrangianEFT, ...]`, not by replaying field shifts on saved
  Greens-simplified artifacts. The next Matchete dump should capture that raw
  `LagrangianEFT`/`EOMSimplify` entry boundary, likely by rerunning the
  validation-mode `Match` path or by adding a focused raw full-source exporter,
  before any runtime scalar/fermion field-redefinition patch is accepted.
- Latest raw `EOMSimplify` boundary checkpoint: extended
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` and regenerated
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json` with
  `raw_lagrangian_eft_eom_boundary`. The dump reconstructs Matchete's raw
  validation source as
  ``RelabelIndices[PackageScope`ReplaceHeavyEOM[lag]] + PackageScope`LoopMatch``
  followed by ``ContractCGs // PackageScope`MatchReduce``. For the registered
  `cHD` projection, this raw source differs from both saved off-shell and saved
  on-shell results; ``PackageScope`InternalSimplify`` maps it exactly to the
  saved off-shell coefficient; ``FieldRedef`PackagePrivate`PerformSystematicFieldRedefs``
  maps the internal-simplified source exactly to the saved on-shell coefficient;
  and both subsequent `GreensSimplify` and direct `EOMSimplify` stay on the
  saved on-shell coefficient. The first generic runtime boundary is therefore
  not the saved-artifact replay path but the unsimplified-source
  `InternalSimplify` plus systematic field-redefinition route.
- Mismatch checklist for the next runtime patch: Matchete dump is
  `debug_singlet_eom_simplify.wls` / `singlet_eom_cHD.debug.json`
  `raw_lagrangian_eft_eom_boundary`; the paired pychete probe still needs to
  compare pychete's generated pre-EOM source against this raw/internal/on-shell
  sequence; the first differing boundary to investigate is pychete's generated
  full source plus Green/internal simplification before matter-field
  redefinitions, not final Wilson projection.
- Latest paired pychete boundary probe: added
  `scripts/debug_pychete_singlet_eom_boundary.py` and generated
  `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`.
  This is the pychete-side counterpart to the Matchete dumps
  `singlet_eom_cHD.debug.json` and
  `singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`.
  It uses the same lower-level selected Wilson-line path as the existing
  partial `cHD` tests, projects the unrenormalized normalized source, pole,
  finite, post-Green, post-heavy, and post-heavy-Green stages, and records the
  committed Matchete off-shell/on-shell coefficients in the same artifact.
- Boundary result: the Matchete selected trace/off-shell checkpoint and the
  Matchete `EOMSimplify` off-shell coefficient agree exactly:
  `-1/4*hbar*A^2*gY^2*(6+5 eps+6 eps log(mu^2/M^2))/(eps*M^4)`.
  After the scalar-vector X-term sign correction, the pychete selected
  normalized unrenormalized source has the `-1` pole/log weight, and the
  post-Green/post-heavy stages leave that projection unchanged. Therefore the
  first current divergence remains
  `selected_wilson_line_source_or_green_projection_before_eom`, not the
  systematic `FieldRedef.m` stage. The next runtime patch should return to
  Matchete's selected insertion/Xterm/WilsonExpand/GreensSimplify behavior for
  this trace and explain why the missing effective two-quarter contribution is
  a generic Wilson-line source/Green-basis or component-index-delta issue
  before attempting new EOM-field-redefinition code.
- Latest scalar-vector sign checkpoint: the paired Matchete dump
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`
  exposes scalar-vector `Xterm` values for `{H,B}`, `{B,H}`,
  `{Conj[H],B}`, and `{B,Conj[H]}`. Comparing those values with the bounded
  pychete `FluctuationOperator.differential_entry(...)` probe showed the first
  generic disagreement in implicit Abelian scalar-vector derivative/OpenCD
  signs. pychete now flips only the one-derivative scalar atoms discovered by
  Symbolica field-pattern matches and uses Matchete's uniform OpenCD sign.
  The regenerated pychete boundary fixture records four nonzero paths
  `0`, `2`, `24`, and `26`, all projecting with the Matchete `-1/4` sign; the
  remaining `cHD` source mismatch is missing path/component coverage before
  EOM, not a path-sign issue.
- The paired bounded pychete source probe
  `assets/validation/pychete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.pychete.source.debug.json`
  was committed as source-only evidence for the same narrowed trace/target.
  At that earlier checkpoint it recorded the target-filtered
  `hScalar-lScalar-lVector-lScalar#wilson0_o0_0_0_0` entry with four terms
  through preaction, prefinal, and runtime-internal checkpoints without
  executing Mathematica at pytest time; the latest indexed-functional-
  derivative checkpoint below supersedes that count with eight terms.
- Latest indexed-functional-derivative checkpoint: the current paired Matchete
  evidence remains
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json`,
  whose eight target-contributing insertion checkpoints all project with
  `-1/4`, and the paired pychete probes are
  `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`,
  `assets/validation/pychete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.pychete.source.debug.json`,
  and the unfiltered source fixture
  `assets/validation/pychete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.pychete.unfiltered.source.debug.json`.
  The first generic runtime mismatch was component-index functional variation:
  converted Singlet interaction terms used one representative Higgs component,
  while the fluctuation basis contains all component slots. pychete now keeps
  exact Symbolica functional variation first, then uses a bounded
  Symbolica-pattern indexed fallback for same-label field atoms and contracts
  the resulting variation deltas through the idenso bridge. This recovers the
  additional paths `12`, `14`, `36`, and `38`.
- Updated status for the same cHD boundary: pychete now has eight nonzero
  Wilson-line paths `{0, 2, 12, 14, 24, 26, 36, 38}`, and every path projects
  with the Matchete `-1/4` insertion sign. The filtered and unfiltered pychete
  source fixtures both record eight zero-order terms, so target filtering is
  not the current source of disagreement. The selected prop-order-zero
  pychete aggregate has the `-2` pole/log weight, while Matchete's saved
  selected trace/off-shell checkpoint still has `-3/2` and the current dump's
  prop-order aggregate fields are `$Failed`/`$Aborted`. The next first-boundary
  comparison must therefore dump or reconstruct Matchete's reduction from
  insertion checkpoints/raw selected prop-order data to the saved validation
  trace, not patch EOM or final `cHD` conditions.
- Latest user reinforcement, 2026-06-28, is confirmed as the active workflow:
  continue running or refreshing focused debug WolframScripts, dissect
  Matchete intermediate stages as deeply as needed, compare them against
  bounded pychete probes at matching semantic boundaries, and patch only the
  first generic Matchete algorithm divergence through Symbolica/idenso/spenso
  or vakint. Every future mismatch-status note should name the Matchete dump,
  the paired pychete probe, and the current suspected boundary explicitly.
- Focused validation for this indexed-variation/source-boundary slice passed:
  `tests/unit/functional/test_scalar_eom.py -k functional_derivative -q`
  (`5 passed, 19 deselected`); watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "chd_four_slot or pychete_boundary_fixture or pychete_source_fixture" -q`
  (`10 passed, 8 deselected`); `python -m py_compile
  scripts/debug_pychete_singlet_eom_boundary.py`; `python -m mypy`; and
  `git diff --check`.
- Latest selected cHD propagation-order checkpoint: refreshed Matchete-side
  evidence with `helper_mathematica_scripts/debug_singlet_wilson_trace.wls`
  for
  `hScalar-lScalar-lVector-lScalar -> cHD` at propagation orders 1 and 2,
  committed as
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop1.debug.json`
  and
  `assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop2.debug.json`.
  Those dumps show the saved selected trace/off-shell coefficient is the sum
  of propagation orders 0, 1, and 2, not only prop-order zero: prop-order zero
  gives the `-2` pole/log weight, prop-order one gives `+1`, and prop-order
  two gives `-1/2`, totaling Matchete's `-3/2` pole/log weight.
- Paired pychete probes for the same trace/target/propagation-order boundary
  exposed two generic stage differences. First, total-order-one pychete terms
  vanished because Wilson-line loop-symmetry pruning counted only the
  propagator-expansion loop-momentum metadata and missed loop-rank information
  still represented as uncontracted `DifferentialOperator(...)` Xterm slots.
  The runtime fix now applies the Matchete symmetry rule term-by-term using
  Symbolica `matches`/`match` over explicit `LoopMomentum(...)` and
  `DifferentialOperator(...)` atoms. Second, total-order-two reached the right
  pole/log structure but kept closed `Metric(mu,mu)` traces formal; replacing
  those traces by `d = 4 - 2*epsilon` before finite Laurent extraction gives
  the required epsilon-times-pole finite shift and matches Matchete's
  prop-order-two constant.
- Current cHD selected-trace status: pychete now matches Matchete's selected
  four-slot Wilson-line finite projections for propagation/total orders 0, 1,
  and 2 individually. The remaining full one-loop-matching frontier is no
  longer this selected-trace aggregation boundary; it shifts back to broader
  selected-source coverage, Green/EOM/on-shell reduction, and eventually full
  Singlet model matching-condition parity.
- Focused validation for this propagation-order slice passed:
  `tests/unit/functional/test_loop_integration.py -q` (`12 passed`);
  `tests/integration/matching/test_fluctuation_operator.py -k
  "open_differential_operator_loop_rank or
  loop_momentum_symmetry_cleanup_preserves_backend_numerators" -q`
  (`1 passed, 114 deselected`); watchdog-wrapped
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_selected_chd_four_slot_prop_order_one_two_match_matchete_dumps
  -q` (`1 passed`); watchdog-wrapped `pytest -m "not slow"
  tests/integration/matching/test_singlet_selected_wilson_coefficients.py -q`
  (`13 passed, 6 deselected`); `python -m mypy`; and `python -m py_compile`
  on the touched source/test files.
- Latest cHD boundary-fixture refresh: `scripts/debug_pychete_singlet_eom_boundary.py`
  now defaults to the selected Wilson-line plan with `max_total_order=2` and
  `max_slot_order=2`, splits generation/evaluation by total order, and
  projects order-local chunks before summing coefficients. This avoids the
  large aggregate projection cost while preserving the Matchete
  propagation-order comparison. The regenerated
  `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`
  records `term_counts_by_total_order = {0: 8, 1: 24, 2: 72}` and pole
  projections `-2 + 1 - 1/2 = -3/2`, matching the Matchete selected
  trace/off-shell checkpoint.
- Current first boundary after this refresh: selected four-slot
  `hScalar-lScalar-lVector-lScalar -> cHD` trace generation and evaluation is
  no longer the mismatch. The pychete selected trace matches Matchete's
  off-shell coefficient; Matchete's on-shell checkpoint still shifts the
  coefficient from `-3/2` to `-5/3` in the pole/log weight. The next runtime
  slice should therefore compare the full pychete pre-EOM source against the
  Matchete `raw_lagrangian_eft_eom_boundary` sequence in
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`, especially
  `InternalSimplify` and `PerformSystematicFieldRedefs`, before adding any
  on-shell field-redefinition code.
- Latest Matchete EOM dissection, 2026-06-28: refreshed
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` and
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json` with the
  internal-simplified source's shift preparation, Higgs `ScalarShift` summary,
  and a replay of `PerformSystematicFieldRedefs` starting from that internal
  source. The paired pychete checkpoint remains
  `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`, which
  matches the selected off-shell trace. The first narrowed Matchete on-shell
  boundary is now `after_shift_dim6_dev3`: matter renormalization and shifts
  through `after_shift_dim6_dev4` leave `cHD` unchanged, while
  `after_shift_dim6_dev3` produces the full off-shell-to-on-shell delta
  proportional to
  `-1/36*hbar*A^2*gY^2*(6 + 17 epsilon + 6 epsilon log)/(epsilon*M^4)`.
  The internal source exposes 105 EOM terms with field labels
  `{H, B, d, e, u, l, q, W}`, and the Higgs scalar shift has 105
  Higgs-containing EOM terms. The next runtime implementation should therefore
  port the generic Matchete scalar/matter `DetermineShifts`/`ScalarShift` and
  source-scoped `ShiftLagrangian` machinery for this dimension-6,
  three-derivative boundary, not add a coefficient-specific projection alias.
- Focused validation for the refreshed Matchete EOM dump passed:
  `dependencies/.venv/bin/python -m pytest
  tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_singlet_chd_matchete_eom_dump_records_dim6_dev3_shift_boundary
  -q` (`1 passed`).
- Latest formal-EOM scalar field-redefinition slice: added
  `scalar_eom_field_redefinition_delta(...)` and
  `Theory.scalar_eom_field_redefinition_delta(...)` as the first bounded
  pychete consumer for Matchete-style explicit `EOM(Field(...))` /
  `EOM(Bar(Field(...)))` terms. The helper discovers light scalar formal-EOM
  atoms with Symbolica patterns, extracts Matchete-style complex scalar shifts
  with native `Expression.coefficient(...)`, applies the source-scoped shift
  through pychete's Symbolica-backed `derive_eom(...)`, and can restrict the
  shifted source by EFT order via `series_eft(...)`. This intentionally does
  not yet expose hidden EOM terms from derivative operators; the next runtime
  frontier is a Matchete-like Green/InternalSimplify exposure stage that
  rewrites pychete's current derivative-source form into explicit formal EOM
  atoms before this consumer can reproduce the Singlet `cHD`
  `after_shift_dim6_dev3` boundary.
- Focused validation for the formal scalar-EOM consumer passed:
  `tests/unit/functional/test_scalar_eom.py -k
  "scalar_eom_field_redefinition_delta" -q` (`2 passed, 24 deselected`);
  `tests/unit/definitions/test_public_api.py -q` (`8 passed`); targeted mypy
  on `src/pychete/functional.py`, `src/pychete/theory.py`,
  `tests/unit/functional/test_scalar_eom.py`, and
  `tests/unit/definitions/test_public_api.py` (`Success: no issues found`).
- Current formal-EOM exposure slice: added `scalar_eom_identities(...)` as the
  bounded Matchete `InternalSimplify`-style scalar Laplacian exposure source,
  extended `scalar_derivative_green_normal_form(..., include_eom=True,
  eom_lagrangian=...)`, and wired the opt-in
  `OneLoopMatchOptions.wilson_line_expose_scalar_eom_terms` through public
  matching and validation preview/gap-report options. The implementation keeps
  atom discovery and coefficient extraction in Symbolica patterns and native
  `Expression.coefficient(...)`, then exposes explicit `EOM(Field(...))` /
  `EOM(Bar(Field(...)))` atoms for the existing field-redefinition consumer.
  This slice is paired to the Matchete checkpoint
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` /
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json` and the
  bounded pychete probes in
  `tests/unit/functional/test_scalar_green_bilinears.py`. It does not yet
  claim full Singlet `cHD` on-shell parity; the next probe must apply the
  exposure plus `scalar_eom_field_redefinition_delta(...)` to the full pychete
  pre-EOM source and compare stage-by-stage with Matchete
  `after_shift_dim6_dev3`.
- Latest user reinforcement, 2026-06-28, has been copied into `AGENTS.md` and
  remains active here: when pychete disagrees with Matchete, keep running or
  refreshing focused debug WolframScripts, dump as many relevant Matchete
  intermediate stages as practical, compare them to bounded pychete probes at
  the same stage, and only patch the first generic algorithm boundary.
- Focused validation for the formal-EOM exposure slice passed:
  `tests/unit/functional/test_scalar_eom.py`,
  `tests/unit/functional/test_scalar_green_bilinears.py`,
  `tests/unit/definitions/test_public_api.py`, and the two targeted
  validation-fixture option plumbing tests (`62 passed`);
  `tests/test_static_typing.py -m typing` (`1 passed`); source mypy on
  `src/pychete/functional.py`, `src/pychete/matching.py`,
  `src/pychete/matching_options.py`, `src/pychete/validation_fixtures.py`,
  and `src/pychete/api.py` (`Success: no issues found`); and
  `git diff --check`.
- Current Singlet `cHD` paired-debug update: the Matchete checkpoint remains
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` /
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`, especially
  the `raw_lagrangian_eft_eom_boundary` replay where
  `after_shift_dim6_dev3` creates the on-shell delta. The paired pychete
  checkpoint `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`
  now records an explicit EOM-exposure probe over the selected
  `hScalar-lScalar-lVector-lScalar` entries after pole+finite extraction:
  10 selected entries, zero field-strength atoms, zero Abelian
  field-strength-divergence targets, zero nonzero vector field-redefinition
  deltas, and 28 scalar Laplacian EOM identities in the higher-derivative
  entries. This narrows the first current mismatch to the
  representative-conversion boundary before field redefinition: Matchete's
  `InternalSimplify` exposes EOM-proportional structures feeding
  `PerformSystematicFieldRedefs`, while pychete's selected source still sits
  in scalar-derivative representatives that project to `cHD` but do not expose
  the Abelian vector-EOM normal form. The next runtime slice should port that
  generic Green/InternalSimplify representative conversion, not add a direct
  `cHD` coefficient patch.
- Focused validation for this boundary-probe checkpoint passed:
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py -k
  "matchete_eom_dump_records_dim6_dev3_shift_boundary or
  pychete_boundary_fixture_records_pre_eom_gap" -q` (`2 passed, 18
  deselected`); `python -m py_compile
  scripts/debug_pychete_singlet_eom_boundary.py`; and `git diff --check`.
- Current paired-debug confirmation, 2026-06-28: the active Matchete
  checkpoint is still
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` /
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`, especially
  the `raw_lagrangian_eft_eom_boundary` replay through
  `PerformSystematicFieldRedefs` where `after_shift_dim6_dev3` first changes
  the `cHD` projection. The paired pychete probe is
  `scripts/debug_pychete_singlet_eom_boundary.py` writing
  `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json`.
  This slice added `expose_abelian_vector_eom_currents(...)` /
  `Theory.expose_abelian_vector_eom_currents(...)`, a bounded generic helper
  that discovers charged scalar first-derivative currents with Symbolica
  patterns and exposes exact Abelian vector-EOM current-current products to
  field-strength-divergence representatives using direct
  `Expression.coefficient(...)` first and pychete's existing
  Symbolica-backed projection extractor for expanded composite factors.
- The refreshed Singlet `cHD` pychete debug fixture now records the helper's
  negative result explicitly: across the 10 selected
  `hScalar-lScalar-lVector-lScalar` entries, exact Abelian current-current
  exposure still produces zero vector-EOM field-strength divergences and zero
  nonzero vector field-redefinition deltas. This is useful narrowing evidence:
  the first mismatch is not a simple inverse Abelian vector-EOM current product
  hiding in pychete's selected source. The remaining generic frontier is still
  Matchete's broader `InternalSimplify`/Green representative conversion and
  scalar/matter shift preparation before `PerformSystematicFieldRedefs`.
- Focused validation for the current current-exposure slice passed:
  `tests/unit/functional/test_scalar_eom.py` plus
  `tests/integration/matching/test_singlet_selected_wilson_coefficients.py::test_selected_chd_pychete_boundary_fixture_records_pre_eom_gap`
  (`28 passed` total); `python -m py_compile
  scripts/debug_pychete_singlet_eom_boundary.py src/pychete/functional.py
  src/pychete/theory.py src/pychete/api.py`;
  `tests/unit/definitions/test_public_api.py -q` (`9 passed`);
  targeted mypy on `src/pychete/functional.py`, `src/pychete/theory.py`,
  `src/pychete/api.py`, `tests/unit/functional/test_scalar_eom.py`, and
  `scripts/debug_pychete_singlet_eom_boundary.py` (`Success: no issues
  found`); and `git diff --check`.
- Current Matchete `FieldRedef` control-structure slice, 2026-06-28: the
  active Matchete checkpoint remains
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` /
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`, with the
  relevant algorithm read directly from
  `Mathematica_reference/Matchete/Package/FieldRedef.m`:
  `PerformSystematicFieldRedefs` loops over `eftOrd = 5..maxOrder` and
  descending derivative counts, `ShiftLagrangian` selects terms with
  `SelectOperatorDevsAndDim[lag, devs, dim]`, and scalar terms are consumed by
  `ScalarShift`. The paired pychete boundary is the existing formal-EOM
  consumer in `src/pychete/functional.py`.
- Implemented the bounded pychete port of that consumer-side control
  structure for already-exposed formal scalar EOM terms:
  `operator_dimension(...)` now assigns formal `EOM(Field(...))` atoms
  Matchete-compatible dimensions; `operator_derivative_count(...)` uses
  Symbolica marker replacements to count scalar EOMs as two derivatives,
  fermion/vector EOMs as one, field strengths as one plus derivative slots,
  and fields by derivative-slot length; `select_terms_by_dimension_and_derivatives(...)`
  selects the Matchete `(devs, dim)` slice; and
  `systematic_scalar_eom_field_redefinition_delta(...)` loops through the
  Matchete `eftOrd`/`devs` order before delegating each selected scalar formal
  EOM slice to `scalar_eom_field_redefinition_delta(...)`. These helpers are
  exposed through `pychete.api` and matching `Theory` methods.
- This slice does not claim to close the Singlet `cHD` mismatch. It ports the
  consumer side once formal EOM terms exist. The first active divergence is
  still upstream: Matchete `InternalSimplify`/Green representative conversion
  exposes the formal EOM terms that feed the `after_shift_dim6_dev3` scalar
  shift, while pychete's selected source currently has only the bounded scalar
  Laplacian identity exposure recorded in the paired pychete debug fixture.
- Focused validation for this `FieldRedef` control-structure slice passed:
  `tests/unit/functional/test_scalar_eom.py -q` (`29 passed`);
  `tests/unit/definitions/test_public_api.py -q` (`9 passed`);
  `tests/unit/eft/test_eft_counting.py -q` (`7 passed`);
  `python -m py_compile src/pychete/eft.py src/pychete/functional.py
  src/pychete/theory.py src/pychete/api.py tests/unit/functional/test_scalar_eom.py
  tests/unit/definitions/test_public_api.py`; targeted mypy on the same
  source/test files (`Success: no issues found`); and `git diff --check`.
- Current Matchete `EoMSplitter` identity slice, 2026-06-28: the relevant
  Matchete algorithm is the EOM branch of `IdentitiesIBP` in
  `Mathematica_reference/Matchete/Package/Simplifications.m`, where
  `EoMSplitter[mu, Field[..., Scalar, ...]]` returns `CD[mu, field]` and the
  total derivative `CD[mu, ...]` is added as a Green-basis identity. The paired
  pychete boundary is `scalar_derivative_green_normal_form(...,
  include_eom=True)` in `src/pychete/functional.py`.
- Implemented `scalar_formal_eom_ibp_identities(...)`, exported it through
  `pychete.api`, and wired it into the scalar Green identity source whenever
  EOM identities are enabled. The helper discovers formal scalar EOM atoms
  with Symbolica tag-restricted patterns, replaces one such atom by the scalar
  splitter `apply_cd([mu], field)`, and builds the total-derivative identity
  through pychete's existing Symbolica-backed `apply_cd(...)`. This is the
  scalar-only Matchete `EoMSplitter` subset; fermion/vector EOM splitter
  support remains future idenso/spenso-backed work.
- Tightened `systematic_scalar_eom_field_redefinition_delta(...)` so the
  formal EOM terms that define the shift may be supplied separately from the
  lower-order source Lagrangian being shifted. This mirrors the Matchete
  `ShiftLagrangian` distinction and matters for selected one-loop traces,
  whose high-order EOM terms do not themselves contain the light kinetic/free
  source terms that get shifted.
- This slice still does not close Singlet `cHD`: it adds the scalar
  EOM-splitter identity and source/shift separation needed downstream once
  `InternalSimplify`/Green representative exposure has produced the formal EOM
  terms. The active first divergence remains the upstream Matchete
  `InternalSimplify` exposure from the selected pychete scalar-derivative
  representatives to the 105 formal EOM terms recorded in
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`.
- Focused validation for this scalar `EoMSplitter` slice passed:
  `tests/unit/functional/test_scalar_green_bilinears.py
  tests/unit/functional/test_scalar_eom.py tests/unit/definitions/test_public_api.py
  -q` (`65 passed`); `python -m py_compile src/pychete/functional.py
  src/pychete/theory.py src/pychete/api.py
  tests/unit/functional/test_scalar_green_bilinears.py
  tests/unit/functional/test_scalar_eom.py
  tests/unit/definitions/test_public_api.py`; targeted mypy on the same
  source/test files (`Success: no issues found`); and `git diff --check`.
- Current Wilson-line scalar EOM finalization slice, 2026-06-28: the
  Matchete checkpoint remains
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` /
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`, especially
  `raw_lagrangian_eft_eom_boundary.internal_field_redefinition_replay` where
  `after_shift_dim6_dev3` is the first nonzero scalar shift. The paired
  pychete boundary is the Wilson-line scalar EOM exposure option plus
  `systematic_scalar_eom_field_redefinition_delta(...)`.
- Implemented the generic Wilson-line finalization wiring for that consumer:
  when `wilson_line_expose_scalar_eom_terms=True`, pychete first runs the
  existing scalar Green/EOM exposure pass, then computes the bounded scalar
  `PerformSystematicFieldRedefs` delta with the configured
  `on_shell_eom_lagrangian` as lower-order source and the exposed Wilson-line
  expression as `eom_terms_lagrangian`. The result supertraces now record the
  exposed source, the scalar EOM field-redefinition delta, and the after-shift
  expression for stage-by-stage Matchete comparison. Validation previews use
  the same helper, so fixture gap probes follow the public matching path.
- This still does not close the Singlet `cHD` mismatch by itself: the active
  first divergence remains upstream formal-EOM exposure. The new wiring means
  that once the selected Wilson-line source exposes the same formal scalar EOM
  terms as Matchete `InternalSimplify`, pychete will immediately apply the
  already-tested scalar `FieldRedef` consumer and record the comparison
  boundary explicitly.
- Focused validation so far for this slice passed:
  `tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_direct_preview_runs_scalar_eom_exposure_without_commutator_flag
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_direct_preview_applies_scalar_eom_field_redefinition_after_exposure
  tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_direct_preview_substitutes_heavy_scalar_solutions
  -q` (`3 passed`);
  `tests/integration/validation/test_validation_fixtures.py::test_validation_fixture_gap_report_forwards_wilson_line_to_public_match_api
  -q` (`1 passed`); `python -m py_compile src/pychete/matching.py
  src/pychete/validation_fixtures.py
  tests/integration/validation/test_validation_fixtures.py`;
  `python -m mypy src/pychete/matching.py
  src/pychete/validation_fixtures.py src/pychete/matching_options.py`
  (`Success: no issues found in 3 source files`); and `git diff --check`.
  A broad mypy invocation on the entire integration test module still hits
  pre-existing test-file typing issues unrelated to this slice, so it was not
  used as the gate.
- Current scalar Green-closure slice, 2026-06-28: the Matchete checkpoints are
  still `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` /
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json` plus the
  corresponding algorithms in
  `Mathematica_reference/Matchete/Package/Simplifications.m`.
  `EoMStandardForm` maps scalar formal EOMs to two covariant derivatives, and
  `IdentitiesIBP`/`EoMSplitter` supplies the total-derivative identities used
  by `InternalSimplify`. The paired pychete probe was a bounded scalar
  Green-normal-form check on fourth-derivative representatives such as
  `Bar(H[{mu, mu, nu, nu}]) H`.
- Found a generic pychete boundary mismatch: the default scalar
  Green/EOM closure exposed formal EOMs for simple scalar Laplacians but not
  for fourth-derivative scalar representatives in the local Wilson-line
  post-integral hook. With a deeper bounded local closure
  (`max_basis_terms=256`, `max_identities=512`, `max_rounds=4`) the existing
  Symbolica-backed identity solver exposes formal scalar EOM factors for the
  same class of representatives. This is a generic Matchete
  `InternalSimplify`/Green-basis port, not a `cHD` coefficient repair.
- Implemented the deeper closure only inside
  `_apply_wilson_line_post_integral_scalar_commutator_bilinears(...)` when
  `expose_scalar_eom_terms=True`, so ordinary lightweight scalar normal-form
  calls keep their existing defaults. Added a focused regression
  `test_wilson_line_scalar_green_hook_closes_four_derivative_formal_eom_neighborhood`.
  The closure may choose the conjugate but equivalent complex-scalar formal
  EOM orientation in some simple cases; the downstream scalar field-shift
  consumer handles both `Bar(H) EOM(H)` and `H EOM(Bar(H))` orientations.
- Focused validation for this closure slice passed:
  `tests/unit/functional/test_scalar_green_bilinears.py -q`
  (`28 passed`); `python -m py_compile src/pychete/matching.py
  tests/unit/functional/test_scalar_green_bilinears.py`; targeted mypy on
  `src/pychete/matching.py` and
  `tests/unit/functional/test_scalar_green_bilinears.py`
  (`Success: no issues found in 2 source files`); and `git diff --check`.
- Latest paired EOM-boundary probe, 2026-06-28: refreshed
  `assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json` from
  `scripts/debug_pychete_singlet_eom_boundary.py` and compared it against the
  current Matchete checkpoint
  `helper_mathematica_scripts/debug_singlet_eom_simplify.wls` /
  `assets/validation/matchete/debug/singlet_eom_cHD.debug.json`. Matchete's
  raw `InternalSimplify` stage records 105 Higgs formal-EOM terms and feeds a
  nonzero `after_shift_dim6_dev3` scalar field redefinition. The paired
  pychete selected-entry probe now records scalar-EOM exposure attempts for
  each of the 10 nonzero selected Wilson-line entries: all 10 currently hit
  `Green-basis reduction discovered more than 256 basis terms`, expose zero
  formal scalar `EOM(...)` atoms, and produce zero scalar
  field-redefinition deltas. This is now the first concrete semantic boundary:
  the next generic port work should target Matchete `InternalSimplify`'s
  operator-basis / identity-neighborhood control for this selected source,
  not the final `cHD` coefficient.
- Short first-full-parity estimate, 2026-06-28: the first realistic full
  nontrivial one-loop matching integration test remains the Singlet Scalar
  Extension to SMEFT, with `cHD` as the hard coefficient. The selected
  `hScalar-lScalar-lVector-lScalar -> cHD` trace/integral/projection path now
  matches Matchete's off-shell checkpoint through propagation orders 0, 1, and
  2, so the remaining first-test work is concentrated in on-shell
  simplification rather than trace generation. Estimated missing work is
  roughly 3-5 coherent slices: port Matchete's class-wise
  `InternalSimplify`/`IBPSimplify` scalar operator grouping, feed the exposed
  formal Higgs EOM terms into the existing scalar `PerformSystematicFieldRedefs`
  consumer, verify full public Singlet route composition with unselected
  supertrace remainder/heavy substitution/on-shell ordering, then lock a full
  Singlet `cHD` regression before broadening within the Singlet model. The
  main unknown is whether the scalar class-wise Green/EOM subset is sufficient
  for this coefficient or whether a 4D/evanescent identity also contributes.
  Current Matchete evidence points to the former: `InternalSimplify` exposes
  105 Higgs formal-EOM terms that feed the first nonzero
  `after_shift_dim6_dev3` scalar shift.
