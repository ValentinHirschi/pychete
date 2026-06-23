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
- idenso exposes `simplify_gamma`, `simplify_color`, `simplify_metrics`, `wrap_indices`, `wrap_dummies`, and related conversion helpers. Future gamma, color, and metric algebra should be delegated through a pychete adapter rather than reimplemented.
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
  heavy charged Dirac fermion `CapitalPsi` with mass `M`, massless charged
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
   - Add `group_algebra/idenso.py` as the only gamma/color/metric simplification
     gateway and convert pychete expressions to idenso/spenso conventions there.
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
