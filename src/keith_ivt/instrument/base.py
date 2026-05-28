from __future__ import annotations

from abc import ABC, abstractmethod
from keith_ivt.models import SweepConfig


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

    def get_current_autorange(self) -> bool:
        raise NotImplementedError("Current autorange query is not supported by this instrument.")

    def set_current_autorange(self, enabled: bool) -> None:
        raise NotImplementedError("Current autorange control is not supported by this instrument.")

    def get_current_range(self) -> float:
        raise NotImplementedError("Current range query is not supported by this instrument.")

    def set_current_range(self, range_A: float) -> None:
        raise NotImplementedError("Current range control is not supported by this instrument.")

    def __enter__(self) -> "SourceMeter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.output_off()
        finally:
            self.close()
