from __future__ import annotations

from symbolica import Expression, S
from symbolica.community import idenso as native_idenso

from pychete import Theory
from pychete.backends import idenso
from pychete.group_algebra import simplify_color, simplify_gamma, simplify_metrics
from pychete.symbols import canonical_string, s


def _same(lhs, rhs) -> bool:
    return canonical_string(lhs) == canonical_string(rhs)


def test_idenso_backend_delegates_core_simplifiers() -> None:
    x = S("x")

    assert _same(idenso.simplify_gamma(x), native_idenso.simplify_gamma(x))
    assert _same(idenso.simplify_color(x), native_idenso.simplify_color(x))
    assert _same(idenso.simplify_metrics(x), native_idenso.simplify_metrics(x))
    assert _same(idenso.to_dots(x), native_idenso.to_dots(x))


def test_idenso_backend_exposes_index_helpers() -> None:
    x = S("x")
    header = S("wrapped")

    assert idenso.list_dangling(x) == native_idenso.list_dangling(x)
    assert _same(idenso.wrap_indices(x, header), native_idenso.wrap_indices(x, header))
    assert _same(idenso.wrap_dummies(x, header), native_idenso.wrap_dummies(x, header))
    assert _same(idenso.cook_indices(x), native_idenso.cook_indices(x))


def test_existing_group_algebra_shim_uses_idenso_backend() -> None:
    x = S("x")

    assert _same(simplify_gamma(x), idenso.simplify_gamma(x))
    assert _same(simplify_color(x), idenso.simplify_color(x))
    assert _same(simplify_metrics(x), idenso.simplify_metrics(x))


def test_idenso_pipeline_is_native_noop_for_plain_symbol() -> None:
    x = S("x")

    assert _same(idenso.simplify_index_algebra(x, dots=True), x)


def test_idenso_pipeline_simplifies_pychete_projectors_through_native_bridge() -> None:
    expr = s.PR**3 + s.PL**2 + s.PR * s.PL + S("x") * s.PL * s.PR

    simplified = idenso.simplify_index_algebra(expr, expand=False, color=False, metrics=False)

    assert _same(simplified, s.PR + s.PL)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PR**2), s.PR)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PL**2), s.PL)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PR * s.PL), Expression.num(0))


def test_idenso_bridge_simplifies_pychete_dirac_products_through_native_gamma() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    nu = s.Index(s.dummy_index(1), s.Lorentz)

    assert _same(idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.PR)), s.PR)
    assert _same(idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.PL)), Expression.num(0))
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.Gamma(mu), s.PR)),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PL, s.Gamma(mu), s.PL)),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.Gamma(mu), s.PL)),
        s.DiracProduct(s.Gamma(mu), s.PL),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PL, s.Gamma(mu), s.PR)),
        s.DiracProduct(s.Gamma(mu), s.PR),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.Gamma(mu), s.Gamma(mu))),
        Expression.num(4),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.Gamma(mu), s.Gamma(nu), s.Gamma(mu))),
        -2 * s.Gamma(nu),
    )


def test_idenso_bridge_simplifies_pychete_dirac_products_inside_ncm() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)

    assert _same(idenso.simplify_pychete_dirac_algebra(s.NCM(s.PR, s.Gamma(mu), s.PR)), Expression.num(0))
    assert _same(
        idenso.simplify_pychete_dirac_algebra(
            s.NCM(S("left"), s.DiracProduct(s.PR, s.Gamma(mu), s.PL), S("right"))
        ),
        s.NCM(S("left"), s.DiracProduct(s.Gamma(mu), s.PL), S("right")),
    )


def test_idenso_bridge_simplifies_registered_open_fermion_chains_through_native_gamma() -> None:
    theory = Theory("idenso_open_fermion_chain")
    left = theory.define_field("psi", s.Fermion)
    right = theory.define_field("Psi", s.Fermion)
    mu = s.Index(s.dummy_index(0), s.Lorentz)

    assert _same(
        idenso.simplify_pychete_open_dirac_chains(
            s.NCM(s.Bar(left()), s.PR, s.Gamma(mu), s.PR, right())
        ),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_open_dirac_chains(
            s.NCM(s.Bar(left()), s.PR, s.Gamma(mu), s.PL, right())
        ),
        s.NCM(s.Bar(left()), s.DiracProduct(s.Gamma(mu), s.PL), right()),
    )
    assert _same(
        idenso.simplify_pychete_open_dirac_chains(
            s.NCM(s.Bar(left()), s.Gamma(mu), s.Gamma(mu), right())
        ),
        4 * s.NCM(s.Bar(left()), right()),
    )


def test_idenso_open_fermion_chain_bridge_requires_registered_field_labels() -> None:
    theory = Theory("idenso_open_fermion_chain_tags")
    right = theory.define_field("Psi", s.Fermion)
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    plain_left = s.Field(S("plain_left"), s.Fermion, s.List(), s.List())
    expression = s.NCM(s.Bar(plain_left), s.PR, s.Gamma(mu), s.PR, right())

    assert _same(idenso.simplify_pychete_open_dirac_chains(expression), expression)


def test_idenso_bridge_simplifies_contiguous_dirac_subwords_inside_mixed_ncm() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)

    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.PR, s.Gamma(mu), s.PR, S("right"))),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.PR, s.Gamma(mu), s.PL, S("right"))),
        s.NCM(S("left"), s.DiracProduct(s.Gamma(mu), s.PL), S("right")),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.Gamma(mu), s.Gamma(mu), S("right"))),
        4 * s.NCM(S("left"), S("right")),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.Gamma(mu), s.Gamma(mu))),
        4 * S("left"),
    )
