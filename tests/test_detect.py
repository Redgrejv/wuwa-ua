import numpy as np

from wuwa_ua.detect import ChangeDetector


def solid(value: int) -> np.ndarray:
    return np.full((80, 400, 3), value, dtype=np.uint8)


def noisy(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(80, 400, 3), dtype=np.uint8)


def test_first_stable_frame_is_emitted_after_the_gate() -> None:
    detector = ChangeDetector(change_threshold=3.0, stable_frames=2)

    assert detector.push(solid(10)) is None
    assert detector.push(solid(10)) is not None


def test_unstable_frames_are_never_emitted() -> None:
    detector = ChangeDetector(change_threshold=3.0, stable_frames=2)

    for seed in range(6):
        assert detector.push(noisy(seed)) is None


def test_same_content_is_not_emitted_twice() -> None:
    detector = ChangeDetector(change_threshold=3.0, stable_frames=2)
    detector.push(solid(10))
    detector.push(solid(10))

    for _ in range(5):
        assert detector.push(solid(10)) is None


def test_new_content_is_emitted_after_stabilising() -> None:
    detector = ChangeDetector(change_threshold=3.0, stable_frames=2)
    detector.push(solid(10))
    detector.push(solid(10))

    assert detector.push(solid(200)) is None
    emitted = detector.push(solid(200))

    assert emitted is not None
    assert int(emitted.mean()) == 200


def test_noise_below_threshold_does_not_retrigger() -> None:
    detector = ChangeDetector(change_threshold=3.0, stable_frames=2)
    detector.push(solid(100))
    detector.push(solid(100))

    assert detector.push(solid(101)) is None
    assert detector.push(solid(101)) is None


def test_longer_gate_requires_more_stable_frames() -> None:
    detector = ChangeDetector(change_threshold=3.0, stable_frames=4)

    assert detector.push(solid(10)) is None
    assert detector.push(solid(10)) is None
    assert detector.push(solid(10)) is None
    assert detector.push(solid(10)) is not None


def test_reset_clears_emitted_state() -> None:
    detector = ChangeDetector(change_threshold=3.0, stable_frames=2)
    detector.push(solid(10))
    detector.push(solid(10))
    detector.reset()

    assert detector.push(solid(10)) is None
    assert detector.push(solid(10)) is not None
