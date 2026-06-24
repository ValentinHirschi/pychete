from __future__ import annotations

from pathlib import Path

from pychete import FieldMassKind, SymbolDataKey, Theory, canonical_string, s
from pychete.loaders import load_matchete_model, load_python_model


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


def test_runtime_code_does_not_depend_on_matchete_reference_checkout() -> None:
    source_root = Path("src/pychete")
    offenders = []
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "Mathematica_reference" in text or "Matchete/Package" in text:
            offenders.append(path)

    assert offenders == []
