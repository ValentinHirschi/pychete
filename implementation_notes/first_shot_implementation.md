# First implementation progress

## 2026-06-23

### Request tracking

- Created `first_shot_user.md` and recorded the initial implementation prompt plus all follow-up prompts.
- This file is the running implementation journal for the first pychete implementation.
- The repository already had uncommitted changes in `.gitignore`, `AGENTS.md`, and `dependencies/install_dependencies.py`; they are being preserved and treated as existing worktree state.

### Repository state

- The Python source is currently only `src/pychete.py`, a dependency smoke-test script.
- The test suite currently only checks local Symbolica community module versions and optional GammaLoop import.
- There is no package metadata or installable `pychete` package yet.
- The Mathematica reference checkout is present at `Mathematica_reference/Matchete` and includes package code, validation tests, and model files.
- `wolframscript` is available locally for behavioral comparisons against the reference implementation.

### Matchete reference findings

- Matchete stores definition metadata in global associations:
  - `$FieldAssociation`
  - `$CouplingAssociation`
  - `$FlavorIndices`
  - `$GaugeGroups`
  - `$GlobalGroups`
- Physics objects remain symbolic expressions:
  - `Field[label, type, indices, derivatives]`
  - `Coupling[label, indices, EFTOrder]`
  - `Index[label, representation]`
  - `FieldStrength[...]`, `Bar[...]`, `CD[...]`, `Delta[...]`, `Metric[...]`
- `DefineField` creates both field metadata and, when applicable, a mass coupling. Its field metadata includes type, index representations, charges, self-conjugacy, chirality, mass label, heavy/light status, zero-mode status, Goldstone/background flags, and UFO data.
- `DefineCoupling` records EFT order, index types, self-conjugacy, permutation symmetries, diagonal-index flags, thermal counting, unitarity, and UFO data.
- Flavor indices carry dimensions; group representations and Clebsch-Gordan definitions are maintained separately from the core gauge/global group records.
- Dummy indices are identified from repeated `Index` expressions. Canonical relabeling assigns deterministic labels separately for each representation and avoids collisions with open indices.
- Flavor diagonal coupling indices require special handling: they are neither ordinary open nor ordinary dummy indices, and closed flavor deltas may become `FlavorSum[Index[...]]` instead of immediately becoming a dimension.
- Covariant derivatives are encoded directly in the derivative-list argument of `Field` and `FieldStrength`; `CD` acts by rewriting those expressions.
- Functional derivatives treat differently differentiated fields as independent, generate deltas/metrics for matching indices, and build variational derivatives by integration by parts over all derivative orders allowed by the EFT truncation.
- `DeriveEOM` differentiates with respect to the barred field. Tree matching expands heavy fields in inverse-mass/EFT order, solves the EOM system order-by-order, stores both inclusive and fixed-order solutions, and substitutes those solutions back into operators.
- EFT counting is expression-based: couplings carry their EFT order in the expression, derivatives contribute one, scalar/vector fields contribute one, fermions contribute three halves, and heavy fields receive an additional suppression count when requested.
- Matching maintains a second, Lagrangian-specific field association. It infers
  heavy masses from the actual mass terms and treats light masses as
  interactions during matching.
- GroupMagic maintains additional registries for groups, representations,
  explicit Clebsch-Gordan tensors, and Clebsch-Gordan properties.
- Representation properties are group, Dynkin coefficients, dimension, and
  reality. Clebsch-Gordan properties include ordered index representations,
  conjugation uniqueness, permutation symmetries, reality, basis membership,
  and delta decomposability.

### Symbolica and community API findings

- Reusable expressions can and should be built from symbols returned by `S(...)`; symbols are callable function heads.
- Symbolica provides Mathematica parse/print modes, expression tree inspection, matching, replacements, transformers, expansion, coefficient extraction, differentiation, and series expansion.
- The Mathematica parser accepts function-call syntax and Wolfram Greek escapes, but not raw WL list braces or complete constructs such as `Module[{...}, ...]`.
- A Matchete model loader therefore needs a small, explicit Wolfram-subset front end before passing individual expressions to Symbolica:
  - comment removal;
  - top-level statement/block splitting;
  - list-brace rewriting to `List[...]`;
  - rule rewriting to `Rule[...]`;
  - `NonCommutativeMultiply`/`**` normalization;
  - interpretation of supported definition calls and a constrained `Module`/assignment subset.
- idenso exposes `simplify_gamma`, `simplify_color`, `simplify_metrics`, `wrap_indices`, `wrap_dummies`, and related conversion helpers. Future gamma and metric algebra should be delegated through a pychete adapter rather than reimplemented. Lie-group algebra must remain group-agnostic in pychete even if backend APIs use colour-oriented names.
- spenso provides representation, slot, tensor, and tensor-library APIs. The initial design should preserve an adapter path to these APIs without requiring spenso objects as pychete's canonical expression representation.
- Namespaced Symbolica heads such as `pychete::field` and model symbols such as
  `model::phi` construct, iterate, match, and round-trip to Mathematica syntax
  cleanly.
