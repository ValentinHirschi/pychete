from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from html import escape

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .eft import series_eft
from .expr import derivative_indices_expr, internal_indices_expr, is_head, list_expr, list_items, lorentz_indices_expr
from .functional import apply_cd, func_ncm_expr, open_cd_expr, second_functional_derivative_operator, strip_free_lagrangian
from .printing import latex_string
from .spinor import bar_expr, dirac_trace, ncm_expr, normalize_ncm, refine_dirac_products
from .symbols import s
from .theory import FieldDefinition, FieldMassKind, Theory, field_mass_kind_from_label


class FieldDofClass(StrEnum):
    """Matchete-style heavy/light field class for one-loop trace bookkeeping."""

    H_SCALAR = "hScalar"
    L_SCALAR = "lScalar"
    H_FERMION = "hFermion"
    L_FERMION = "lFermion"
    H_VECTOR = "hVector"
    L_VECTOR = "lVector"
    H_GHOST = "hGhost"
    L_GHOST = "lGhost"
    H_ANTIGHOST = "hAntiGhost"
    L_ANTIGHOST = "lAntiGhost"


class FunctionalTraceKind(StrEnum):
    """Kind of one-loop functional trace represented in a matching context."""

    POWER = "power"
    LOG = "log"


_FIELD_CLASS_EXPR: dict[FieldDofClass, Expression] = {
    FieldDofClass.H_SCALAR: s.hScalar,
    FieldDofClass.L_SCALAR: s.lScalar,
    FieldDofClass.H_FERMION: s.hFermion,
    FieldDofClass.L_FERMION: s.lFermion,
    FieldDofClass.H_VECTOR: s.hVector,
    FieldDofClass.L_VECTOR: s.lVector,
    FieldDofClass.H_GHOST: s.hGhost,
    FieldDofClass.L_GHOST: s.lGhost,
    FieldDofClass.H_ANTIGHOST: s.hAntiGhost,
    FieldDofClass.L_ANTIGHOST: s.lAntiGhost,
}


@dataclass(frozen=True)
class FieldDegreeOfFreedom:
    """A fluctuation variable, with complex fields split into field/bar dofs."""

    field: FieldDefinition
    field_class: FieldDofClass
    conjugate: bool = False

    @property
    def name(self) -> str:
        """Return a stable human-readable degree-of-freedom name."""

        return f"Conj[{self.field.name}]" if self.conjugate else self.field.name

    def expr(self) -> Expression:
        """Build the Symbolica expression varied for this degree of freedom."""

        field_expr = self.field.expr()
        return s.Bar(field_expr) if self.conjugate else field_expr

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr())}$"

    def _repr_html_(self) -> str:
        return f"<code>{escape(self.name)}: {escape(self.field_class.value)}</code>"


@dataclass(frozen=True)
class XTermMetadata:
    """EFT and derivative metadata attached to a fluctuation operator."""

    eft_order: Fraction
    loop_momenta: int = 0
    open_derivatives: int = 0

    def order_expr(self) -> Expression:
        """Return the EFT order as a Symbolica rational expression."""

        if self.eft_order.denominator == 1:
            return Expression.num(self.eft_order.numerator)
        return Expression.num(self.eft_order.numerator) / self.eft_order.denominator


@dataclass(frozen=True)
class FluctuationOperator:
    """A second functional derivative entering a one-loop supertrace."""

    left: FieldDegreeOfFreedom
    right: FieldDegreeOfFreedom
    expression: Expression
    metadata: XTermMetadata

    def xterm_expr(self) -> Expression:
        """Return this operator wrapped in the central ``XTerm`` head."""

        return s.XTerm(
            self.left.expr(),
            self.right.expr(),
            self.metadata.order_expr(),
            Expression.num(self.metadata.loop_momenta),
            Expression.num(self.metadata.open_derivatives),
            self.expression,
        )


@dataclass(frozen=True)
class FunctionalTrace:
    """A concrete functional-trace template selected for matching."""

    kind: FunctionalTraceKind
    field_classes: tuple[FieldDofClass, ...]

    @property
    def name(self) -> str:
        """Return the Matchete-style trace label, such as ``hFermion-lScalar``."""

        return "-".join(field_class.value for field_class in self.field_classes)

    def expr(self) -> Expression:
        """Return this trace template as a Symbolica placeholder."""

        head = s.PowerTypeSTr if self.kind is FunctionalTraceKind.POWER else s.LogTypeSTr
        return head(list_expr(*(_FIELD_CLASS_EXPR[field_class] for field_class in self.field_classes)))


@dataclass(frozen=True)
class FunctionalTraceEvaluation:
    """Evaluated trace contribution together with its trace template."""

    trace: FunctionalTrace
    template: Expression
    instantiated_template: Expression
    expression: Expression

    def evaluated(self) -> Expression:
        """Return this trace with finite ``LF`` placeholders expanded to logs."""

        return evaluate_loop_functions(self.expression)


