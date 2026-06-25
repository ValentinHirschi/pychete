from __future__ import annotations

from pathlib import Path

from symbolica import Expression

from pychete import FieldChirality, FieldMassKind, FieldRole, GroupKind, RepresentationReality, SymbolDataKey, SymbolRole, Theory, canonical_string, s
from pychete.backends import spenso
from pychete.loaders import load_matchete_model, load_python_model, parse_matchete_expression
from pychete.validation_fixtures import load_validation_fixture


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


def test_vlf_mathematica_and_python_assets_share_metadata_with_distinct_free_lag_conventions() -> None:
    mathematica_theory, mathematica_expressions = load_matchete_model(Path("assets/models/VLF_toy_model.m"))
    python_theory, python_expressions = load_python_model(Path("assets/models/VLF_toy_model.py"))
    mathematica_lagrangian = canonical_string(mathematica_expressions["lagrangian"])
    python_lagrangian = canonical_string(python_expressions["lagrangian"])

    assert mathematica_theory.to_json_obj() == python_theory.to_json_obj()
    assert set(mathematica_expressions) == set(python_expressions) == {"lagrangian"}
    assert mathematica_lagrangian != python_lagrangian
    assert mathematica_lagrangian.count("field_A") == 1
    assert python_lagrangian.count("field_A") == 3
    assert "/pychete::Coupling(VLF_toy_model::coupling_e,pychete::List(),0)^2" in mathematica_lagrangian
    assert "/pychete::Coupling(VLF_toy_model::coupling_e,pychete::List(),0)^2" not in python_lagrangian


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
    assert theory.representations[rep_key].dimension_value == 4
    assert theory.representations[rep_key].reality_kind is RepresentationReality.PSEUDOREAL
    label = theory.representation_labels["quad"]
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_GROUP.value) == "SU2L"
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_DYNKIN.value) == [Expression.num(3)]
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_DIMENSION.value) == 4
    assert label.get_symbol_data(SymbolDataKey.REPRESENTATION_REALITY.value) == RepresentationReality.PSEUDOREAL.value
    assert "representation_group_SU2L" in _local_tags(label)


def test_matchete_loader_preserves_defined_cg_tensors(tmp_path: Path) -> None:
    model = tmp_path / "cg_tensors.m"
    model.write_text(
        "\n".join(
            [
                "DefineGaugeGroup[SU2L, SU@2, gL, W];",
                "DefineRepresentation[SU2L[quad], SU2L, {3}];",
                "DefineCG[C4, {SU2L[fund], Bar@SU2L[fund], Bar@SU2L[quad]},",
                "    First@InvariantTensors[SU@2, {{1}, CRep@{1}, CRep@{3}}, Normalization->2]];",
                "DefineField[Theta, Scalar, Indices->SU2L[quad], Mass->{Heavy, MTheta}];",
                "Module[{i,j,M}, C4[i,j,M] Theta[M]];",
            ]
        ),
        encoding="utf-8",
    )

    theory, expressions = load_matchete_model(model, theory_name="loader_cg_tensors")

    c4 = theory.cg_tensor_handle("C4")
    reps = c4.definition.representation_exprs
    assert set(expressions) == {"lagrangian"}
    assert len(reps) == 3
    assert canonical_string(reps[0]) == "loader_cg_tensors::group_SU2L(pychete::fund)"
    assert canonical_string(reps[1]) == "pychete::Bar(loader_cg_tensors::group_SU2L(pychete::fund))"
    assert canonical_string(reps[2]) == "pychete::Bar(loader_cg_tensors::group_SU2L(loader_cg_tensors::representation_quad))"
    assert c4.definition.source_text is not None
    assert "InvariantTensors" in c4.definition.source_text
    assert (
        "pychete::CG(loader_cg_tensors::cg_tensor_C4,"
        "pychete::List(loader_cg_tensors::external_i,loader_cg_tensors::external_j,loader_cg_tensors::external_M))"
        in canonical_string(expressions["lagrangian"])
    )
    assert "external_C4" not in canonical_string(expressions["lagrangian"])


def test_matchete_loader_lowers_builtin_cg_labels_to_registered_tensors() -> None:
    theory, expressions = load_matchete_model(Path("assets/models/SM.m"))
    eps = parse_matchete_expression("CG[eps[SU2L],{i,j}]", theory)
    gen = parse_matchete_expression("CG[gen[SU2L[fund]],{J,i,j}]", theory)
    fstruct = parse_matchete_expression("CG[fStruct[SU2L],{I,J,K}]", theory)

    assert "eps_SU2L" in theory.cg_tensors
    assert "gen_SU2L_fund" in theory.cg_tensors
    assert "fStruct_SU2L" in theory.cg_tensors
    assert canonical_string(eps).startswith("pychete::CG(SM::cg_tensor_eps_SU2L,")
    assert canonical_string(gen).startswith("pychete::CG(SM::cg_tensor_gen_SU2L_fund,")
    assert canonical_string(fstruct).startswith("pychete::CG(SM::cg_tensor_fStruct_SU2L,")
    lagrangian = canonical_string(expressions["lagrangian"])
    assert "SM::cg_tensor_eps_SU2L" in lagrangian
    assert "external_eps" not in lagrangian
    assert theory.cg_tensors["eps_SU3c"].source_text == "builtin:eps"
    assert len(theory.cg_tensors["eps_SU3c"].representation_exprs) == 3


