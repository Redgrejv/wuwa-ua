from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from wuwa_ua.config import Config
from wuwa_ua.pipeline import Pipeline
from wuwa_ua.translate.cache import TranslationCache
from wuwa_ua.translate.errors import TranslationUnavailable
from wuwa_ua.translate.glossary import Glossary
from wuwa_ua.types import OcrResult, Region, SubtitleLine


class FakeOcr:
    def __init__(self, results: list[OcrResult]) -> None:
        self._results = results
        self.calls = 0

    def recognize(self, image: np.ndarray) -> OcrResult:
        result = self._results[min(self.calls, len(self._results) - 1)]
        self.calls += 1
        return result


class FakeTranslator:
    def __init__(self, reply: str | None = "Нам треба йти.") -> None:
        self._reply = reply
        self.calls = 0
        self.seen_context: list[str] = []

    def translate(
        self,
        text: str,
        context: Sequence[str],
        entries: Sequence[tuple[str, str]],
    ) -> str:
        self.calls += 1
        self.seen_context = list(context)
        if self._reply is None:
            raise TranslationUnavailable("down")
        return self._reply


class FakeDisplay:
    def __init__(self) -> None:
        self.shown: list[SubtitleLine] = []
        self.backgrounds: list[object] = []
        self.clears = 0
        self.pendings = 0
        self.events: list[str] = []

    def show(self, line: SubtitleLine, background=None) -> None:
        self.shown.append(line)
        self.backgrounds.append(background)
        self.events.append("show")

    def pending(self, background=None) -> None:
        self.pendings += 1
        self.events.append("pending")

    def clear(self) -> None:
        self.clears += 1


def make_config(tmp_path: Path) -> Config:
    return Config(
        region=Region(monitor="DP-4", x=0.0, y=0.0, width=1.0, height=1.0),
        sample_fps=4.0,
        change_threshold=3.0,
        stable_frames=2,
        min_confidence=60.0,
        translate_timeout=4.0,
        context_lines=3,
        display_mode="window",
        clear_after=1.5,
        plate_top=0.798,
        speaker_x=0.33,
        speaker_y=0.748,
        speaker_width=0.34,
        speaker_height=0.044,
        speaker_min_confidence=0.0,
        display_monitor="DP-5",
        capture_source="window",
        monitor_index=1,
        hotkey_key="Page_Up",
        hotkey_refresh_key="Home",
        hotkey_window="steam_app_3513350",
        hotkey_window_title="Wuthering Waves",
        watch_process="Wuthering Waves.exe",
        backend="nllb",
        model_path=tmp_path / "model",
        device="cpu",
        beam_size=4,
        model="test",
        ollama_host="http://x",
        restore_token="",
    )


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_pipeline(
    tmp_path: Path,
    ocr: FakeOcr,
    translator: FakeTranslator,
    display: FakeDisplay,
    clock: FakeClock | None = None,
) -> Pipeline:
    return Pipeline(
        config=make_config(tmp_path),
        capture=None,
        ocr=ocr,
        translator=translator,
        cache=TranslationCache(tmp_path / "cache.sqlite"),
        glossary=Glossary.load(tmp_path / "missing.tsv"),
        display=display,
        history_path=tmp_path / "history.jsonl",
        clock=clock,
    )


def blank() -> np.ndarray:
    return np.zeros((10, 10, 3), dtype=np.uint8)


def test_translates_and_shows(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )

    line = pipeline.process(blank())

    assert line is not None
    assert line.translation == "Нам треба йти."
    assert line.translated is True
    assert display.shown[-1].translation == "Нам треба йти."


def test_low_confidence_is_dropped(tmp_path: Path) -> None:
    display = FakeDisplay()
    translator = FakeTranslator()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 40.0)]), translator, display
    )

    assert pipeline.process(blank()) is None
    assert translator.calls == 0
    assert display.shown == []