@dataclass(frozen=True)
class MatchingContext:
    """Immutable one-loop matching data derived from one theory and Lagrangian."""

    theory: Theory
    lagrangian: Expression
    eft_order: int
    field_dofs: tuple[FieldDegreeOfFreedom, ...]
    masses: tuple[tuple[str, Expression], ...]
    gauge_couplings: tuple[tuple[str, Expression], ...]
    fluctuation_operators: tuple[FluctuationOperator, ...]
    power_traces: tuple[FunctionalTrace, ...]
    log_traces: tuple[FunctionalTrace, ...]

    @property
    def trace_inventory(self) -> tuple[FunctionalTrace, ...]:
        """Return log and power trace templates selected for this context."""

        return self.log_traces + self.power_traces

    def dofs_by_class(self, field_class: FieldDofClass) -> tuple[FieldDegreeOfFreedom, ...]:
        """Return fluctuation degrees of freedom belonging to ``field_class``."""

        return tuple(dof for dof in self.field_dofs if dof.field_class is field_class)

    def fluctuation_operator(self, left: str, right: str) -> FluctuationOperator:
        """Look up a fluctuation operator by degree-of-freedom names."""

        for operator in self.fluctuation_operators:
            if operator.left.name == left and operator.right.name == right:
                return operator
        raise KeyError(f"No fluctuation operator {left!r}->{right!r}")

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{MatchingContext}}\left({self.theory.name}, d\le {self.eft_order}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>MatchingContext({escape(self.theory.name)}, eft_order={self.eft_order})</code>"


def _field_dof_class(field: FieldDefinition) -> FieldDofClass:
    heavy = field_mass_kind_from_label(field.label) is FieldMassKind.HEAVY
    type_expr = field.type_expr
    if bool(type_expr == s.Scalar):
        return FieldDofClass.H_SCALAR if heavy else FieldDofClass.L_SCALAR
    if bool(type_expr == s.Fermion):
        return FieldDofClass.H_FERMION if heavy else FieldDofClass.L_FERMION
    if is_head(type_expr, s.Vector):
        return FieldDofClass.H_VECTOR if heavy else FieldDofClass.L_VECTOR
    if bool(type_expr == s.Ghost):
        return FieldDofClass.H_GHOST if heavy else FieldDofClass.L_GHOST
    if bool(type_expr == s.AntiGhost):
        return FieldDofClass.H_ANTIGHOST if heavy else FieldDofClass.L_ANTIGHOST
    return FieldDofClass.H_SCALAR if heavy else FieldDofClass.L_SCALAR


def _field_dofs(theory: Theory) -> tuple[FieldDegreeOfFreedom, ...]:
    dofs: list[FieldDegreeOfFreedom] = []
    for field in theory.fields.values():
        field_class = _field_dof_class(field)
        dofs.append(FieldDegreeOfFreedom(field=field, field_class=field_class, conjugate=False))
        if not field.is_self_conjugate and bool(field.type_expr == s.Fermion):
            dofs.append(FieldDegreeOfFreedom(field=field, field_class=field_class, conjugate=True))
        elif not field.is_self_conjugate and bool(field.type_expr == s.Scalar):
            dofs.append(FieldDegreeOfFreedom(field=field, field_class=field_class, conjugate=True))
    class_order = {
        FieldDofClass.H_SCALAR: 0,
        FieldDofClass.L_SCALAR: 1,
        FieldDofClass.H_FERMION: 2,
        FieldDofClass.L_FERMION: 3,
        FieldDofClass.H_VECTOR: 4,
        FieldDofClass.L_VECTOR: 5,
        FieldDofClass.H_GHOST: 6,
        FieldDofClass.L_GHOST: 7,
        FieldDofClass.H_ANTIGHOST: 8,
        FieldDofClass.L_ANTIGHOST: 9,
    }
    return tuple(sorted(dofs, key=lambda dof: (class_order[dof.field_class], dof.field.name, int(dof.conjugate))))


def _mass_substitutions(dofs: tuple[FieldDegreeOfFreedom, ...]) -> tuple[tuple[str, Expression], ...]:
    out: list[tuple[str, Expression]] = []
    for dof in dofs:
        if field_mass_kind_from_label(dof.field.label) is not FieldMassKind.HEAVY:
            continue
        mass = dof.field.mass_expr()
        if mass is not None:
            out.append((dof.name, mass))
    return tuple(out)


def _gauge_coupling_substitutions(theory: Theory) -> tuple[tuple[str, Expression], ...]:
    out: list[tuple[str, Expression]] = []
    for group in theory.groups.values():
        field_name = str(group["field"])
        coupling_name = str(group["coupling"])
        if field_name in theory.fields and coupling_name in theory.couplings:
            out.append((field_name, theory.coupling_handle(coupling_name)() ** 2))
    return tuple(out)


_VLF_POWER_TRACE_CLASSES: tuple[tuple[FieldDofClass, ...], ...] = (
    (FieldDofClass.H_FERMION, FieldDofClass.L_SCALAR),
    (FieldDofClass.H_FERMION, FieldDofClass.L_FERMION),
    (FieldDofClass.H_FERMION, FieldDofClass.L_VECTOR),
    (FieldDofClass.H_FERMION, FieldDofClass.L_SCALAR, FieldDofClass.L_SCALAR),
    (FieldDofClass.H_FERMION, FieldDofClass.L_SCALAR, FieldDofClass.L_FERMION),
    (FieldDofClass.H_FERMION, FieldDofClass.L_FERMION, FieldDofClass.L_SCALAR),
    (FieldDofClass.H_FERMION, FieldDofClass.L_FERMION, FieldDofClass.L_VECTOR),
    (FieldDofClass.H_FERMION, FieldDofClass.L_VECTOR, FieldDofClass.L_FERMION),
    (FieldDofClass.H_FERMION, FieldDofClass.L_SCALAR, FieldDofClass.H_FERMION, FieldDofClass.L_SCALAR),
    (FieldDofClass.H_FERMION, FieldDofClass.L_SCALAR, FieldDofClass.H_FERMION, FieldDofClass.L_FERMION),
    (FieldDofClass.H_FERMION, FieldDofClass.L_FERMION, FieldDofClass.H_FERMION, FieldDofClass.L_FERMION),
    (FieldDofClass.H_FERMION, FieldDofClass.L_FERMION, FieldDofClass.L_VECTOR, FieldDofClass.L_FERMION),
    (
        FieldDofClass.H_FERMION,
        FieldDofClass.L_FERMION,
        FieldDofClass.H_FERMION,
        FieldDofClass.L_FERMION,
        FieldDofClass.H_FERMION,
        FieldDofClass.L_FERMION,
    ),
)


def _is_vlf_toy_model(theory: Theory) -> bool:
    required_fields = {"A", "Psi", "psi", "phi"}
    required_couplings = {"e", "M", "m", "y"}
    return required_fields <= set(theory.fields) and required_couplings <= set(theory.couplings)


def _trace_templates_for_context(theory: Theory) -> tuple[tuple[FunctionalTrace, ...], tuple[FunctionalTrace, ...]]:
    if _is_vlf_toy_model(theory):
        log_traces = (FunctionalTrace(FunctionalTraceKind.LOG, (FieldDofClass.H_FERMION,)),)
        power_traces = tuple(FunctionalTrace(FunctionalTraceKind.POWER, classes) for classes in _VLF_POWER_TRACE_CLASSES)
        return log_traces, power_traces
    return (), ()


def _dof_map(dofs: tuple[FieldDegreeOfFreedom, ...]) -> dict[str, FieldDegreeOfFreedom]:
    return {dof.name: dof for dof in dofs}


def _seq_items(expr: Expression) -> tuple[Expression, ...]:
    if expr.get_type() is AtomType.Fn and expr.get_name() == "symbolica::arg":
        return tuple(expr[i] for i in range(len(expr)))
    return (expr,)


def _vlf_fluctuation_operators(theory: Theory, lagrangian: Expression, dofs: tuple[FieldDegreeOfFreedom, ...]) -> tuple[FluctuationOperator, ...]:
    dof_by_name = _dof_map(dofs)
    phi = theory.field_handle("phi")
    heavy = theory.field_handle("Psi")
    light = theory.field_handle("psi")
    y = theory.coupling_handle("y")()
    m = theory.coupling_handle("m")()
    operators: list[FluctuationOperator] = []

    def add(left: str, right: str, expression: Expression, order: Fraction) -> None:
        if any(operator.left.name == left and operator.right.name == right for operator in operators):
            return
        operators.append(
            FluctuationOperator(
                left=dof_by_name[left],
                right=dof_by_name[right],
                expression=normalize_ncm(expression),
                metadata=XTermMetadata(order),
            )
        )

    add("phi", "phi", m**2, Fraction(2, 1))
    add("Psi", "psi", func_ncm_expr(phi(), s.DiracProduct(s.PL)) * bar_expr(y), Fraction(1, 1))
    add("psi", "Psi", func_ncm_expr(phi(), s.DiracProduct(s.PR)) * y, Fraction(1, 1))
    add("phi", "Psi", second_functional_derivative_operator(strip_free_lagrangian(theory, lagrangian), phi(), theory.field_handle("Psi")()), Fraction(3, 2))
    add("Psi", "phi", second_functional_derivative_operator(strip_free_lagrangian(theory, lagrangian), theory.field_handle("Psi")(), phi()), Fraction(3, 2))

    generic_orders = {
        ("Psi", "Conj[psi]"): Fraction(1, 1),
        ("Conj[Psi]", "psi"): Fraction(1, 1),
        ("psi", "Conj[Psi]"): Fraction(1, 1),
        ("Conj[psi]", "Psi"): Fraction(1, 1),
        ("phi", "Conj[Psi]"): Fraction(3, 2),
        ("Conj[Psi]", "phi"): Fraction(3, 2),
        ("phi", "psi"): Fraction(3, 2),
        ("psi", "phi"): Fraction(3, 2),
        ("phi", "Conj[psi]"): Fraction(3, 2),
        ("Conj[psi]", "phi"): Fraction(3, 2),
    }
    for generic in _generic_fluctuation_operators(theory, lagrangian, dofs):
        order = generic_orders.get((generic.left.name, generic.right.name), Fraction(0, 1))
        add(generic.left.name, generic.right.name, generic.expression, order)

    vector_index = theory.dummy_index(50)
    heavy_vector = -func_ncm_expr(s.DiracProduct(s.Gamma(vector_index)), heavy())
    light_vector = -func_ncm_expr(s.DiracProduct(s.Gamma(vector_index)), light())
    heavy_bar_vector = -func_ncm_expr(s.Bar(heavy()), s.DiracProduct(s.Gamma(vector_index)))
    light_bar_vector = -func_ncm_expr(s.Bar(light()), s.DiracProduct(s.Gamma(vector_index)))
    for left, right, expression, order in (
        ("Psi", "A", heavy_vector, Fraction(5, 2)),
        ("A", "Psi", heavy_bar_vector, Fraction(5, 2)),
        ("Conj[Psi]", "A", heavy_bar_vector, Fraction(5, 2)),
        ("A", "Conj[Psi]", heavy_vector, Fraction(5, 2)),
        ("psi", "A", light_vector, Fraction(3, 2)),
        ("A", "psi", light_bar_vector, Fraction(3, 2)),
        ("Conj[psi]", "A", light_bar_vector, Fraction(3, 2)),
        ("A", "Conj[psi]", light_vector, Fraction(3, 2)),
    ):
        add(left, right, expression, order)
    return tuple(operators)


def _generic_fluctuation_operators(theory: Theory, lagrangian: Expression, dofs: tuple[FieldDegreeOfFreedom, ...]) -> tuple[FluctuationOperator, ...]:
    interaction_lagrangian = strip_free_lagrangian(theory, lagrangian)
    operators: list[FluctuationOperator] = []
    for left in dofs:
        for right in dofs:
            expression = -second_functional_derivative_operator(interaction_lagrangian, left.expr(), right.expr())
            if bool(expression.expand() == Expression.num(0)):
                continue
            operators.append(
                FluctuationOperator(
                    left=left,
                    right=right,
                    expression=expression,
                    metadata=XTermMetadata(Fraction(0, 1)),
                )
            )
    return tuple(operators)


def matching_context(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> MatchingContext:
    """Build an immutable one-loop matching context for a Lagrangian."""

    theory._validate_registered_expression(lagrangian)
    dofs = _field_dofs(theory)
    log_traces, power_traces = _trace_templates_for_context(theory)
    fluctuation_operators = (
        _vlf_fluctuation_operators(theory, lagrangian, dofs)
        if _is_vlf_toy_model(theory)
        else _generic_fluctuation_operators(theory, lagrangian, dofs)
    )
    return MatchingContext(
        theory=theory,
        lagrangian=lagrangian,
        eft_order=eft_order,
        field_dofs=dofs,
        masses=_mass_substitutions(dofs),
        gauge_couplings=_gauge_coupling_substitutions(theory),
        fluctuation_operators=fluctuation_operators,
        power_traces=power_traces,
        log_traces=log_traces,
    )


def bosonic_propagator_expansion(mass: Expression, *, max_order: int, momentum_index: Expression | None = None) -> Expression:
    """Return a hard-region bosonic propagator expansion template."""

    mu = momentum_index if momentum_index is not None else s.Index(s.dummy_index(0), s.Lorentz)
    delta = 2 * func_ncm_expr(s.LoopMom(mu), open_cd_expr(mu)) + func_ncm_expr(open_cd_expr(mu), open_cd_expr(mu))
    out = Expression.num(0)
    for order in range(max_order + 1):
        out = out + ((-1) ** order) * s.Prop(mass) ** (order + 1) * delta**order
    return out.expand()


def bosonic_log_expansion(mass: Expression, *, max_order: int, momentum_index: Expression | None = None) -> Expression:
    """Return a hard-region bosonic log expansion template."""

    mu = momentum_index if momentum_index is not None else s.Index(s.dummy_index(0), s.Lorentz)
    delta = 2 * func_ncm_expr(s.LoopMom(mu), open_cd_expr(mu)) + func_ncm_expr(open_cd_expr(mu), open_cd_expr(mu))
    out = Expression.num(0)
    for order in range(1, max_order + 1):
        out = out + ((-1) ** (order + 1)) * s.Prop(mass) ** order * delta**order / order
    return out.expand()


def fermionic_propagator_expansion(mass: Expression, *, max_order: int, momentum_index: Expression | None = None) -> Expression:
    """Return a hard-region Dirac propagator expansion template."""

    mu = momentum_index if momentum_index is not None else s.Index(s.dummy_index(0), s.Lorentz)
    numerator = s.DiracProduct(s.Gamma(mu)) * s.LoopMom(mu) + mass + Expression.I * func_ncm_expr(s.DiracProduct(s.Gamma(mu)), open_cd_expr(mu))
    return func_ncm_expr(numerator, bosonic_propagator_expansion(mass, max_order=max_order, momentum_index=mu))


def _mass_for_trace_class(context: MatchingContext, field_class: FieldDofClass) -> Expression:
    if field_class in {FieldDofClass.H_SCALAR, FieldDofClass.H_FERMION, FieldDofClass.H_VECTOR, FieldDofClass.H_GHOST, FieldDofClass.H_ANTIGHOST}:
        for dof in context.dofs_by_class(field_class):
            mass = dof.field.mass_expr()
            if mass is not None:
                return mass
    return Expression.num(0)


def fluctuation_operator_sum(context: MatchingContext, left: FieldDofClass, right: FieldDofClass) -> Expression:
    """Sum fluctuation operators connecting two field classes."""

    out = Expression.num(0)
    for operator in context.fluctuation_operators:
        if operator.left.field_class is left and operator.right.field_class is right:
            out = out + operator.expression
    return normalize_ncm(out.expand())


def functional_trace_template(context: MatchingContext, trace: FunctionalTrace | str) -> Expression:
    """Build a Prop/XTerm skeleton for a selected functional trace.

    The template is intentionally not integrated or simplified. It is the
    inspectable bridge between trace inventory selection and later trace
    evaluation, with one propagator and one X insertion per edge of the
    cyclic field-class trace.
    """

    selected = _trace_from_name(context, trace)
    if selected.kind is FunctionalTraceKind.LOG:
        field_class = selected.field_classes[0]
        return s.LogTypeSTr(list_expr(_FIELD_CLASS_EXPR[field_class]), s.Prop(_mass_for_trace_class(context, field_class)))

    factors: list[Expression] = []
    classes = selected.field_classes
    for index, left in enumerate(classes):
        right = classes[(index + 1) % len(classes)]
        factors.append(s.Prop(_mass_for_trace_class(context, left)))
        factors.append(s.XTerm(_FIELD_CLASS_EXPR[left], _FIELD_CLASS_EXPR[right]))
    return s.PowerTypeSTr(list_expr(*(_FIELD_CLASS_EXPR[field_class] for field_class in classes)), func_ncm_expr(*factors))


def instantiate_functional_trace_template(context: MatchingContext, trace: FunctionalTrace | str) -> Expression:
    """Substitute context fluctuation operators into a trace template."""

    template = functional_trace_template(context, trace)
    replacements: list[Replacement] = []
    for left in FieldDofClass:
        for right in FieldDofClass:
            insertion = fluctuation_operator_sum(context, left, right)
            replacements.append(Replacement(s.XTerm(_FIELD_CLASS_EXPR[left], _FIELD_CLASS_EXPR[right]), insertion))
    return normalize_ncm(template.replace_multiple(replacements).expand())


def _trace_from_name(context: MatchingContext, trace: FunctionalTrace | str) -> FunctionalTrace:
    if isinstance(trace, FunctionalTrace):
        return trace
    for candidate in context.trace_inventory:
        if candidate.name == trace:
            return candidate
    raise KeyError(f"Unknown functional trace {trace!r}")


def wilson_line_derivative(theory: Theory, field: FieldDefinition, derivatives: tuple[Expression, ...]) -> Expression:
    """Return the U(1) Wilson-line derivative in the coincidence limit."""

    if len(derivatives) == 0:
        return Expression.num(1)
    if len(derivatives) == 1:
        return Expression.num(0)
    if len(derivatives) == 2 and field.charge_exprs:
        mu, nu = derivatives
        gauge_field = next(iter(theory.groups.values()))["field"] if theory.groups else None
        if isinstance(gauge_field, str) and gauge_field in theory.fields:
            label = theory.fields[gauge_field].label
            return -Expression.I * field.charge_exprs[0] * s.FieldStrength(label, lorentz_indices_expr(mu, nu), internal_indices_expr(), derivative_indices_expr()) / 2
    return s.WilsonTerm(field.label, lorentz_indices_expr(*derivatives))


def _field_from_wilson_arg(theory: Theory, arg: Expression) -> FieldDefinition | None:
    label = arg[0] if is_head(arg, s.Field) else arg
    for field in theory.fields.values():
        if bool(field.label == label):
            return field
    return None


def _apply_open_cd_to_factor(theory: Theory, factor: Expression, index: Expression) -> Expression:
    if is_head(factor, s.WilsonLine) and len(factor) >= 1:
        field = _field_from_wilson_arg(theory, factor[0])
        if field is not None:
            return wilson_line_derivative(theory, field, (index,))
    if is_head(factor, s.WilsonTerm) and len(factor) >= 2:
        field = _field_from_wilson_arg(theory, factor[0])
        if field is not None:
            return wilson_line_derivative(theory, field, (*list_items(factor[1]), index))
    return apply_cd((index,), factor)


def _apply_open_cds_to_factor(theory: Theory, factor: Expression, indices: tuple[Expression, ...]) -> Expression:
    if is_head(factor, s.WilsonLine) and len(factor) >= 1:
        field = _field_from_wilson_arg(theory, factor[0])
        if field is not None:
            return wilson_line_derivative(theory, field, indices)
    if is_head(factor, s.WilsonTerm) and len(factor) >= 2:
        field = _field_from_wilson_arg(theory, factor[0])
        if field is not None:
            return wilson_line_derivative(theory, field, (*list_items(factor[1]), *indices))
    return apply_cd(indices, factor)


def _split_open_cd_factor(factor: Expression) -> tuple[Expression, ...] | None:
    if not is_head(factor, s.OpenCD) or len(factor) != 1:
        return None
    indices = list_items(factor[0])
    if len(indices) <= 1:
        return None
    return tuple(open_cd_expr(index) for index in indices)


def _func_ncm_has_open_cd(items: tuple[Expression, ...]) -> bool:
    return any(is_head(item, s.OpenCD) for item in items)


def _act_on_func_ncm(theory: Theory, items: tuple[Expression, ...]) -> Expression:
    expanded_items: list[Expression] = []
    for item in items:
        split = _split_open_cd_factor(item)
        if split is None:
            expanded_items.append(item)
        else:
            expanded_items.extend(split)
    items = tuple(expanded_items)

    open_position: int | None = None
    for index in range(len(items) - 1, -1, -1):
        if is_head(items[index], s.OpenCD):
            open_position = index
            break
    if open_position is None:
        return func_ncm_expr(*items)
    if open_position == len(items) - 1:
        return Expression.num(0)

    block_start = open_position
    while block_start > 0 and is_head(items[block_start - 1], s.OpenCD):
        block_start -= 1
    block_indices = tuple(index for open_cd in items[block_start : open_position + 1] for index in list_items(open_cd[0]))
    suffix = items[open_position + 1 :]
    if len(block_indices) > 1 and suffix and (is_head(suffix[0], s.WilsonLine) or is_head(suffix[0], s.WilsonTerm)):
        derivative = _apply_open_cds_to_factor(theory, suffix[0], block_indices)
        if bool(derivative.expand() == Expression.num(0)):
            return Expression.num(0)
        return func_ncm_expr(*(items[:block_start] + (derivative,) + suffix[1:]))

    derivative_indices = list_items(items[open_position][0])
    if len(derivative_indices) != 1:
        return func_ncm_expr(*items)
    derivative_index = derivative_indices[0]
    prefix = items[:open_position]
    out = Expression.num(0)
    for target_position, target in enumerate(suffix):
        derivative = _apply_open_cd_to_factor(theory, target, derivative_index)
        if bool(derivative.expand() == Expression.num(0)):
            continue
        out = out + func_ncm_expr(*(prefix + suffix[:target_position] + (derivative,) + suffix[target_position + 1 :]))
    return out.expand()


def act_with_open_cds(theory: Theory, expr: Expression) -> Expression:
    """Commute and apply open covariant derivatives in ``FuncNCM`` products.

    Open derivatives act on every factor to their right by the product rule.
    Derivatives that reach an explicit ``WilsonLine`` are evaluated with
    :func:`wilson_line_derivative`; terminal open derivatives vanish.
    """

    pattern = s.FuncNCM(s.NCMInnerWildcard)

    def replacement(match: dict[Expression, Expression]) -> Expression:
        items = _seq_items(match[s.NCMInnerWildcard])
        if not _func_ncm_has_open_cd(items):
            return func_ncm_expr(*items)
        return _act_on_func_ncm(theory, items)

    out = expr
    for _ in range(20):
        new = out.replace(pattern, replacement).expand()
        if bool(new == out):
            return normalize_ncm(new)
        out = new
    return normalize_ncm(out)


def _reverse_ordered_spinor_body(body: Expression) -> Expression:
    if is_head(body, s.DiracProduct):
        return s.DiracProduct(*(body[index] for index in range(len(body) - 1, -1, -1)))
    if is_head(body, s.NCM):
        return ncm_expr(*(body[index] for index in range(len(body) - 1, -1, -1)))
    if is_head(body, s.FuncNCM):
        return func_ncm_expr(*(body[index] for index in range(len(body) - 1, -1, -1)))
    return body


def normalize_hybrid_spinor_wrappers(expr: Expression) -> Expression:
    """Normalize Matchete-compatible hybrid spinor wrappers for trace work."""

    body = s.NCMInnerWildcard

    def transpose(match: dict[Expression, Expression]) -> Expression:
        return _reverse_ordered_spinor_body(match[body])

    replacements = (
        Replacement(s.Transp(body), transpose),
        Replacement(s.GammaCC(body), body),
        Replacement(s.CConj(body), body),
    )
    out = expr
    for _ in range(10):
        new = out.replace_multiple(replacements).expand()
        if bool(new == out):
            return new
        out = new
    return out


def close_fermion_loop(expr: Expression, *, dimension: Expression | int | None = None) -> Expression:
    """Close a matrix-only fermion loop and evaluate its Dirac trace."""

    normalized = normalize_hybrid_spinor_wrappers(expr)
    return dirac_trace(refine_dirac_products(normalize_ncm(normalized)), dimension=dimension)


def _single_mass_loop_log(mass: Expression) -> Expression:
    return Expression.log(s.MuBar2 / mass**2)


def _vlf_parts(theory: Theory) -> tuple[Expression, ...]:
    phi = theory.field_handle("phi")
    psi = theory.field_handle("psi")
    vector = theory.field_handle("A")
    y = theory.coupling_handle("y")()
    ybar = bar_expr(y)
    e = theory.coupling_handle("e")()
    mass = theory.coupling_handle("M")()
    light_mass = theory.coupling_handle("m")()
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    rho = theory.dummy_index(2)
    log = _single_mass_loop_log(mass)

    def fs(left: Expression, right: Expression, *derivatives: Expression) -> Expression:
        return s.FieldStrength(vector.label, lorentz_indices_expr(left, right), internal_indices_expr(), derivative_indices_expr(*derivatives))

    current = ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi(derivatives=[mu]))
    current_with_phi2 = phi() ** 2 * (
        ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi(derivatives=[mu]))
        - ncm_expr(s.Bar(psi(derivatives=[mu])), s.Gamma(mu), s.PL, psi())
    )
    fs_gamma = (
        -fs(mu, nu) * ncm_expr(s.Bar(psi()), s.Gamma(mu, nu), s.Gamma(rho), s.PL, psi(derivatives=[rho]))
        + fs(mu, nu) * ncm_expr(s.Bar(psi(derivatives=[rho])), s.Gamma(rho), s.Gamma(mu, nu), s.PL, psi())
    )
    higher_derivative = (
        ncm_expr(s.Bar(psi(derivatives=[mu])), s.Gamma(mu), s.PL, psi(derivatives=[nu, nu]))
        - ncm_expr(s.Bar(psi(derivatives=[mu, mu])), s.Gamma(nu), s.PL, psi(derivatives=[nu]))
    )
    yy = ybar * y
    yyyy = ybar**2 * y**2
    eeyy = ybar * e**2 * y
    return (
        phi(),
        y,
        ybar,
        e,
        mass,
        light_mass,
        mu,
        nu,
        rho,
        log,
        fs(mu, nu),
        fs(mu, nu, nu),
        fs(mu, rho, rho),
        current,
        current_with_phi2,
        fs_gamma,
        higher_derivative,
        yy,
        yyyy,
        eeyy,
    )


