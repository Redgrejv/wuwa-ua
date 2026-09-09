from __future__ import annotations

import re
import tomllib
from pathlib import Path

HOTKEY_FIELDS = ("key", "refresh_key", "history_key")
DEFAULTS = {"key": "Page_Up", "refresh_key": "Page_Down", "history_key": "Home"}
NAMED_KEYS = {
    "Page_Up",
    "Page_Down",
    "Home",
    "End",
    "Insert",
    "Delete",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "F10",
    "F11",
    "F12",
}
SECTION = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*$")
CYRILLIC_TO_LATIN = {
    "a": "f", "be": "comma", "ve": "d", "ghe": "u", "de": "l", "ie": "t",
    "zhe": "semicolon", "ze": "p", "i": "b", "shorti": "q", "ka": "r",
    "el": "k", "em": "v", "en": "y", "o": "j", "pe": "g", "er": "h",
    "es": "c", "te": "n", "u": "e", "ef": "a", "ha": "bracketleft",
    "tse": "w", "che": "x", "sha": "i", "shcha": "o", "softsign": "m",
    "yeru": "s", "yu": "period", "ya": "z",
}


class SettingsError(Exception):
    pass


def is_supported_key(name: str) -> bool:
    if not name:
        return True
    if name in NAMED_KEYS:
        return True
    return len(name) == 1 and name.isalnum()


def latin_fallback(name: str) -> str:
    if is_supported_key(name):
        return name
    if not name.startswith("Cyrillic_"):
        return ""
    letter = name.removeprefix("Cyrillic_").lower()
    mapped = CYRILLIC_TO_LATIN.get(letter, "")
    return mapped if is_supported_key(mapped) else ""


def read_hotkeys(path: Path) -> dict[str, str]:
    if not path.is_file():
        return dict(DEFAULTS)
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    section = data.get("hotkey", {})
    if not isinstance(section, dict):
        return dict(DEFAULTS)
    return {field: str(section.get(field, DEFAULTS[field])) for field in HOTKEY_FIELDS}


def _validate(values: dict[str, str]) -> None:
    for field in HOTKEY_FIELDS:
        name = values.get(field, "")
        if not is_supported_key(name):
            raise SettingsError(f"клавіша не підтримується: {name}")
    chosen = [values.get(field, "") for field in HOTKEY_FIELDS]
    filled = [name for name in chosen if name]
    if len(filled) != len(set(filled)):
        raise SettingsError("клавіші однакові — признач різні")


def write_hotkeys(path: Path, values: dict[str, str]) -> None:
    _validate(values)

    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    output: list[str] = []
    written: set[str] = set()
    inside = False

    for line in lines:
        match = SECTION.match(line)
        if match:
            if inside:
                output.extend(_missing(values, written))
                written.update(HOTKEY_FIELDS)
            inside = match.group("name").strip() == "hotkey"
            output.append(line)
            continue
        if inside:
            field = _field_of(line)
            if field is not None:
                output.append(f'{field} = "{values.get(field, DEFAULTS[field])}"')
                written.add(field)
                continue
        output.append(line)

    if inside:
        output.extend(_missing(values, written))
    elif not written:
        if output and output[-1].strip():
            output.append("")
        output.append("[hotkey]")
        output.extend(_missing(values, set()))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(output).rstrip("\n") + "\n", encoding="utf-8")


def _field_of(line: str) -> str | None:
    stripped = line.split("=", 1)[0].strip()
    return stripped if stripped in HOTKEY_FIELDS else None


def _missing(values: dict[str, str], written: set[str]) -> list[str]:
    return [
        f'{field} = "{values.get(field, DEFAULTS[field])}"'
        for field in HOTKEY_FIELDS
        if field not in written
    ]
