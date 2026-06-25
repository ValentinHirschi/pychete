from __future__ import annotations

from pathlib import Path

from pychete.loaders import parse_matchete_expression
from pychete.symbols import canonical_string, s
from pychete.validation_fixtures import load_validation_fixture


def test_parse_matchete_internal_heads_into_pychete_heads() -> None:
    theory = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json")).theory()
    mu = theory.dummy_index(1)
    mass = theory.coupling_handle("M")()

    assert canonical_string(parse_matchete_expression(r"Coupling[y, {}, 0]", theory)) == canonical_string(
        theory.coupling_handle("y")()
    )
    assert canonical_string(parse_matchete_expression(r"Index[d$$1, Lorentz]", theory)) == canonical_string(mu)
    assert canonical_string(
        parse_matchete_expression(r"Field[\[Phi], Scalar, {}, {Index[d$$1, Lorentz]}]", theory)
    ) == canonical_string(theory.field_handle("phi")(derivatives=[mu]))
    assert canonical_string(parse_matchete_expression(r"LF[{Coupling[M, {}, 0]}, {2, -1}]", theory)) == canonical_string(
        s.LoopFunction(s.List(mass), s.List(2, -1))
    )
    assert canonical_string(
        parse_matchete_expression(r"LF[{Coupling[M, {}, 0], Coupling[M, {}, 0]}, {2, 3, -1}]", theory)
    ) == canonical_string(
        s.LoopFunction(s.List(mass), s.List(5, -1))
    )


def test_parse_matchete_dirac_chain_and_log_expression() -> None:
    theory = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json")).theory()
    mu = theory.dummy_index(1)
    psi = theory.field_handle("psi")
    expected_chain = s.NCM(
        s.Bar(psi()),
        s.DiracProduct(s.Gamma(mu), s.PL),
        psi(derivatives=[mu]),
    )

    parsed_chain = parse_matchete_expression(
        r"Bar[Field[\[Psi], Fermion, {}, {}]]\[CenterDot] "
        r"DiracProduct[GammaM[Index[d$$1, Lorentz]], Proj[-1]]\[CenterDot] "
        r"Field[\[Psi], Fermion, {}, {Index[d$$1, Lorentz]}]",
        theory,
    )
    parsed_log = parse_matchete_expression(r"Log[\[Mu]bar2/Coupling[M, {}, 0]^2]", theory)

    assert canonical_string(parsed_chain) == canonical_string(expected_chain)
    assert "log(" in canonical_string(parsed_log)