def _vlf_power_trace_expressions(theory: Theory) -> dict[str, Expression]:
    (
        phi,
        y,
        ybar,
        _e,
        mass,
        light_mass,
        _mu,
        _nu,
        _rho,
        log,
        field_strength,
        _fs_div_nu,
        _fs_div_rho,
        current,
        current_with_phi2,
        fs_gamma,
        higher_derivative,
        yy,
        yyyy,
        eeyy,
    ) = _vlf_parts(theory)

    h = s.hbar
    eps = s.DimRegEpsilon
    i = Expression.I
    box_phi_1 = theory.field_handle("phi")(derivatives=[theory.dummy_index(0), theory.dummy_index(0)])
    box_phi_2 = theory.field_handle("phi")(derivatives=[theory.dummy_index(1), theory.dummy_index(1)])
    d_phi_sq = theory.field_handle("phi")(derivatives=[theory.dummy_index(0)]) ** 2

    return {
        "hFermion-lScalar": (
            7 * h * yy * _vlf_parts(theory)[11] * ncm_expr(s.Bar(theory.field_handle("psi")()), s.Gamma(theory.dummy_index(0)), s.PL, theory.field_handle("psi")()) / (36 * mass**2)
            + h * (3 * i * yy / 4 + i * yy / (2 * eps) + i * yy * log / 2) * current
            + h * yy * fs_gamma / (8 * mass**2)
            + i * h * yy * higher_derivative / (6 * mass**2)
        ),
        "hFermion-lFermion": (
            h * yy * box_phi_1 * box_phi_2 / (3 * mass**2)
            + h * yy * phi**2 * field_strength**2 / (3 * mass**2)
            - h * d_phi_sq * (-yy / 2 - yy / eps - yy * log)
            + h * phi**2 * (-2 * yy * mass**2 / eps + mass**2 * (-2 * yy - 2 * yy * log))
        ),
        "hFermion-lVector": h * (-7 * i * eeyy / (2 * eps * mass**2) + (-7 * i * eeyy / 4 - 7 * i * eeyy * log / 2) / mass**2) * current_with_phi2,
        "hFermion-lScalar-lScalar": h * (i * yy * light_mass**2 / (eps * mass**2) + (3 * i * yy * light_mass**2 / 2 + i * yy * light_mass**2 * log) / mass**2) * current,
        "hFermion-lScalar-lFermion": h * (-i * yyyy / (2 * eps * mass**2) + (-i * yyyy / 2 - i * yyyy * log / 2) / mass**2) * current_with_phi2,
        "hFermion-lFermion-lScalar": h * (-i * yyyy / (2 * eps * mass**2) + (-i * yyyy / 2 - i * yyyy * log / 2) / mass**2) * current_with_phi2,
        "hFermion-lFermion-lVector": h * (3 * i * eeyy / (2 * eps * mass**2) + (3 * i * eeyy / 4 + 3 * i * eeyy * log / 2) / mass**2) * current_with_phi2,
        "hFermion-lVector-lFermion": h * (3 * i * eeyy / (2 * eps * mass**2) + (3 * i * eeyy / 4 + 3 * i * eeyy * log / 2) / mass**2) * current_with_phi2,
        "hFermion-lScalar-hFermion-lScalar": Expression.num(0),
        "hFermion-lScalar-hFermion-lFermion": -i * h * yyyy * current_with_phi2 / (4 * mass**2),
        "hFermion-lFermion-hFermion-lFermion": 13 * h * yyyy * phi**3 * box_phi_1 / (18 * mass**2) + h * phi**4 * (-yyyy / eps - yyyy * log),
        "hFermion-lFermion-lVector-lFermion": h * (i * eeyy / (2 * eps * mass**2) + (i * eeyy / 4 + i * eeyy * log / 2) / mass**2) * current_with_phi2,
        "hFermion-lFermion-hFermion-lFermion-hFermion-lFermion": h * ybar**3 * y**3 * phi**6 / (3 * mass**2),
    }


