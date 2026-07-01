from __future__ import annotations

import re
from enum import StrEnum
from functools import cached_property
from typing import Any

from symbolica import Expression, S


_SYMBOL_NAMESPACE = "pychete"


def _sym(name: str, **kwargs: Any) -> Expression:
    try:
        return S(name, **kwargs)
    except TypeError:
        if "print" not in kwargs:
            raise
        retry_kwargs = dict(kwargs)
        retry_kwargs.pop("print")
        return S(name, **retry_kwargs)


class SymbolRole(StrEnum):
    """Role tags attached to pychete-managed Symbolica symbols."""

    PROJECT = "pychete"
    LABEL = "label"
    FIELD = "field"
    COUPLING = "coupling"
    INDEX = "index"
    INDEX_TYPE = "index_type"
    GROUP = "group"
    EXTERNAL = "external"


class SymbolDataKey(StrEnum):
    """Symbolica symbol-data keys used by pychete."""

    THEORY = "theory"
    ROLE = "role"
    LABEL = "label"
    NAME = "name"
    FIELD_TYPE = "field_type"
    INDICES = "indices"
    EFT_ORDER = "eft_order"
    SELF_CONJUGATE = "self_conjugate"
    MASS_KIND = "mass_kind"
    MASS_LABEL = "mass_label"
    MASS_INDICES = "mass_indices"
    CHARGES = "charges"
    DIMENSION = "dimension"
    GROUP_TYPE = "group_type"
    GROUP_COUPLING = "group_coupling"
    GROUP_FIELD = "group_field"


