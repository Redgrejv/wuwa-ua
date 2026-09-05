from __future__ import annotations

from collections.abc import Sequence

import requests

from wuwa_ua.translate.errors import TranslationUnavailable
from wuwa_ua.translate.glossary import SYSTEM_PROMPT, build_prompt


class OllamaTranslator:
    def __init__(self, model: str, host: str = "http://127.0.0.1:11434", timeout: float = 4.0) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._timeout = timeout

    def translate(
        self,
        text: str,
        context: Sequence[str],
        entries: Sequence[tuple[str, str]],
    ) -> str:
        payload = {
            "model": self._model,
            "system": SYSTEM_PROMPT,
            "prompt": build_prompt(text, context, entries),
            "stream": False,
            "options": {"temperature": 0.2},
        }
        try:
            response = requests.post(f"{self._host}/api/generate", json=payload, timeout=self._timeout)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise TranslationUnavailable(str(exc)) from exc

        if not isinstance(body, dict):
            raise TranslationUnavailable(f"invalid JSON body: not a dict, got {type(body).__name__}")

        raw = body.get("response", "")
        if not isinstance(raw, str):
            raise TranslationUnavailable(f"invalid response value: not a string, got {type(raw).__name__}")

        cleaned = self._clean(raw)
        if not cleaned:
            raise TranslationUnavailable("порожня відповідь моделі")
        return cleaned

    def _clean(self, raw: str) -> str:
        first = raw.strip().splitlines()
        if not first:
            return ""
        line = first[0].strip()
        if len(line) >= 2 and line[0] == '"' and line[-1] == '"':
            line = line[1:-1].strip()
        return line
