from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wuwa_ua.types import Region

DISPLAY_MODES = ("window", "overlay")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    region: Region
    sample_fps: float
    change_threshold: float
    stable_frames: int
    min_confidence: float
    translate_timeout: float
    context_lines: int
    display_mode: str
    display_monitor: str
    model: str
    ollama_host: str
    restore_token: str


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"секція [{name}] має бути таблицею")
    return value


def _region(data: dict[str, Any]) -> Region:
    raw = data.get("region")
    if not isinstance(raw, dict):
        raise ConfigError("у конфізі відсутня секція [region]")
    try:
        region = Region(
            monitor=str(raw["monitor"]),
            x=float(raw["x"]),
            y=float(raw["y"]),
            width=float(raw["width"]),
            height=float(raw["height"]),
        )
    except KeyError as exc:
        raise ConfigError(f"у секції [region] відсутнє поле {exc.args[0]}") from exc
    if region.width <= 0 or region.height <= 0:
        raise ConfigError("ширина й висота [region] мають бути додатними")
    if not (0.0 <= region.x and 0.0 <= region.y):
        raise ConfigError("зона виходить за межі екрана")
    if region.x + region.width > 1.0 or region.y + region.height > 1.0:
        raise ConfigError("зона виходить за межі екрана")
    return region


def load_config(path: Path) -> Config:
    if not path.is_file():
        raise ConfigError(f"конфіг не знайдено: {path}")
    with path.open("rb") as handle:
        data = tomllib.load(handle)

    region = _region(data)
    detect = _section(data, "detect")
    ocr = _section(data, "ocr")
    translate = _section(data, "translate")
    display = _section(data, "display")
    capture = _section(data, "capture")

    mode = str(display.get("mode", "window"))
    if mode not in DISPLAY_MODES:
        raise ConfigError(f"невідомий режим виводу: {mode}")

    return Config(
        region=region,
        sample_fps=float(capture.get("sample_fps", 4.0)),
        change_threshold=float(detect.get("change_threshold", 3.0)),
        stable_frames=int(detect.get("stable_frames", 2)),
        min_confidence=float(ocr.get("min_confidence", 60.0)),
        translate_timeout=float(translate.get("timeout", 4.0)),
        context_lines=int(translate.get("context_lines", 3)),
        display_mode=mode,
        display_monitor=str(display.get("monitor", "")),
        model=str(translate.get("model", "")),
        ollama_host=str(translate.get("host", "http://127.0.0.1:11434")),
        restore_token=str(capture.get("restore_token", "")),
    )
