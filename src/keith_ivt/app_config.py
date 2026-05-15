from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os


@dataclass(frozen=True)
class HardwareConfig:
    port: str = "COM3"
    baud_rate: int = 9600
    terminal: str = "REAR"
    sense_mode: str = "2W"
    debug: bool = False
    debug_model: str = "Linear resistor 10 kΩ"


@dataclass(frozen=True)
class SweepDefaults:
    start: float = -1.0
    stop: float = 1.0
    step: float = 0.1
    compliance: float = 0.1
    nplc: float = 1.0
    duration_s: float = 10.0
    interval_s: float = 0.5


@dataclass(frozen=True)
class PlotConfig:
    default_views: tuple[str, ...] = ("Linear", "Log |Y|")
    max_live_points: int = 20000
    default_layout: str = "auto"


@dataclass(frozen=True)
class UiConfig:
    theme: str = "light"
    font_scale: float = 1.0
    font_family: str = "Segoe UI Variable"


@dataclass(frozen=True)
class AppPaths:
    root: Path
    logs: Path
    exports: Path
    autosaves: Path
    presets: Path
    settings: Path

    @classmethod
    def from_root(cls, root: str | os.PathLike[str] | None = None) -> "AppPaths":
        project_root = Path(root) if root is not None else Path.cwd()
        return cls(
            root=project_root,
            logs=project_root / "logs",
            exports=project_root / "exports",
            autosaves=project_root / "autosaves",
            presets=project_root / "presets",
            settings=project_root / "config",
        )

    def ensure(self) -> None:
        for path in (self.logs, self.exports, self.autosaves, self.presets, self.settings):
            path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class AppConfig:
    hardware: HardwareConfig = HardwareConfig()
    sweep: SweepDefaults = SweepDefaults()
    plot: PlotConfig = PlotConfig()
    ui: UiConfig = UiConfig()

    def to_dict(self) -> dict:
        return asdict(self)


def default_config_path(root: str | os.PathLike[str] | None = None) -> Path:
    return AppPaths.from_root(root).settings / "HappyMeasure.config.json"


def save_app_config(config: AppConfig, path: str | os.PathLike[str]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def load_app_config(path: str | os.PathLike[str]) -> AppConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return AppConfig(
        hardware=HardwareConfig(**data.get("hardware", {})),
        sweep=SweepDefaults(**data.get("sweep", {})),
        plot=PlotConfig(**{**data.get("plot", {}), "default_views": tuple(data.get("plot", {}).get("default_views", PlotConfig().default_views))}),
        ui=UiConfig(**data.get("ui", {})),
    )
