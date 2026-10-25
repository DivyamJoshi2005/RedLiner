from typing import Callable, Any, Optional
import time


class OSINTExceptionHandler:
    """Manages timeouts, rate limits, and fallback retries for OSINT collectors."""

    @staticmethod
    def execute_with_fallback(func: Callable, fallback_val: Any, max_retries: int = 2) -> Any:
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                time.sleep(0.1)
                if attempt == max_retries - 1:
                    return fallback_val
        return fallback_val