- Namespaced wildcard symbols successfully match the proposed field-expression
  shape, validating a central store for reusable heads and pattern placeholders.

### Emerging architecture

- Use a top-level mutable `Theory` object to own registries and current
  Lagrangian state, avoiding Matchete-style process-global physics state.
- Keep registry keys and values Symbolica expressions wherever practical. Use frozen Python records only for validated metadata and service configuration.
- Make the canonical field/coupling/index/Lagrangian representation Symbolica expressions with stable pychete namespaced heads.
- Centralize every reusable Symbolica symbol and wildcard in one symbol registry module. String parsing is limited to external input and genuinely one-off literals.
- Split implementation into package submodules for symbols, model state/definitions, indices, expressions/conjugation, derivatives, EFT counting, functional derivatives, tree matching, model loading, and group-algebra adapters.
- Vendor only required model inputs into a top-level `assets/` directory; runtime code and tests must not read from `Mathematica_reference/Matchete`.
- Separate definition state from a Lagrangian-specific analysis snapshot. The
  latter contains inferred field properties, EOM solutions, and heavy-field
  leading orders and is invalidated whenever the Lagrangian changes.
- Store self-contained Symbolica definition expressions behind validated Python
  registry facades. Do not attach mutable theory metadata to Symbolica symbols,
  since symbol data is process-global and unsuitable for independent theories.

### Live VLF reference

- Loaded `Models/VLF_toy_model.m` with local Matchete.
- It defines Abelian gauge group `U1e`, coupling `e`, real massless vector `A`,
  heavy charged Dirac fermion `Psi` with mass `M`, massless charged
  Dirac fermion `psi`, real light scalar `phi` with mass `m`, and complex
  Yukawa coupling `y`.
- The resulting Lagrangian contains scalar, vector, and Dirac free terms plus
  the right-handed Yukawa interaction and its left-handed Hermitian conjugate.
- First-slice VLF acceptance will mean parsing the actual model input,
  registering all definitions, and constructing the full symbolic Lagrangian.
  Fermion integration and gamma simplification are not first-slice matching
  requirements.

### Live phi4 reference

- For a real light scalar with mass `m` and real coupling `lambda`, Matchete
  represents
  `L = 1/2 (d phi)^2 - 1/2 m^2 phi^2 - lambda phi^4/24`.
- Its EOM residual is
  `-Box phi - m^2 phi - lambda phi^3/6`.

### Remaining planning work

- The stock `Validation/Tests/Matching.wl` only covers a gauge fluctuation-operator case and does not provide a simple tree-level scalar EOM test.
- Constructed and ran a minimal reference case directly with local Matchete:
  - real heavy scalar `S` with mass `M`;
  - real massless light scalar `phi`;
  - interaction `-(g/2) S phi^2`.
- Matchete returns the heavy-field EOM
  `-Box S - M^2 S - (g/2) phi^2`.
- Its leading heavy-field solution is
  `S = -g phi^2/(2 M^2)`, with higher derivative corrections generated
  order-by-order.
- Through EFT dimension six, `Match[..., LoopOrder -> 0]` returns
  `1/2 (d phi)^2 + g^2 phi^4/(8 M^2) + g^2 phi^2 (d phi)^2/(2 M^4)`.
- `SetCurrentLagrangian` must initialize the current field association before
  `DetermineEOMs` is called directly; `Match` normally performs that setup.

### Decision-complete implementation plan

1. Package and symbol foundation
   - Replace the single `src/pychete.py` script with an installable
     `src/pychete/` package and add `pyproject.toml`.
   - Add a process-global, state-free `SymbolStore` exposed as `s`.
   - Create all reusable pychete heads, tags, constants, generated-label
     factories, and wildcard placeholders through that store only.
   - Use `pychete::` for internal heads and a model namespace for user labels.

2. Canonical expressions
   - Use `field(label, type, indices(...), derivatives(...))`,
     `coupling(label, indices(...), eft_order)`, and
     `index(label, representation)` as the central forms.
   - Add heads for `field_strength`, `bar`, `delta`, `metric`, `flavor_sum`,
     `ncm`, `dirac_product`, `gamma`, `projector`, `cg`, and expanded heavy
     field labels.
   - Implement constructors, conjugation, Hermitian completion, covariant
     derivative insertion, expansion, and canonical expression comparison.

3. Theory and registries
   - Add a mutable `Theory` object with independent registries for fields,
     couplings, index types, groups, representations, and invariant tensors.
   - Store registry values as validated, self-contained Symbolica definition
     expressions. Python registry/view classes provide ergonomic property
     access and transactions.
   - Keep a separate current Lagrangian and invalidatable analysis snapshot
     containing Lagrangian-specific field properties, EOMs, and heavy-field
     leading orders.
   - Definition methods return callable handles while all physics results are
     Symbolica expressions.

