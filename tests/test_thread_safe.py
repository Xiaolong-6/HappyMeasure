from __future__ import annotations

import threading

from keith_ivt.utils.thread_safe import ThreadSafeBuffer, ThreadSafeXYBuffer


def test_thread_safe_buffer_bounds_and_overflow_flag():
    buffer = ThreadSafeBuffer[int](maxsize=3)
    buffer.extend([1, 2, 3, 4])
    assert buffer.get_snapshot() == [2, 3, 4]
    assert buffer.had_overflow() is True
    assert buffer.had_overflow() is False
    assert buffer.pop_front() == 2
    assert buffer.get_snapshot() == [3, 4]


def test_thread_safe_xy_buffer_keeps_pairs_consistent():
    xy = ThreadSafeXYBuffer(maxsize=1000)

    def worker(offset: int) -> None:
        for idx in range(100):
            xy.append(offset + idx, -(offset + idx))

    threads = [threading.Thread(target=worker, args=(n * 1000,)) for n in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    x, y = xy.get_snapshot()
    assert len(x) == len(y) == 500
    assert all(a == -b for a, b in zip(x, y))
