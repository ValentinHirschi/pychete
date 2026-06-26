from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from symbolica import Expression

from .expr import list_expr
from .operator_bases import OperatorBasis, define_wilson_coefficient_from_basis
from .symbols import SymbolRole, s
from .theory_metadata import ExternalHandle

if TYPE_CHECKING:
    from .theory import Theory


SmeftOperatorBuilder = Callable[["Theory", tuple[Expression, ...]], Expression | None]


SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES = (
    "cllHH",
    "cG",
    "cGt",
    "cW",
    "cWt",
    "cHG",
    "cHGt",
    "cHW",
    "cHWt",
    "cHB",
    "cHBt",
    "cHWB",
    "cHWtB",
    "cH",
    "cHBox",
    "cHD",
    "ceH",
    "cuH",
    "cdH",
    "ceW",
    "ceB",
    "cuG",
    "cuW",
    "cuB",
    "cdG",
    "cdW",
    "cdB",
    "cHl1",
    "cHl3",
    "cHe",
    "cHq1",
    "cHq3",
    "cHu",
    "cHd",
    "cHud",
    "cll",
    "cqq1",
    "cqq3",
    "clq1",
    "clq3",
    "cee",
    "cuu",
    "cdd",
    "ceu",
    "ced",
    "cud1",
    "cud8",
    "cle",
    "clu",
    "cld",
    "cqe",
    "cqu1",
    "cqu8",
    "cqd1",
    "cqd8",
    "cduq",
    "cqqu",
    "cqqq",
    "cduu",
    "cledq",
    "cquqd1",
    "cquqd8",
    "clequ1",
    "clequ3",
)


def smeft_warsaw_operator_names() -> tuple[str, ...]:
    """Return SMEFT Warsaw operator labels with pychete-native builders."""

    return smeft_warsaw_basis().operator_names()


def smeft_warsaw_basis() -> OperatorBasis:
    """Return pychete's optional built-in SMEFT Warsaw operator basis."""

    builders = _smeft_warsaw_operator_builders()
    return OperatorBasis(
        "SMEFT",
        {name: builders[name] for name in SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES},
    )


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

    return smeft_warsaw_basis().operator(theory, name, tuple(indices))


def _smeft_warsaw_operator_builders() -> dict[str, SmeftOperatorBuilder]:
    return {
        "cllHH": _weinberg_operator,
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
        "cHud": _right_handed_higgs_current_operator,
        "ceH": _yukawa_higgs_operator("e"),
        "cuH": _yukawa_higgs_operator("u"),
        "cdH": _yukawa_higgs_operator("d"),
        "ceW": _dipole_operator("e", "W"),
        "ceB": _dipole_operator("e", "B"),
        "cuG": _dipole_operator("u", "G"),
        "cuW": _dipole_operator("u", "W"),
        "cuB": _dipole_operator("u", "B"),
        "cdG": _dipole_operator("d", "G"),
        "cdW": _dipole_operator("d", "W"),
        "cdB": _dipole_operator("d", "B"),
        "cll": _vector_four_fermion_operator(("l", "l"), triplet=False),
        "cqq1": _vector_four_fermion_operator(("q", "q"), triplet=False),
        "cqq3": _vector_four_fermion_operator(("q", "q"), triplet=True),
        "clq1": _vector_four_fermion_operator(("l", "q"), triplet=False),
        "clq3": _vector_four_fermion_operator(("l", "q"), triplet=True),
        "cee": _vector_four_fermion_operator(("e", "e"), triplet=False),
        "cuu": _vector_four_fermion_operator(("u", "u"), triplet=False),
        "cdd": _vector_four_fermion_operator(("d", "d"), triplet=False),
        "ceu": _vector_four_fermion_operator(("e", "u"), triplet=False),
        "ced": _vector_four_fermion_operator(("e", "d"), triplet=False),
        "cud1": _vector_four_fermion_operator(("u", "d"), triplet=False),
        "cud8": _vector_four_fermion_operator(("u", "d"), color_octet=True),
        "cle": _vector_four_fermion_operator(("l", "e"), triplet=False),
        "clu": _vector_four_fermion_operator(("l", "u"), triplet=False),
        "cld": _vector_four_fermion_operator(("l", "d"), triplet=False),
        "cqe": _vector_four_fermion_operator(("q", "e"), triplet=False),
        "cqu1": _vector_four_fermion_operator(("q", "u"), triplet=False),
        "cqu8": _vector_four_fermion_operator(("q", "u"), color_octet=True),
        "cqd1": _vector_four_fermion_operator(("q", "d"), triplet=False),
        "cqd8": _vector_four_fermion_operator(("q", "d"), color_octet=True),
        "cledq": _scalar_four_fermion_operator("ledq"),
        "cquqd1": _scalar_four_fermion_operator("quqd1"),
        "cquqd8": _scalar_four_fermion_operator("quqd8"),
        "clequ1": _scalar_four_fermion_operator("lequ1"),
        "clequ3": _scalar_four_fermion_operator("lequ3"),
        "cduq": _baryon_number_violating_operator("duq"),
        "cqqu": _baryon_number_violating_operator("qqu"),
        "cqqq": _baryon_number_violating_operator("qqq"),
        "cduu": _baryon_number_violating_operator("duu"),
    }


