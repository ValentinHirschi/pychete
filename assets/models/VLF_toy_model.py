from __future__ import annotations

from pychete import FieldMassKind, Theory, s


def build():
    theory = Theory("VLF_toy_model")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    u1e_charge = theory.group_charge("U1e", 1)
    heavy_psi = theory.define_field("Psi", s.Fermion, charges=[u1e_charge], mass=(FieldMassKind.HEAVY, "M"))
    psi = theory.define_field("psi", s.Fermion, charges=[u1e_charge], mass=0)
    phi = theory.define_field("phi", s.Scalar, mass=(FieldMassKind.LIGHT, "m"), self_conjugate=True)
    y = theory.define_coupling("y")

    lint = -y() * s.NCM(s.Bar(psi()), s.PR, heavy_psi()) * phi()
    lagrangian = theory.free_lag("A", heavy_psi, psi, phi) + lint + s.Bar(lint)
    return theory, {"lagrangian": lagrangian}
