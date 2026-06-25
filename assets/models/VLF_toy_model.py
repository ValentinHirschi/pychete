from __future__ import annotations

from pychete import FieldMassKind, Theory, bar_expr, s
from pychete.spinor import ncm_expr


def build():
    theory = Theory("VLF_toy_model")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    unit_charge = theory.gauge_charge("U1e", 1).expr
    heavy_psi = theory.define_field("Psi", s.Fermion, charges=[unit_charge], mass=(FieldMassKind.HEAVY, "M"))
    psi = theory.define_field("psi", s.Fermion, charges=[unit_charge], mass=0)
    phi = theory.define_field("phi", s.Scalar, mass=(FieldMassKind.LIGHT, "m"), self_conjugate=True)
    y = theory.define_coupling("y")

    lint = -y() * ncm_expr(s.Bar(psi()), s.PR, heavy_psi()) * phi()
    lagrangian = theory.free_lag("A", heavy_psi, psi, phi) + lint + bar_expr(lint)
    return theory, {"lagrangian": lagrangian}
