from __future__ import annotations

import json

from symbolica import Expression, S

from pychete import (
    BuiltinIndexType,
    ExternalKind,
    FieldChirality,
    FieldMassKind,
    FieldRole,
    FreeLagConvention,
    GroupKind,
    RepresentationReality,
    SymbolDataKey,
    SymbolRole,
    Theory,
    canonical_string,
    collect_indices,
    define_smeft_wilson_coefficient,
    matching_condition_targets,
    s,
    smeft_warsaw_operator,
    smeft_warsaw_operator_names,
)
from pychete.expr import cg_tensor_pattern, coupling_pattern, field_pattern, matching_subexpressions
from tests.conftest import assert_expr_equal


def _local_tags(label: Expression) -> set[str]:
    return {str(tag).split("::")[-1] for tag in label.get_tags()}


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


def test_field_symbol_data_stores_charges_and_chirality() -> None:
    theory = Theory("field_charge_data")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    charge = theory.group_charge("U1Y", S("qY"))
    fermion = theory.define_field(
        "l",
        s.Fermion,
        charges=[charge],
        chirality=FieldChirality.LEFT,
        mass=0,
    )

    label = fermion.label
    assert label.get_symbol_data(SymbolDataKey.CHARGES.value) == [charge]
    assert label.get_symbol_data(SymbolDataKey.CHIRALITY.value) == FieldChirality.LEFT.value
    assert fermion.definition.charge_exprs == (charge,)
    assert fermion.definition.chirality_kind is FieldChirality.LEFT

    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    restored_field = restored.field_handle("l")
    assert restored_field.definition.chirality_kind is FieldChirality.LEFT
    assert [canonical_string(charge_expr) for charge_expr in restored_field.definition.charge_exprs] == [canonical_string(charge)]
    assert restored.groups == theory.groups
    assert canonical_string(restored.group_charge("U1Y", S("qY"))) == canonical_string(charge)


def test_free_lag_uses_abelian_charge_symbol_data_for_complex_scalar_kinetic() -> None:
    theory = Theory("charged_scalar_free")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    theory.define_gauge_group("U1X", s.U1, "gX", "X")
    theory.define_global_group("U1Global", s.U1)
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[
            theory.group_charge("U1Y", 2),
            theory.group_charge("U1X", -3),
            theory.group_charge("U1Global", 11),
        ],
        self_conjugate=False,
        mass=(FieldMassKind.LIGHT, "m"),
    )
    g_y = theory.coupling_handle("gY")
    g_x = theory.coupling_handle("gX")
    b_field = theory.field_handle("B")
    x_field = theory.field_handle("X")
    mass = theory.coupling_handle("m")
    mu = theory.dummy_index(0)
    field = phi()
    derived_field = phi(derivatives=[mu])
    connection = 2 * g_y() * b_field() - 3 * g_x() * x_field()
    expected = (
        s.Bar(derived_field) * derived_field
        + Expression.I * connection * s.Bar(field) * derived_field
        - Expression.I * connection * s.Bar(derived_field) * field
        + connection**2 * s.Bar(field) * field
        - mass() ** 2 * s.Bar(field) * field
    )

    assert_expr_equal(theory.free_lag(phi), expected)


def test_free_lag_uses_abelian_charge_symbol_data_for_fermion_current() -> None:
    theory = Theory("charged_fermion_free")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    psi = theory.define_field(
        "psi",
        s.Fermion,
        charges=[theory.group_charge("U1e", S("q"))],
        mass=(FieldMassKind.LIGHT, "m"),
    )
    coupling = theory.coupling_handle("e")
    vector = theory.field_handle("A")
    mass = theory.coupling_handle("m")
    mu = theory.dummy_index(0)
    field = psi()
    connection = S("q") * coupling() * vector()
    expected = (
        Expression.I * s.NCM(s.Bar(field), s.Gamma(mu), psi(derivatives=[mu]))
        + connection * s.NCM(s.Bar(field), s.Gamma(mu), field)
        - mass() * s.NCM(s.Bar(field), field)
    )

    assert_expr_equal(theory.free_lag(psi), expected)


def test_free_lag_rejects_abelian_charged_self_conjugate_scalars() -> None:
    theory = Theory("charged_real_scalar_free")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=True,
        mass=0,
    )

    try:
        theory.free_lag(phi)
    except ValueError as exc:
        assert "self-conjugate scalar fields cannot carry Abelian gauge charges" in str(exc)
    else:
        raise AssertionError("charged self-conjugate scalar free_lag did not fail")