4. Definitions and free Lagrangians
   - Implement scalar, non-chiral fermion, vector, flavor-index, coupling, U(1),
     and SU(N) definitions needed by the selected reference tests and VLF model.
   - Auto-create mass couplings with Matchete-compatible EFT orders and
     diagonal-index flags.
   - Auto-create gauge couplings, vector fields, fundamental/adjoint
     representation metadata, and symbolic invariant heads.
   - Implement scalar free Lagrangians fully; implement the representation-level
     Dirac/vector free terms required to load VLF.

5. Generic indices
   - Unify Lorentz, flavor, and group representation indices under registered
     index-type metadata with dimension and duality/reality.
   - Implement open/dummy/diagonal-index discovery, repeated-index validation,
     deterministic per-representation relabeling, deltas, metrics, flavor sums,
     and contraction.
   - Preserve Matchete's special behavior for diagonal flavor couplings.

6. EFT and functional methods
   - Implement recursive operator-dimension counting directly on canonical
     expressions and inclusive/exclusive EFT truncation.
   - Implement partial functional derivatives with delta/metric kernels.
   - Implement variational derivatives as the Matchete integration-by-parts sum
     over differentiated fields up to the requested EFT order.
   - Expose scalar EOM residuals as symbolic `eom(field, residual)` expressions.

7. Scalar tree matching
   - Infer heavy scalar mass properties from the current Lagrangian.
   - Expand each heavy scalar into fixed EFT-order field expressions.
   - Solve the EOM system order-by-order by isolating the unique linear
     fixed-order heavy field; fail clearly for unsupported nonlinear/ambiguous
     systems.
   - Substitute inclusive solutions, truncate, contract/relabel indices, remove
     heavy fields, and Hermitianize the result.
   - Reproduce the live Matchete heavy-scalar result through dimension six.

8. Wolfram model input
   - Vendor the exact `VLF_toy_model.m` input under `assets/models/` with
     provenance; never read executable code from the reference checkout.
   - Build a balanced Wolfram-subset scanner and evaluator for comments, lists,
     rules, assignments, `Module`, `@`, `//`, `**`, and the supported Matchete
     definition/expression calls.
   - Use Symbolica's Mathematica parser after syntax normalization rather than
     implementing algebra parsing.
   - Resolve both the upstream `VLF_toy_model.m` spelling and normalized
     `VLFToyModel.m` lookup.
   - Fully construct the VLF registries and symbolic Lagrangian; do not claim
     fermionic matching in this slice.

9. Group algebra boundary
   - Add `group_algebra/idenso.py` as the gamma/metric simplification gateway
     and convert pychete expressions to idenso/spenso conventions there.
   - Keep Symbolica fallback rules in `group_algebra/fallbacks.py` only for
     unsupported operations; do not duplicate idenso algorithms.

10. Tests and validation
    - Organize tests under dependency, unit/definitions, unit/indices,
      unit/eft, unit/functional, integration/models, and
      integration/matching.
    - Port the relevant `Definitions.wl`, `FlavorIndices.wl`, and
      `EFTCounting.wl` expectations.
    - Add phi4 construction/EOM tests, VLF asset-load snapshots, and heavy-scalar
      EOM/tree-match tests from the live Wolfram reference outputs.
    - Add independence/invalidation tests for multiple `Theory` instances and a
      static check that runtime pychete code does not reference
      `Mathematica_reference/Matchete`.
    - Run the managed pytest suite, package import smoke test, and selected
      wolframscript comparison scripts during implementation.

### Locked assumptions

- `Theory` is the initial public top-level object.
- VLF support means complete symbolic loading, not fermionic tree matching.
- First matching support is scalar-only but its interfaces are designed for
  later fermion/vector and multi-field systems.
- The actual reference test path is
  `Mathematica_reference/Matchete/Validation/Tests/Definitions.wl`; the prompt's
  `validation/Definitions.m` is treated as referring to that file.
- The reference baseline is branch `vectors`, commit
  `ad2619adbea55eef49f3f504cc7e148c76593eaf`.

### Implementation started

- Left Plan Mode and began the first implementation against the accepted goal
  statement.
- Confirmed the managed virtual environment exposes Symbolica 2.1.0 and the
  expected local `symbolica`, `spenso`, `idenso`, and `vakint` revisions when
  `~/.bashrc` is sourced.
- Updated the dependency installer smoke command to run the package module with
  `PYTHONPATH=src`.
- Added `pyproject.toml` with pytest `src/` import configuration.

### Implemented first foundation slice

- Replaced the single-file smoke script with a `src/pychete/` package and
  package smoke entry point.
