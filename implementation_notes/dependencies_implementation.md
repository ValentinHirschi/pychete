## 2026-06-23

- Started implementing the first dependency setup task from `dependencies_user.md`.
- Inspected upstream repository layout:
  - `symbolica-community` is cloned from `symbolica-dev/symbolica-community` on `main`.
  - `symbolica` has a `dev` branch and currently requires Rust 1.89.
  - `idenso` is not a standalone public `alphal00p/idenso` repository.
  - Current `symbolica-community` sources patch `spenso`, `idenso`, `spenso-hep-lib`, and `vakint` from the `alphal00p/gammaloop` workspace, so the installer will use that workspace for the local path crates.
- Planned installer behavior:
  - create/use `dependencies/.venv`;
  - avoid installing anything into an already active caller virtualenv;
  - check `git`, `rustc`, `cargo`, and venv-local `maturin`;
  - clone/update managed upstream source checkouts;
  - patch `symbolica-community/Cargo.toml` and `src/lib.rs`;
  - build a release wheel with `maturin` and install it into `dependencies/.venv`;
  - skip work by default when the venv import smoke test already passes;
  - support `--recompile` and `--reset`.
- Implemented `dependencies/install_dependencies.py`.
  - Uses `dependencies/.venv` as the managed virtual environment.
  - Installs/uses `maturin` inside that venv.
  - Checks for `git`, `cargo`, `rustc`, and Rust >= 1.89.
  - Clones `symbolica-community` from `main`, `symbolica` from `dev`, and the `gammaloop` revision referenced by current `symbolica-community` for local `spenso`, `idenso`, and `vakint` crates.
  - Rewrites `symbolica-community/Cargo.toml` to use local paths.
  - Patches `symbolica-community/src/lib.rs` to expose `LOCAL_VERSIONS` as a Python dictionary with `symbolica`, `spenso`, `idenso`, and `vakint` revision hashes.
  - Builds a release wheel with `maturin` and installs it into the managed venv with `pip`.
  - Runs an import smoke test and then runs `src/pychete.py`.
- Implemented `src/pychete.py`.
  - Imports `symbolica`, `symbolica.community.idenso`, `symbolica.community.spenso`, and `symbolica.community.vakint`.
  - Validates and pretty-prints `symbolica.LOCAL_VERSIONS`.
- Updated `.gitignore` to ignore generated dependency checkouts, wheels, venv files, and Python bytecode caches.
- Validation performed:
  - `python3 -m py_compile dependencies/install_dependencies.py src/pychete.py`
  - `python3 dependencies/install_dependencies.py --help`
- Full Rust wheel compilation was not run during implementation because it would clone and compile the full Symbolica/PyO3 stack.

### Follow-up audit

- Rechecked the implementation against the user task.
- Tightened item (a): when launched from an active virtualenv, `install_dependencies.py` now re-execs itself with the base Python executable and removes `VIRTUAL_ENV`/`PYTHONHOME` from the child environment before continuing. If Python cannot identify a distinct base executable, it still ignores the caller venv for managed subprocesses.
- Added `tests/test_symbolica_local_versions.py` for pytest. The test imports `symbolica` and verifies that `LOCAL_VERSIONS` is a top-level dictionary containing non-empty `symbolica`, `vakint`, `spenso`, and `idenso` revision strings.
- Populated `README.md` with a minimal project description and online references for Matchete/Machete.
- Populated `AGENT.md` with test-running instructions, the ban on `sympy`/`scipy`, required use of Symbolica/idenso/spenso/vakint, and local source/stub locations for API discovery.
- Extended `install_dependencies.py` to patch GammaLoop's Cargo workspace to the local Symbolica checkout, build the GammaLoop Python API wheel in release mode, install it into `dependencies/.venv`, and include `import gammaloop` in the installer smoke test.
- Extended pytest coverage so `tests/test_symbolica_local_versions.py` verifies that `gammaloop` imports and exposes `GammaLoopAPI`.
- Added `--no-gammaloop` to `install_dependencies.py` because the GammaLoop release build is slow. The installer writes `dependencies/install_manifest.json`; pytest only imports/checks GammaLoop when that manifest says GammaLoop was requested. The manifest records that GammaLoop uses the `ufo_support,python_abi` feature set and local Symbolica with `gmp` enabled when requested.
- Verified the fast path with `python3 dependencies/install_dependencies.py --recompile --no-gammaloop`.
  - Symbolica rebuilt and installed successfully.
  - GammaLoop build was skipped.
  - `dependencies/install_manifest.json` recorded `"gammaloop": {"requested": false, "installed": false, ...}`.
  - `dependencies/.venv/bin/python -m pytest tests -q` reported `1 passed, 1 skipped`.
