#!/usr/bin/env bash
# Builds the demo reel end to end.
#
#   ./demo/build.sh
#
# Needs: .venv-demo with manim installed, plus ffmpeg on PATH.
# Everything it produces is derived -- the sources are scene.py and music.py.
set -euo pipefail

cd "$(dirname "$0")/.."
PY=.venv-demo/bin/python
MANIM=.venv-demo/bin/manim
RAW=demo/media/videos/scene/1080p60/BeingHumanDemo.mp4
OUT=demo/being-human-demo.mp4

echo "==> render"
"$MANIM" -qh -r 1080,1080 --media_dir demo/media demo/scene.py BeingHumanDemo >/dev/null 2>&1

DUR=$("$PY" -c "import json;print(json.load(open('demo/captions.json'))['duration'])")

echo "==> music bed (${DUR}s)"
"$PY" demo/music.py --seconds "$DUR" --out demo/bed.wav

echo "==> subtitles"
"$PY" - <<'PYEOF'
import json

def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return "%02d:%02d:%06.3f" % (h, m, s).replace(".", ",") if False else \
           "%02d:%02d:%02d,%03d" % (h, m, int(s), round((s - int(s)) * 1000))

d = json.load(open("demo/captions.json"))
lines = []
for i, c in enumerate(d["cues"], 1):
    lines += [str(i), "%s --> %s" % (ts(c["start"]), ts(c["end"])), c["text"], ""]
open("demo/being-human-demo.srt", "w").write("\n".join(lines))
print("   %d cues -> demo/being-human-demo.srt" % len(d["cues"]))
PYEOF

echo "==> mux audio"
# -shortest so the bed can never run past the picture.
ffmpeg -v error -y -i "$RAW" -i demo/bed.wav \
  -c:v copy -c:a aac -b:a 192k -shortest "$OUT"

echo "==> readme gif"
# Two-pass palette: a single global palette on this flat dark UI keeps the file
# small without the banding a naive -vf scale would produce.
ffmpeg -v error -y -i "$OUT" -vf "fps=12,scale=480:-1:flags=lanczos,palettegen=stats_mode=diff" /tmp/pal.png
ffmpeg -v error -y -i "$OUT" -i /tmp/pal.png \
  -lavfi "fps=12,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4" \
  demo/being-human-demo.gif

echo
echo "built:"
ls -lh "$OUT" demo/being-human-demo.gif demo/being-human-demo.srt | awk '{print "  "$9"  "$5}'