- Added the central `SymbolStore` exposed as `pychete.s`; reusable heads now
  use `pychete::Field`, `pychete::Coupling`, `pychete::Index`,
  `pychete::CD`, `pychete::Bar`, `pychete::NCM`, and related Matchete-like
  namespaced heads.
- Added `Theory`, field/coupling handles, flavor/Lorentz index definitions,
  mass-coupling creation, scalar free Lagrangians, minimal vector/fermion
  symbolic free terms, and pretty JSON checkpoints.
- Added a top-level `PycheteState` checkpoint object with `theories` and
  `active_theory`.
- Added parse-stable `canonical_string()` based on Symbolica `format_plain()`.
- Added scalar EFT counting and inclusive/exclusive truncation for fields,
  couplings, products, powers, and sums.
- Added scalar functional derivatives/EOMs using Symbolica replacement and
  differentiation through temporary variables, with explicit product-rule
  covariant derivatives.
- Added scalar tree matching for diagonal real heavy scalar fields in the first
  supported source-interaction class. The minimal reference model now gives
  the expected `S_1`, zero even orders, `S_3`, and the Matchete dimension-six
  tree EFT result, and an additional regression covers two independent heavy
  scalars.
- Extended scalar matching to non-self-conjugate diagonal heavy scalars by
  solving independent `Field` and `Bar[Field]` EOMs. Complex scalar free
  Lagrangians now use `Bar[D S] D S - M^2 Bar[S] S`, while real scalars keep
  the `1/2` normalization.
- Added a complex-heavy-scalar regression with independent `y` and `yb`
  sources. It verifies `S_1`, `Bar[S]_1`, `S_3`, and the final tree EFT
  `y yb phi^4/M^2 + 4 y yb phi^2(d phi)^2/M^4` plus the light kinetic term.
- Added generic index utilities for index collection, open/dummy detection, and
  deterministic dummy relabeling, including repeated-index counting inside
  Symbolica powers.
- Added `assets/models/VLF_toy_model.m` and a conservative first-slice
  Matchete model loader for the supported Wolfram subset used by that file:
  definitions, options, `Module`, assignment, `FreeLag`, `PlusHc`,
  `Bar@...`, postfix `//RelabelIndices`, and `**` spin chains. Runtime
  pychete code does not read from `Mathematica_reference/Matchete`.
- Added `assets/models/VLF_toy_model.py` and a trusted Python model loader
  expecting `build() -> Theory`. The Mathematica-asset and Python-asset VLF
  loaders now canonicalize to the same JSON object.
- Added `mathematica/theory_loader.m` as an optional Matchete-side JSON export
  helper; it is not imported by runtime pychete code.
- Added an idenso adapter boundary under `pychete/group_algebra/`.

### Current verification

- `source "$HOME/.bashrc"; dependencies/.venv/bin/python -m pytest tests`
  passes with 17 tests and 1 expected skip because GammaLoop API was not
  requested in the current dependency manifest.
- `source "$HOME/.bashrc"; PYTHONPATH=src dependencies/.venv/bin/python -m pychete`
  passes and reports the managed Symbolica community module revisions.
- Static scan found no runtime `sympy`/`scipy` imports and no runtime reference
  to `Mathematica_reference` or `Matchete/Package` under `src/pychete`.

### Known remaining gaps

- The Mathematica loader is deliberately limited to the supported VLF toy model
  Wolfram subset; it is not yet a general Matchete/Wolfram evaluator.
- Scalar matching currently covers diagonal real and complex heavy scalar
  source interactions, including several independent real heavy scalar fields.
  Mixed quadratic mass matrices still need the next abstraction layer.
- EFT denominator Taylor expansion for additive denominators, full
  GroupMagic-style CG handling, and idenso expression conversion are not yet
  implemented.

## 2026-06-25

### VLF tree-level matching goal

- Started the VLF-capable foundation goal: pychete should load the VLF toy
  model, represent fermion/NCM/Abelian gauge structure natively in Symbolica,
  derive and solve the heavy Dirac-field tree EOM, and reproduce Matchete's
  raw off-shell dimension-six tree EFT with no remaining heavy fields.
- Locked user decisions for this slice:
  - Match the raw off-shell Matchete tree result through dimension six, before
    IBP/Green simplification.
  - Add `Theory.match(..., loop_order=0)` and reject nonzero loop orders.
  - Implement open spin chains and the projector identities needed for heavy
    spinor EOMs; defer charge conjugation and Majorana fermions.

### Current implementation pass

- Confirmed the worktree was clean before starting this pass.
- Re-read the current package structure, scalar matcher, functional
  derivative machinery, VLF loaders, and agent notes before making code edits.
- Updating project notes and agent guidance first, then proceeding to the
  Symbolica-native NCM, fermion, Abelian charge, and VLF matching layers.
