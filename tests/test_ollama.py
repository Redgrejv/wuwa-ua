from typing import Any

import pytest
import requests

from wuwa_ua.translate.errors import TranslationUnavailable
from wuwa_ua.translate.ollama import OllamaTranslator


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


def test_returns_the_model_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        return FakeResponse({"response": "Нам треба йти."})

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="test", host="http://x", timeout=1.0)

    assert translator.translate("We should go.", context=[], entries=[]) == "Нам треба йти."


def test_strips_whitespace_and_wrapping_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        return FakeResponse({"response": '  "Нам треба йти."  '})

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="test", host="http://x", timeout=1.0)

    assert translator.translate("We should go.", context=[], entries=[]) == "Нам треба йти."


def test_keeps_only_the_first_line(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        return FakeResponse({"response": "Нам треба йти.\n\nПояснення: це переклад."})

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="test", host="http://x", timeout=1.0)

    assert translator.translate("We should go.", context=[], entries=[]) == "Нам треба йти."


def test_timeout_raises_translation_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        raise requests.Timeout("too slow")

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="test", host="http://x", timeout=1.0)

    with pytest.raises(TranslationUnavailable):
        translator.translate("We should go.", context=[], entries=[])


def test_connection_error_raises_translation_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        raise requests.ConnectionError("ollama is down")

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="test", host="http://x", timeout=1.0)

    with pytest.raises(TranslationUnavailable):
        translator.translate("We should go.", context=[], entries=[])


def test_http_error_raises_translation_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        return FakeResponse({}, status=500)

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="test", host="http://x", timeout=1.0)

    with pytest.raises(TranslationUnavailable):
        translator.translate("We should go.", context=[], entries=[])


def test_empty_reply_raises_translation_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        return FakeResponse({"response": "   "})

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="test", host="http://x", timeout=1.0)

    with pytest.raises(TranslationUnavailable):
        translator.translate("We should go.", context=[], entries=[])


def test_request_carries_model_prompt_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse({"response": "Мандрівнику, зачекай."})

    monkeypatch.setattr(requests, "post", fake_post)
    translator = OllamaTranslator(model="gemma3:4b", host="http://x", timeout=2.5)
    translator.translate("Rover, wait.", context=["Not yet."], entries=[("Rover", "Мандрівник")])

    assert captured["url"] == "http://x/api/generate"
    assert captured["json"]["model"] == "gemma3:4b"
    assert captured["json"]["stream"] is False
    assert "Rover, wait." in captured["json"]["prompt"]
    assert "Мандрівник" in captured["json"]["prompt"]
    assert "Not yet." in captured["json"]["prompt"]
    assert captured["timeout"] == 2.5
