from __future__ import annotations

import json
import time
from concurrent.futures import Future, ThreadPoolExecutor
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from wuwa_ua.config import Config
from wuwa_ua.detect import ChangeDetector
from wuwa_ua.gender import regender
from wuwa_ua.normalize import cache_key, is_meaningful
from wuwa_ua.region import crop, plate_crop
from wuwa_ua.translate.errors import TranslationUnavailable
from wuwa_ua.types import Region, SubtitleLine

DEFAULT_HISTORY_PATH = Path.home() / ".local" / "share" / "wuwa-ua" / "history.jsonl"


class Pipeline:
    def __init__(
        self,
        config: Config,
        capture: Any,
        ocr: Any,
        translator: Any,
        cache: Any,
        glossary: Any,
        display: Any,
        history_path: Path = DEFAULT_HISTORY_PATH,
        clock: Any = None,
        speakers: Any = None,
        morph: Any = None,
        speaker_region: Region | None = None,
        speaker_ocr: Any = None,
    ) -> None:
        self._config = config
        self._capture = capture
        self._ocr = ocr
        self._translator = translator
        self._cache = cache
        self._glossary = glossary
        self._display = display
        self._history_path = history_path
        self._clock = clock or time.monotonic
        self._speakers = speakers
        self._morph = morph
        self._speaker_region = speaker_region
        self._speaker_ocr = speaker_ocr or ocr
        self._detector = ChangeDetector(config.change_threshold, config.stable_frames)
        self._paused = False
        self._last_key = ""
        self._last_logged_key = ""
        self._empty_since: float | None = None
        self._showing = False
        self._frame: np.ndarray | None = None
        self._last_line: SubtitleLine | None = None
        self._speaker_pool = ThreadPoolExecutor(max_workers=1)
        self.context: deque[str] = deque(maxlen=config.context_lines)

    def handle_command(self, command: str) -> str:
        if command == "pause":
            self._pause()
            return "paused"
        if command == "resume":
            self._resume()
            return "resumed"
        if command == "toggle":
            if self._paused:
                self._resume()
                return "resumed"
            self._pause()
            return "paused"
        if command == "refresh":
            return self._refresh()
        if command == "status":
            return "paused" if self._paused else "running"
        return f"невідома команда: {command}"

    def process(self, region_crop: np.ndarray) -> SubtitleLine | None:
        if self._paused:
            return None

        result = self._ocr.recognize(region_crop)
        if result.confidence < self._config.min_confidence or not is_meaningful(result.text):
            self._note_empty()
            return None

        self._empty_since: float | None = None
        source = result.text
        key = cache_key(source)
        if key == self._last_key:
            return None
        self._last_key = key

        gender = self._speaker_pool.submit(self._speaker_gender)

        cached = self._cache.get(source)
        if cached is not None:
            return self._emit(SubtitleLine(source, self._gendered(cached, gender), True, time.time()))

        self._display.pending(self._background())
        try:
            translation = self._translator.translate(
                source, list(self.context), self._glossary.entries_for(source)
            )
        except TranslationUnavailable:
            return self._emit(SubtitleLine(source, source, False, time.time()))

        self._cache.put(source, translation)
        return self._emit(
            SubtitleLine(source, self._gendered(translation, gender), True, time.time())
        )

    def run(self) -> None:
        interval = 1.0 / self._config.sample_fps
        next_sample = time.monotonic()
        for frame in self._capture.frames():
            now = time.monotonic()
            if now < next_sample:
                continue
            next_sample = now + interval
            if self._paused:
                continue
            self._frame = frame.image
            candidate = self._detector.push(crop(frame.image, self._config.region))
            if candidate is not None:
                self.process(candidate)
            else:
                self.tick()

    def _gendered(self, translation: str, pending: Future[str]) -> str:
        try:
            gender = pending.result(timeout=2.0)
        except Exception:
            return translation
        if not gender or self._morph is None:
            return translation
        return regender(translation, gender, self._morph)

    def _speaker_gender(self) -> str:
        if self._speakers is None or self._speaker_region is None or self._frame is None:
            return ""
        name = self._speaker_ocr.recognize(crop(self._frame, self._speaker_region))
        if name.confidence < self._config.speaker_min_confidence or not name.text.strip():
            return ""
        return self._speakers.gender_of(name.text)

    def _background(self) -> np.ndarray | None:
        if self._frame is None:
            return None
        return plate_crop(self._frame, self._config.region, self._config.plate_top)

    def _pause(self) -> None:
        self._paused = True
        if self._showing:
            self._hide(keep_last=True)

    def _resume(self) -> None:
        self._paused = False
        if self._last_line is not None and not self._showing:
            restored = self._last_line
            self._emit(restored)
            self._last_key = cache_key(restored.source)

    def _refresh(self) -> str:
        if self._paused:
            return "paused"
        if self._frame is None:
            return "нема що оновлювати"
        self._last_key = ""
        self._last_logged_key = ""
        self.process(crop(self._frame, self._config.region))
        return "refreshed"

    def _note_empty(self) -> None:
        if not self._showing:
            return
        if self._empty_since is None:
            self._empty_since = self._clock()
        self.tick()

    def tick(self) -> None:
        if not self._showing or self._empty_since is None:
            return
        if self._clock() - self._empty_since >= self._config.clear_after:
            self._hide()

    def _hide(self, keep_last: bool = False) -> None:
        self._display.clear()
        self._showing = False
        self._empty_since: float | None = None
        self._last_key = ""
        if not keep_last:
            self._frame = None
            self._last_line = None

    def _emit(self, line: SubtitleLine) -> SubtitleLine:
        self._display.show(line, self._background())
        self._showing = True
        self._last_line = line
        key = cache_key(line.source)
        if key != self._last_logged_key:
            self.context.append(line.source)
            self._log(line)
            self._last_logged_key = key
        return line

    def _log(self, line: SubtitleLine) -> None:
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": line.timestamp,
            "source": line.source,
            "translation": line.translation,
            "translated": line.translated,
        }
        with self._history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
