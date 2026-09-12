from __future__ import annotations

import importlib


def test_public_happymeasure_namespace_exposes_runtime_version() -> None:
    import happymeasure
    from keith_ivt import version as legacy_version

    assert happymeasure.__version__ == legacy_version.VERSION
    assert happymeasure.PACKAGE_NAME == "happymeasure"
    assert happymeasure.LEGACY_PACKAGE_NAME == "keith_ivt"


def test_happymeasure_version_module_uses_single_legacy_source() -> None:
    public_version = importlib.import_module("happymeasure.version")
    legacy_version = importlib.import_module("keith_ivt.version")

    assert public_version is legacy_version
    assert public_version.PACKAGE_NAME == "happymeasure"
    assert public_version.LEGACY_PACKAGE_NAME == "keith_ivt"


def test_public_command_modules_are_importable() -> None:
    assert importlib.import_module("happymeasure.__main__")
    assert importlib.import_module("happymeasure.hardware_preflight")
    assert importlib.import_module("happymeasure.diagnostics.__main__")
