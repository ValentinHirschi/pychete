from __future__ import annotations

from pathlib import Path

from symbolica import Expression

from pychete import FieldChirality, FieldMassKind, FieldRole, GroupKind, RepresentationReality, SymbolDataKey, SymbolRole, Theory, canonical_string, s
from pychete.loaders import load_matchete_model, load_python_model


def _local_tags(label: Expression) -> set[str]:
    return {str(tag).split("::")[-1] for tag in label.get_tags()}


def test_python_model_loader_uses_build_function(tmp_path: Path) -> None:
    model = tmp_path / "simple_model.py"
    model.write_text(
        "\n".join(
            [
                "from pychete import Theory, s",
                "def build():",
                "    theory = Theory('python_model')",
                "    phi = theory.define_field('phi', s.Scalar, self_conjugate=True, mass=0)",
                "    lagrangian = theory.free_lag(phi)",
                "    return theory, {'lagrangian': lagrangian}",
            ]
        ),
        encoding="utf-8",
    )

    theory, expressions = load_python_model(model)

    assert isinstance(theory, Theory)
    assert theory.name == "python_model"
    assert "phi" in theory.fields
    assert set(expressions) == {"lagrangian"}
    theory._validate_registered_expression(expressions["lagrangian"])


def test_vlf_toy_model_asset_loads_without_runtime_reference_dependency() -> None:
    path = Path("assets/models/VLF_toy_model.m")

    theory, expressions = load_matchete_model(path)

    assert theory.name == "VLF_toy_model"
    assert {"A", "Psi", "psi", "phi"} <= set(theory.fields)
    assert {"e", "M", "m", "y"} <= set(theory.couplings)
    assert theory.fields["Psi"].heavy is True
    assert len(theory.fields["Psi"].charge_exprs) == 1
    assert canonical_string(theory.fields["Psi"].charge_exprs[0]) == "VLF_toy_model::group_U1e(1)"
    assert canonical_string(theory.fields["psi"].charge_exprs[0]) == "VLF_toy_model::group_U1e(1)"
    assert theory.fields["phi"].mass_kind is FieldMassKind.LIGHT
    assert set(expressions) == {"lagrangian"}
    theory._validate_registered_expression(expressions["lagrangian"])


def test_vlf_mathematica_and_python_assets_canonicalize_to_same_json() -> None:
    mathematica_theory, mathematica_expressions = load_matchete_model(Path("assets/models/VLF_toy_model.m"))
    python_theory, python_expressions = load_python_model(Path("assets/models/VLF_toy_model.py"))

    assert mathematica_theory.to_json_obj() == python_theory.to_json_obj()
    assert {
        name: canonical_string(expression)
        for name, expression in mathematica_expressions.items()
    } == {
        name: canonical_string(expression)
        for name, expression in python_expressions.items()
    }


def test_matchete_loader_preserves_supported_coupling_options(tmp_path: Path) -> None:
    model = tmp_path / "couplings.m"
    model.write_text(
        "\n".join(
            [
                "DefineCoupling[Y, Indices->{Flavor, Flavor}, EFTOrder->1, SelfConjugate->{2, 1},",
                "    Symmetries->{SymmetricPermutation[2, 1]}, DiagonalCoupling->{False, True}, ThermalPowerCounting->2];",
                "DefineCoupling[U, Indices->{Flavor, Flavor}, Unitary->True];",
                "DefineCoupling[{c1, c2}, SelfConjugate->True];",
            ]
        ),
        encoding="utf-8",
    )

    theory, expressions = load_matchete_model(model, theory_name="loader_couplings")

    flavor = theory.index_types["Flavor"].symbol
    y = theory.coupling_handle("Y")
    assert expressions == {}
    assert y.definition.index_exprs == (flavor, flavor)
    assert y.definition.eft_order == 1
    assert y.definition.self_conjugate_spec == (2, 1)
    assert y.definition.diagonal_flags == (False, True)
    assert y.definition.thermal_power_counting == 2
    assert [canonical_string(expr) for expr in y.definition.symmetry_exprs] == [canonical_string(s.SymmetricPermutation(2, 1))]
    assert y.label.get_symbol_data(SymbolDataKey.SYMMETRIES.value) == [s.SymmetricPermutation(2, 1)]
    assert theory.coupling_handle("U").definition.is_unitary is True
    assert theory.coupling_handle("c1").definition.self_conjugate_spec is True
    assert theory.coupling_handle("c2").definition.self_conjugate_spec is True


def test_matchete_loader_preserves_field_role_options(tmp_path: Path) -> None:
    model = tmp_path / "field_roles.m"
    model.write_text(
        "\n".join(
            [
                "DefineField[c, Ghost, Mass->{Heavy, Mc}];",
                "DefineField[cb, AntiGhost, Mass->{Heavy, Mcb}];",
                "DefineField[chi, Scalar, GoldstoneBoson->True, SelfConjugate->True, Mass->0];",
                "DefineField[v, Scalar, BackgroundField->True, SelfConjugate->True, Mass->0];",
                "DefineField[phi0, Scalar, ZeroMode->True, SelfConjugate->True, Mass->0];",
            ]
        ),
        encoding="utf-8",
    )

    theory, expressions = load_matchete_model(model, theory_name="loader_field_roles")

    assert expressions == {}
    assert theory.fields["c"].role is FieldRole.GHOST
    assert theory.fields["cb"].role is FieldRole.ANTI_GHOST
    assert theory.fields["chi"].role is FieldRole.GOLDSTONE
    assert theory.fields["v"].role is FieldRole.BACKGROUND
    assert theory.fields["v"].is_propagating is False
    assert theory.fields["phi0"].is_zero_mode is True
    assert "field_role_background" in _local_tags(theory.fields["v"].label)
    assert "zero_mode" in _local_tags(theory.fields["phi0"].label)


