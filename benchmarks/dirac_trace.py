from __future__ import annotations

import argparse
import statistics
import time
from collections.abc import Callable
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from symbolica import Expression, S
from symbolica.community.idenso import simplify_gamma
from symbolica.community.spenso import Representation, TensorName

from pychete import Theory, dirac_trace, s


def _measure(label: str, callback: Callable[[], object], iterations: int, repeats: int) -> tuple[str, float, float]:
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(iterations):
            callback()
        samples.append((time.perf_counter() - start) / iterations)
    return label, statistics.median(samples), min(samples)


def _pychete_trace_expr(length: int):
    theory = Theory(f"dirac_trace_bench_{length}")
    indices = tuple(theory.lorentz_index(f"mu{i}") for i in range(length))
    return s.DiracProduct(*(s.Gamma(index) for index in indices))


def _idenso_trace_expr(length: int):
    gamma = TensorName.gamma()
    mink = Representation.mink(S("d"))
    bis = Representation.bis(4)
    spin_indices = tuple(bis(f"a{i}") for i in range(length))
    factors = []
    for i in range(length):
        left = spin_indices[i]
        right = spin_indices[(i + 1) % length]
        factors.append(gamma(mink(f"mu{i}"), left, right).to_expression())
    out = Expression.num(1)
    for factor in factors:
        out *= factor
    return out


def _idenso_lower_and_trace(length: int):
    return simplify_gamma(_idenso_trace_expr(length)).expand()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark native pychete Dirac traces against idenso.")
    parser.add_argument("--lengths", type=int, nargs="+", default=[2, 4, 6], help="Closed ordinary gamma trace lengths.")
    parser.add_argument("--iterations", type=int, default=100, help="Iterations per timing sample.")
    parser.add_argument("--repeats", type=int, default=5, help="Timing samples per benchmark.")
    args = parser.parse_args()

    for length in args.lengths:
        pychete_expr = _pychete_trace_expr(length)
        idenso_expr = _idenso_trace_expr(length)
        measurements = [
            _measure("pychete native", lambda: dirac_trace(pychete_expr), args.iterations, args.repeats),
            _measure("idenso simplify only", lambda: simplify_gamma(idenso_expr).expand(), args.iterations, args.repeats),
            _measure("idenso lower+simplify", lambda: _idenso_lower_and_trace(length), args.iterations, args.repeats),
        ]
        print(f"\n{length} ordinary gammas")
        for label, median, best in measurements:
            print(f"  {label:22s} median={median * 1e6:10.2f} us  best={best * 1e6:10.2f} us")


if __name__ == "__main__":
    main()
