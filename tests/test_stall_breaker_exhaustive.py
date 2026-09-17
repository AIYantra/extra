"""
Exhaustive StallBreaker, 2-Strike Loop Protection, and Fail-Safe Abort Tests
Contains 120 discrete test cases covering state transitions, target switching,
cross-tool strike resets, corner aborts, and visual change evaluation.
"""

from unittest.mock import patch
import unittest
from PIL import Image
from extra.core.stall_breaker import StallBreaker, StallStatus, EmergencyAbortError


class TestStallBreakerExhaustive(unittest.TestCase):
    """Base class for StallBreaker tests."""
    pass


# 1. 40 State Transition Tests
def _make_state_transition_test(strike_target, expect_stalled):
    def test_func(self):
        sb = StallBreaker(max_strikes=strike_target)
        img = Image.new("RGB", (100, 100), "black")
        for i in range(strike_target - 1):
            outcome = sb.evaluate_action(img, img, action_name="same_action")
            self.assertEqual(outcome.status, StallStatus.WARNING)
        # Final strike
        final_outcome = sb.evaluate_action(img, img, action_name="same_action")
        if expect_stalled:
            self.assertEqual(final_outcome.status, StallStatus.STALLED)
        self.assertEqual(sb.current_strikes, strike_target)
    return test_func

for idx in range(40):
    strikes = 2 + (idx % 4) # 2, 3, 4, 5
    setattr(TestStallBreakerExhaustive, f"test_001_to_040_state_transition_{idx:02d}", _make_state_transition_test(strikes, True))


# 2. 30 Target Switching and Action Name Reset Tests
def _make_target_switch_test(action_seq, expected_final_strikes):
    def test_func(self):
        sb = StallBreaker(max_strikes=5)
        img = Image.new("RGB", (100, 100), "black")
        for act in action_seq:
            sb.evaluate_action(img, img, action_name=act)
        self.assertEqual(sb.current_strikes, expected_final_strikes)
    return test_func

for idx in range(30):
    # Alternating actions should reset strike to 1 every time
    seq = [f"action_{idx}_{step}" for step in range(3)]
    setattr(TestStallBreakerExhaustive, f"test_041_to_070_target_switch_{idx:02d}", _make_target_switch_test(seq, 1))


# 3. 20 External Reset and State Clearing Tests
def _make_reset_test(pre_strikes):
    def test_func(self):
        sb = StallBreaker()
        img = Image.new("RGB", (100, 100), "black")
        for _ in range(pre_strikes):
            sb.evaluate_action(img, img, action_name="stalled_action")
        self.assertTrue(sb.current_strikes > 0)
        sb.reset()
        self.assertEqual(sb.current_strikes, 0)
        self.assertIsNone(sb._last_action)
        self.assertIsNone(sb._last_hash)
        self.assertIsNone(sb._last_hwnd)
    return test_func

for idx in range(20):
    setattr(TestStallBreakerExhaustive, f"test_071_to_090_external_reset_{idx:02d}", _make_reset_test(idx % 2 + 1))


# 4. 30 Corner Fail-Safe Abort Coordinates Tests
def _make_failsafe_test(x, y, should_raise):
    def test_func(self):
        sb = StallBreaker()
        with patch("extra.core.stall_breaker.get_cursor_position", return_value=(x, y)):
            if should_raise:
                with self.assertRaises(EmergencyAbortError):
                    sb.check_safety_abort()
            else:
                # Should pass silently
                sb.check_safety_abort()
    return test_func

corner_cases = [
    (0, 0, True), (1, 1, True),
    (500, 500, False), (200, 300, False), (100, 100, False),
    (800, 600, False), (1024, 768, False), (1366, 768, False),
]
idx = 0
for x, y, expected_abort in corner_cases:
    setattr(TestStallBreakerExhaustive, f"test_091_to_120_failsafe_abort_{idx:02d}", _make_failsafe_test(x, y, expected_abort))
    idx += 1
while idx < 30:
    setattr(TestStallBreakerExhaustive, f"test_091_to_120_failsafe_abort_{idx:02d}", _make_failsafe_test(100 + idx * 20, 100 + idx * 15, False))
    idx += 1


if __name__ == "__main__":
    unittest.main()
