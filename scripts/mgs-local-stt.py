#!/usr/bin/env python3
"""Offline local STT command backend, isolated from Hermes' Python runtime."""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--language', default='pt')
    parser.add_argument('--model', choices=['base'], default='base')
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error('Input audio does not exist')
    if args.input.stat().st_size > 50 * 1024 * 1024:
        parser.error('Audio exceeds 50 MiB local safety limit')
    if args.language != 'pt':
        parser.error('This deployment is approved for Portuguese only')
    import numpy as np
    from faster_whisper import WhisperModel

    args.runtime.mkdir(parents=True, exist_ok=True)
    with (args.runtime / 'transcription.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        decoded = subprocess.run(
            ['/usr/bin/ffmpeg', '-nostdin', '-v', 'error', '-i', str(args.input),
             '-t', '1800', '-f', 'f32le', '-ac', '1', '-ar', '16000', 'pipe:1'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
        ).stdout
        if not decoded:
            raise RuntimeError('Audio decoded to an empty buffer')
        model = WhisperModel(
            args.model, device='cpu', compute_type='int8', cpu_threads=2,
            download_root=str(args.runtime / 'models'), local_files_only=True,
        )
        segments, _ = model.transcribe(
            np.frombuffer(decoded, dtype=np.float32), language=args.language,
        )
        text = ' '.join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise RuntimeError('Transcription returned no text')
        args.output.write_text(text + '\n', encoding='utf-8')
        os.chmod(args.output, 0o600)


if __name__ == '__main__':
    main()
