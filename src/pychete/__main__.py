from __future__ import annotations

from pprint import pprint


def main() -> None:
    import symbolica
    import symbolica.community.idenso
    import symbolica.community.spenso
    import symbolica.community.vakint

    from . import Theory, s

    local_versions = getattr(symbolica, "LOCAL_VERSIONS", None)
    if not isinstance(local_versions, dict):
        raise RuntimeError("symbolica.LOCAL_VERSIONS is missing or is not a dict")

    expected = {"symbolica", "spenso", "idenso", "vakint"}
    missing = expected.difference(local_versions)
    if missing:
        raise RuntimeError(f"symbolica.LOCAL_VERSIONS is missing keys: {sorted(missing)}")

    theory = Theory("smoke")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    assert phi().format_plain()

    print("Loaded pychete with Symbolica community modules: idenso, spenso, vakint")
    print("LOCAL_VERSIONS:")
    pprint(local_versions)


if __name__ == "__main__":
    main()
