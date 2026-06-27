from __future__ import annotations

import pytest
from symbolica import Expression

from pychete.backends import idenso
from pychete.functional import expose_scalar_derivative_commutator_bilinears
from pychete.matching_results import MatchingResult
from pychete.symbols import s
from pychete.theory import Theory
from tests.conftest import assert_expr_equal


def _scalar_su2_probe() -> tuple[Theory, object, Expression, Expression, Expression, Expression]:
    theory = Theory("scalar_green_bilinear_probe")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    weak = theory.field_handle("W")
    i = theory.index("i", fund)
    a = theory.index("A", adj)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    target = (
        s.Bar(higgs(i))
        * higgs(i)
        * s.FieldStrength(weak.label, s.List(mu, nu), s.List(a), s.List()) ** 2
        / theory.coupling_handle("gL")() ** 2
    )
    return theory, higgs, target, i, mu, nu


@pytest.mark.parametrize(
    ("name", "derivatives", "expected_weight"),
    (
        ("Dbar_abab_H", ("mu", "nu", "mu", "nu"), Expression.num(1) / Expression.num(8)),
        ("Dbar_aabb_H", ("mu", "mu", "nu", "nu"), Expression.num(0)),
        ("Dbar_abba_H", ("mu", "nu", "nu", "mu"), Expression.num(1) / Expression.num(4)),
    ),
)
def test_scalar_green_bilinear_exposes_one_sided_four_derivative_field_strength_component(
    name: str,
    derivatives: tuple[str, str, str, str],
    expected_weight: Expression,
) -> None:
    theory, higgs, target, i, mu, nu = _scalar_su2_probe()
    derivative_lookup = {"mu": mu, "nu": nu}
    derivative_tuple = tuple(derivative_lookup[label] for label in derivatives)
    source = s.Bar(higgs(i, derivatives=derivative_tuple)) * higgs(i)

    coefficient = _project_c_hw_like_coefficient(theory, source, target)

    assert name
    assert_expr_equal(coefficient, expected_weight * theory.coupling_handle("gL")() ** 2)


@pytest.mark.parametrize(
    ("field_derivatives", "expected_weight"),
    (
        (("mu", "nu"), Expression.num(1) / Expression.num(4)),
        (("nu", "mu"), Expression.num(1) / Expression.num(8)),
    ),
)
def test_scalar_green_bilinear_exposes_two_derivative_field_strength_component(
    field_derivatives: tuple[str, str],
    expected_weight: Expression,
) -> None:
    theory, higgs, target, i, mu, nu = _scalar_su2_probe()
    derivative_lookup = {"mu": mu, "nu": nu}
    field_derivative_tuple = tuple(derivative_lookup[label] for label in field_derivatives)
    source = s.Bar(higgs(i, derivatives=[mu, nu])) * higgs(i, derivatives=field_derivative_tuple)

    coefficient = _project_c_hw_like_coefficient(theory, source, target)

    assert_expr_equal(coefficient, expected_weight * theory.coupling_handle("gL")() ** 2)


def test_scalar_green_bilinear_preserves_antisymmetric_commutator_component() -> None:
    theory, higgs, target, i, mu, nu = _scalar_su2_probe()
    source = (
        (s.Bar(higgs(i, derivatives=[mu, nu])) - s.Bar(higgs(i, derivatives=[nu, mu])))
        * (higgs(i, derivatives=[mu, nu]) - higgs(i, derivatives=[nu, mu]))
    ).expand()

    coefficient = _project_c_hw_like_coefficient(theory, source, target)

    assert_expr_equal(coefficient, theory.coupling_handle("gL")() ** 2 / 4)


def _project_c_hw_like_coefficient(theory: Theory, source: Expression, target: Expression) -> Expression:
    normalized = expose_scalar_derivative_commutator_bilinears(
        theory,
        source,
        include_gauge_coupling=False,
        expand_commutators=True,
    )
    normalized = idenso.simplify_pychete_field_strength_group_algebra(theory, normalized)
    normalized = idenso.simplify_pychete_color_algebra(theory, normalized)
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized.expand(),
    )
    return result.project_matching_conditions({"cHW_like": target}, expand_source=False)["cHW_like"].expand()