- Added the requested AGENTS.md planning-question rule: material planning,
  physics-scope, API, validation, and architecture questions must wait for the
  user's explicit answer.
- Added Symbolica-native NCM support with central sequence wildcards, linear
  `NCM`, scalar-aware normalization, scalar extraction, nested-chain
  flattening, projector identities, chirality flips across gamma matrices,
  active Hermitian conjugation through `bar_expr`, and open/closed spin-chain
  classification.
- Extended field metadata with gauge-charge expressions and updated the VLF
  Mathematica/Python loaders so `Charges -> {U1e[1]}` is preserved in Symbolica
  symbol data. The Python and Mathematica VLF assets still canonicalize to the
  same theory JSON and Lagrangian.
- Updated Abelian vector free-lagrangian normalization to include the gauge
  coupling denominator, yielding the Matchete-style `-F^2/(4 e^2)` term.
- Fixed the functional-derivative path to normalize NCM before extracting the
  variation coefficient and added an ordered-chain NCM variation rule with
  Grassmann signs, avoiding Symbolica `der(..., NCM, ...)` artifacts.
- Added a first heavy-Dirac solver for diagonal vector-like fermions. For the
  VLF toy model it derives the open-chain EOM, solves the leading source and
  derivative correction, substitutes the solution, and canonizes the
  first-derivative bilinear to Matchete's raw off-shell antisymmetric form.
- Local probe result for the VLF Python asset now has no heavy `Psi` and gives
  the expected tree interaction:
  `I/2 phi^2 y Bar[y]/M^2 (Bar[psi] gamma P_L D psi -
  Bar[D psi] gamma P_L psi)`, plus the light free Lagrangian.

### VLF implementation verification

- Added focused tests for:
  - NCM scalar extraction, Hermitian conjugation, projector identities, and
    open/closed spin-chain classification.
  - Abelian charge metadata and U(1) vector free-lagrangian normalization.
  - Heavy-fermion EOM derivation with open NCM chains.
  - idenso gamma and explicit-dimension projector smoke coverage, with spenso
    limited to interop construction of tensor expressions.
  - Python and Mathematica VLF tree-level matching through dimension six.
- Added a small spenso bridge under `pychete/group_algebra/` as an interop
  probe, not as the Dirac-algebra engine. The local API probe confirmed
  symbolic-`D` gamma contractions should be delegated to idenso, while
  projector identities are reliable at explicit dimension and remain backed by
  pychete's Symbolica projector fallback for symbolic-`D` chains.
- Verification command:
  `source "$HOME/.bashrc"; dependencies/.venv/bin/python -m pytest tests`
  passed with 68 tests and 1 expected skip for the optional GammaLoop API.
- Runtime scan found no `sympy`/`scipy` imports and no runtime pychete
  dependency on `Mathematica_reference` or `Matchete/Package`.

### Notebook examples

- Started adding VLF examples to `examples/scalar_theory_playground.ipynb`.
- The examples will demonstrate loading the Python and Mathematica VLF assets,
  inspecting charge/NCM data, deriving the heavy-fermion EOM, solving the first
  heavy-spinor orders, and matching against the raw off-shell dimension-six
  tree result.
- Added the notebook cells and validated them by executing every code cell in
  order from the managed environment. Also reran the focused VLF/model tests:
  `dependencies/.venv/bin/python -m pytest tests/integration/matching/test_vlf_tree.py tests/integration/models/test_model_loaders.py`.
- Clarified the VLF field-list display: charges are stored as Symbolica
  expressions, but the notebook had been converting them to canonical strings
  before printing. Updated the example to display formatted charge expressions
  such as `charges=[U1e(1)]` instead of a Python list of quoted strings.
- Added a notebook-local imaginary-unit formatter so `as_symbolica` and
  `as_latex` compact unit imaginary coefficients such as `-1𝑖` to `-𝑖` (and
  LaTeX `-\mathrm{i}`), without changing the underlying Symbolica expression.

### Dummy-index API clarification

- Inspected the VLF theory returned by the Python loader after the user noticed
  `vlf.dummy_index`.
- Confirmed this is the public bound method `Theory.dummy_index(...)`, not a
  stored field, loader artifact, or theory-owned dummy-index registry entry.
  The loaded VLF theory has no dummy/index entries in `_symbols`,
  `symbol_manifest()`, or JSON metadata. Dummy labels still appear inside
  expressions as the central built-in `pychete::dummy_index(...)` head, which is
  the intended non-registered representation.

### Expression zero checks

- Replaced string-based zero checks with Symbolica expression equality against
  `Expression.num(0)` after expansion.
- Updated both the VLF notebook assertion and the shared pytest
  `assert_expr_equal` helper so formatting is used only as a failure message,
  never as the semantic zero test.