def test_matchete_loader_preserves_global_groups(tmp_path: Path) -> None:
    model = tmp_path / "global_groups.m"
    model.write_text(
        "\n".join(
            [
                "DefineGlobalGroup[SU2F, SU@2];",
                "DefineGlobalGroup[U1X, U1];",
                "DefineField[x, Scalar, Indices->{SU2F[fund]}, Charges->{U1X[1]}, Mass->0];",
            ]
        ),
        encoding="utf-8",
    )

    theory, expressions = load_matchete_model(model, theory_name="loader_global_groups")

    assert expressions == {}
    assert theory.groups["SU2F"]["kind"] == GroupKind.GLOBAL.value
    assert theory.groups["SU2F"]["abelian"] is False
    assert theory.groups["U1X"]["kind"] == GroupKind.GLOBAL.value
    assert theory.groups["U1X"]["abelian"] is True
    assert "coupling" not in theory.groups["SU2F"]
    assert canonical_string(theory.fields["x"].indices[0]) == "loader_global_groups::group_SU2F(pychete::fund)"
    assert canonical_string(theory.fields["x"].charge_exprs[0]) == "loader_global_groups::group_U1X(1)"
    assert "group_kind_global" in _local_tags(theory.symbol("SU2F", role=SymbolRole.GROUP))


def test_matchete_loader_preserves_custom_representations(tmp_path: Path) -> None:
    model = tmp_path / "representations.m"
    model.write_text(
        "\n".join(
            [
                "DefineGaugeGroup[SU2L, SU@2, gL, W];",
                "DefineRepresentation[SU2L[quad], SU2L, {3}];",
                "DefineField[Theta, Scalar, Indices->{SU2L[quad]}, SelfConjugate->True, Mass->0];",
            ]
        ),
        encoding="utf-8",
    )

    theory, expressions = load_matchete_model(model, theory_name="loader_representations")

    rep_key = "loader_representations::group_SU2L(loader_representations::representation_quad)"
    assert expressions == {}
    assert canonical_string(theory.fields["Theta"].indices[0]) == rep_key
    assert rep_key in theory.representations
    assert theory.representations[rep_key].group == "SU2L"
    assert theory.representations[rep_key].reality_kind is RepresentationReality.UNKNOWN
    label = theory.representation_labels["quad"]
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_GROUP.value) == "SU2L"
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_DYNKIN.value) == [Expression.num(3)]
    assert "representation_group_SU2L" in _local_tags(label)


def test_sm_model_metadata_loads_without_lagrangian_parsing() -> None:
    theory, expressions = load_matchete_model(Path("assets/models/SM.m"), include_lagrangian=False)

    assert expressions == {}
    assert set(theory.groups) == {"SU3c", "SU2L", "U1Y"}
    assert {"G", "W", "B", "q", "u", "d", "l", "e", "H"} <= set(theory.fields)
    assert {"gs", "gL", "gY", "Yu", "Yd", "Ye", "mu2", "lambda"} <= set(theory.couplings)
    assert theory.index_types["Flavor"].dimension == 3
    assert theory.fields["q"].chirality_kind is FieldChirality.LEFT
    assert theory.fields["u"].chirality_kind is FieldChirality.RIGHT
    assert canonical_string(theory.fields["H"].charge_exprs[0]) == "SM::group_U1Y(1/2)"
    assert theory.couplings["mu2"].eft_order == 2
    assert theory.couplings["Yu"].index_exprs == (theory.index_types["Flavor"].symbol, theory.index_types["Flavor"].symbol)


def test_default_parent_model_assets_load_metadata_without_reference_checkout() -> None:
    expected = {
        "Singlet_Scalar_Extension": ({"phi", "H", "q", "l"}, {"A", "M", "kappa", "muphi", "lambdaphi", "Yu"}),
        "E_VLL": ({"EE", "H", "q", "l"}, {"ME", "yE", "Yu"}),
        "S1S3LQs": ({"S1", "S3", "H", "q", "l"}, {"M1", "M3", "y1L", "y1R", "y3L", "lambdaH13"}),
    }

    for name, (fields, couplings) in expected.items():
        theory, expressions = load_matchete_model(Path(f"assets/models/{name}.m"), include_lagrangian=False)
        assert theory.name == name
        assert expressions == {}
        assert fields <= set(theory.fields)
        assert couplings <= set(theory.couplings)
        assert set(theory.groups) == {"SU3c", "SU2L", "U1Y"}
        assert theory.index_types["Flavor"].dimension == 3


def test_default_parent_model_child_lagrangians_parse_with_parent_metadata() -> None:
    for name in ("Singlet_Scalar_Extension", "E_VLL", "S1S3LQs"):
        theory, expressions = load_matchete_model(Path(f"assets/models/{name}.m"))
        assert theory.name == name
        assert set(expressions) == {"lagrangian"}
        assert {"H", "q", "l"} <= set(theory.fields)
        theory._validate_registered_expression(expressions["lagrangian"])


def test_runtime_code_does_not_depend_on_matchete_reference_checkout() -> None:
    source_root = Path("src/pychete")
    offenders = []
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "Mathematica_reference" in text or "Matchete/Package" in text:
            offenders.append(path)

    assert offenders == []
