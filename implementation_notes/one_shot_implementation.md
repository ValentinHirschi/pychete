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
  pychete. Do not repair a disagreement from the final coefficient alone.
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
  linear field-like atoms, but those identities are not yet fed into a
  Symbolica-backed row-reduction/normal-form solver. The next Green-basis
  slice should build the bounded operator-class vector space around these
  identities instead of extending the one-pair emitter.

## Latest Validation

- `PYTHONPATH=src dependencies/.venv/bin/python -m mypy` passed with no issues.
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py
  tests/unit/definitions/test_public_api.py -q` passed (`64 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_theory_definitions.py -k "commutator" -q`
  passed (`20 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/definitions/test_public_api.py -q` passed (`8 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py -q` passed
  (`61 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py -k
  "projection and (ibp or chd or hbox)" -q` passed (`10 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py -k
  "ibp_scalar_bilinear or derivative_slot or hbox_ibp or registered_hbox_ibp
  or first_derivative_ibp or gauge_eom" -q` passed (`6 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_scalar_green_bilinears.py -q` passed
  (`15 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_scalar_green_bilinears.py
  tests/integration/validation/test_numeric_probes.py -k
  "scalar_laplacian_ibp or chd" -q` passed (`5 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py -k
  "chd and (gauge_eom or current or first_derivative_ibp)" -q` passed
  (`3 passed`).
- Watchdog-wrapped selected Singlet `hScalar-lScalar -> cHD` order-zero smoke
  with scalar-Laplacian and scalar-first-derivative IBP support still returned
  projected coefficient `0`.
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/unit/functional/test_scalar_green_bilinears.py -q` passed
  (`15 passed`).
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py -k
  "chd and (gauge_eom or current)" -q` passed (`2 passed`).
- Watchdog-wrapped
  `dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_validation_fixtures.py -k
  "pre_eom_terms_for_derivative_higgs_target" -q` passed.
- Watchdog-wrapped selected Singlet `hScalar-lScalar -> cHD` order-zero smoke
  with the scalar-Laplacian IBP pass ran and still returned projected
  coefficient `0`.
- `PYTHONPATH=src dependencies/.venv/bin/python -m pytest
  tests/integration/validation/test_numeric_probes.py -k "chd and gauge_eom"
  -q` passed.
- `git diff --check` passed.
- Previous watchdog-wrapped focused checks for the same slice passed:
  the cHD Wilson-line filter regression and the Wilson-line target-filter
  regression group.

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
