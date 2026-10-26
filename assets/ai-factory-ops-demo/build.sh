#!/usr/bin/env bash
# Full pipeline: fonts -> score -> frames -> mp4.
# Frames render in parallel; JOBS defaults to 4.
set -euo pipefail
cd "$(dirname "$0")"

JOBS=${JOBS:-4}
TOTAL=$(grep -oE 'DUR=[0-9]+' demo.html | head -1 | cut -d= -f2)
FRAMES=$((TOTAL * 60))

[ -f fonts.css ] || uv run python fetch_fonts.py
uv run --with numpy python audio.py

mkdir -p frames out
per=$(( (FRAMES + JOBS - 1) / JOBS ))
for ((j = 0; j < JOBS; j++)); do
  a=$((j * per)); b=$((a + per - 1)); [ $b -ge $FRAMES ] && b=$((FRAMES - 1))
  [ $a -gt $b ] && continue
  uv run --with playwright python render.py frames $(seq $a $b) &
done
wait

ffmpeg -y -loglevel error -framerate 60 -i frames/f%05d.png -i audio.wav \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high \
  -movflags +faststart -c:a aac -b:a 192k -shortest \
  out/ai-factory-operations-agent.mp4
echo "out/ai-factory-operations-agent.mp4  (${TOTAL}s)"
