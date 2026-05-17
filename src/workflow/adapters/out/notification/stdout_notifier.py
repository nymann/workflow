from __future__ import annotations


class StdoutNotifier:
    def notify(self, message: str) -> None:
        print(message)
