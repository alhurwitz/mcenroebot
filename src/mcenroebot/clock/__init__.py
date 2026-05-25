"""Testable timing abstractions — Clock protocol, SystemClock, FakeClock.

This package provides a thin layer over Python's timing primitives so that
any code that needs to sleep or read the current time can accept a ``Clock``
and be tested deterministically with ``FakeClock`` without any wall-clock
delays.

Layout
------
    protocol.py  — Clock protocol (runtime-checkable).
    system.py    — SystemClock backed by time.monotonic() + asyncio.sleep.
    fake.py      — FakeClock for deterministic unit tests.
    __main__.py  — entry point for `python -m mcenroebot.clock`.

Coordinate / units
------------------
    Time values are in **seconds**. ``SystemClock.now()`` uses
    ``time.monotonic()`` — not ``time.time()`` — because the predictor and
    swing modules use clocks for *relative* timing only, and
    ``time.monotonic()`` is immune to wall-clock jumps (NTP corrections,
    DST, etc.) that could otherwise produce catastrophic negative deltas.

Negative sleep
--------------
    Passing a negative ``seconds`` argument to ``sleep()`` or ``advance()``
    raises ``ValueError``. ``asyncio.sleep`` silently accepts negatives and
    treats them as zero, but in this domain a negative sleep almost always
    indicates a programming error (e.g. a predicted impact time already
    passed), so explicit rejection is safer.
"""

from __future__ import annotations

from mcenroebot.clock.fake import FakeClock
from mcenroebot.clock.protocol import Clock
from mcenroebot.clock.system import SystemClock

__all__ = ["Clock", "FakeClock", "SystemClock", "_demo"]


def _demo() -> None:
    """Print a quick sanity-check of both clock implementations.

    Run with ``python -m mcenroebot.clock``.
    """
    import asyncio as _asyncio

    print("=== SystemClock ===")
    sc: Clock = SystemClock()
    t0 = sc.now()
    t1 = sc.now()
    print(f"  now() x2 : {t0:.6f}  {t1:.6f}  (non-decreasing: {t1 >= t0})")

    async def _system_sleep_demo() -> None:
        before = sc.now()
        await sc.sleep(0.02)
        after = sc.now()
        print(f"  sleep(0.02): elapsed {after - before:.4f}s")

    _asyncio.run(_system_sleep_demo())

    print()
    print("=== FakeClock ===")
    fc = FakeClock(start=100.0)
    print(f"  start  : now={fc.now()}  elapsed={fc.elapsed}")
    fc.advance(5.0)
    print(f"  +5s    : now={fc.now()}  elapsed={fc.elapsed}")

    async def _fake_sleep_demo() -> None:
        import time as _time

        wall_before = _time.monotonic()
        await fc.sleep(1_000.0)
        wall_after = _time.monotonic()
        print(f"  sleep(1000): fake now={fc.now()}  wall elapsed={wall_after - wall_before:.6f}s")

    _asyncio.run(_fake_sleep_demo())
