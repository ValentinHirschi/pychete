from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from symbolica import Expression

from .expr import list_expr
from .symbols import SymbolRole, s
from .theory_metadata import ExternalHandle

if TYPE_CHECKING:
    from .theory import Theory


SmeftOperatorBuilder = Callable[["Theory", tuple[Expression, ...]], Expression | None]


SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES = (
    "cG",
    "cGt",
    "cH",
    "cHB",
    "cHBt",
    "cHD",
    "cHG",
    "cHGt",
    "cHW",
    "cHWB",
    "cHWt",
    "cHWtB",
    "cHBox",
    "cHd",
    "cHe",
    "cHl1",
    "cHl3",
    "cHq1",
    "cHq3",
    "cHu",
    "cW",
    "cWt",
    "cdH",
    "ceH",
    "cuH",
)


def smeft_warsaw_operator_names() -> tuple[str, ...]:
    """Return SMEFT Warsaw operator labels with pychete-native builders."""

    return SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES


def smeft_warsaw_operator(
    theory: Theory,
    name: str,
    indices: Iterable[Expression] = (),
) -> Expression | None:
    """Build a supported SMEFT Warsaw operator monomial for ``theory``.

    The returned expression intentionally excludes the Wilson coefficient
    itself and uses pychete's canonical Symbolica heads for fields, field
    strengths, covariant derivatives, CG tensors, and non-commutative Dirac
    chains. If the requested operator is not implemented yet, or if ``theory``
    does not carry the required SM field/group metadata, ``None`` is returned.
    """

    flavor_indices = tuple(indices)
    builders: dict[str, SmeftOperatorBuilder] = {
        "cG": _triple_field_strength_operator("G", "gs", "fStruct_SU3c", dual=False),
        "cGt": _triple_field_strength_operator("G", "gs", "fStruct_SU3c", dual=True),
        "cW": _triple_field_strength_operator("W", "gL", "fStruct_SU2L", dual=False),
        "cWt": _triple_field_strength_operator("W", "gL", "fStruct_SU2L", dual=True),
        "cHG": _higgs_field_strength_operator("G", "gs", dual=False),
        "cHGt": _higgs_field_strength_operator("G", "gs", dual=True),
        "cHW": _higgs_field_strength_operator("W", "gL", dual=False),
        "cHWt": _higgs_field_strength_operator("W", "gL", dual=True),
        "cHB": _higgs_field_strength_operator("B", "gY", dual=False),
        "cHBt": _higgs_field_strength_operator("B", "gY", dual=True),
        "cHWB": _higgs_mixed_field_strength_operator(dual=False),
        "cHWtB": _higgs_mixed_field_strength_operator(dual=True),
        "cH": _higgs_power_operator,
        "cHBox": _higgs_box_operator,
        "cHD": _higgs_derivative_operator,
        "cHl1": _higgs_current_operator("l", triplet=False),
        "cHl3": _higgs_current_operator("l", triplet=True),
        "cHe": _higgs_current_operator("e", triplet=False),
        "cHq1": _higgs_current_operator("q", triplet=False),
        "cHq3": _higgs_current_operator("q", triplet=True),
        "cHu": _higgs_current_operator("u", triplet=False),
        "cHd": _higgs_current_operator("d", triplet=False),
        "ceH": _yukawa_higgs_operator("e"),
        "cuH": _yukawa_higgs_operator("u"),
        "cdH": _yukawa_higgs_operator("d"),
    }
    builder = builders.get(name)
    if builder is None:
        return None
    return builder(theory, flavor_indices)


def define_smeft_wilson_coefficient(
    theory: Theory,
    name: str,
    *,
    indices: Iterable[Expression] = (),
    eft_order: int = 0,
    basis: str = "SMEFT",
) -> ExternalHandle:
    """Define a SMEFT Wilson coefficient and attach known Warsaw operator data."""

    index_tuple = tuple(indices)
    return theory.define_wilson_coefficient(
        name,
        indices=index_tuple,
        eft_order=eft_order,
        basis=basis,
        operator=smeft_warsaw_operator(theory, name, index_tuple),
    )