def test_free_lag_matchete_convention_keeps_covariant_terms_implicit() -> None:
    theory = Theory("matchete_free_lag_convention")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    psi = theory.define_field(
        "psi",
        s.Fermion,
        charges=[theory.group_charge("U1e", 1)],
        mass=(FieldMassKind.HEAVY, "M"),
    )
    vector = theory.field_handle("A")
    coupling = theory.coupling_handle("e")
    mass = theory.coupling_handle("M")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    field = psi()
    strength = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List())
    expected = (
        -strength**2 / (4 * coupling() ** 2)
        + Expression.I * s.NCM(s.Bar(field), s.DiracProduct(s.Gamma(mu)), psi(derivatives=[mu]))
        - mass() * s.NCM(s.Bar(field), field)
    )

    assert_expr_equal(theory.free_lag("A", psi, convention=FreeLagConvention.MATCHETE), expected)


def test_matching_condition_targets_expose_symbolica_role_metadata() -> None:
    theory = Theory("target_metadata")
    flavor = theory.define_flavor_index("Flavor", 3)
    i = theory.index("i", flavor.symbol)
    j = theory.index("j", flavor.symbol)
    yukawa = theory.define_coupling("Y", indices=[flavor.symbol, flavor.symbol])
    higgs = theory.define_field("H", s.Scalar, mass=0)
    operator = (s.Bar(higgs()) * higgs()) ** 3
    wilson = theory.define_wilson_coefficient(
        "cHl",
        indices=[i, j],
        eft_order=6,
        basis="SMEFT",
        operator=operator,
    )

    targets = matching_condition_targets(
        {
            "y": yukawa(i, j),
            "wilson": s.Coupling(wilson.label, s.List(i, j), Expression.num(6)),
        }
    )
    by_name = {target.name: target for target in targets}

    assert by_name["y"].is_coupling is True
    assert by_name["y"].is_external is False
    assert by_name["y"].is_wilson_coefficient is False
    assert by_name["y"].indices == (i, j)
    assert by_name["y"].eft_order == 0
    assert by_name["wilson"].is_coupling is False
    assert by_name["wilson"].is_external is True
    assert by_name["wilson"].is_wilson_coefficient is True
    assert by_name["wilson"].external_kind is ExternalKind.WILSON_COEFFICIENT
    assert by_name["wilson"].basis == "SMEFT"
    assert by_name["wilson"].indices == (i, j)
    assert by_name["wilson"].eft_order == 6
    assert by_name["wilson"].operator == operator
    assert by_name["wilson"].projection_expression == operator


def test_gauge_and_global_groups_store_kind_and_abelian_symbol_data() -> None:
    theory = Theory("group_metadata")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    su2f = theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    u1x = theory.define_global_group("U1X", s.U1)

    assert theory.groups["U1Y"]["kind"] == GroupKind.GAUGE.value
    assert theory.groups["U1Y"]["abelian"] is True
    assert theory.groups["U1Y"]["coupling"] == "gY"
    assert theory.groups["U1Y"]["field"] == "B"
    assert theory.groups["SU2F"]["kind"] == GroupKind.GLOBAL.value
    assert theory.groups["SU2F"]["abelian"] is False
    assert "coupling" not in theory.groups["SU2F"]
    assert su2f.get_symbol_data(SymbolDataKey.GROUP_KIND.value) == GroupKind.GLOBAL.value
    assert su2f.get_symbol_data(SymbolDataKey.GROUP_ABELIAN.value) == 0
    assert "group_kind_global" in _local_tags(su2f)
    assert "non_abelian" in _local_tags(su2f)
    assert u1x.get_symbol_data(SymbolDataKey.GROUP_ABELIAN.value) == 1
    assert canonical_string(theory.group_charge("U1X", S("x"))) == "group_metadata::group_U1X(python::x)"
    su2f_fund = canonical_string(su2f(s.fund))
    su2f_adj = canonical_string(su2f(s.adj))
    assert theory.representations[su2f_fund].dimension_value == 2
    assert theory.representations[su2f_fund].reality_kind is RepresentationReality.PSEUDOREAL
    assert theory.representations[su2f_adj].dimension_value == 3
    assert theory.representations[su2f_adj].reality_kind is RepresentationReality.REAL
    assert canonical_string(theory.define_representation("SU2F", "fund")) == su2f_fund
    assert theory.cg_tensors["gen_SU2F_fund"].representation_exprs == (su2f(s.adj), su2f(s.fund), s.Bar(su2f(s.fund)))
    assert theory.cg_tensors["fStruct_SU2F"].representation_exprs == (su2f(s.adj), su2f(s.adj), su2f(s.adj))
    assert theory.cg_tensors["eps_SU2F"].representation_exprs == (su2f(s.fund), su2f(s.fund))
    assert theory.cg_tensor_handle("gen_SU2F_fund").definition.source_text == "builtin:gen"

    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    restored_su2f = restored.symbol("SU2F", role=SymbolRole.GROUP)
    assert restored.groups == theory.groups
    assert restored.representations[su2f_fund].dimension_value == 2
    assert restored.representations[su2f_adj].reality_kind is RepresentationReality.REAL
    assert restored.cg_tensors["eps_SU2F"].representation_exprs == (su2f(s.fund), su2f(s.fund))
    assert restored_su2f.get_symbol_data(SymbolDataKey.GROUP_KIND.value) == GroupKind.GLOBAL.value
    assert "group_kind_global" in _local_tags(restored_su2f)