- Updated exact imaginary factors in tests to use `Expression.I` instead of
  Python `1j`, and rationalized zero-test differences before comparing to
  `Expression.num(0)`.
- Revalidated by executing all notebook code cells and running
  `source "$HOME/.bashrc"; dependencies/.venv/bin/python -m pytest tests`,
  which passed with 68 tests and 1 expected skip.

### Dirac-algebra engine clarification

- Recorded the corrected interpretation of the Symbolica community modules:
  idenso is the primary engine for Dirac, Lorentz, metric, and
  dimensional-regularization algebra, including future `d = 4 - 2 epsilon`
  work. spenso should be treated as the tensor-network/evaluation layer, or as
  a bridge for constructing tensor expressions, rather than as the canonical
  symbolic Dirac-algebra implementation.
- Updated `AGENTS.md` with that distinction so future gamma/Lorentz work starts
  from idenso and only uses spenso where tensor-network representation or
  evaluation is genuinely needed.
- Traced `spenso_bridge.py` dependencies. It was only exported through
  `pychete.group_algebra` and used by the smoke test, not by matching, loaders,
  or notebooks.
- Replaced `spenso_bridge.py` plus the thin `idenso.py` wrapper with a single
  `group_algebra/idenso_bridge.py`. The new bridge keeps `simplify_gamma` and
  `simplify_metrics` as idenso calls, and exposes neutral tensor constructors
  (`gamma_tensor`, `chiral_projector_tensor`, `spin_metric_tensor`) for
  expressions meant to be consumed by idenso. spenso remains an internal
  implementation detail for constructing those tensor expressions.
- Removed `simplify_color` from the pychete-facing `group_algebra` surface.
  Colour is not a special pychete group: future group algebra should be built
  around general Lie-group data and identities, not a dedicated colour/SU(3)
  path. idenso's colour-named routines can be revisited only as backend details
  if they fit that general abstraction.

### Matchete NCM validation port

- Started porting the in-scope Dirac/NCM validation tests from
  `Mathematica_reference/Matchete/Validation/Tests/NCM.wl`.
- The scope gate for this pass is "current pychete Dirac-algebra features":
  native Symbolica NCM ordering/linearity/scalar extraction, `bar_expr`/Hermitian
  conjugation behavior, projector normalization, and spin-chain classification.
  Fully fledged Matchete tensor-index simplification, charge conjugation,
  Majorana-specific chains, and broader Lie-group algebra remain out of scope
  unless they are already implemented by pychete.
- Added Matchete-style spin-chain predicate helpers:
  `is_left_open_spin_chain`, `is_right_open_spin_chain`, and
  `is_closed_spin_chain`. These wrap `spin_chain_kind` while preserving
  Matchete's convention that pure Dirac matrix chains are both left- and
  right-open.
- Extended `normalize_ncm` with conservative nested closed-spinor-line
  extraction for the endpoint vocabulary currently implemented in pychete
  (`Bar[fermion]`, `fermion`, and Dirac atoms). This ports Matchete's active
  "Contraction of spinors 1-3" behavior without introducing unsupported
  `Transp`/`CConj` semantics.
- Added `tests/unit/spinor/test_matchete_ncm_reference.py` covering these active
  Matchete `NCM.wl` TestIDs:
  - `Extract scalar from spin chain`
  - `Extract derivative scalar from spin chain`
  - `Contraction of spinors 1`
  - `Contraction of spinors 2`
  - `Contraction of spinors 3`
  - `LOpenSpinChainQ 1-5, 7, 9`
  - `ROpenSpinChainQ 1-5, 7, 9`
  - `ClosedSpinChainQ 1-4`
  - `CanonizeSpinorLines: nothing 1, 2, 4` as normalization no-ops in the
    currently implemented endpoint vocabulary.
- Left the remaining active Matchete `NCM.wl` TestIDs unported for this pass
  because they require not-yet-implemented pychete features:
  - `Bar of Majorana with Dirac fermions 1-2`, `Bar of Majorana mass`,
    `Canonical ordering 2-4`, `CanonizeSpinorLines: nothing 3`, and
    `CanonizeSpinorLines: split chain 1-3` require `CConj`, `Transp`,
    GammaCC, or Majorana-specific canonicalization.
  - `LOpenSpinChainQ 6, 8`, `ROpenSpinChainQ 6, 8`, and
    `Canonical ordering 1, 5` require `Transp`.
  - `CanonizeSpinorLines: abort 1-2` require a public/explicit
    `CanonizeSpinorLines` operation with Matchete-style diagnostics rather than
    the current passive normalization path.
- Focused verification passed:
  `source "$HOME/.bashrc"; dependencies/.venv/bin/python -m pytest tests/unit/spinor/test_matchete_ncm_reference.py tests/unit/spinor/test_ncm.py`
  and `tests/unit/definitions/test_public_api.py`.
