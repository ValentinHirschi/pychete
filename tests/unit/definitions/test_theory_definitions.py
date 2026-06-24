from __future__ import annotations

import json

from symbolica import S

from pychete import BuiltinIndexType, FieldMassKind, SymbolDataKey, SymbolRole, Theory, canonical_string, collect_indices, s
from pychete.expr import coupling_pattern, field_pattern, matching_subexpressions


def test_field_and_mass_coupling_definitions_follow_matchete_orders() -> None:
    theory = Theory("defs")
    flavor = theory.define_flavor_index("Flavor", 3)

    heavy = theory.define_field(
        "Phi",
        s.Scalar,
        indices=[flavor.symbol],
        mass=(FieldMassKind.HEAVY, "MPhi", [flavor.symbol]),
    )
    light = theory.define_field(
        "psi",
        s.Fermion,
        indices=[flavor.symbol],
        mass=(FieldMassKind.LIGHT, "mpsi", [flavor.symbol, flavor.symbol]),
    )

    assert theory.fields[heavy.name].heavy is True
    assert theory.couplings["MPhi"].eft_order == 0
    assert theory.couplings["mpsi"].eft_order == 1
    assert canonical_string(heavy(theory.index("f", flavor.symbol))).startswith("pychete::Field")
    assert canonical_string(light(theory.index("f", flavor.symbol))).startswith("pychete::Field")


def test_field_symbol_data_stores_local_mass_metadata() -> None:
    theory = Theory("field_symbol_data")
    flavor = theory.define_flavor_index("Flavor", 3)
    heavy = theory.define_field(
        "Phi",
        s.Scalar,
        indices=[flavor.symbol],
        mass=(FieldMassKind.HEAVY, "MPhi", [flavor.symbol]),
    )

    label = heavy.label
    assert label.get_symbol_data(SymbolDataKey.MASS_KIND.value) == FieldMassKind.HEAVY.value
    assert label.get_symbol_data(SymbolDataKey.MASS_LABEL.value) == theory.coupling_handle("MPhi").label
    assert label.get_symbol_data(SymbolDataKey.MASS_INDICES.value) == [flavor.symbol]
    assert theory.mass_expr(heavy.definition) == theory.coupling_handle("MPhi")(flavor.symbol)


def test_mass_kind_and_builtin_index_type_use_enums_internally() -> None:
    theory = Theory("enum_defs")
    heavy = theory.define_field("H", s.Scalar, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("l", s.Scalar, mass=("Light", "m"))
    zero_mass = theory.define_field("phi", s.Scalar, mass=0)

    assert {kind.value for kind in FieldMassKind} == {"heavy", "light"}
    assert theory.fields[heavy.name].mass_kind is FieldMassKind.HEAVY
    assert theory.fields[light.name].mass_kind is FieldMassKind.LIGHT
    assert theory.fields[zero_mass.name].mass_kind is FieldMassKind.LIGHT
    assert theory.fields[zero_mass.name].mass_label is None
    assert theory.fields[zero_mass.name].mass_expr() is None
    assert BuiltinIndexType.LORENTZ.value in theory.index_types
    assert canonical_string(theory.index("mu")).endswith("pychete::Lorentz)")


def test_symbol_collectors_require_role_tags_on_user_labels_except_indices() -> None:
    theory = Theory("tagged_collectors")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    lam = theory.define_coupling("lambda")
    mu = theory.lorentz_index("mu")

    untagged_field = s.Field(S("plain_field_label"), s.Scalar, s.List(), s.List())
    untagged_coupling = s.Coupling(S("plain_coupling_label"), s.List(), 0)
    untagged_index = s.Index(S("plain_index_label"), s.Lorentz)

    expr = phi() + lam() + mu + untagged_field + untagged_coupling + untagged_index

    assert matching_subexpressions(expr, field_pattern(), s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)) == (phi(),)
    assert matching_subexpressions(expr, coupling_pattern(), s.CouplingLabelWildcard.req_tag(SymbolRole.COUPLING.value)) == (lam(),)
    assert {canonical_string(info.expr) for info in collect_indices(expr)} == {
        canonical_string(mu),
        canonical_string(untagged_index),
    }


def test_theory_json_checkpoint_contains_metadata_without_lagrangian_expression() -> None:
    theory = Theory("json_scalar")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = theory.free_lag(phi)

    payload = json.loads(theory.to_json())

    assert payload["schema_version"] == 2
    assert payload["theory_name"] == "json_scalar"
    assert "lagrangian" not in payload
    assert "field" in {entry["role"] for entry in payload["symbols"]}
    assert all(entry["role"] != "index" for entry in payload["symbols"])
    assert payload["fields"]["phi"]["mass_kind"] == FieldMassKind.LIGHT.value
    assert payload["fields"]["phi"]["mass_label"] is None
    theory._validate_registered_expression(lagrangian)
    assert "pychete::Index(pychete::dummy_index(0),pychete::Lorentz)" in canonical_string(lagrangian)
    assert "pychete::index_d" not in canonical_string(lagrangian)


def test_json_checkpoint_preserves_mass_symbol_data() -> None:
    theory = Theory("json_mass_data")
    flavor = theory.define_flavor_index("Flavor", 3)
    heavy = theory.define_field(
        "Phi",
        s.Scalar,
        indices=[flavor.symbol],
        mass=(FieldMassKind.HEAVY, "MPhi", [flavor.symbol]),
    )
    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    restored_heavy = restored.field_handle("Phi")

    assert canonical_string(restored_heavy.definition.mass_expr()) == canonical_string(heavy.definition.mass_expr())
    assert restored_heavy.label.get_symbol_data(SymbolDataKey.MASS_KIND.value) == FieldMassKind.HEAVY.value
    assert restored_heavy.label.get_symbol_data(SymbolDataKey.MASS_LABEL.value) == restored.coupling_handle("MPhi").label