def test_meaningless_text_is_dropped(tmp_path: Path) -> None:
    display = FakeDisplay()
    translator = FakeTranslator()
    pipeline = make_pipeline(tmp_path, FakeOcr([OcrResult("|| ..", 95.0)]), translator, display)

    assert pipeline.process(blank()) is None
    assert translator.calls == 0


def test_cache_hit_skips_the_translator(tmp_path: Path) -> None:
    display = FakeDisplay()
    translator = FakeTranslator()
    ocr = FakeOcr([OcrResult("We should go.", 90.0), OcrResult("Other line.", 90.0), OcrResult("We should go.", 90.0)])
    pipeline = make_pipeline(tmp_path, ocr, translator, display)

    pipeline.process(blank())
    pipeline.process(blank())
    pipeline.process(blank())

    assert translator.calls == 2
    assert display.shown[-1].translation == "Нам треба йти."


def test_translator_failure_falls_back_to_source(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(reply=None), display
    )

    line = pipeline.process(blank())

    assert line is not None
    assert line.translation == "We should go."
    assert line.translated is False


def test_failed_translation_is_not_cached(tmp_path: Path) -> None:
    display = FakeDisplay()
    cache = TranslationCache(tmp_path / "cache.sqlite")
    pipeline = Pipeline(
        config=make_config(tmp_path),
        capture=None,
        ocr=FakeOcr([OcrResult("We should go.", 90.0)]),
        translator=FakeTranslator(reply=None),
        cache=cache,
        glossary=Glossary.load(tmp_path / "missing.tsv"),
        display=display,
        history_path=tmp_path / "history.jsonl",
    )

    pipeline.process(blank())

    assert cache.get("We should go.") is None


def test_context_grows_and_is_bounded(tmp_path: Path) -> None:
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult(f"Line {index}.", 90.0) for index in range(6)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display)

    for _ in range(6):
        pipeline.process(blank())

    assert len(pipeline.context) == 3


def test_identical_text_is_not_emitted_twice(tmp_path: Path) -> None:
    display = FakeDisplay()
    translator = FakeTranslator()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), translator, display
    )

    assert pipeline.process(blank()) is not None
    assert pipeline.process(blank()) is None
    assert len(display.shown) == 1


def test_text_differing_by_one_word_is_emitted(tmp_path: Path) -> None:
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go now.", 90.0), OcrResult("We should go home.", 90.0)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display)

    assert pipeline.process(blank()) is not None
    assert pipeline.process(blank()) is not None
    assert len(display.shown) == 2


def test_history_file_records_every_shown_line(tmp_path: Path) -> None:
    display = FakeDisplay()
    history = tmp_path / "history.jsonl"
    pipeline = Pipeline(
        config=make_config(tmp_path),
        capture=None,
        ocr=FakeOcr([OcrResult("We should go.", 90.0)]),
        translator=FakeTranslator(),
        cache=TranslationCache(tmp_path / "cache.sqlite"),
        glossary=Glossary.load(tmp_path / "missing.tsv"),
        display=display,
        history_path=history,
    )

    pipeline.process(blank())

    assert "Нам треба йти." in history.read_text(encoding="utf-8")


def test_pause_stops_processing(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )
    pipeline.handle_command("pause")

    assert pipeline.process(blank()) is None

    pipeline.handle_command("resume")

    assert pipeline.process(blank()) is not None


def test_unknown_command_is_reported(tmp_path: Path) -> None:
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("x", 90.0)]), FakeTranslator(), FakeDisplay()
    )

    assert "невідома" in pipeline.handle_command("fly").lower()


def test_overlay_is_cleared_once_the_dialogue_ends(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0)] + [OcrResult("", 0.0)] * 10)
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display, clock)

    pipeline.process(blank())
    pipeline.process(blank())
    clock.advance(2.0)
    pipeline.tick()

    assert display.clears == 1


def test_a_short_gap_does_not_clear_the_overlay(tmp_path: Path) -> None:
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0), OcrResult("", 0.0), OcrResult("", 0.0)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display)

    for _ in range(3):
        pipeline.process(blank())

    assert display.clears == 0


