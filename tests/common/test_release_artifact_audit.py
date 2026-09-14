from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "tools" / "release" / "audit_portable_artifacts.py"


def _load_audit_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_artifact_audit", AUDIT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_map_runtime_audit_allows_numpy_openblas_name() -> None:
    audit = _load_audit_module()
    names = [
        "MapReconstruction/_internal/numpy.libs/libscipy_openblas64_abc123.dll",
        "MapReconstruction/_internal/PySide6/Qt6Core.dll",
    ]
    assert audit._map_runtime_failures(names, "artifact.zip") == []


def test_map_runtime_audit_rejects_real_optional_packages() -> None:
    audit = _load_audit_module()
    names = [
        "MapReconstruction/_internal/scipy/signal/_peak_finding.py",
        "MapReconstruction/_internal/PySide6/Qt6WebEngineCore.dll",
    ]
    failures = audit._map_runtime_failures(names, "artifact.zip")
    assert any("scipy" in failure.lower() for failure in failures)
    assert any("webengine" in failure.lower() for failure in failures)


def test_name_audit_allows_empty_logs_directory_but_rejects_log_files() -> None:
    audit = _load_audit_module()
    assert audit._name_failures("logs", "portable", is_file=False) == []
    failures = audit._name_failures("logs/session.log", "portable", is_file=True)
    assert any("runtime log file" in failure for failure in failures)


def test_internal_dependency_text_keeps_exact_privacy_checks_without_generic_home_noise() -> None:
    audit = _load_audit_module()
    upstream_example = "See /Users/example/project for an upstream documentation example."
    assert audit._text_failures(upstream_example, "dependency", scan_generic_home=False) == []

    private_identifier = "instrument serial: " + "461" + "2952"
    failures = audit._text_failures(private_identifier, "dependency", scan_generic_home=False)
    assert any("private identifier" in failure for failure in failures)