def _has(theory: Theory, *, fields: Iterable[str] = (), couplings: Iterable[str] = (), cg: Iterable[str] = ()) -> bool:
    return (
        all(name in theory.fields for name in fields)
        and all(name in theory.couplings for name in couplings)
        and all(name in theory.cg_tensors for name in cg)
    )


def _index(theory: Theory, label: str, representation: Expression = s.Lorentz) -> Expression:
    return theory.index(theory.symbol(f"smeft_{label}", role=SymbolRole.INDEX), representation)


def _field_index(theory: Theory, label: str, field_name: str, position: int) -> Expression:
    return _index(theory, label, theory.fields[field_name].indices[position])


def _cg_index(theory: Theory, label: str, cg_name: str, position: int) -> Expression:
    return _index(theory, label, theory.cg_tensors[cg_name].representation_exprs[position])


def _flavor_pair(theory: Theory, indices: tuple[Expression, ...]) -> tuple[Expression, Expression] | None:
    if len(indices) == 2:
        return indices
    flavor = theory.index_types.get("Flavor")
    if flavor is None:
        return None
    return _index(theory, "p", flavor.symbol), _index(theory, "r", flavor.symbol)


def _higgs_bilinear(theory: Theory, label: str = "i") -> Expression | None:
    if not _has(theory, fields=("H",)):
        return None
    h = theory.field_handle("H")
    index = _field_index(theory, label, "H", 0)
    return s.Bar(h(index)) * h(index)


def _field_strength(theory: Theory, field_name: str, mu: Expression, nu: Expression, *indices: Expression) -> Expression:
    field = theory.field_handle(field_name)
    return s.FieldStrength(field.label, list_expr(mu, nu), list_expr(*indices), list_expr())


def _lc_tensor(theory: Theory, *indices: Expression) -> Expression:
    return theory.define_external("LCTensor")(*indices)


