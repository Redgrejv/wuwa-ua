from __future__ import annotations

import re
import unicodedata

REPLACEMENTS = {
    '‘': "'",
    '’': "'",
    '‚': "'",
    '“': '"',
    '”': '"',
    '„': '"',
    '…': '...',
    '\xa0': ' ',
}

DASHES = {
    '–': '-',
    '—': '-',
}

LONE_PIPE = re.compile(r"(?<![^\s(\"'])\|(?=[\s.,!?;:]|'[a-z]|$)")
HYPHEN_BREAK = re.compile(r"-\s*\n\s*")
WHITESPACE = re.compile(r"\s+")
KEPT_CONTROLS = "\n\t\r"
MIN_LETTERS = 2
MIN_LETTER_RATIO = 0.5


def normalize(text: str) -> str:
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    text = LONE_PIPE.sub("I", text)
    text = HYPHEN_BREAK.sub("", text)
    for source, target in DASHES.items():
        text = text.replace(source, target)
    text = "".join(char for char in text if unicodedata.category(char)[0] != "C" or char in KEPT_CONTROLS)
    text = WHITESPACE.sub(" ", text)
    return text.strip()


def is_meaningful(text: str) -> bool:
    stripped = normalize(text)
    letters = [char for char in stripped if char.isalpha()]
    if len(letters) < MIN_LETTERS:
        return False
    visible = [char for char in stripped if not char.isspace()]
    if not visible:
        return False
    return len(letters) / len(visible) >= MIN_LETTER_RATIO


def cache_key(text: str) -> str:
    return normalize(text).casefold()