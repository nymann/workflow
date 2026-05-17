from __future__ import annotations


class NullNotifier:
    def notify(self, message: str) -> None:
        _ = message


class StdoutNotifier:
    def notify(self, message: str) -> None:
        print(message)
