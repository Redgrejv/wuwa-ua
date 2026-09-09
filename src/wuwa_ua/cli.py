from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path
from typing import Any

from wuwa_ua.config import load_config
from wuwa_ua.control import COMMANDS, ControlServer, send_command
from wuwa_ua.watch import GameWatcher
from wuwa_ua.gender import Speakers
from wuwa_ua.ocr.tesseract import TesseractOcr
from wuwa_ua.pipeline import Pipeline
from wuwa_ua.region import calibrate, render_region_toml
from wuwa_ua.translate.cache import TranslationCache
from wuwa_ua.translate.glossary import Glossary
from wuwa_ua.translate.nllb import NllbTranslator
from wuwa_ua.translate.ollama import OllamaTranslator
from wuwa_ua.types import Region

from wuwa_ua.paths import (
    CACHE_PATH,
    CONFIG_PATH,
    GLOSSARY_PATH,
    HISTORY_PATH,
    SPEAKERS_PATH,
    control_endpoint,
)





def build_morph() -> Any:
    import pymorphy3

    return pymorphy3.MorphAnalyzer(lang="uk")


def build_translator(config: Any) -> Any:
    if config.backend == "nllb":
        return NllbTranslator.from_path(
            config.model_path, device=config.device, beam_size=config.beam_size
        )
    return OllamaTranslator(config.model, config.ollama_host, config.translate_timeout)


def cmd_calibrate(args: argparse.Namespace) -> int:
    token = ""
    source = "window"
    if CONFIG_PATH.is_file():
        config = load_config(CONFIG_PATH)
        token = config.restore_token
        source = config.capture_source
    from wuwa_ua.capture.portal import PortalCapture

    capture = PortalCapture(restore_token=token, source=source)
    capture.start()
    region = calibrate(capture, args.monitor)
    capture.stop()
    print(render_region_toml(region))
    print(f'# restore_token = "{capture.restore_token}"')
    print(f"# скопіюй у {CONFIG_PATH}")
    return 0


def build_capture(config: Any) -> Any:
    if sys.platform == "win32":
        from wuwa_ua.capture.windows import MonitorCapture

        return MonitorCapture(monitor_index=config.monitor_index)

    from wuwa_ua.capture.portal import PortalCapture

    return PortalCapture(restore_token=config.restore_token, source=config.capture_source)


def build_display(config: Any) -> Any:
    if sys.platform == "win32":
        from wuwa_ua.display.overlay_windows import WindowsOverlayDisplay

        return WindowsOverlayDisplay(region=config.region, plate_top=config.plate_top)

    if config.display_mode != "overlay":
        from wuwa_ua.display.window import WindowDisplay

        return WindowDisplay(monitor=config.display_monitor)

    from wuwa_ua.display.overlay import OverlayDisplay

    return OverlayDisplay(
        monitor=config.region.monitor,
        region=config.region,
        plate_top=config.plate_top,
    )


def build_hotkey(config: Any, bindings: dict[str, Any]) -> Any:
    if sys.platform == "win32":
        from wuwa_ua.hotkey_windows import WindowsHotkeyListener

        return WindowsHotkeyListener(config.hotkey_window_title, bindings)

    from wuwa_ua.hotkey import HotkeyListener

    return HotkeyListener(config.hotkey_window, bindings)


def relaunch_with_layer_shell(argv: list[str]) -> None:
    if sys.platform == "win32":
        return

    from wuwa_ua.display.overlay import find_layer_shell_library, needs_preload, preload_env

    library = find_layer_shell_library()
    if not needs_preload(os.environ, library):
        return
    os.execve(
        sys.executable,
        [sys.executable, "-m", "wuwa_ua.cli", *argv],
        preload_env(os.environ, library),
    )


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(CONFIG_PATH)
    if config.display_mode == "overlay":
        relaunch_with_layer_shell(sys.argv[1:])

    capture = build_capture(config)
    capture.start()

    display = build_display(config)
    pipeline = Pipeline(
        config=config,
        capture=capture,
        ocr=TesseractOcr(min_confidence=config.min_confidence),
        translator=build_translator(config),
        cache=TranslationCache(CACHE_PATH),
        glossary=Glossary.load(GLOSSARY_PATH),
        display=display,
        speakers=Speakers.load(SPEAKERS_PATH),
        morph=build_morph(),
        speaker_region=Region(
            monitor=config.region.monitor,
            x=config.speaker_x,
            y=config.speaker_y,
            width=config.speaker_width,
            height=config.speaker_height,
        ),
    )

    server = ControlServer(control_endpoint(), pipeline.handle_command)
    server.start()

    bindings = {
        config.hotkey_key: lambda: pipeline.handle_command("toggle"),
        config.hotkey_refresh_key: lambda: pipeline.handle_command("refresh"),
    }
    hotkey: Any = None
    if any(bindings):
        hotkey = build_hotkey(config, bindings)
        hotkey.start()

    threading.Thread(target=pipeline.run, daemon=True).start()
    try:
        display.run()
    finally:
        if hotkey is not None:
            hotkey.stop()
        server.stop()
        capture.stop()
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    config = load_config(CONFIG_PATH)
    watcher = GameWatcher(config.watch_process, [sys.executable, "-m", "wuwa_ua.cli", "run"])
    print(f"чекаю на процес гри: {config.watch_process}")
    watcher.loop()
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    from wuwa_ua.display.history_window import HistoryWindow

    HistoryWindow(HISTORY_PATH, limit=args.limit).run()
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    try:
        print(send_command(control_endpoint(), args.command))
    except ConnectionError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="wuwa-ua")
    subparsers = parser.add_subparsers(dest="command", required=True)
    calibrate_parser = subparsers.add_parser("calibrate", help="виділити зону субтитрів")
    calibrate_parser.add_argument(
        "--monitor", required=True, help="connector-імʼя екрана гри, напр. DP-4"
    )
    subparsers.add_parser("run", help="запустити переклад")
    subparsers.add_parser("watch", help="чекати на гру й запускати переклад разом із нею")
    history_parser = subparsers.add_parser("history", help="відкрити вікно з історією діалогу")
    history_parser.add_argument("--limit", type=int, default=500, help="скільки останніх реплік показати")
    for name in COMMANDS:
        subparsers.add_parser(name, help=f"надіслати команду {name}")
    args = parser.parse_args()

    if args.command == "calibrate":
        return cmd_calibrate(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "watch":
        return cmd_watch(args)
    if args.command == "history":
        return cmd_history(args)
    return cmd_send(args)


if __name__ == "__main__":
    sys.exit(main())