def test_representations_store_symbolica_metadata_and_survive_json_restore() -> None:
    theory = Theory("representation_metadata")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    quad = theory.define_representation(
        "SU2F",
        "quad",
        dynkin=[Expression.num(3)],
        dimension=4,
        reality=RepresentationReality.PSEUDOREAL,
    )
    field = theory.define_field("Theta", s.Scalar, indices=[quad], self_conjugate=True, mass=0)

    label = theory.representation_labels["quad"]
    assert canonical_string(quad) == "representation_metadata::group_SU2F(representation_metadata::representation_quad)"
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_GROUP.value) == "SU2F"
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_DYNKIN.value) == [Expression.num(3)]
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_DIMENSION.value) == 4
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_REALITY.value) == RepresentationReality.PSEUDOREAL.value
    assert "representation_group_SU2F" in _local_tags(label)
    assert "representation_reality_pseudoreal" in _local_tags(label)
    assert field.definition.indices == (quad,)
    assert theory.representations[canonical_string(quad)].reality_kind is RepresentationReality.PSEUDOREAL

    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    restored_quad = restored.representations[canonical_string(quad)].expr
    restored_label = restored.representation_labels["quad"]

    assert canonical_string(restored_quad) == canonical_string(quad)
    assert restored_label.get_symbol_data(SymbolDataKey.REPRESENTATION_REALITY.value) == RepresentationReality.PSEUDOREAL.value
    assert restored.field_handle("Theta").definition.indices == (restored_quad,)
    assert "representation_reality_pseudoreal" in _local_tags(restored_label)


def test_conjugate_representation_lookup_uses_underlying_registered_metadata() -> None:
    theory = Theory("conjugate_representations")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    su3c = theory.symbol("SU3c", role=SymbolRole.GROUP)
    fund = su3c(s.fund)
    barred_fund = s.Bar(fund)

    assert theory.representation_definition(barred_fund) is theory.representations[canonical_string(fund)]
    assert theory.representation_dimension(barred_fund) == 3
    assert theory.representation_reality(barred_fund) is RepresentationReality.COMPLEX
    assert theory.is_conjugate_representation(barred_fund) is True
    assert theory.is_conjugate_representation(fund) is False

    try:
        theory.representation_definition(s.Bar(S("unregistered_rep")))
    except KeyError as exc:
        assert "Unknown representation" in str(exc)
    else:
        raise AssertionError("unregistered conjugate representation metadata lookup was accepted")