def test_the_overlay_is_not_cleared_again_while_it_stays_empty(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0)] + [OcrResult("", 0.0)] * 30)
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display, clock)

    pipeline.process(blank())
    pipeline.process(blank())
    for _ in range(20):
        clock.advance(2.0)
        pipeline.tick()

    assert display.clears == 1


def test_the_same_line_shows_again_after_a_clear(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    ocr = FakeOcr(
        [OcrResult("We should go.", 90.0), OcrResult("", 0.0), OcrResult("We should go.", 90.0)]
    )
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display, clock)

    pipeline.process(blank())
    pipeline.process(blank())
    clock.advance(2.0)
    pipeline.tick()
    pipeline.process(blank())

    assert display.clears == 1
    assert len(display.shown) == 2


def test_pause_hides_what_is_on_screen(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )
    pipeline.process(blank())

    pipeline.handle_command("pause")

    assert display.clears == 1


def test_pause_with_nothing_on_screen_hides_nothing(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )

    pipeline.handle_command("pause")

    assert display.clears == 0


def test_toggle_hides_then_lets_the_line_come_back(tmp_path: Path) -> None:
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display)
    pipeline.process(blank())

    assert pipeline.handle_command("toggle") == "paused"
    assert display.clears == 1
    assert pipeline.process(blank()) is None

    assert pipeline.handle_command("toggle") == "resumed"

    assert len(display.shown) == 2
    assert pipeline.process(blank()) is None
    assert len(display.shown) == 2


def test_a_line_that_flickers_back_is_shown_but_logged_once(tmp_path: Path) -> None:
    display = FakeDisplay()
    history = tmp_path / "history.jsonl"
    clock = FakeClock()
    ocr = FakeOcr(
        [OcrResult("We should go.", 90.0), OcrResult("", 0.0), OcrResult("We should go.", 90.0)]
    )
    pipeline = Pipeline(
        config=make_config(tmp_path),
        capture=None,
        ocr=ocr,
        translator=FakeTranslator(),
        cache=TranslationCache(tmp_path / "cache.sqlite"),
        glossary=Glossary.load(tmp_path / "missing.tsv"),
        display=display,
        history_path=history,
        clock=clock,
    )

    pipeline.process(blank())
    pipeline.process(blank())
    clock.advance(2.0)
    pipeline.tick()
    pipeline.process(blank())

    assert len(display.shown) == 2
    assert history.read_text(encoding="utf-8").count("We should go.") == 1


def test_a_different_line_in_between_is_logged_again(tmp_path: Path) -> None:
    display = FakeDisplay()
    history = tmp_path / "history.jsonl"
    ocr = FakeOcr(
        [OcrResult("We should go.", 90.0), OcrResult("Wait here.", 90.0), OcrResult("We should go.", 90.0)]
    )
    pipeline = Pipeline(
        config=make_config(tmp_path),
        capture=None,
        ocr=ocr,
        translator=FakeTranslator(),
        cache=TranslationCache(tmp_path / "cache.sqlite"),
        glossary=Glossary.load(tmp_path / "missing.tsv"),
        display=display,
        history_path=history,
    )

    for _ in range(3):
        pipeline.process(blank())

    assert history.read_text(encoding="utf-8").count("We should go.") == 2


def test_resume_brings_the_last_line_back_at_once(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )
    pipeline.process(blank())
    pipeline.handle_command("toggle")

    assert display.clears == 1

    pipeline.handle_command("toggle")

    assert len(display.shown) == 2
    assert display.shown[-1].translation == "Нам треба йти."


def test_resume_without_anything_shown_shows_nothing(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )

    pipeline.handle_command("toggle")
    pipeline.handle_command("toggle")

    assert display.shown == []


def test_a_line_cleared_by_the_dialogue_ending_is_not_restored(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0)] + [OcrResult("", 0.0)] * 10)
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display, clock)

    pipeline.process(blank())
    pipeline.process(blank())
    clock.advance(2.0)
    pipeline.tick()

    pipeline.handle_command("toggle")
    pipeline.handle_command("toggle")

    assert len(display.shown) == 1


