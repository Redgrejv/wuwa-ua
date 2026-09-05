from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

SYSTEM_PROMPT = (
    "Ти перекладаєш діалоги відеогри з англійської українською. "
    "Зберігай тон, регістр і довжину репліки. Не пояснюй, не коментуй, "
    "не додавай лапок від себе. Виводь ЛИШЕ переклад одним рядком."
)


class Glossary:
    def __init__(self, entries: list[tuple[str, str]]) -> None:
        self._entries = entries

    @classmethod
    def load(cls, path: Path) -> Glossary:
        if not path.is_file():
            return cls([])
        entries: list[tuple[str, str]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("\t")
            if len(parts) < 2:
                continue
            source = parts[0].strip()
            target = parts[1].strip()
            if source and target:
                entries.append((source, target))
        return cls(entries)

    def entries_for(self, text: str) -> list[tuple[str, str]]:
        matched: list[tuple[str, str]] = []
        for source, target in self._entries:
            pattern = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE)
            if pattern.search(text):
                matched.append((source, target))
        return matched


def build_prompt(text: str, context: Sequence[str], entries: Sequence[tuple[str, str]]) -> str:
    blocks: list[str] = []
    if entries:
        lines = "\n".join(f"{source} = {target}" for source, target in entries)
        blocks.append(f"ВЛАСНІ НАЗВИ (вживай саме так):\n{lines}")
    if context:
        lines = "\n".join(context)
        blocks.append(f"ПОПЕРЕДНІ РЕПЛІКИ (тільки для контексту, не перекладай їх):\n{lines}")
    blocks.append(f"ПЕРЕКЛАДИ ЦЕ:\n{text}")
    return "\n\n".join(blocks)