def test_cg_tensors_store_symbolica_metadata_and_survive_json_restore() -> None:
    theory = Theory("cg_metadata")
    su2 = theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    fund = su2(s.fund)
    eps = theory.define_cg_tensor(
        "eps2",
        [fund, fund],
        tensor=S("raw_eps_tensor"),
        source="First@InvariantTensors[SU@2, {{1}, {1}}]",
    )

    i = S("i")
    j = S("j")
    expr = eps(i, j)

    assert eps.label.get_symbol_data(SymbolDataKey.CG_REPRESENTATIONS.value) == [fund, fund]
    assert eps.label.get_symbol_data(SymbolDataKey.CG_TENSOR.value) == S("raw_eps_tensor")
    assert eps.label.get_symbol_data(SymbolDataKey.CG_SOURCE.value) == "First@InvariantTensors[SU@2, {{1}, {1}}]"
    assert "cg_tensor_rank_2" in _local_tags(eps.label)
    assert expr == s.CG(eps.label, s.List(i, j))
    assert theory.cg_tensors["eps2"].representation_exprs == (fund, fund)

    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    restored_eps = restored.cg_tensor_handle("eps2")
    assert restored_eps.label.get_symbol_data(SymbolDataKey.CG_REPRESENTATIONS.value) == [fund, fund]
    assert restored_eps.label.get_symbol_data(SymbolDataKey.CG_TENSOR.value) == S("raw_eps_tensor")
    assert restored_eps(S("i"), S("j")) == expr


def test_cg_tensor_restore_backfills_legacy_manifest_tensor_data() -> None:
    theory = Theory("cg_legacy_manifest")
    su2 = theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    fund = su2(s.fund)
    theory.define_cg_tensor("eps2", [fund, fund], tensor=s.List(s.List(2, 2), s.List(0, 1, -1, 0)))
    obj = theory.to_json_obj()
    for entry in obj["symbols"]:
        if entry["role"] == SymbolRole.CG_TENSOR.value and entry["name"] == "eps2":
            entry["data"].pop(SymbolDataKey.CG_TENSOR.value)

    restored = Theory.from_json_obj(obj)
    restored_tensor = restored.cg_tensor_handle("eps2").definition.tensor_expr

    assert restored_tensor is not None
    assert canonical_string(restored_tensor) == "pychete::List(pychete::List(2,2),pychete::List(0,1,-1,0))"


def test_field_symbol_data_stores_field_roles_and_propagation_flags() -> None:
    theory = Theory("field_roles")
    ghost = theory.define_field("c", s.Ghost, mass=(FieldMassKind.HEAVY, "Mc"))
    goldstone = theory.define_field("chi", s.Scalar, field_role=FieldRole.GOLDSTONE, self_conjugate=True, mass=0)
    background = theory.define_field("v", s.Scalar, field_role=FieldRole.BACKGROUND, self_conjugate=True, mass=0)
    zero_mode = theory.define_field("phi0", s.Scalar, zero_mode=True, self_conjugate=True, mass=0)

    assert ghost.definition.role is FieldRole.GHOST
    assert ghost.definition.is_ghost is True
    assert ghost.label.get_symbol_data(SymbolDataKey.FIELD_ROLE.value) == FieldRole.GHOST.value
    assert "field_role_ghost" in _local_tags(ghost.label)
    assert "propagating" in _local_tags(ghost.label)

    assert goldstone.definition.is_goldstone is True
    assert goldstone.label.get_symbol_data(SymbolDataKey.FIELD_ROLE.value) == FieldRole.GOLDSTONE.value
    assert "field_role_goldstone" in _local_tags(goldstone.label)

    assert background.definition.is_background is True
    assert background.definition.is_propagating is False
    assert background.label.get_symbol_data(SymbolDataKey.PROPAGATING.value) == 0
    assert "field_role_background" in _local_tags(background.label)
    assert "non_propagating" in _local_tags(background.label)

    assert zero_mode.definition.is_zero_mode is True
    assert zero_mode.label.get_symbol_data(SymbolDataKey.ZERO_MODE.value) == 1
    assert "zero_mode" in _local_tags(zero_mode.label)

    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    assert restored.field_handle("c").definition.role is FieldRole.GHOST
    assert restored.field_handle("chi").definition.role is FieldRole.GOLDSTONE
    assert restored.field_handle("v").definition.is_propagating is False
    assert "field_role_background" in _local_tags(restored.field_handle("v").label)
    assert restored.field_handle("phi0").definition.is_zero_mode is True


