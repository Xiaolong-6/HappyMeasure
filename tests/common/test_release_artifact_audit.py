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
