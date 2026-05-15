from __future__ import annotations

from abc import ABC, abstractmethod
from keith_ivt.models import SenseMode, SweepConfig, Terminal


class SourceMeter(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def identify(self) -> str: ...

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def configure_for_sweep(self, config: SweepConfig) -> None: ...

    @abstractmethod
    def set_source(self, source_cmd: str, value: float) -> None: ...

    @abstractmethod
    def read_source_and_measure(self) -> tuple[float, float]: ...

    @abstractmethod
    def output_on(self) -> None: ...

    @abstractmethod
    def output_off(self) -> None: ...

    def __enter__(self) -> "SourceMeter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.output_off()
        finally:
            self.close()
