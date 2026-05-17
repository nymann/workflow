from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramNotifier:
    bot_token: str
    chat_id: str
    timeout_seconds: float = 10.0

    def notify(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        body = json.dumps({"chat_id": self.chat_id, "text": message}).encode()
        request = urllib.request.Request(
            url,
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            response.read()
