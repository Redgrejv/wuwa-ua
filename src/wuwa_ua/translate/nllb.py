from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from wuwa_ua.translate.errors import TranslationUnavailable

SOURCE_LANG = "eng_Latn"
TARGET_LANG = "ukr_Cyrl"
BEAM_SIZE = 4
INTRA_THREADS = 8
COMPUTE_TYPES = {"cuda": "int8_float16", "cpu": "int8"}
CUDA_LIB_GLOB = "nvidia/*/lib/*.so*"
MAX_DECODING_LENGTH = 160
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


class TranslationEngine(Protocol):
    def translate(self, sentences: list[str]) -> list[str]: ...


def split_sentences(text: str) -> list[str]:
    return [part for part in SENTENCE_END.split(text.strip()) if part]


def apply_glossary(text: str, entries: Sequence[tuple[str, str]]) -> str:
    for source, target in sorted(entries, key=lambda entry: len(entry[0]), reverse=True):
        text = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE).sub(target, text)
    return text


def preload_cuda_libraries() -> None:
    import ctypes
    import site

    roots = [Path(entry) for entry in site.getsitepackages()]
    roots.extend(Path(entry) for entry in (site.getusersitepackages(),) if entry)
    for root in roots:
        for library in sorted(root.glob(CUDA_LIB_GLOB)):
            try:
                ctypes.CDLL(str(library), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                continue


def select_device(
    model_path: Path,
    device: str,
    threads: int,
    factory: Any,
) -> tuple[str, Any]:
    if device == "cuda":
        preload_cuda_libraries()
        try:
            translator = factory(
                str(model_path),
                device="cuda",
                compute_type=COMPUTE_TYPES["cuda"],
                intra_threads=threads,
            )
        except Exception:
            device = "cpu"
        else:
            return "cuda", translator
    translator = factory(
        str(model_path),
        device="cpu",
        compute_type=COMPUTE_TYPES["cpu"],
        intra_threads=threads,
    )
    return "cpu", translator


class CTranslate2Engine:
    def __init__(
        self,
        model_path: Path,
        beam_size: int = BEAM_SIZE,
        threads: int = INTRA_THREADS,
        device: str = "cuda",
    ) -> None:
        import ctranslate2
        import sentencepiece

        self._beam_size = beam_size
        self._tokenizer = sentencepiece.SentencePieceProcessor(
            str(model_path / "sentencepiece.bpe.model")
        )
        self.device, self._translator = select_device(
            model_path, device, threads, ctranslate2.Translator
        )

    def translate(self, sentences: list[str]) -> list[str]:
        batch = [
            [SOURCE_LANG] + self._tokenizer.encode(sentence, out_type=str) + ["</s>"]
            for sentence in sentences
        ]
        results = self._translator.translate_batch(
            batch,
            target_prefix=[[TARGET_LANG]] * len(batch),
            beam_size=self._beam_size,
            max_decoding_length=MAX_DECODING_LENGTH,
        )
        translated: list[str] = []
        for result in results:
            tokens = result.hypotheses[0]
            if tokens[:1] == [TARGET_LANG]:
                tokens = tokens[1:]
            translated.append(self._tokenizer.decode(tokens))
        return translated


class NllbTranslator:
    def __init__(self, engine: TranslationEngine) -> None:
        self._engine = engine

    @classmethod
    def from_path(
        cls,
        model_path: Path,
        device: str = "cuda",
        beam_size: int = BEAM_SIZE,
    ) -> NllbTranslator:
        return cls(engine=CTranslate2Engine(model_path, beam_size=beam_size, device=device))

    def translate(
        self,
        text: str,
        context: Sequence[str],
        entries: Sequence[tuple[str, str]],
    ) -> str:
        sentences = split_sentences(apply_glossary(text, entries))
        if not sentences:
            return ""
        try:
            translated = self._engine.translate(sentences)
        except Exception as exc:
            raise TranslationUnavailable(str(exc)) from exc
        return " ".join(translated)
