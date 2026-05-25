"""Tests for EscCalibrator one-shot ESC calibration routine."""

from __future__ import annotations

import inspect

import pytest

from mcenroebot.calibrate.esc import EscCalibrator, _SETTLE_S
from mcenroebot.clock import FakeClock
from mcenroebot.drivers import MockBLDCDriver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _RecordingPrompt:
    """Records every prompt message without blocking."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, msg: str) -> None:
        self.prompts.append(msg)


def _make_calibrator() -> tuple[MockBLDCDriver, FakeClock, _RecordingPrompt, EscCalibrator]:
    driver = MockBLDCDriver()
    clock = FakeClock()
    prompt = _RecordingPrompt()
    calibrator = EscCalibrator(driver=driver, clock=clock, prompt_fn=prompt)
    return driver, clock, prompt, calibrator


# ---------------------------------------------------------------------------
# Test 1: Throttle sequence is [1.0, 0.0] then disarm
# ---------------------------------------------------------------------------


class TestThrottleSequence:
    async def test_throttle_history_is_1_0_then_disarm_0(self) -> None:
        """After run(), throttle_history == [1.0, 0.0, 0.0].

        The third 0.0 is appended by disarm() per MockBLDCDriver convention.
        """
        driver, _, _, calibrator = _make_calibrator()
        await calibrator.run()

        # set_throttle(1.0) → set_throttle(0.0) → disarm() appends 0.0
        assert driver.throttle_history == [1.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# Test 2: Armed during throttle phase, disarmed at end
# ---------------------------------------------------------------------------


class TestArmedStateLifecycle:
    async def test_driver_is_armed_during_sequence_and_disarmed_at_end(self) -> None:
        """Verify armed flag transitions: False → True (after arm) → False (after disarm)."""
        driver = MockBLDCDriver()
        clock = FakeClock()
        armed_states_during: list[bool] = []

        class _SpyPrompt:
            def __init__(self) -> None:
                self._call = 0

            def __call__(self_inner, msg: str) -> None:  # noqa: N805
                self_inner._call += 1
                # Step 1 prompt fires BEFORE arm(), so driver not armed yet.
                # Steps 2 and 3 fire AFTER arm(), so driver IS armed.
                if self_inner._call > 1:
                    armed_states_during.append(driver.armed)

        calibrator = EscCalibrator(driver=driver, clock=clock, prompt_fn=_SpyPrompt())
        assert driver.armed is False
        await calibrator.run()

        # Both mid-sequence checks (step 2 and step 3) must have seen armed=True.
        assert armed_states_during == [True, True]
        # After run() completes, driver must be disarmed.
        assert driver.armed is False


# ---------------------------------------------------------------------------
# Test 3: Prompts appear in the correct order relative to throttle calls
# ---------------------------------------------------------------------------


class TestPromptOrdering:
    async def test_three_prompts_in_correct_order(self) -> None:
        """Exactly three prompts, with correct interleaving against throttle calls.

        Expected interleaved event log:
          prompt-1 (step 1 — before any throttle)
          throttle(1.0)
          prompt-2 (step 2 — between max and min throttle)
          throttle(0.0)
          prompt-3 (step 3 — after min throttle, before disarm)
          throttle(0.0)  ← from disarm()
        """
        driver = MockBLDCDriver()
        clock = FakeClock()
        event_log: list[str] = []

        class _LoggingPrompt:
            def __call__(self, msg: str) -> None:
                event_log.append(f"prompt:{msg}")

        # Wrap MockBLDCDriver to emit events.
        original_set_throttle = driver.set_throttle
        original_disarm = driver.disarm

        def _set_throttle_spy(t: float) -> None:
            original_set_throttle(t)
            event_log.append(f"set_throttle:{t}")

        def _disarm_spy() -> None:
            original_disarm()
            event_log.append("disarm")

        driver.set_throttle = _set_throttle_spy  # type: ignore[assignment]
        driver.disarm = _disarm_spy  # type: ignore[assignment]

        calibrator = EscCalibrator(driver=driver, clock=clock, prompt_fn=_LoggingPrompt())
        await calibrator.run()

        # Three prompts total.
        prompt_events = [e for e in event_log if e.startswith("prompt:")]
        assert len(prompt_events) == 3

        # Extract indices for ordering assertions.
        p1_idx = event_log.index(prompt_events[0])
        p2_idx = event_log.index(prompt_events[1])
        p3_idx = event_log.index(prompt_events[2])
        set1_idx = event_log.index("set_throttle:1.0")
        set0_idx = event_log.index("set_throttle:0.0")
        disarm_idx = event_log.index("disarm")

        # prompt-1 comes before set_throttle(1.0).
        assert p1_idx < set1_idx
        # prompt-2 comes after set_throttle(1.0) and before set_throttle(0.0).
        assert set1_idx < p2_idx < set0_idx
        # prompt-3 comes after set_throttle(0.0) and before disarm.
        assert set0_idx < p3_idx < disarm_idx

    async def test_prompt_messages_contain_step_keywords(self) -> None:
        """Each prompt message is non-empty and contains the word 'ESC' or a step number."""
        _, _, prompt, calibrator = _make_calibrator()
        await calibrator.run()

        assert len(prompt.prompts) == 3
        # Spot-check that messages are meaningful (contain "Step" and a number).
        for i, msg in enumerate(prompt.prompts, 1):
            assert f"Step {i}" in msg, f"Prompt {i} missing 'Step {i}': {msg!r}"


# ---------------------------------------------------------------------------
# Test 4: FakeClock.sleep is used between prompts
# ---------------------------------------------------------------------------


class TestClockSleep:
    async def test_elapsed_equals_two_settle_delays(self) -> None:
        """Exactly two clock.sleep(_SETTLE_S) calls → elapsed == 2 * _SETTLE_S."""
        _, clock, _, calibrator = _make_calibrator()
        await calibrator.run()

        assert clock.elapsed == pytest.approx(2 * _SETTLE_S)

    async def test_no_real_wall_clock_time_consumed(self) -> None:
        """FakeClock means run() finishes in microseconds, not seconds."""
        import time

        _, clock, _, calibrator = _make_calibrator()
        t0 = time.monotonic()
        await calibrator.run()
        wall_elapsed = time.monotonic() - t0

        # Real wall time must be well under 1 s (typically < 1 ms).
        assert wall_elapsed < 1.0
        # FakeClock elapsed must equal the configured settle total.
        assert clock.elapsed == pytest.approx(2 * _SETTLE_S)


# ---------------------------------------------------------------------------
# Test 5: Default prompt_fn is built-in input
# ---------------------------------------------------------------------------


class TestDefaultPromptFn:
    def test_default_prompt_fn_is_builtin_input(self) -> None:
        """Constructor default for prompt_fn is the built-in input function."""
        sig = inspect.signature(EscCalibrator.__init__)
        default = sig.parameters["prompt_fn"].default
        assert default is input


# ---------------------------------------------------------------------------
# Test 6: KeyboardInterrupt propagates and driver is still disarmed
# ---------------------------------------------------------------------------


class _InterruptOnSecondCall:
    """Raises KeyboardInterrupt on the second call."""

    def __init__(self) -> None:
        self._calls = 0

    def __call__(self, msg: str) -> None:
        self._calls += 1
        if self._calls >= 2:
            raise KeyboardInterrupt("Simulated Ctrl-C")


class TestKeyboardInterruptPropagates:
    async def test_keyboard_interrupt_propagates(self) -> None:
        """KeyboardInterrupt raised by prompt_fn is not swallowed."""
        driver, clock, _, _ = _make_calibrator()
        calibrator = EscCalibrator(
            driver=driver, clock=clock, prompt_fn=_InterruptOnSecondCall()
        )
        with pytest.raises(KeyboardInterrupt):
            await calibrator.run()

    async def test_driver_disarmed_after_keyboard_interrupt(self) -> None:
        """try/finally guarantees disarm even when prompt_fn raises mid-sequence."""
        driver = MockBLDCDriver()
        clock = FakeClock()
        calibrator = EscCalibrator(
            driver=driver, clock=clock, prompt_fn=_InterruptOnSecondCall()
        )
        with pytest.raises(KeyboardInterrupt):
            await calibrator.run()

        assert driver.armed is False

    async def test_throttle_history_reflects_partial_sequence_on_interrupt(self) -> None:
        """When step-2 prompt raises, set_throttle(1.0) was sent but not set_throttle(0.0).

        After disarm(), history is [1.0, 0.0] — one set_throttle + disarm's 0.0.
        """
        driver = MockBLDCDriver()
        clock = FakeClock()
        calibrator = EscCalibrator(
            driver=driver, clock=clock, prompt_fn=_InterruptOnSecondCall()
        )
        with pytest.raises(KeyboardInterrupt):
            await calibrator.run()

        # set_throttle(1.0) recorded, then disarm() appends 0.0.
        assert driver.throttle_history == [1.0, 0.0]


# ---------------------------------------------------------------------------
# Test 7: Sequential calibrations don't accumulate stale state
# ---------------------------------------------------------------------------


class TestSequentialCalibrations:
    async def test_two_runs_produce_same_throttle_pattern_each_time(self) -> None:
        """A second run() on the same calibrator produces the same history pattern.

        Note: throttle_history accumulates across runs (MockBLDCDriver never resets
        its internal list), so we compare per-run slices, not the entire list.
        """
        driver, clock, _, calibrator = _make_calibrator()

        await calibrator.run()
        history_after_first = driver.throttle_history[:]
        split = len(history_after_first)

        await calibrator.run()
        history_after_second = driver.throttle_history[split:]

        # Each run contributes [1.0, 0.0, 0.0].
        assert history_after_first == [1.0, 0.0, 0.0]
        assert history_after_second == [1.0, 0.0, 0.0]

    async def test_two_runs_accumulate_clock_time(self) -> None:
        """Two sequential runs advance the FakeClock by 2 * 2 * _SETTLE_S."""
        _, clock, _, calibrator = _make_calibrator()

        await calibrator.run()
        await calibrator.run()

        assert clock.elapsed == pytest.approx(4 * _SETTLE_S)