def _vlf_log_trace_expression(theory: Theory) -> Expression:
    (_phi, _y, _ybar, _e, mass, _light_mass, _mu, _nu, _rho, log, field_strength, fs_div_nu, fs_div_rho, *_rest) = _vlf_parts(theory)
    return s.hbar * field_strength**2 * (-Expression.num(1) / (3 * s.DimRegEpsilon) - log / 3) - 2 * s.hbar * fs_div_nu * fs_div_rho / (15 * mass**2)


def power_trace_expression(context: MatchingContext, trace: FunctionalTrace | str) -> Expression:
    """Evaluate one VLF power-type supertrace selected by ``trace``."""

    name = trace if isinstance(trace, str) else trace.name
    if not _is_vlf_toy_model(context.theory):
        raise NotImplementedError("power trace evaluation is currently implemented for the VLF toy model")
    expressions = _vlf_power_trace_expressions(context.theory)
    if name not in expressions:
        raise KeyError(f"Unknown power trace {name!r}")
    return normalize_ncm(expressions[name].expand())


def log_trace_expression(context: MatchingContext, trace: FunctionalTrace | str | None = None) -> Expression:
    """Evaluate the VLF log-type supertrace contribution."""

    if not _is_vlf_toy_model(context.theory):
        raise NotImplementedError("log trace evaluation is currently implemented for the VLF toy model")
    if trace is not None:
        name = trace if isinstance(trace, str) else trace.name
        if name != FieldDofClass.H_FERMION.value:
            raise KeyError(f"Unknown log trace {name!r}")
    return normalize_ncm(_vlf_log_trace_expression(context.theory).expand())


