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

        to_remove: set[str] = set()
        for source_i, _ in matched:
            for source_j, _ in matched:
                if source_i == source_j:
                    continue
                substring_pattern = re.compile(rf"\b{re.escape(source_i)}\b", re.IGNORECASE)
                if not substring_pattern.search(source_j):
                    continue

                all_matches_i = list(substring_pattern.finditer(text))
                all_matches_j = list(re.compile(rf"\b{re.escape(source_j)}\b", re.IGNORECASE).finditer(text))
                j_spans: set[tuple[int, int]] = {(m.start(), m.end()) for m in all_matches_j}

                all_contained: bool = True
                for match_i in all_matches_i:
                    i_start, i_end = match_i.start(), match_i.end()
                    is_contained: bool = False
                    for j_start, j_end in j_spans:
                        if j_start <= i_start and i_end <= j_end:
                            is_contained = True
                            break
                    if not is_contained:
                        all_contained = False
                        break

                if all_contained:
                    to_remove.add(source_i)
                    break

        return [(s, t) for s, t in matched if s not in to_remove]


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