def test_matchete_expression_parser_registers_unknown_external_symbols() -> None:
    theory = Theory("loader_externals")
    expression = parse_matchete_expression("cHB + F[1] + Coupling[cHW, {}, 0]", theory)

    assert sorted(theory.externals) == ["F", "cHB", "cHW"]
    assert theory.external_handle("cHB").label.get_symbol_data(SymbolDataKey.ROLE.value) == SymbolRole.EXTERNAL.value
    assert theory.external_handle("cHW").label.get_symbol_data(SymbolDataKey.NAME.value) == "cHW"
    assert "loader_externals::external_F(1)" in canonical_string(expression)
    assert "pychete::Coupling(loader_externals::external_cHW,pychete::List(),0)" in canonical_string(expression)
    theory._validate_registered_expression(expression)


def test_matchete_loader_expands_module_local_cg_helper_functions(tmp_path: Path) -> None:
    model = tmp_path / "local_cg_helpers.m"
    model.write_text(
        "\n".join(
            [
                "DefineGaugeGroup[SU2L, SU@2, gL, W];",
                "Module[{i,j,J,tau},",
                "  tau[Jadj_, ifund_, jfund_] := 2 CG[gen[SU2L[fund]], {Jadj, ifund, jfund}];",
                "  tau[J,i,j]",
                "];",
            ]
        ),
        encoding="utf-8",
    )

    theory, expressions = load_matchete_model(model, theory_name="loader_local_cg_helpers")
    lagrangian = canonical_string(expressions["lagrangian"])

    assert "external_tau" not in lagrangian
    assert "loader_local_cg_helpers::cg_tensor_gen_SU2L_fund" in lagrangian
    assert lagrangian.startswith("2*pychete::CG(")
    assert theory.cg_tensors["gen_SU2L_fund"].source_text == "builtin:gen"


def test_s1s3_model_lagrangian_expands_local_cg_helpers() -> None:
    theory, expressions = load_matchete_model(Path("assets/models/S1S3LQs.m"))
    lagrangian = canonical_string(expressions["lagrangian"])

    assert "external_tauSU2L" not in lagrangian
    assert "external_epsilonSU2L" not in lagrangian
    assert "external_fSU2L" not in lagrangian
    assert "S1S3LQs::cg_tensor_gen_SU2L_fund" in lagrangian
    assert "S1S3LQs::cg_tensor_eps_SU2L" in lagrangian
    assert "S1S3LQs::cg_tensor_fStruct_SU2L" in lagrangian
    assert lagrangian.count("pychete::CG(") >= 5
    theory._validate_registered_expression(expressions["lagrangian"])


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
    assert theory.representations["SM::group_SU3c(pychete::fund)"].dimension_value == 3
    assert theory.representations["SM::group_SU3c(pychete::fund)"].reality_kind is RepresentationReality.COMPLEX
    assert theory.representations["SM::group_SU3c(pychete::adj)"].dimension_value == 8
    assert theory.representations["SM::group_SU3c(pychete::adj)"].reality_kind is RepresentationReality.REAL
    assert theory.representations["SM::group_SU2L(pychete::fund)"].dimension_value == 2
    assert theory.representations["SM::group_SU2L(pychete::fund)"].reality_kind is RepresentationReality.PSEUDOREAL


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
        if name == "S1S3LQs":
            s1_color = theory.fields["S1"].indices[0]
            assert theory.is_conjugate_representation(s1_color) is True
            assert theory.representation_dimension(s1_color) == 3
            assert theory.representation_reality(s1_color) is RepresentationReality.COMPLEX


def test_default_parent_model_child_lagrangians_parse_with_parent_metadata() -> None:
    for name in ("Singlet_Scalar_Extension", "E_VLL", "S1S3LQs"):
        theory, expressions = load_matchete_model(Path(f"assets/models/{name}.m"))
        assert theory.name == name
        assert set(expressions) == {"lagrangian"}
        assert {"H", "q", "l"} <= set(theory.fields)
        theory._validate_registered_expression(expressions["lagrangian"])


def test_default_loaded_model_fixtures_store_sparse_cg_components_for_spenso() -> None:
    expected_components = {"tFundf_SU2L": 36, "tFundf_SU3c": 576}
    for name in ("Singlet_Scalar_Extension", "E_VLL", "S1S3LQs"):
        fixture = load_validation_fixture(Path(f"assets/validation/pychete/{name}.model_fixture.json"))
        theory = fixture.theory()
        library = spenso.cg_tensor_library_to_spenso(theory)

        for tensor_name, component_count in expected_components.items():
            definition = theory.cg_tensor_handle(tensor_name).definition
            components = spenso.stored_cg_tensor_components(theory, tensor_name)
            structure = spenso.cg_tensor_structure_to_spenso(theory, tensor_name)
            registered = library[structure.get_name().to_expression()]

            assert definition.tensor_expr is not None
            assert definition.source_text is not None
            assert definition.source_text.startswith("SparseArray[Automatic")
            assert components is not None
            assert len(components) == component_count
            assert type(registered).__name__ == "TensorStructure"
            assert len(registered) == component_count


def test_runtime_code_does_not_depend_on_matchete_reference_checkout() -> None:
    source_root = Path("src/pychete")
    offenders = []
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "Mathematica_reference" in text or "Matchete/Package" in text:
            offenders.append(path)

    assert offenders == []