def _higgs_power_operator(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
    del indices
    h1 = _higgs_bilinear(theory, "i")
    h2 = _higgs_bilinear(theory, "j")
    h3 = _higgs_bilinear(theory, "k")
    if h1 is None or h2 is None or h3 is None:
        return None
    return h1 * h2 * h3


def _higgs_box_operator(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
    del indices
    h1 = _higgs_bilinear(theory, "i")
    h2 = _higgs_bilinear(theory, "j")
    if h1 is None or h2 is None:
        return None
    mu = _index(theory, "mu")
    return h1 * s.CD(list_expr(mu, mu), h2)


def _higgs_derivative_operator(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
    del indices
    if not _has(theory, fields=("H",)):
        return None
    h = theory.field_handle("H")
    i = _field_index(theory, "i", "H", 0)
    j = _field_index(theory, "j", "H", 0)
    mu = _index(theory, "mu")
    return h(i) * s.CD(mu, s.Bar(h(i))) * s.Bar(h(j)) * s.CD(mu, h(j))


def _higgs_field_strength_operator(
    field_name: str,
    coupling_name: str,
    *,
    dual: bool,
) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        del indices
        if not _has(theory, fields=("H", field_name), couplings=(coupling_name,)):
            return None
        h2 = _higgs_bilinear(theory)
        if h2 is None:
            return None
        mu = _index(theory, "mu")
        nu = _index(theory, "nu")
        eta = _index(theory, "eta")
        kappa = _index(theory, "kappa")
        gauge_indices = _field_strength_indices(theory, field_name, "A")
        if gauge_indices is None:
            return None
        first_lorentz = (eta, kappa) if dual else (mu, nu)
        first = _field_strength(theory, field_name, *first_lorentz, *gauge_indices)
        second = _field_strength(theory, field_name, mu, nu, *gauge_indices)
        prefactor = -Expression.num(1) / 2 * _lc_tensor(theory, mu, nu, eta, kappa) if dual else Expression.num(1)
        return prefactor * h2 * first * second / theory.coupling_handle(coupling_name)() ** 2

    return build


def _field_strength_indices(theory: Theory, field_name: str, label: str) -> tuple[Expression, ...] | None:
    if field_name == "B":
        return ()
    cg_name = "fStruct_SU3c" if field_name == "G" else "fStruct_SU2L"
    if cg_name not in theory.cg_tensors:
        return None
    return (_cg_index(theory, label, cg_name, 0),)


def _higgs_mixed_field_strength_operator(*, dual: bool) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        del indices
        if not _has(theory, fields=("H", "W", "B"), couplings=("gL", "gY"), cg=("gen_SU2L_fund",)):
            return None
        h = theory.field_handle("H")
        i_h = _field_index(theory, "i", "H", 0)
        j_h = _field_index(theory, "j", "H", 0)
        j_gen = _cg_index(theory, "j", "gen_SU2L_fund", 2)
        i_gen = _cg_index(theory, "i", "gen_SU2L_fund", 1)
        adj = _cg_index(theory, "J", "gen_SU2L_fund", 0)
        tau = 2 * theory.cg_tensor_handle("gen_SU2L_fund")(adj, i_gen, j_gen)
        mu = _index(theory, "mu")
        nu = _index(theory, "nu")
        eta = _index(theory, "eta")
        kappa = _index(theory, "kappa")
        w_lorentz = (eta, kappa) if dual else (mu, nu)
        prefactor = -Expression.num(1) / 2 * _lc_tensor(theory, mu, nu, eta, kappa) if dual else Expression.num(1)
        return (
            prefactor
            * s.Bar(h(i_h))
            * tau
            * h(j_h)
            * _field_strength(theory, "W", *w_lorentz, adj)
            * _field_strength(theory, "B", mu, nu)
            / (theory.coupling_handle("gL")() * theory.coupling_handle("gY")())
        )

    return build


def _triple_field_strength_operator(
    field_name: str,
    coupling_name: str,
    cg_name: str,
    *,
    dual: bool,
) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        del indices
        if not _has(theory, fields=(field_name,), couplings=(coupling_name,), cg=(cg_name,)):
            return None
        a = _cg_index(theory, "A", cg_name, 0)
        b = _cg_index(theory, "B", cg_name, 1)
        c = _cg_index(theory, "C", cg_name, 2)
        mu = _index(theory, "mu")
        nu = _index(theory, "nu")
        rho = _index(theory, "rho")
        sigma = _index(theory, "sigma")
        eta = _index(theory, "eta")
        kappa = _index(theory, "kappa")
        first_lorentz = (eta, kappa) if dual else (mu, nu)
        prefactor = Expression.num(1) / 2 * _lc_tensor(theory, mu, nu, eta, kappa) if dual else -Expression.num(1)
        return (
            prefactor
            * theory.cg_tensor_handle(cg_name)(a, b, c)
            * _field_strength(theory, field_name, *first_lorentz, a)
            * _field_strength(theory, field_name, nu, rho, b)
            * _field_strength(theory, field_name, rho, sigma, c)
            / theory.coupling_handle(coupling_name)() ** 3
        )

    return build


def _hermitian_cd(mu: Expression, left: Expression, right: Expression) -> Expression:
    return Expression.I * left * s.CD(mu, right) - Expression.I * s.CD(mu, left) * right


def _higgs_singlet_current(theory: Theory, mu: Expression) -> Expression | None:
    if not _has(theory, fields=("H",)):
        return None
    h = theory.field_handle("H")
    i = _field_index(theory, "i", "H", 0)
    return _hermitian_cd(mu, s.Bar(h(i)), h(i))


def _higgs_triplet_current(theory: Theory, mu: Expression, adj: Expression) -> Expression | None:
    if not _has(theory, fields=("H",), cg=("gen_SU2L_fund",)):
        return None
    h = theory.field_handle("H")
    i_h = _field_index(theory, "i", "H", 0)
    j_h = _field_index(theory, "j", "H", 0)
    i_gen = _cg_index(theory, "i", "gen_SU2L_fund", 1)
    j_gen = _cg_index(theory, "j", "gen_SU2L_fund", 2)
    tau = 2 * theory.cg_tensor_handle("gen_SU2L_fund")(adj, i_gen, j_gen)
    return _hermitian_cd(mu, s.Bar(h(i_h)), tau * h(j_h))


def _higgs_current_operator(
    field_name: str,
    *,
    triplet: bool,
) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        if not _has(theory, fields=("H", field_name)):
            return None
        if triplet and "gen_SU2L_fund" not in theory.cg_tensors:
            return None
        flavor_pair = _flavor_pair(theory, indices)
        if flavor_pair is None:
            return None
        p, r = flavor_pair
        mu = _index(theory, "mu")
        adj = _cg_index(theory, "J", "gen_SU2L_fund", 0) if triplet else None
        h_current = _higgs_triplet_current(theory, mu, adj) if triplet and adj is not None else _higgs_singlet_current(theory, mu)
        if h_current is None:
            return None
        return h_current * _fermion_current(theory, field_name, p, r, mu, adj=adj if triplet else None)

    return build


def _fermion_current(
    theory: Theory,
    field_name: str,
    p: Expression,
    r: Expression,
    mu: Expression,
    *,
    adj: Expression | None = None,
) -> Expression:
    field = theory.field_handle(field_name)
    if field_name == "l":
        left = _field_index(theory, "k", field_name, 0) if adj is not None else _field_index(theory, "j", field_name, 0)
        right = _field_index(theory, "m", field_name, 0) if adj is not None else left
        current = s.NCM(s.Bar(field(left, p)), s.Gamma(mu), field(right, r))
        if adj is None:
            return current
        tau = 2 * theory.cg_tensor_handle("gen_SU2L_fund")(
            adj,
            _cg_index(theory, "k", "gen_SU2L_fund", 1),
            _cg_index(theory, "m", "gen_SU2L_fund", 2),
        )
        return tau * current
    if field_name == "q":
        color = _field_index(theory, "alpha", field_name, 0)
        left = _field_index(theory, "k", field_name, 1) if adj is not None else _field_index(theory, "j", field_name, 1)
        right = _field_index(theory, "m", field_name, 1) if adj is not None else left
        current = s.NCM(s.Bar(field(color, left, p)), s.Gamma(mu), field(color, right, r))
        if adj is None:
            return current
        tau = 2 * theory.cg_tensor_handle("gen_SU2L_fund")(
            adj,
            _cg_index(theory, "k", "gen_SU2L_fund", 1),
            _cg_index(theory, "m", "gen_SU2L_fund", 2),
        )
        return tau * current
    if field_name in {"u", "d"}:
        color = _field_index(theory, "alpha", field_name, 0)
        return s.NCM(s.Bar(field(color, p)), s.Gamma(mu), field(color, r))
    return s.NCM(s.Bar(field(p)), s.Gamma(mu), field(r))


def _yukawa_higgs_operator(field_name: str) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        if not _has(theory, fields=("H", field_name)):
            return None
        if field_name in {"u"} and "eps_SU2L" not in theory.cg_tensors:
            return None
        flavor_pair = _flavor_pair(theory, indices)
        if flavor_pair is None:
            return None
        p, r = flavor_pair
        h2 = _higgs_bilinear(theory, "i")
        if h2 is None:
            return None
        h = theory.field_handle("H")
        if field_name == "e":
            su2 = _field_index(theory, "j", "H", 0)
            return h2 * h(su2) * s.NCM(s.Bar(theory.field_handle("l")(su2, p)), theory.field_handle("e")(r))
        if field_name == "d":
            su2 = _field_index(theory, "j", "H", 0)
            color = _field_index(theory, "alpha", "d", 0)
            return h2 * h(su2) * s.NCM(s.Bar(theory.field_handle("q")(color, su2, p)), theory.field_handle("d")(color, r))
        su2_q = _field_index(theory, "j", "q", 1)
        su2_h = _field_index(theory, "k", "H", 0)
        eps = theory.cg_tensor_handle("eps_SU2L")(
            _cg_index(theory, "j", "eps_SU2L", 0),
            _cg_index(theory, "k", "eps_SU2L", 1),
        )
        color = _field_index(theory, "alpha", "u", 0)
        return h2 * eps * s.Bar(h(su2_h)) * s.NCM(s.Bar(theory.field_handle("q")(color, su2_q, p)), theory.field_handle("u")(color, r))

    return build


__all__ = [
    "SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES",
    "define_smeft_wilson_coefficient",
    "smeft_warsaw_operator",
    "smeft_warsaw_operator_names",
]
