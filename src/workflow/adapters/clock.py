from __future__ import annotations

import time


class SystemClock:
    def now_unix(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()
