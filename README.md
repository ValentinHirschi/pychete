# pychete

`pychete` is an experimental project attempting to port the Matchete/Machete
Mathematica code for automated effective-field-theory matching fully to
Python + Symbolica.

Development guidance is in `AGENTS.md`. In particular, new symbolic work must
check and prefer native Symbolica, idenso, spenso, and vakint primitives before
adding Python-side symbolic algorithms.

The intended public Python API is listed in `src/pychete/api.py` and re-exported
from the package root.

References:

- Matchete source repository: <https://gitlab.com/matchete/matchete>
- Proof-of-concept paper: <https://arxiv.org/abs/2212.04510>
- EFT tools overview: <https://link.springer.com/article/10.1140/epjc/s10052-023-12323-y>