def test_field_role_validation_matches_matchete_constraints() -> None:
    theory = Theory("field_role_validation")

    try:
        theory.define_field("bad_goldstone", s.Fermion, field_role=FieldRole.GOLDSTONE)
    except ValueError as exc:
        assert "Goldstone" in str(exc)
    else:
        raise AssertionError("non-scalar Goldstone field was accepted")

    try:
        theory.define_field("bad_ghost", s.Scalar, field_role=FieldRole.GHOST)
    except ValueError as exc:
        assert "ghost field roles" in str(exc)
    else:
        raise AssertionError("ghost role with non-ghost field type was accepted")

    try:
        theory.define_field("bad_background", s.Scalar, field_role=FieldRole.BACKGROUND, mass=(FieldMassKind.HEAVY, "M"))
    except ValueError as exc:
        assert "non-propagating" in str(exc)
    else:
        raise AssertionError("background field with mass metadata was accepted")


def test_coupling_symbol_data_stores_matchete_metadata() -> None:
    theory = Theory("coupling_metadata")
    flavor = theory.define_flavor_index("Flavor", 3)
    symmetry = s.SymmetricPermutation(2, 1)
    y = theory.define_coupling(
        "Y",
        indices=[flavor.symbol, flavor.symbol],
        eft_order=1,
        self_conjugate=(2, 1),
        symmetries=[symmetry],
        diagonal=[False, True],
        thermal_power_counting=2,
    )

    label = y.label
    assert label.get_symbol_data(SymbolDataKey.INDICES.value) == [flavor.symbol, flavor.symbol]
    assert label.get_symbol_data(SymbolDataKey.SELF_CONJUGATE.value) == [2, 1]
    assert label.get_symbol_data(SymbolDataKey.SYMMETRIES.value) == [symmetry]
    assert label.get_symbol_data(SymbolDataKey.DIAGONAL_COUPLING.value) == [False, True]
    assert label.get_symbol_data(SymbolDataKey.THERMAL_POWER_COUNTING.value) == 2
    assert label.get_symbol_data(SymbolDataKey.UNITARY.value) == 0
    assert y.definition.index_exprs == (flavor.symbol, flavor.symbol)
    assert y.definition.self_conjugate_spec == (2, 1)
    assert y.definition.symmetry_exprs == (symmetry,)
    assert y.definition.diagonal_flags == (False, True)
    assert y.definition.is_unitary is False

    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    restored_y = restored.coupling_handle("Y")
    assert restored_y.definition.self_conjugate_spec == (2, 1)
    assert [canonical_string(expr) for expr in restored_y.definition.symmetry_exprs] == [canonical_string(symmetry)]
    assert restored_y.definition.diagonal_flags == (False, True)
    assert restored_y.definition.thermal_power_counting == 2
    assert restored_y.label.get_symbol_data(SymbolDataKey.SYMMETRIES.value) == [s.SymmetricPermutation(2, 1)]


def test_unitary_couplings_require_zero_order_square_index_space() -> None:
    theory = Theory("unitary_couplings")
    flavor = theory.define_flavor_index("Flavor", 3)
    other = theory.define_flavor_index("OtherFlavor", 2)

    u = theory.define_coupling("U", indices=[flavor.symbol, flavor.symbol], unitary=True)
    assert u.definition.is_unitary is True

    try:
        theory.define_coupling("bad_order", indices=[flavor.symbol, flavor.symbol], eft_order=1, unitary=True)
    except ValueError as exc:
        assert "EFT order 0" in str(exc)
    else:
        raise AssertionError("unitary coupling with non-zero EFT order was accepted")

    try:
        theory.define_coupling("bad_shape", indices=[flavor.symbol, other.symbol], unitary=True)
    except ValueError as exc:
        assert "matrix couplings" in str(exc)
    else:
        raise AssertionError("unitary coupling with non-square index metadata was accepted")


def test_diagonal_and_self_conjugation_metadata_must_match_index_count() -> None:
    theory = Theory("coupling_validation")
    flavor = theory.define_flavor_index("Flavor", 3)

    try:
        theory.define_coupling("D", indices=[flavor.symbol, flavor.symbol], diagonal=True)
    except ValueError as exc:
        assert "diagonal coupling" in str(exc)
    else:
        raise AssertionError("diagonal coupling flag with wrong arity was accepted")

    try:
        theory.define_coupling("C", indices=[flavor.symbol, flavor.symbol], self_conjugate=(1,))
    except ValueError as exc:
        assert "self-conjugation permutation" in str(exc)
    else:
        raise AssertionError("self-conjugation permutation with wrong arity was accepted")


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


