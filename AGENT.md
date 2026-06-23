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
`E("...")` to construct reusable internal expressions. String parsing is
reserved for external model input and genuinely one-off expressions.

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
