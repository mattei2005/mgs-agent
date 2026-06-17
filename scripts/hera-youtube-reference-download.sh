#!/usr/bin/env bash
set -euo pipefail

# Download/analyze YouTube reference videos for Hera using a persistent authenticated cookie jar.
# Do NOT commit cookies. Default cookie path lives under the Hera profile private data dir.

URL="${1:-}"
if [[ -z "$URL" ]]; then
  echo "usage: $0 <youtube-url> [output-dir]" >&2
  exit 2
fi

OUT_DIR="${2:-/root/mgs-agent/data/references/hera/youtube}"
COOKIE_FILE="${HERA_YOUTUBE_COOKIES:-/root/.hermes/profiles/hera/secrets/youtube-cookies.txt}"

if [[ ! -s "$COOKIE_FILE" ]]; then
  cat >&2 <<EOF
ERROR: YouTube cookies file not found or empty: $COOKIE_FILE

Provide a Netscape-format cookies.txt exported from a logged-in browser, then run again.
Do not paste cookies into chat; attach as a file or store securely.
EOF
  exit 3
fi

mkdir -p "$OUT_DIR"
VIDEO_OUT="$OUT_DIR/reference.%(ext)s"

uvx yt-dlp \
  --cookies "$COOKIE_FILE" \
  --user-agent 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36' \
  -f 'bv*[height<=1080]+ba/b[height<=1080]/b' \
  --merge-output-format mp4 \
  -o "$VIDEO_OUT" \
  "$URL"

VIDEO_PATH="$(find "$OUT_DIR" -maxdepth 1 -type f -name 'reference.*' | sort | tail -1)"
if [[ -z "$VIDEO_PATH" || ! -s "$VIDEO_PATH" ]]; then
  echo "ERROR: download did not produce a video in $OUT_DIR" >&2
  exit 4
fi

mkdir -p "$OUT_DIR/frames"
ffmpeg -y -i "$VIDEO_PATH" -vf 'fps=1,scale=540:-1' "$OUT_DIR/frames/frame_%03d.jpg" >/tmp/hera-youtube-frames.log 2>&1
ffprobe -v error -show_entries format=duration,size:stream=index,codec_type,codec_name,width,height -of json "$VIDEO_PATH" > "$OUT_DIR/ffprobe.json"

printf 'ok=true\nvideo=%s\nframes_dir=%s\nprobe=%s\n' "$VIDEO_PATH" "$OUT_DIR/frames" "$OUT_DIR/ffprobe.json"
