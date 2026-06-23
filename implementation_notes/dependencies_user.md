I want you to prepare a first basic setup for this program pychete which aims at a re-implementation in python+Symbolica the mathematica code Machete.

As a first step I want you to implement:

dependencies/install_dependencies.py

which should do the following:

a) If you currently within a python venv, exit it.

b) Create a new python venv in `dependencies` and you'll then do everything in install_dependencies.py as if you were within it (and ask the user at the end to source it).

c) Make sure rust and maturin are available (otherwise prompt the user to install those)

d) Download the source code of [symbolica-dev/symbolica-community.git](https://github.com/symbolica-dev/symbolica-community.git) locally  (main branch) into `dependencies` and modify the Cargo.toml there to have the following three dependencies (symbolica (latest dev branch), spenso, idenso, and vakint pointing to the corresponding local paths in the ./dependencies folder, which you should populate by also downloading their corresponding source code.
Maybe do an automatic minor modification of the pyo3 library that will be buid their so that it exposes a global variable that will be a dictionary called `LOCAL_VERSIONS` which contains three keys "symbolica", "vakint" "spenso" and "idenso" with values being the revhashes they are compiled against at the moment (do this when downloading those for the first time.)

e) Build the wheel for symbolica-community in release mode and install it with `pip` within the virtual environment.

f) Make a first main in src/pychete.py which does not much except that it loads symbolica, idenso, spenso and vakint and also confirms the existence of the top-level variable `LOCAL_VERSIONS` and prints its content with prettyprint.

g) Make sure the script `install_dependencies.py` does nothing by default if all is already installed, and has the option `--recompile` which just recompiles all (incremental if possible, not hard clean), and `--reset` that nukes all and makes sure to start from scratch.