def test_numeric_coefficients_use_symbolica_arithmetic_not_symbol_store() -> None:
    x = S("x")

    assert canonical_string(x / 24) == "1/24*python::x"
    assert canonical_string(x / 2) == "1/2*python::x"
    assert not hasattr(s, "half")
    assert not hasattr(s, "sixth")
    assert not hasattr(s, "twenty_fourth")


def test_external_symbols_are_registered_with_symbol_data_and_survive_json_restore() -> None:
    theory = Theory("external_defs")
    external = theory.define_external("cHB")
    argument = S("x")
    expression = s.Coupling(external.label, s.List(), 0) + external(argument)

    assert sorted(theory.externals) == ["cHB"]
    assert theory.external_handle("cHB").label == external.label
    assert external.label.get_symbol_data(SymbolDataKey.ROLE.value) == SymbolRole.EXTERNAL.value
    assert external.label.get_symbol_data(SymbolDataKey.NAME.value) == "cHB"
    assert "external" in _local_tags(external.label)

    theory._validate_registered_expression(expression)
    payload = json.loads(theory.to_json())
    assert payload["externals"]["cHB"]["label"] == canonical_string(external.label)

    restored = Theory.from_json_obj(payload)
    restored_external = restored.external_handle("cHB")
    restored_expression = restored._parse_registered_expression(canonical_string(expression))

    assert sorted(restored.externals) == ["cHB"]
    assert canonical_string(restored_external.label) == canonical_string(external.label)
    assert restored_external.label.get_symbol_data(SymbolDataKey.ROLE.value) == SymbolRole.EXTERNAL.value
    assert canonical_string(restored_expression) == canonical_string(expression)


def test_wilson_coefficients_store_basis_and_matching_target_metadata() -> None:
    theory = Theory("wilson_defs")
    flavor = theory.define_flavor_index("Flavor", 3)
    i = theory.index("i1", flavor.symbol)
    j = theory.index("i2", flavor.symbol)
    higgs = theory.define_field("H", s.Scalar, mass=0)
    operator = s.Bar(higgs()) * higgs() * s.Bar(higgs()) * higgs()
    wilson = theory.define_wilson_coefficient("cHd", indices=[i, j], basis="SMEFT", operator=operator)

    assert wilson.definition.kind is ExternalKind.WILSON_COEFFICIENT
    assert wilson.definition.basis_name == "SMEFT"
    assert wilson.definition.operator_expr == operator
    assert wilson.definition.order == 0
    assert [canonical_string(index) for index in wilson.definition.index_exprs] == [
        canonical_string(i),
        canonical_string(j),
    ]
    assert wilson.label.get_symbol_data(SymbolDataKey.EXTERNAL_KIND.value) == ExternalKind.WILSON_COEFFICIENT.value
    assert wilson.label.get_symbol_data(SymbolDataKey.BASIS.value) == "SMEFT"
    assert wilson.label.get_symbol_data(SymbolDataKey.OPERATOR.value) == operator
    assert "external_kind_wilson_coefficient" in _local_tags(wilson.label)
    assert "basis_SMEFT" in _local_tags(wilson.label)

    payload = json.loads(theory.to_json())
    assert payload["externals"]["cHd"]["operator"] == canonical_string(operator)
    restored = Theory.from_json_obj(payload)
    restored_wilson = restored.external_handle("cHd")

    assert restored_wilson.definition.kind is ExternalKind.WILSON_COEFFICIENT
    assert restored_wilson.definition.basis_name == "SMEFT"
    assert canonical_string(restored_wilson.definition.operator_expr) == canonical_string(operator)
    assert [canonical_string(index) for index in restored_wilson.definition.index_exprs] == [
        canonical_string(i),
        canonical_string(j),
    ]