class FakeSpeakers:
    def __init__(self, gender: str = "f") -> None:
        self._gender = gender
        self.asked: list[str] = []

    def gender_of(self, name: str) -> str:
        self.asked.append(name)
        return self._gender


def gendered_pipeline(tmp_path: Path, ocr, translator, display, speakers, gender_region=True):
    import pymorphy3

    from wuwa_ua.types import Region as R

    return Pipeline(
        config=make_config(tmp_path),
        capture=None,
        ocr=ocr,
        translator=translator,
        cache=TranslationCache(tmp_path / "cache.sqlite"),
        glossary=Glossary.load(tmp_path / "missing.tsv"),
        display=display,
        history_path=tmp_path / "history.jsonl",
        speakers=speakers,
        morph=pymorphy3.MorphAnalyzer(lang="uk"),
        speaker_region=R(monitor="DP-4", x=0.0, y=0.0, width=1.0, height=0.5) if gender_region else None,
        speaker_ocr=FakeOcr([OcrResult("Jinhsi", 90.0)]),
    )


def test_translation_is_regendered_for_a_female_speaker(tmp_path: Path) -> None:
    display = FakeDisplay()
    speakers = FakeSpeakers("f")
    pipeline = gendered_pipeline(
        tmp_path,
        FakeOcr([OcrResult("I was tired.", 90.0)]),
        FakeTranslator(reply="Я втомився."),
        display,
        speakers,
    )
    pipeline._frame = np.zeros((100, 100, 3), dtype=np.uint8)

    line = pipeline.process(blank())

    assert line is not None
    assert line.translation == "Я втомилася."
    assert speakers.asked == ["Jinhsi"]


def test_translation_is_left_alone_for_a_male_speaker(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = gendered_pipeline(
        tmp_path,
        FakeOcr([OcrResult("I was tired.", 90.0)]),
        FakeTranslator(reply="Я втомився."),
        display,
        FakeSpeakers("m"),
    )
    pipeline._frame = np.zeros((100, 100, 3), dtype=np.uint8)

    assert pipeline.process(blank()).translation == "Я втомився."


def test_unknown_speaker_leaves_the_translation_alone(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = gendered_pipeline(
        tmp_path,
        FakeOcr([OcrResult("I was tired.", 90.0)]),
        FakeTranslator(reply="Я втомився."),
        display,
        FakeSpeakers(""),
    )
    pipeline._frame = np.zeros((100, 100, 3), dtype=np.uint8)

    assert pipeline.process(blank()).translation == "Я втомився."


def test_the_cache_keeps_the_ungendered_translation(tmp_path: Path) -> None:
    display = FakeDisplay()
    cache_path = tmp_path / "cache.sqlite"
    pipeline = gendered_pipeline(
        tmp_path,
        FakeOcr([OcrResult("I was tired.", 90.0)]),
        FakeTranslator(reply="Я втомився."),
        display,
        FakeSpeakers("f"),
    )
    pipeline._frame = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline.process(blank())

    assert TranslationCache(cache_path).get("I was tired.") == "Я втомився."


def test_a_new_line_shows_the_loader_before_translating(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )

    pipeline.process(blank())

    assert display.pendings == 1


def test_a_cached_line_skips_the_loader(tmp_path: Path) -> None:
    display = FakeDisplay()
    ocr = FakeOcr(
        [OcrResult("We should go.", 90.0), OcrResult("Other.", 90.0), OcrResult("We should go.", 90.0)]
    )
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display)

    pipeline.process(blank())
    pipeline.process(blank())
    pipeline.process(blank())

    assert display.pendings == 2


def test_the_loader_comes_before_the_text(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )

    pipeline.process(blank())

    assert display.events == ["pending", "show"]


def test_restoring_after_a_pause_does_not_show_the_loader(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )
    pipeline.process(blank())
    pipeline.handle_command("toggle")

    pipeline.handle_command("toggle")

    assert display.pendings == 1


def test_refresh_translates_the_current_frame_again(tmp_path: Path) -> None:
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display)
    pipeline._frame = np.zeros((100, 100, 3), dtype=np.uint8)
    pipeline.process(blank())

    assert pipeline.handle_command("refresh") == "refreshed"
    assert len(display.shown) == 2