- Final verification passed:
  `source "$HOME/.bashrc"; dependencies/.venv/bin/python -m pytest tests`
  collected 78 tests with 77 passing and 1 expected skip for the optional
  GammaLoop API.

### NCM commutativity hot-path optimization

- Reworked `is_commutative_spin_factor` to use a noncommutative blacklist with
  a commutative default. It now fast-returns for numbers/variables, recurses
  only for structural `Add`, `Mul`, `Pow`, `Bar`, and `CD`, and uses one
  function-head lookup for pychete heads instead of checking every known
  commutative head individually.
- Preserved the current noncommutative cases: chiral projectors, `NCM`,
  `DiracProduct`, `Gamma`, fermion fields, `Bar[fermion]`, and
  derivatives of noncommutative spin factors. Couplings, field strengths,
  metrics, CG tensors, and future ordinary function heads now fall through to
  the intended commutative default.
- Added a regression test in `tests/unit/spinor/test_ncm.py` for the new
  default-commutative policy and the known noncommutative exceptions.
- Verification passed:
  `source "$HOME/.bashrc"; dependencies/.venv/bin/python -m pytest tests`
  collected 79 tests with 78 passing and 1 expected skip for the optional
  GammaLoop API.

### LaTeX spinor and derivative formatting

- Updated the central Symbolica print callback for pychete derivatives so
  LaTeX covariant derivatives print as prefix operators on the immediate field,
  e.g. `D_{\mu}\phi`, instead of wrapping the field argument in
  `\left(...\right)`.
- Added LaTeX-specific barred-field printing that keeps the bar on the field
  symbol and leaves derivative operators outside it. Both derivative-indexed
  fields and explicit `CD[mu, Bar[field]]`/`Bar[CD[mu, field]]` forms now
  display as `D_{\mu}\bar{\psi}`.
- Added a lightweight LaTeX endpoint check for NCM/DiracProduct printing:
  chains beginning with a barred fermion endpoint and ending with a fermion
  endpoint now print inside `\left(...\right)` so closed bilinears stand apart
  from surrounding commutative factors.
- Added focused pretty-printing regression coverage for derivative formatting,
  barred derivative fields, parenthesized closed NCM chains, and unparenthesized
  open spin chains.
- Verification passed:
  `source "$HOME/.bashrc"; PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests`
  collected 80 tests with 79 passing and 1 expected skip for the optional
  GammaLoop API.

### Expression-aware LaTeX formatting

- Inspected Symbolica's Python custom print callback plumbing and confirmed it
  passes ordinary print options plus `level`/`bracket_level`, but not the
  internal `in_exp_base` flag needed for a callback to know it is being printed
  as the base of a power.
- Kept the existing atom-level callbacks for direct Symbolica formatting, and
  added a pychete-aware recursive LaTeX formatter behind `latex_string(...)`
  and `display_string(..., PrintMode.Latex)`.
- The new LaTeX formatter handles the expression contexts that native symbol
  callbacks cannot see:
  - derivative fields raised to powers now print as
    `\left(D_{\mu}\phi\right)^{2}`;
  - neighboring equal derivative labels collapse to `D^{2}\phi`;
  - products put numerical coefficients and coupling prefactors before the
    operator factors, e.g. `\lambda \phi^{4}` and
    `y \phi^{2}(\bar{\psi}\gamma^{\mu}\psi)`.
- Updated the pretty-printing tests to use `latex_string` for expression-level
  LaTeX snapshots while still keeping direct `Expression.format` checks for the
  simpler atom-level callbacks.
- Updated `examples/lagrangian_printout.py` and the notebook `as_latex` helper
  to call `latex_string(...)` so examples use the same pychete-aware LaTeX path.
- Verification passed:
  `source "$HOME/.bashrc"; PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests`
  collected 81 tests with 80 passing and 1 expected skip for the optional
  GammaLoop API.

### Coefficient-only LaTeX fractions

- Refined the pychete LaTeX product formatter so fractions are used only for
  coefficient material: signed numerical factors plus coupling/mass prefactors.
  Field factors, NCM chains, field strengths, and other operator factors are
  kept outside the fraction even when the coefficient contains inverse powers
  such as `M^{-2}`.
- Extended numerical coefficient parsing to recognize Symbolica's pure
  imaginary rational spellings such as `-1𝑖/2` and `-1/2𝑖`, so the sign and
  imaginary unit stay in the leading coefficient block.
- Added regression coverage for mass-suppressed spinor terms, e.g.
  `-\frac{\mathrm{i}}{2 M^{2}} \bar{y} y \phi^{2}
  (\bar{\psi}\gamma^{\mu}P_L\psi)`, ensuring the operator never appears in
  the numerator of a big fraction.
- Verification passed:
  `source "$HOME/.bashrc"; PYTHONPATH=src dependencies/.venv/bin/python -m pytest tests`
  collected 82 tests with 81 passing and 1 expected skip for the optional
  GammaLoop API.