def test_smeft_warsaw_operator_builders_attach_wilson_operator_metadata() -> None:
    theory = Theory("smeft_ops")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    flavor = theory.define_flavor_index("Flavor", 3)
    su3_fund = theory.define_representation("SU3c", "fund")
    su2_fund = theory.define_representation("SU2L", "fund")
    theory.define_field("H", s.Scalar, indices=[su2_fund], mass=0)
    theory.define_field("q", s.Fermion, indices=[su3_fund, su2_fund, flavor.symbol], mass=0)
    theory.define_field("u", s.Fermion, indices=[su3_fund, flavor.symbol], mass=0)
    theory.define_field("l", s.Fermion, indices=[su2_fund, flavor.symbol], mass=0)
    theory.define_field("e", s.Fermion, indices=[flavor.symbol], mass=0)
    theory.define_field("d", s.Fermion, indices=[su3_fund, flavor.symbol], mass=0)

    p = theory.index("p", flavor.symbol)
    r = theory.index("r", flavor.symbol)
    s_flavor = theory.index("s", flavor.symbol)
    t = theory.index("t", flavor.symbol)
    c_h = define_smeft_wilson_coefficient(theory, "cH")
    c_hb = define_smeft_wilson_coefficient(theory, "cHB")
    c_hwb = define_smeft_wilson_coefficient(theory, "cHWB")
    c_hd = define_smeft_wilson_coefficient(theory, "cHd", indices=[p, r])
    c_ew = define_smeft_wilson_coefficient(theory, "ceW", indices=[p, r])
    c_ll = define_smeft_wilson_coefficient(theory, "cll", indices=[p, r, s_flavor, t])
    c_duq = define_smeft_wilson_coefficient(theory, "cduq", indices=[p, r, s_flavor, t])

    assert len(smeft_warsaw_operator_names()) == 64
    for name in smeft_warsaw_operator_names():
        flavor_indices = ()
        if name in {"cllHH", "ceH", "cuH", "cdH", "ceW", "ceB", "cuG", "cuW", "cuB", "cdG", "cdW", "cdB", "cHl1", "cHl3", "cHe", "cHq1", "cHq3", "cHu", "cHd", "cHud"}:
            flavor_indices = (p, r)
        elif name not in {"cG", "cGt", "cW", "cWt", "cHG", "cHGt", "cHW", "cHWt", "cHB", "cHBt", "cHWB", "cHWtB", "cH", "cHBox", "cHD"}:
            flavor_indices = (p, r, s_flavor, t)
        operator = smeft_warsaw_operator(theory, name, flavor_indices)
        assert operator is not None, name
        theory._validate_registered_expression(operator)

    for handle in (c_h, c_hb, c_hwb, c_hd, c_ew, c_ll, c_duq):
        assert handle.definition.operator_expr is not None
        theory._validate_registered_expression(handle.definition.operator_expr)
    assert "field_H" in canonical_string(c_h.definition.operator_expr)
    assert "field_B" in canonical_string(c_hb.definition.operator_expr)
    assert "cg_tensor_gen_SU2L_fund" in canonical_string(c_hwb.definition.operator_expr)
    assert "field_d" in canonical_string(c_hd.definition.operator_expr)
    assert "pychete::Sigma" in canonical_string(c_ew.definition.operator_expr)
    assert "pychete::NCM" in canonical_string(c_hd.definition.operator_expr)


def test_external_metadata_must_be_registered_before_generic_use() -> None:
    theory = Theory("external_metadata_order")
    theory.define_external("cHB")

    try:
        theory.define_wilson_coefficient("cHB", basis="SMEFT")
    except ValueError as exc:
        assert "before parsing" in str(exc)
    else:
        raise AssertionError("external metadata was silently changed after generic registration")


def test_symbol_collectors_require_role_tags_on_user_labels_except_indices() -> None:
    theory = Theory("tagged_collectors")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    lam = theory.define_coupling("lambda")
    theory.define_gauge_group("SU2F", s.SU(Expression.num(2)), "gF", "VF")
    eps = theory.cg_tensor_handle("eps_SU2F")
    mu = theory.lorentz_index("mu")

    untagged_field = s.Field(S("plain_field_label"), s.Scalar, s.List(), s.List())
    untagged_coupling = s.Coupling(S("plain_coupling_label"), s.List(), 0)
    untagged_cg = s.CG(S("plain_cg_label"), s.List(mu))
    untagged_index = s.Index(S("plain_index_label"), s.Lorentz)

    expr = phi() + lam() + eps(mu, mu) + mu + untagged_field + untagged_coupling + untagged_cg + untagged_index

    assert matching_subexpressions(expr, field_pattern(), s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)) == (phi(),)
    assert matching_subexpressions(expr, coupling_pattern(), s.CouplingLabelWildcard.req_tag(SymbolRole.COUPLING.value)) == (lam(),)
    assert matching_subexpressions(expr, cg_tensor_pattern(), s.CGTensorLabelWildcard.req_tag(SymbolRole.CG_TENSOR.value)) == (
        eps(mu, mu),
    )
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