def test_refresh_without_a_frame_reports_it(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )

    assert pipeline.handle_command("refresh") == "нема що оновлювати"
    assert display.shown == []


def test_refresh_while_paused_does_nothing(tmp_path: Path) -> None:
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("We should go.", 90.0)]), FakeTranslator(), display
    )
    pipeline._frame = np.zeros((100, 100, 3), dtype=np.uint8)
    pipeline.handle_command("pause")

    assert pipeline.handle_command("refresh") == "paused"
    assert display.shown == []


def test_speaker_is_recognised_while_the_line_is_translating(tmp_path: Path) -> None:
    import threading

    order: list[str] = []
    started = threading.Event()

    class SlowSpeakerOcr:
        def recognize(self, image):
            started.set()
            time.sleep(0.05)
            order.append("speaker-done")
            return OcrResult("Jinhsi", 90.0)

    class WatchingTranslator(FakeTranslator):
        def translate(self, text, context, entries):
            assert started.wait(1.0), "розпізнавання імені не почалось до перекладу"
            order.append("translate")
            return "Я втомився."

    import pymorphy3

    from wuwa_ua.types import Region as R

    display = FakeDisplay()
    pipeline = Pipeline(
        config=make_config(tmp_path),
        capture=None,
        ocr=FakeOcr([OcrResult("I was tired.", 90.0)]),
        translator=WatchingTranslator(),
        cache=TranslationCache(tmp_path / "cache.sqlite"),
        glossary=Glossary.load(tmp_path / "missing.tsv"),
        display=display,
        history_path=tmp_path / "history.jsonl",
        speakers=FakeSpeakers("f"),
        morph=pymorphy3.MorphAnalyzer(lang="uk"),
        speaker_region=R(monitor="DP-4", x=0.0, y=0.0, width=1.0, height=0.5),
        speaker_ocr=SlowSpeakerOcr(),
    )
    pipeline._frame = np.zeros((100, 100, 3), dtype=np.uint8)

    line = pipeline.process(blank())

    assert line.translation == "Я втомилася."
    assert order == ["translate", "speaker-done"] or order == ["speaker-done", "translate"]


def test_overlay_clears_even_when_the_detector_stays_quiet(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0), OcrResult("", 0.0)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display, clock)

    pipeline.process(blank())
    pipeline.process(blank())

    assert display.clears == 0

    clock.advance(2.0)
    pipeline.tick()

    assert display.clears == 1


def test_a_short_silence_does_not_clear(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("We should go.", 90.0), OcrResult("", 0.0)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display, clock)

    pipeline.process(blank())
    pipeline.process(blank())
    clock.advance(0.5)
    pipeline.tick()

    assert display.clears == 0


def test_a_new_line_cancels_the_pending_clear(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    ocr = FakeOcr([OcrResult("First.", 90.0), OcrResult("", 0.0), OcrResult("Second.", 90.0)])
    pipeline = make_pipeline(tmp_path, ocr, FakeTranslator(), display, clock)

    pipeline.process(blank())
    pipeline.process(blank())
    clock.advance(1.0)
    pipeline.process(blank())
    clock.advance(1.0)
    pipeline.tick()

    assert display.clears == 0


def test_tick_does_nothing_when_nothing_is_shown(tmp_path: Path) -> None:
    clock = FakeClock()
    display = FakeDisplay()
    pipeline = make_pipeline(
        tmp_path, FakeOcr([OcrResult("", 0.0)]), FakeTranslator(), display, clock
    )

    clock.advance(10.0)
    pipeline.tick()

    assert display.clears == 0
