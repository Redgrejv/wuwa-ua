#!/usr/bin/env bash
set -euo pipefail
NAME="${1:?usage: grab_fixture.sh <name>}"
OUT="$HOME/wuwa-ua/captures"
mkdir -p "$OUT"
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
mon.save(sys.argv[2])
print(f"saved {sys.argv[2]} {mon.size}")
PY
rm -f "$TMP"
