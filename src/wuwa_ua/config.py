from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wuwa_ua.types import Region

DISPLAY_MODES = ("window", "overlay")
CAPTURE_SOURCES = ("window", "monitor")
BACKENDS = ("nllb", "ollama")
DEVICES = ("cuda", "cpu")
DEFAULT_MODEL_PATH = Path.home() / ".local/share/wuwa-ua/models/nllb-1.3b"


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
    clear_after: float
    plate_top: float
    speaker_x: float
    speaker_y: float
    speaker_width: float
    speaker_height: float
    speaker_min_confidence: float
    display_monitor: str
    capture_source: str
    hotkey_key: str
    hotkey_refresh_key: str
    hotkey_window: str
    watch_process: str
    backend: str
    model_path: Path
    device: str
    beam_size: int
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
    hotkey = _section(data, "hotkey")
    watch = _section(data, "watch")
    speaker = _section(data, "speaker")
    capture = _section(data, "capture")

    mode = str(display.get("mode", "window"))
    if mode not in DISPLAY_MODES:
        raise ConfigError(f"невідомий режим виводу: {mode}")

    source = str(capture.get("source", "window"))
    if source not in CAPTURE_SOURCES:
        raise ConfigError(f"невідоме джерело захоплення: {source}")

    backend = str(translate.get("backend", "nllb"))
    if backend not in BACKENDS:
        raise ConfigError(f"невідомий бекенд перекладу: {backend}")

    device = str(translate.get("device", "cuda"))
    if device not in DEVICES:
        raise ConfigError(f"невідомий пристрій для перекладу: {device}")

    return Config(
        region=region,
        sample_fps=float(capture.get("sample_fps", 4.0)),
        change_threshold=float(detect.get("change_threshold", 3.0)),
        stable_frames=int(detect.get("stable_frames", 2)),
        min_confidence=float(ocr.get("min_confidence", 60.0)),
        translate_timeout=float(translate.get("timeout", 4.0)),
        context_lines=int(translate.get("context_lines", 3)),
        display_mode=mode,
        clear_after=float(display.get("clear_after", 1.5)),
        plate_top=float(display.get("plate_top", 0.0)),
        speaker_x=float(speaker.get("x", 0.33)),
        speaker_y=float(speaker.get("y", 0.748)),
        speaker_width=float(speaker.get("width", 0.34)),
        speaker_height=float(speaker.get("height", 0.044)),
        speaker_min_confidence=float(speaker.get("min_confidence", 0.0)),
        display_monitor=str(display.get("monitor", "")),
        capture_source=source,
        hotkey_key=str(hotkey.get("key", "Page_Up")),
        hotkey_refresh_key=str(hotkey.get("refresh_key", "Home")),
        hotkey_window=str(hotkey.get("window", "steam_app_3513350")),
        watch_process=str(watch.get("process", "Wuthering Waves.exe")),
        backend=backend,
        model_path=Path(str(translate.get("model_path", DEFAULT_MODEL_PATH))).expanduser(),
        device=device,
        beam_size=int(translate.get("beam_size", 4)),
        model=str(translate.get("model", "")),
        ollama_host=str(translate.get("host", "http://127.0.0.1:11434")),
        restore_token=str(capture.get("restore_token", "")),
    )
