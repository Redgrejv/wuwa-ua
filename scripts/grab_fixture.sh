#!/usr/bin/env bash
set -euo pipefail
NAME="${1:?usage: grab_fixture.sh <name>}"
OUT="$HOME/wuwa-ua/tests/ocr_fixtures"
TMP=$(mktemp /tmp/wuwa-grab-XXXX.png)
spectacle -b -n -f -o "$TMP" 2>/dev/null
sleep 1.5
python3 - "$TMP" "$OUT/$NAME.png" <<'PY'
import sys
from PIL import Image
im = Image.open(sys.argv[1])
S = 2
mx, my, mw, mh = 2560, 1080, 2560, 1440
mon = im.crop((mx*S, my*S, (mx+mw)*S, (my+mh)*S))
W, H = mon.size
mon.crop((int(0.18*W), int(0.79*H), int(0.82*W), int(0.93*H))).save(sys.argv[2])
print("saved", sys.argv[2])
PY
rm -f "$TMP"
