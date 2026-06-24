"""Print a small pychete Lagrangian in Symbolica and LaTeX formats."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from symbolica import PrintMode

from pychete import FieldMassKind, Theory, s


FORMAT_OPTIONS = {
    "max_line_length": None,
    "color_top_level_sum": False,
    "color_builtin_symbols": False,
    "bracket_level_colors": None,
    "print_ring": False,
    "multiplication_operator": "*",
    "num_exp_as_superscript": False,
}


def main() -> None:
    theory = Theory("lagrangian_printout")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        self_conjugate=True,
        mass=(FieldMassKind.LIGHT, "m"),
    )
    lam = theory.define_coupling("lambda")

    lagrangian = theory.free_lag(phi) - lam() * phi() ** 4 / 24

    print("Symbolica:")
    print(lagrangian.format(mode=PrintMode.Symbolica, **FORMAT_OPTIONS))
    print()
    print("LaTeX:")
    print(lagrangian.format(mode=PrintMode.Latex, **FORMAT_OPTIONS))


if __name__ == "__main__":
    main()
