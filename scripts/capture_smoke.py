from __future__ import annotations

import itertools
import sys

import cv2

from wuwa_ua.capture.portal import CaptureError, PortalCapture


def main() -> int:
    source = sys.argv[1] if len(sys.argv) > 1 else "window"
    capture = PortalCapture(source=source)
    try:
        capture.start()
    except CaptureError as exc:
        print(f"не вдалося почати захоплення ({source}): {exc}")
        return 1

    print(f"source: {source}")
    print(f"restore_token: {capture.restore_token}")
    try:
        for index, frame in enumerate(itertools.islice(capture.frames(), 5)):
            path = f"/tmp/wuwa-capture-{index}.png"
            cv2.imwrite(path, frame.image)
            print(f"{path}  {frame.image.shape}")
    except CaptureError as exc:
        print(f"потік обірвався: {exc}")
        return 1
    finally:
        capture.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
