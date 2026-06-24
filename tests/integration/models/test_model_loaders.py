from __future__ import annotations

from pathlib import Path

from pychete import FieldMassKind, Theory, canonical_string, s
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


def test_runtime_code_does_not_depend_on_matchete_reference_checkout() -> None:
    source_root = Path("src/pychete")
    offenders = []
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "Mathematica_reference" in text or "Matchete/Package" in text:
            offenders.append(path)

    assert offenders == []