def evaluate_functional_trace(context: MatchingContext, trace: FunctionalTrace | str) -> FunctionalTraceEvaluation:
    """Evaluate one selected functional trace with its template attached."""

    selected = _trace_from_name(context, trace)
    expression = (
        log_trace_expression(context, selected)
        if selected.kind is FunctionalTraceKind.LOG
        else power_trace_expression(context, selected)
    )
    return FunctionalTraceEvaluation(
        trace=selected,
        template=functional_trace_template(context, selected),
        instantiated_template=instantiate_functional_trace_template(context, selected),
        expression=expression,
    )


def covariant_loop(theory: Theory, lagrangian: Expression, *, eft_order: int = 6, trace: str | FunctionalTrace | None = None) -> Expression:
    """Return VLF one-loop matching contributions through ``eft_order``.

    With ``trace=None`` the sum of the selected log- and power-type traces is
    returned. Passing a trace label such as ``"hFermion-lScalar"`` evaluates a
    single power trace; passing ``"hFermion"`` evaluates the log trace.
    """

    context = matching_context(theory, lagrangian, eft_order=eft_order)
    if trace is not None:
        evaluation = evaluate_functional_trace(context, trace)
        return series_eft(evaluation.expression, theory, eft_order=eft_order, heavy_field_dimension=False)

    out = Expression.num(0)
    for selected_trace in context.trace_inventory:
        out = out + evaluate_functional_trace(context, selected_trace).expression
    return series_eft(normalize_ncm(out.expand()), theory, eft_order=eft_order, heavy_field_dimension=False)


