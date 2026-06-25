from __future__ import annotations

from symbolica import Expression

from ..symbols import s

Dimension = int | Expression


def _idenso():
    import symbolica.community.idenso as idenso

    return idenso


def _spenso():
    import symbolica.community.spenso as spenso

    return spenso


def simplify_gamma(expr: Expression) -> Expression:
    """Simplify Dirac gamma algebra through idenso."""

    return _idenso().simplify_gamma(expr)


def simplify_metrics(expr: Expression) -> Expression:
    """Simplify metric contractions through idenso."""

    return _idenso().simplify_metrics(expr)


def tensor_representations(dim: Dimension):
    """Return Lorentz and bispinor tensor representations consumed by idenso.

    spenso owns these tensor constructors, but the resulting Symbolica
    expressions are built for the idenso simplification pipeline.
    """

    spenso = _spenso()
    return spenso.Representation.mink(dim), spenso.Representation.bis(dim)


def gamma_tensor(mu: Expression, left: Expression, right: Expression, *, dim: Dimension) -> Expression:
    """Build a gamma-matrix tensor expression in idenso's expected convention."""

    spenso = _spenso()
    mink, bis = tensor_representations(dim)
    return spenso.TensorName.gamma()(bis(left), bis(right), mink(mu)).to_expression()


def chiral_projector_tensor(chirality: Expression, left: Expression, right: Expression, *, dim: Dimension) -> Expression:
    """Build a chiral-projector tensor expression in idenso's convention."""

    spenso = _spenso()
    _, bis = tensor_representations(dim)
    if bool(chirality == s.PL):
        name = spenso.TensorName.projm()
    elif bool(chirality == s.PR):
        name = spenso.TensorName.projp()
    else:
        raise ValueError("chirality must be s.PL or s.PR")
    return name(bis(left), bis(right)).to_expression()


def spin_metric_tensor(left: Expression, right: Expression, *, dim: Dimension) -> Expression:
    """Build a bispinor metric tensor expression in idenso's convention."""

    spenso = _spenso()
    _, bis = tensor_representations(dim)
    return spenso.TensorName.g()(bis(left), bis(right)).to_expression()