### Projector representation audit

- Traced current uses of `s.PL`, `s.PR`, and `s.Proj`.
- `s.PL` and `s.PR` are the canonical active pychete projector atoms used by
  the Mathematica loader, VLF asset, NCM normalization, heavy-fermion matching,
  and idenso bridge.
- `s.Proj` is currently only a Matchete-shaped leftover/generic wrapper: it is
  registered in `SymbolStore`, accepted by `is_dirac_atom`, and covered by a
  pretty-printing smoke test, but it is not used by the actual projector
  simplification or matching path.
- Removed `s.Proj` from the central symbol registry, custom print handlers, and
  pretty-printing smoke coverage. `s.PL` and `s.PR` remain the sole canonical
  pychete chirality projectors.
- Moved `s.PL` and `s.PR` into the cached noncommutative spin-symbol blacklist
  used by `is_commutative_spin_factor`, so projector atoms are handled through
  the same name-based hot path as `NCM`, `Gamma`, and `DiracProduct` instead of
  through separate equality checks.

### Symbolica normalization hook design note

- Inspected the local Symbolica 2.1.0 source for symbol normalization hooks.
  Python symbols accept a `normalization=Transformer` argument; the transformer
  is run after Symbolica's own function normalization whenever an expression
  with that head is normalized.
- Confirmed a hook can enforce local invariants immediately at construction
  time, e.g. `f()` can normalize to `42` in a fresh-symbol smoke test.
- Confirmed the documented self-reference caveat: creating a normalizer whose
  pattern mentions the same symbol by name defines the symbol before the hooked
  definition is installed, causing a redefinition error. Self-normalizers need
  wildcard-function patterns or a deliberately staged construction.
- Current conclusion: use hooks for small, pure, idempotent NCM invariants that
  can be expressed as native Symbolica transformers. Do not move the full
  current `normalize_ncm` body into a Python `Transformer.map` hook yet, because
  it would run on every `NCM` construction, cross the Python boundary, depend on
  pychete semantic predicates such as fermion/scalar field metadata, and make
  it harder to opt out, debug, or attach Matchete-style diagnostics.
- Recommended migration path: keep explicit `normalize_ncm` as the semantic
  normalization service for now, while progressively moving purely syntactic
  pieces into the `s.NCM` symbol definition once they are expressible without
  Python callbacks and once import-order/redefinition tests are in place.

### Heavy-field matching solution refactor

- Replaced the duplicated `HeavyScalarSolution`/`HeavyFermionSolution`
  dataclass bodies in `matching.py` with a single concrete
  `HeavyFieldSolution`.
- `HeavyFieldSolution` owns EFT-order summation, conjugate fallback behavior,
  notebook `_repr_latex_`/`_repr_html_` hooks, and inclusive-solution
  normalization. It now calls the common NCM normalizer for every heavy field
  solution, including scalars.
- Removed the `HeavyScalarSolution = HeavyFieldSolution` and
  `HeavyFermionSolution = HeavyFieldSolution` aliases. The public API now
  exposes `HeavyFieldSolution` plus a `HeavyFieldFamily` enum carried by each
  solution.
- Added an internal `_HeavyFieldSolverSpec` registry shape: each heavy-field
  family contributes a field-type selector, an EOM/source builder, an order
  solver, and a conjugate-order strategy. `match_tree` now solves all
  registered heavy-field families through this registry instead of manually
  merging scalar and fermion solution maps.
- Added `Theory.solve_heavy_field_eoms` for the generic all-family solve path.
  The scalar and fermion methods remain as convenience filters over the same
  generic solver machinery.
- Preserved the public `solve_heavy_scalar_eoms` and
  `solve_heavy_fermion_eoms` wrappers as compatibility entry points, backed by
  the shared solver machinery.
- Exported `HeavyFieldSolution` and `HeavyFieldFamily` through
  `pychete.api`/package root as the common solution concept and family tag.
- Added shared matching-local and functional-local normalization helpers that
  call `normalize_ncm(expr)`. The extra explicit second normalization pass was
  removed after checking `normalize_ncm` itself: it already performs NCM
  replacement before expansion and repeats to a fixed point.
- Matching now uses the common NCM normalizer when preparing Lagrangians,
  zeroing heavy fields in sources, summing inclusive solutions, building
  scalar/fermion order solutions, replacing heavy fields, and returning the
  final matched result.
- Functional derivative/EOM code and the fermion derivative bilinear
  canonicalizer now rely directly on the same `normalize_ncm` ordering instead
  of expanding first.
- Verification passed:
  `source "$HOME/.bashrc"; dependencies/.venv/bin/python -m pytest tests`
  collected 79 tests with 78 passing and 1 expected skip for the optional
  GammaLoop API.