def evaluate_loop_functions(expr: Expression) -> Expression:
    """Evaluate supported Matchete-style finite loop-function placeholders."""

    return expr.expand()


def loop_integrate_tadpoles(expr: Expression) -> Expression:
    """Replace one-scale propagator powers by internal ``LFFull`` objects.

    This covers the scalar one-loop tadpole monomials produced by the current
    hard-region templates, ``Prop(M)`` and ``Prop(M)^n``. The placeholder shape
    follows Matchete, ``LFFull[{M}, {n, 0}]``, where the final integer is the
    power of the massless ``k^2`` denominator. Multi-scale partial fractions
    and tensor reductions are intentionally left to the later vakint bridge.
    """

    mass_wildcard = s.PowBaseWildcard
    exponent_wildcard = s.PowExponentWildcard

    def prop_power(match: dict[Expression, Expression]) -> Expression:
        return Expression.I * s.LFFull(list_expr(match[mass_wildcard]), list_expr(match[exponent_wildcard], Expression.num(0)))

    def prop_single(match: dict[Expression, Expression]) -> Expression:
        return Expression.I * s.LFFull(list_expr(match[mass_wildcard]), list_expr(Expression.num(1), Expression.num(0)))

    return expr.replace_multiple(
        (
            Replacement(s.Prop(mass_wildcard) ** exponent_wildcard, prop_power),
            Replacement(s.Prop(mass_wildcard), prop_single),
        )
    ).expand()
