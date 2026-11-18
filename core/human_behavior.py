"""
CappyAutoPost - Human Behavior Simulator
Simulates realistic human interaction:
- Keystroke delays with natural jitter and thinking pauses
- Gaussian bell-curve delays between posts
- Smooth mouse scrolling and reading pauses
"""
import time
import random
import math
from typing import Optional

class HumanSimulator:
    @staticmethod
    def compute_gaussian_delay(min_seconds: float, max_seconds: float) -> float:
        """
        Computes a Gaussian bell-curve delay strictly bounded within [min_seconds, max_seconds].
        Does not sleep by itself.
        """
        low = max(0.0, float(min_seconds))
        high = max(low, float(max_seconds))
        if high <= low:
            return low

        mean = (low + high) / 2.0
        std_dev = max(0.1, (high - low) / 4.0)
        val = random.gauss(mean, std_dev)
        return max(low, min(high, val))

    @staticmethod
    def smart_sleep(target_seconds: float, std_dev: float = None, min_seconds: float = 3.0, max_seconds: Optional[float] = None) -> float:
        """
        Sleeps with a Gaussian bell-curve distribution to mimic real human timing.
        Returns the actual slept duration.
        """
        if std_dev is None:
            std_dev = max(0.5, target_seconds * 0.15)
        
        actual_delay = random.gauss(target_seconds, std_dev)
        actual_delay = max(min_seconds, actual_delay)
        if max_seconds is not None:
            actual_delay = min(max_seconds, actual_delay)
        
        if actual_delay > 0:
            time.sleep(actual_delay)
        return actual_delay

    @staticmethod
    def get_keystroke_delay(char: str) -> float:
        """
        Calculates typing delay for a single character in seconds.
        Adds extra delay after punctuation or occasional 'thinking' pauses.
        """
        # Base typing speed: 30ms to 75ms
        base_delay = random.uniform(0.03, 0.075)

        # Longer pause after punctuation
        if char in {".", "!", "?", "\n"}:
            base_delay += random.uniform(0.15, 0.35)
        elif char in {",", ";", ":", "-"}:
            base_delay += random.uniform(0.08, 0.18)
        # 8% chance of a slight thinking hesitation
        elif random.random() < 0.08:
            base_delay += random.uniform(0.12, 0.28)

        return base_delay

    @staticmethod
    def smooth_scroll(driver, scroll_amount: int = 400, steps: int = 5) -> None:
        """
        Smoothly scrolls the browser viewport downwards to emulate natural reading.
        """
        try:
            step_size = scroll_amount // steps
            for _ in range(steps):
                jitter = random.randint(-15, 15)
                driver.execute_script(f"window.scrollBy(0, {step_size + jitter});")
                time.sleep(random.uniform(0.08, 0.2))
            time.sleep(random.uniform(0.3, 0.7))
        except Exception:
            pass