class SymbolStore:
    """Central store for reusable pychete Symbolica symbols.

    The package-level instance ``s`` provides expression heads such as
    ``s.Field`` and atoms such as ``s.Scalar``. Construct reusable pychete
    atoms through this store so they receive the custom pretty-printer.
    """

    namespace = _SYMBOL_NAMESPACE
    builtin_registry_names = (
        "List",
        "InternalIndices",
        "DerivativeIndices",
        "LorentzIndices",
        "Field",
        "Coupling",
        "Index",
        "dummy_index",
        "FieldStrength",
        "Bar",
        "CD",
        "Delta",
        "Metric",
        "LCTensor",
        "FlavorSum",
        "NCM",
        "DiracProduct",
        "Gamma",
        "Gamma5",
        "CG",
        "EOM",
        "HeavyFieldOrder",
        "FreeLag",
        "Scalar",
        "Fermion",
        "Vector",
        "Ghost",
        "AntiGhost",
        "Lorentz",
        "SpacetimeDimension",
        "U1",
        "SU",
        "fund",
        "adj",
        "PR",
        "PL",
        "ConjBodyWildcard",
        "NCMLeftWildcard",
        "NCMRightWildcard",
        "NCMInnerWildcard",
        "NCMFactorWildcard",
        "NCMSplitFactorWildcard",
        "NCMSplitRestWildcard",
        "NCMGammaIndexWildcard",
        "FieldLabelWildcard",
        "FieldTypeWildcard",
        "FieldIndicesWildcard",
        "FieldDerivativesWildcard",
        "IndexLabelWildcard",
        "IndexRepresentationWildcard",
        "PowBaseWildcard",
        "PowExponentWildcard",
        "CDIndexWildcard",
        "CDBodyWildcard",
        "CouplingLabelWildcard",
        "CouplingIndicesWildcard",
        "CouplingOrderWildcard",
        "FieldStrengthLabelWildcard",
        "FieldStrengthLorentzWildcard",
        "FieldStrengthIndicesWildcard",
        "FieldStrengthDerivativesWildcard",
        "EFTExpansionParameter",
        "CDVariationParameter",
        "FunctionalVariationParameter",
    )

    def head(self, name: str, **kwargs: Any) -> Expression:
        from .printing import print_builtin

        kwargs.setdefault("print", print_builtin)
        return _sym(f"{self.namespace}::{name}", **kwargs)

    @cached_property
    def SymbolicaConj(self) -> Expression:
        """Symbolica's native conjugation head used by ``Expression.conj``."""

        return _sym("symbolica::conj")

    def user(self, namespace: str, name: str, **kwargs: Any) -> Expression:
        from .printing import print_user_symbol

        kwargs.setdefault("print", print_user_symbol)
        return _sym(f"{namespace}::{safe_symbol_name(name)}", **kwargs)

    def register_builtins(self) -> None:
        for name in self.builtin_registry_names:
            getattr(self, name)

    def builtin_symbols_by_canonical_name(self) -> dict[str, Expression]:
        from .serialization import canonical_string

        self.register_builtins()
        return {canonical_string(getattr(self, name)): getattr(self, name) for name in self.builtin_registry_names}

    @cached_property
    def List(self) -> Expression:
        return self.head("List")

    @cached_property
    def InternalIndices(self) -> Expression:
        return self.head("InternalIndices")

    @cached_property
    def DerivativeIndices(self) -> Expression:
        return self.head("DerivativeIndices")

    @cached_property
    def LorentzIndices(self) -> Expression:
        return self.head("LorentzIndices")

    @cached_property
    def Field(self) -> Expression:
        return self.head("Field")

    @cached_property
    def Coupling(self) -> Expression:
        return self.head("Coupling", is_scalar=True)

    @cached_property
    def Index(self) -> Expression:
        return self.head("Index")

    @cached_property
    def dummy_index(self) -> Expression:
        return self.head("dummy_index")

    @cached_property
    def FieldStrength(self) -> Expression:
        return self.head("FieldStrength", is_scalar=True)

    @cached_property
    def Bar(self) -> Expression:
        return self.head("Bar")

    @cached_property
    def CD(self) -> Expression:
        return self.head("CD")

    @cached_property
    def Delta(self) -> Expression:
        return self.head("Delta", is_scalar=True)

    @cached_property
    def Metric(self) -> Expression:
        return self.head("Metric", is_scalar=True, is_symmetric=True)

    @cached_property
    def LCTensor(self) -> Expression:
        return self.head("LCTensor", is_scalar=True, is_antisymmetric=True)

    @cached_property
    def FlavorSum(self) -> Expression:
        return self.head("FlavorSum", is_scalar=True)

    @cached_property
    def NCM(self) -> Expression:
        return self.head("NCM", is_linear=True)

    @cached_property
    def DiracProduct(self) -> Expression:
        return self.head("DiracProduct")

    @cached_property
    def Gamma(self) -> Expression:
        return self.head("Gamma", is_antisymmetric=True)

    @cached_property
    def Gamma5(self) -> Expression:
        return self.head("Gamma5")

    @cached_property
    def CG(self) -> Expression:
        return self.head("CG")

    @cached_property
    def EOM(self) -> Expression:
        return self.head("EOM")

    @cached_property
    def HeavyFieldOrder(self) -> Expression:
        return self.head("HeavyFieldOrder")

    @cached_property
    def FreeLag(self) -> Expression:
        return self.head("FreeLag")

    @cached_property
    def Scalar(self) -> Expression:
        return self.head("Scalar")

    @cached_property
    def Fermion(self) -> Expression:
        return self.head("Fermion")

    @cached_property
    def Vector(self) -> Expression:
        return self.head("Vector")

    @cached_property
    def Ghost(self) -> Expression:
        return self.head("Ghost")

    @cached_property
    def AntiGhost(self) -> Expression:
        return self.head("AntiGhost")

    @cached_property
    def Lorentz(self) -> Expression:
        return self.head("Lorentz")

    @cached_property
    def SpacetimeDimension(self) -> Expression:
        return self.head("SpacetimeDimension", is_scalar=True)

    @cached_property
    def U1(self) -> Expression:
        return self.head("U1")

    @cached_property
    def SU(self) -> Expression:
        return self.head("SU")

    @cached_property
    def fund(self) -> Expression:
        return self.head("fund")

    @cached_property
    def adj(self) -> Expression:
        return self.head("adj")

    @cached_property
    def PR(self) -> Expression:
        return self.head("PR")

    @cached_property
    def PL(self) -> Expression:
        return self.head("PL")

    @cached_property
    def ConjBodyWildcard(self) -> Expression:
        return self.head("conj_body_")

    @cached_property
    def NCMLeftWildcard(self) -> Expression:
        return self.head("ncm_left__")

    @cached_property
    def NCMRightWildcard(self) -> Expression:
        return self.head("ncm_right__")

    @cached_property
    def NCMInnerWildcard(self) -> Expression:
        return self.head("ncm_inner__")

    @cached_property
    def NCMFactorWildcard(self) -> Expression:
        return self.head("ncm_factor_")

    @cached_property
    def NCMSplitFactorWildcard(self) -> Expression:
        return self.head("ncm_split_factor_")

    @cached_property
    def NCMSplitRestWildcard(self) -> Expression:
        return self.head("ncm_split_rest_")

    @cached_property
    def NCMGammaIndexWildcard(self) -> Expression:
        return self.head("ncm_gamma_index_")

    @cached_property
    def FieldLabelWildcard(self) -> Expression:
        return self.head("field_label_")

    @cached_property
    def FieldTypeWildcard(self) -> Expression:
        return self.head("field_type_")

    @cached_property
    def FieldIndicesWildcard(self) -> Expression:
        return self.head("field_indices_")

    @cached_property
    def FieldDerivativesWildcard(self) -> Expression:
        return self.head("field_derivatives_")

    @cached_property
    def IndexLabelWildcard(self) -> Expression:
        return self.head("index_label_")

    @cached_property
    def IndexRepresentationWildcard(self) -> Expression:
        return self.head("index_representation_")

    @cached_property
    def PowBaseWildcard(self) -> Expression:
        return self.head("pow_base_")

    @cached_property
    def PowExponentWildcard(self) -> Expression:
        return self.head("pow_exponent_")

    @cached_property
    def CDIndexWildcard(self) -> Expression:
        return self.head("cd_index_")

    @cached_property
    def CDBodyWildcard(self) -> Expression:
        return self.head("cd_body_")

    @cached_property
    def CouplingLabelWildcard(self) -> Expression:
        return self.head("coupling_label_")

    @cached_property
    def CouplingIndicesWildcard(self) -> Expression:
        return self.head("coupling_indices_")

    @cached_property
    def CouplingOrderWildcard(self) -> Expression:
        return self.head("coupling_order_")

    @cached_property
    def FieldStrengthLabelWildcard(self) -> Expression:
        return self.head("field_strength_label_")

    @cached_property
    def FieldStrengthLorentzWildcard(self) -> Expression:
        return self.head("field_strength_lorentz_")

    @cached_property
    def FieldStrengthIndicesWildcard(self) -> Expression:
        return self.head("field_strength_indices_")

    @cached_property
    def FieldStrengthDerivativesWildcard(self) -> Expression:
        return self.head("field_strength_derivatives_")

    @cached_property
    def EFTExpansionParameter(self) -> Expression:
        return self.head("eft_order_parameter", is_scalar=True)

    @cached_property
    def CDVariationParameter(self) -> Expression:
        return self.head("cd_variation_parameter", is_scalar=True)

    @cached_property
    def FunctionalVariationParameter(self) -> Expression:
        return self.head("functional_variation_parameter", is_scalar=True)


s = SymbolStore()


_GREEK_ESCAPES = {
    r"\[Phi]": "phi",
    r"\[Psi]": "psi",
    r"\[CapitalPhi]": "Phi",
    r"\[CapitalPsi]": "Psi",
    r"\[Lambda]": "lambda",
    r"\[Kappa]": "kappa",
    r"\[Mu]": "mu",
    r"\[Nu]": "nu",
}


def safe_symbol_name(name: str) -> str:
    out = name.strip()
    for source, replacement in _GREEK_ESCAPES.items():
        out = out.replace(source, replacement)
    out = re.sub(r"[^0-9A-Za-z_]+", "_", out)
    out = out.strip("_")
    if not out:
        out = "unnamed"
    if out[0].isdigit():
        out = f"n_{out}"
    return out


def symbol_data(expr: Expression, key: SymbolDataKey, default: Any = None) -> Any:
    try:
        return expr.get_symbol_data(key.value)
    except KeyError:
        return default