def define_smeft_wilson_coefficient(
    theory: Theory,
    name: str,
    *,
    indices: Iterable[Expression] = (),
    eft_order: int = 0,
    basis: str = "SMEFT",
) -> ExternalHandle:
    """Define a SMEFT Wilson coefficient and attach known Warsaw operator data."""

    return define_wilson_coefficient_from_basis(
        theory,
        smeft_warsaw_basis(),
        name,
        indices=indices,
        eft_order=eft_order,
        basis=basis,
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


def _flavor_tuple(theory: Theory, indices: tuple[Expression, ...], count: int) -> tuple[Expression, ...] | None:
    if len(indices) == count:
        return indices
    if indices:
        return None
    flavor = theory.index_types.get("Flavor")
    if flavor is None:
        return None
    labels = ("p", "r", "s", "t")[:count]
    return tuple(_index(theory, label, flavor.symbol) for label in labels)


def _coupling(theory: Theory, name: str) -> Expression:
    return theory.coupling_handle(name)()


def _cg(theory: Theory, name: str, *indices: Expression) -> Expression:
    return theory.cg_tensor_handle(name)(*indices)


def _tau(theory: Theory, adj: Expression, left: Expression, right: Expression) -> Expression:
    return 2 * _cg(theory, "gen_SU2L_fund", adj, left, right)


def _su2_eps(theory: Theory, left: Expression, right: Expression, *, barred: bool = False) -> Expression:
    eps = _cg(theory, "eps_SU2L", left, right)
    return s.Bar(eps) if barred else eps


def _su3_eps(theory: Theory, first: Expression, second: Expression, third: Expression, *, barred: bool = False) -> Expression:
    eps = _cg(theory, "eps_SU3c", first, second, third)
    return s.Bar(eps) if barred else eps


def _su3_gen(theory: Theory, adj: Expression, left: Expression, right: Expression) -> Expression:
    return _cg(theory, "gen_SU3c_fund", adj, left, right)


def _sigma(mu: Expression, nu: Expression) -> Expression:
    return s.DiracProduct(s.Sigma(mu, nu))


def _gamma(mu: Expression) -> Expression:
    return s.Gamma(mu)


def _ncm(*operands: Expression) -> Expression:
    return s.NCM(*operands)


def _barred_charge_conjugate(expr: Expression) -> Expression:
    return s.Bar(s.CConj(expr))


def _charge_conjugate_bar(expr: Expression) -> Expression:
    return s.CConj(s.Bar(expr))


def _lepton_doublet(theory: Theory, su2_label: str, flavor: Expression) -> Expression:
    return theory.field_handle("l")(_field_index(theory, su2_label, "l", 0), flavor)


def _lepton_singlet(theory: Theory, flavor: Expression) -> Expression:
    return theory.field_handle("e")(flavor)


def _quark_doublet(theory: Theory, color_label: str, su2_label: str, flavor: Expression) -> Expression:
    return theory.field_handle("q")(
        _field_index(theory, color_label, "q", 0),
        _field_index(theory, su2_label, "q", 1),
        flavor,
    )


def _up_quark(theory: Theory, color_label: str, flavor: Expression) -> Expression:
    return theory.field_handle("u")(_field_index(theory, color_label, "u", 0), flavor)


def _down_quark(theory: Theory, color_label: str, flavor: Expression) -> Expression:
    return theory.field_handle("d")(_field_index(theory, color_label, "d", 0), flavor)


def _fermion(theory: Theory, field_name: str, flavor: Expression, *, color: str = "alpha", su2: str = "i") -> Expression:
    if field_name == "l":
        return _lepton_doublet(theory, su2, flavor)
    if field_name == "e":
        return _lepton_singlet(theory, flavor)
    if field_name == "q":
        return _quark_doublet(theory, color, su2, flavor)
    if field_name == "u":
        return _up_quark(theory, color, flavor)
    if field_name == "d":
        return _down_quark(theory, color, flavor)
    raise ValueError(f"unsupported SMEFT fermion field {field_name!r}")


def _vector_current(
    theory: Theory,
    field_name: str,
    left_flavor: Expression,
    right_flavor: Expression,
    mu: Expression,
    *,
    color: str = "alpha",
    su2_left: str = "i",
    su2_right: str | None = None,
) -> Expression:
    right = su2_left if su2_right is None else su2_right
    left_field = _fermion(theory, field_name, left_flavor, color=color, su2=su2_left)
    right_field = _fermion(theory, field_name, right_flavor, color=color, su2=right)
    return _ncm(s.Bar(left_field), _gamma(mu), right_field)


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


def _weinberg_operator(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
    if not _has(theory, fields=("H", "l"), cg=("eps_SU2L",)):
        return None
    flavors = _flavor_pair(theory, indices)
    if flavors is None:
        return None
    p, r = flavors
    i = _field_index(theory, "i", "H", 0)
    j = _field_index(theory, "j", "l", 0)
    k = _field_index(theory, "k", "H", 0)
    m = _field_index(theory, "m", "l", 0)
    return (
        _su2_eps(theory, i, j, barred=True)
        * _su2_eps(theory, k, m, barred=True)
        * theory.field_handle("H")(i)
        * theory.field_handle("H")(k)
        * _ncm(_barred_charge_conjugate(theory.field_handle("l")(j, p)), theory.field_handle("l")(m, r))
    )


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


def _right_handed_higgs_current_operator(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
    if not _has(theory, fields=("H", "u", "d"), cg=("eps_SU2L",)):
        return None
    flavors = _flavor_pair(theory, indices)
    if flavors is None:
        return None
    p, r = flavors
    i = _field_index(theory, "i", "H", 0)
    j = _field_index(theory, "j", "H", 0)
    mu = _index(theory, "mu")
    color = _field_index(theory, "alpha", "u", 0)
    return (
        Expression.I
        * _su2_eps(theory, i, j, barred=True)
        * theory.field_handle("H")(j)
        * s.CD(mu, theory.field_handle("H")(i))
        * _ncm(s.Bar(theory.field_handle("u")(color, p)), _gamma(mu), theory.field_handle("d")(color, r))
    )


def _dipole_operator(fermion: str, gauge_field: str) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        if not _has(theory, fields=("H", "q" if fermion in {"u", "d"} else "l", fermion, gauge_field)):
            return None
        gauge_indices = _field_strength_indices(theory, gauge_field, "A")
        if gauge_indices is None:
            return None
        if fermion in {"u", "d"} and "eps_SU2L" not in theory.cg_tensors:
            return None
        if gauge_field == "W" and "gen_SU2L_fund" not in theory.cg_tensors:
            return None
        if gauge_field == "G" and "gen_SU3c_fund" not in theory.cg_tensors:
            return None
        coupling_name = {"B": "gY", "W": "gL", "G": "gs"}[gauge_field]
        if coupling_name not in theory.couplings:
            return None
        flavors = _flavor_pair(theory, indices)
        if flavors is None:
            return None
        p, r = flavors
        mu = _index(theory, "mu")
        nu = _index(theory, "nu")
        strength = _field_strength(theory, gauge_field, mu, nu, *gauge_indices)
        sigma = _sigma(mu, nu)
        if fermion == "e":
            i_l = _field_index(theory, "i", "l", 0)
            e = theory.field_handle("e")
            if gauge_field == "W":
                j_h = _field_index(theory, "j", "H", 0)
                return (
                    -_ncm(s.Bar(theory.field_handle("l")(i_l, p)), sigma, e(r))
                    * _tau(theory, gauge_indices[0], i_l, j_h)
                    * theory.field_handle("H")(j_h)
                    * strength
                    / _coupling(theory, coupling_name)
                )
            h_i = _field_index(theory, "i", "H", 0)
            return (
                -_ncm(s.Bar(theory.field_handle("l")(i_l, p)), sigma, e(r))
                * theory.field_handle("H")(h_i)
                * strength
                / _coupling(theory, coupling_name)
            )
        q = theory.field_handle("q")
        color_left = _field_index(theory, "alpha", "q", 0)
        su2_q = _field_index(theory, "i", "q", 1)
        if fermion == "u":
            right_color = _field_index(theory, "beta" if gauge_field == "G" else "alpha", "u", 0)
            right = theory.field_handle("u")(right_color, r)
            higgs_index = _field_index(theory, "j", "H", 0)
            higgs_factor = _su2_eps(theory, su2_q, higgs_index) * s.Bar(theory.field_handle("H")(higgs_index))
            if gauge_field == "G":
                return (
                    -_ncm(s.Bar(q(color_left, su2_q, p)), sigma, right)
                    * _su3_gen(theory, gauge_indices[0], color_left, right_color)
                    * higgs_factor
                    * strength
                    / _coupling(theory, coupling_name)
                )
            if gauge_field == "W":
                tau_index = _field_index(theory, "j", "H", 0)
                higgs_contracted = _field_index(theory, "k", "H", 0)
                return (
                    -_ncm(s.Bar(q(color_left, su2_q, p)), sigma, right)
                    * _tau(theory, gauge_indices[0], su2_q, tau_index)
                    * _su2_eps(theory, tau_index, higgs_contracted)
                    * s.Bar(theory.field_handle("H")(higgs_contracted))
                    * strength
                    / _coupling(theory, coupling_name)
                )
            return (
                -_ncm(s.Bar(q(color_left, su2_q, p)), sigma, right)
                * higgs_factor
                * strength
                / _coupling(theory, coupling_name)
            )
        right_color = _field_index(theory, "beta" if gauge_field == "G" else "alpha", "d", 0)
        right = theory.field_handle("d")(right_color, r)
        h_i = _field_index(theory, "i", "H", 0)
        if gauge_field == "G":
            return (
                -_ncm(s.Bar(q(color_left, su2_q, p)), sigma, right)
                * theory.field_handle("H")(h_i)
                * _su3_gen(theory, gauge_indices[0], color_left, right_color)
                * strength
                / _coupling(theory, coupling_name)
            )
        if gauge_field == "W":
            h_j = _field_index(theory, "j", "H", 0)
            return (
                -_ncm(s.Bar(q(color_left, su2_q, p)), sigma, right)
                * _tau(theory, gauge_indices[0], su2_q, h_j)
                * theory.field_handle("H")(h_j)
                * strength
                / _coupling(theory, coupling_name)
            )
        return (
            -_ncm(s.Bar(q(color_left, su2_q, p)), sigma, right)
            * theory.field_handle("H")(h_i)
            * strength
            / _coupling(theory, coupling_name)
        )

    return build


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


def _vector_four_fermion_operator(
    fields: tuple[str, str],
    *,
    triplet: bool = False,
    color_octet: bool = False,
) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        if not _has(theory, fields=fields):
            return None
        if triplet and "gen_SU2L_fund" not in theory.cg_tensors:
            return None
        if color_octet and "gen_SU3c_fund" not in theory.cg_tensors:
            return None
        flavors = _flavor_tuple(theory, indices, 4)
        if flavors is None:
            return None
        p, r, s_flavor, t = flavors
        mu = _index(theory, "mu")
        first, second = fields
        if triplet:
            adj = _cg_index(theory, "J", "gen_SU2L_fund", 0)
            first_tau = _tau(
                theory,
                adj,
                _field_index(theory, "i", first, 1 if first == "q" else 0),
                _field_index(theory, "j", first, 1 if first == "q" else 0),
            )
            second_tau = _tau(
                theory,
                adj,
                _field_index(theory, "k", second, 1 if second == "q" else 0),
                _field_index(theory, "m", second, 1 if second == "q" else 0),
            )
            first_current = _vector_current(
                theory,
                first,
                p,
                r,
                mu,
                color="alpha",
                su2_left="i",
                su2_right="j",
            )
            second_current = _vector_current(
                theory,
                second,
                s_flavor,
                t,
                mu,
                color="beta",
                su2_left="k",
                su2_right="m",
            )
            return first_tau * first_current * second_tau * second_current
        if color_octet:
            adj = _cg_index(theory, "A", "gen_SU3c_fund", 0)
            first_left_color = _field_index(theory, "alpha", first, 0)
            first_right_color = _field_index(theory, "beta", first, 0)
            second_left_color = _field_index(theory, "delta", second, 0)
            second_right_color = _field_index(theory, "kappa", second, 0)
            return (
                _su3_gen(theory, adj, first_left_color, first_right_color)
                * _ncm(
                    s.Bar(_fermion(theory, first, p, color="alpha", su2="i")),
                    _gamma(mu),
                    _fermion(theory, first, r, color="beta", su2="i"),
                )
                * _su3_gen(theory, adj, second_left_color, second_right_color)
                * _ncm(
                    s.Bar(_fermion(theory, second, s_flavor, color="delta", su2="j")),
                    _gamma(mu),
                    _fermion(theory, second, t, color="kappa", su2="j"),
                )
            )
        return _vector_current(
            theory,
            first,
            p,
            r,
            mu,
            color="alpha",
            su2_left="i",
        ) * _vector_current(
            theory,
            second,
            s_flavor,
            t,
            mu,
            color="beta",
            su2_left="j",
        )

    return build


def _scalar_four_fermion_operator(kind: str) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        flavors = _flavor_tuple(theory, indices, 4)
        if flavors is None:
            return None
        p, r, s_flavor, t = flavors
        if kind == "ledq":
            if not _has(theory, fields=("l", "e", "d", "q")):
                return None
            return _ncm(s.Bar(_lepton_doublet(theory, "i", p)), _lepton_singlet(theory, r)) * _ncm(
                s.Bar(_down_quark(theory, "alpha", s_flavor)),
                _quark_doublet(theory, "alpha", "i", t),
            )
        if kind in {"quqd1", "quqd8"}:
            if not _has(theory, fields=("q", "u", "d"), cg=("eps_SU2L",)):
                return None
            first_q = _quark_doublet(theory, "alpha", "i", p)
            first_u = _up_quark(theory, "beta" if kind == "quqd8" else "alpha", r)
            second_q = _quark_doublet(theory, "delta" if kind == "quqd8" else "beta", "j", s_flavor)
            second_d = _down_quark(theory, "kappa" if kind == "quqd8" else "beta", t)
            expr = _ncm(s.Bar(first_q), first_u) * _su2_eps(
                theory,
                _field_index(theory, "i", "q", 1),
                _field_index(theory, "j", "q", 1),
            ) * _ncm(s.Bar(second_q), second_d)
            if kind == "quqd8":
                if "gen_SU3c_fund" not in theory.cg_tensors:
                    return None
                adj = _cg_index(theory, "A", "gen_SU3c_fund", 0)
                expr = (
                    _su3_gen(theory, adj, _field_index(theory, "alpha", "q", 0), _field_index(theory, "beta", "u", 0))
                    * expr
                    * _su3_gen(theory, adj, _field_index(theory, "delta", "q", 0), _field_index(theory, "kappa", "d", 0))
                )
            return expr
        if kind in {"lequ1", "lequ3"}:
            if not _has(theory, fields=("l", "e", "q", "u"), cg=("eps_SU2L",)):
                return None
            mu = _index(theory, "mu")
            nu = _index(theory, "nu")
            middle = (_sigma(mu, nu),) if kind == "lequ3" else ()
            return (
                _ncm(s.Bar(_lepton_doublet(theory, "i", p)), *middle, _lepton_singlet(theory, r))
                * _su2_eps(theory, _field_index(theory, "i", "l", 0), _field_index(theory, "j", "q", 1))
                * _ncm(s.Bar(_quark_doublet(theory, "alpha", "j", s_flavor)), *middle, _up_quark(theory, "alpha", t))
            )
        raise ValueError(f"unsupported SMEFT scalar four-fermion kind {kind!r}")

    return build


def _baryon_number_violating_operator(kind: str) -> SmeftOperatorBuilder:
    def build(theory: Theory, indices: tuple[Expression, ...]) -> Expression | None:
        if not _has(theory, fields=("q", "u", "d", "l", "e"), cg=("eps_SU3c",)):
            return None
        if kind in {"duq", "qqu", "qqq"} and "eps_SU2L" not in theory.cg_tensors:
            return None
        flavors = _flavor_tuple(theory, indices, 4)
        if flavors is None:
            return None
        p, r, s_flavor, t = flavors
        alpha = _field_index(theory, "alpha", "q", 0)
        beta = _field_index(theory, "beta", "q", 0)
        delta = _field_index(theory, "delta", "q", 0)
        color_eps = _su3_eps(theory, alpha, beta, delta, barred=True)
        if kind == "duq":
            i = _field_index(theory, "i", "q", 1)
            j = _field_index(theory, "j", "l", 0)
            return (
                color_eps
                * _su2_eps(theory, i, j, barred=True)
                * _ncm(_charge_conjugate_bar(_down_quark(theory, "alpha", p)), _up_quark(theory, "beta", r))
                * _ncm(_charge_conjugate_bar(_quark_doublet(theory, "delta", "i", s_flavor)), _lepton_doublet(theory, "j", t))
            )
        if kind == "qqu":
            i = _field_index(theory, "i", "q", 1)
            j = _field_index(theory, "j", "q", 1)
            return (
                color_eps
                * _su2_eps(theory, i, j, barred=True)
                * _ncm(_charge_conjugate_bar(_quark_doublet(theory, "alpha", "i", p)), _quark_doublet(theory, "beta", "j", r))
                * _ncm(_charge_conjugate_bar(_up_quark(theory, "delta", s_flavor)), _lepton_singlet(theory, t))
            )
        if kind == "qqq":
            i = _field_index(theory, "i", "q", 1)
            j = _field_index(theory, "j", "l", 0)
            k = _field_index(theory, "k", "q", 1)
            m = _field_index(theory, "m", "q", 1)
            return (
                color_eps
                * _su2_eps(theory, i, j, barred=True)
                * _su2_eps(theory, k, m, barred=True)
                * _ncm(_charge_conjugate_bar(_quark_doublet(theory, "alpha", "i", p)), _quark_doublet(theory, "beta", "k", r))
                * _ncm(_charge_conjugate_bar(_quark_doublet(theory, "delta", "m", s_flavor)), _lepton_doublet(theory, "j", t))
            )
        if kind == "duu":
            return color_eps * _ncm(
                _charge_conjugate_bar(_down_quark(theory, "alpha", p)),
                _up_quark(theory, "beta", r),
            ) * _ncm(
                _charge_conjugate_bar(_up_quark(theory, "delta", s_flavor)),
                _lepton_singlet(theory, t),
            )
        raise ValueError(f"unsupported SMEFT baryon-number-violating kind {kind!r}")

    return build


__all__ = [
    "SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES",
    "define_smeft_wilson_coefficient",
    "smeft_warsaw_basis",
    "smeft_warsaw_operator",
    "smeft_warsaw_operator_names",
]
