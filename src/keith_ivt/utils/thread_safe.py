from __future__ import annotations

from collections import deque
from typing import Generic, Iterable, TypeVar
import threading

T = TypeVar("T")


class ThreadSafeBuffer(Generic[T]):
    """Bounded thread-safe FIFO-style buffer with snapshot reads."""

    def __init__(self, maxsize: int = 1000) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._buffer: deque[T] = deque(maxlen=maxsize)
        self._lock = threading.RLock()
        self._maxsize = maxsize
        self._overflowed = False

    def append(self, item: T) -> None:
        with self._lock:
            if len(self._buffer) >= self._maxsize:
                self._overflowed = True
            self._buffer.append(item)

    def extend(self, items: Iterable[T]) -> None:
        with self._lock:
            for item in items:
                if len(self._buffer) >= self._maxsize:
                    self._overflowed = True
                self._buffer.append(item)

    def pop_front(self) -> T | None:
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer.popleft()

    def get_snapshot(self) -> list[T]:
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._overflowed = False

    def had_overflow(self) -> bool:
        with self._lock:
            value = self._overflowed
            self._overflowed = False
            return value

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)

    def is_empty(self) -> bool:
        return len(self) == 0


class ThreadSafeXYBuffer:
    """Thread-safe bounded XY buffer that keeps X/Y lengths consistent."""

    def __init__(self, maxsize: int = 1000) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._x_data: deque[float] = deque(maxlen=maxsize)
        self._y_data: deque[float] = deque(maxlen=maxsize)
        self._lock = threading.RLock()
        self._maxsize = maxsize

    def append(self, x: float, y: float) -> None:
        with self._lock:
            self._x_data.append(float(x))
            self._y_data.append(float(y))

    def get_snapshot(self) -> tuple[list[float], list[float]]:
        with self._lock:
            return list(self._x_data), list(self._y_data)

    def clear(self) -> None:
        with self._lock:
            self._x_data.clear()
            self._y_data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._x_data)
