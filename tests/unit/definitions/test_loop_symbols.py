from __future__ import annotations

from symbolica import Expression, PrintMode

from pychete import canonical_string, s


FORMAT_OPTIONS = {
    "max_line_length": None,
    "color_top_level_sum": False,
    "color_builtin_symbols": False,
    "bracket_level_colors": None,
    "print_ring": False,
    "multiplication_operator": "*",
    "num_exp_as_superscript": False,
}


def test_loop_matching_builtins_are_registered_and_pretty_printed() -> None:
    builtins = (
        s.FuncNCM(s.OpenCD(s.LorentzIndices()), s.Prop(s.MuBar2)),
        s.LoopMom(s.LorentzIndices()),
        s.LFFull(s.List(s.MuBar2), s.List(Expression.num(1), Expression.num(0))),
        s.LF(s.List(s.MuBar2), s.List(Expression.num(1), Expression.num(0))),
        s.WilsonLine(s.MuBar2),
        s.WilsonTerm(s.MuBar2, s.LorentzIndices()),
        s.XTerm(s.MuBar2),
        s.MTerm(s.MuBar2),
        s.GaugeCTerm(s.MuBar2),
        s.PowerTypeSTr(s.MuBar2),
        s.LogTypeSTr(s.MuBar2),
        s.Transp(s.MuBar2),
        s.GammaCC(s.MuBar2),
        s.CConj(s.MuBar2),
        s.DimRegEpsilon,
        s.hbar,
        s.hScalar,
        s.lScalar,
        s.hFermion,
        s.lFermion,
        s.hVector,
        s.lVector,
        s.hGhost,
        s.lGhost,
        s.hAntiGhost,
        s.lAntiGhost,
    )

    for expr in builtins:
        assert canonical_string(expr)
        for mode in (PrintMode.Symbolica, PrintMode.Latex, PrintMode.Mathematica, PrintMode.Sympy, PrintMode.Typst):
            output = expr.format(mode=mode, **FORMAT_OPTIONS)
            assert output
            assert "pychete::" not in output
