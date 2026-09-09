from __future__ import annotations

from pathlib import Path

from wuwa_ua.translate.nllb import COMPUTE_TYPES, select_device


class Boom:
    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError("no cuda here")


def ok_factory(calls: list[dict]):
    def factory(path: str, **kwargs):
        calls.append({"path": path, **kwargs})
        return object()

    return factory


def test_cuda_is_used_when_it_works() -> None:
    calls: list[dict] = []

    device, _ = select_device(Path("/m"), "cuda", 8, ok_factory(calls))

    assert device == "cuda"
    assert calls[0]["device"] == "cuda"
    assert calls[0]["compute_type"] == COMPUTE_TYPES["cuda"]


def test_cuda_failure_falls_back_to_cpu() -> None:
    calls: list[dict] = []
    attempts = [Boom, ok_factory(calls)]

    def factory(path: str, **kwargs):
        return attempts.pop(0)(path, **kwargs)

    device, _ = select_device(Path("/m"), "cuda", 8, factory)

    assert device == "cpu"
    assert calls[0]["compute_type"] == COMPUTE_TYPES["cpu"]


def test_cpu_is_used_when_asked() -> None:
    calls: list[dict] = []

    device, _ = select_device(Path("/m"), "cpu", 8, ok_factory(calls))

    assert device == "cpu"
    assert len(calls) == 1
