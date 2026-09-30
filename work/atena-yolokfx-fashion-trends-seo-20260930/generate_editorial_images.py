#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT_DIR = Path('/root/mgs-agent/work/atena-yolokfx-fashion-trends-seo-20260930/images')
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL = 'gemini-3.1-flash-image-preview'

BRIEFS = {
    'how-to-style-polka-dots': (
        'Ultra-realistic editorial fashion photograph, horizontal 3:2 composition. '
        'A stylish adult woman in a bright but refined urban cafe setting wearing a balanced black-and-white polka-dot midi skirt with a simple solid knit top and clean minimal accessories. '
        'Natural candid posture, outfit fully visible, sophisticated everyday styling rather than runway drama, soft window light, subtle depth of field, premium lifestyle magazine photography. '
        'No text, no typography, no logos, no brand marks, no watermarks, no shopping bags, no distorted hands, no extra limbs, no collage, no illustration.'
    ),
    'how-to-style-a-lace-midi-skirt': (
        'Ultra-realistic editorial fashion photograph, horizontal 3:2 composition. '
        'A stylish adult woman outdoors on a calm city sidewalk wearing an ivory lace midi skirt with a relaxed neutral crewneck sweater and understated flats, showing an easy daytime outfit that balances delicate texture with casual basics. '
        'Full outfit visible, natural movement, soft daylight, elegant but approachable, premium fashion magazine photography, realistic fabric detail. '
        'No text, no typography, no logos, no brand marks, no watermarks, no bridal styling, no distorted anatomy, no collage, no illustration.'
    ),
    'slow-decorating-2026': (
        'Ultra-realistic editorial interiors photograph, horizontal 3:2 composition. '
        'A warm lived-in living room being thoughtfully decorated over time, with a neutral sofa, vintage wood side table, a few framed personal artworks leaning before hanging, layered natural textiles, one ceramic vase, and a person calmly arranging a meaningful object. '
        'Collected rather than showroom-perfect, warm afternoon light, authentic textures, restrained color palette, premium home magazine photography. '
        'No text, no typography, no logos, no brand marks, no watermarks, no clutter piles, no surreal furniture, no collage, no illustration.'
    ),
    'analog-hobbies-2026': (
        'Ultra-realistic editorial lifestyle photograph, horizontal 3:2 composition. '
        'A sunlit wooden table with an adult person enjoying hands-on analog hobbies: writing a letter with a fountain pen, a small embroidery hoop, sketchbook, and simple paper craft materials arranged naturally, with the person actively making rather than posing. '
        'Cozy offline afternoon, tactile materials, soft natural light, calm realistic home setting, premium lifestyle magazine photography. '
        'No readable text, no typography overlay, no logos, no brand marks, no watermarks, no phone or laptop as the focus, no distorted hands, no collage, no illustration.'
    ),
}


def get_api_key() -> str:
    env = os.environ.copy()
    env.setdefault('OP_DEFAULT_VAULT', 'MGS Conteúdo')
    proc = subprocess.run(
        ['op', 'item', 'get', 'Gemini API Key - MGS Core', '--vault', env['OP_DEFAULT_VAULT'], '--fields', 'api_key', '--reveal'],
        env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    key = proc.stdout.strip()
    if not key:
        raise RuntimeError('Gemini API key was empty')
    return key


def generate(key: str, slug: str, prompt: str) -> dict:
    endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?{urllib.parse.urlencode({"key": key})}'
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'responseModalities': ['TEXT', 'IMAGE'],
            'imageConfig': {'aspectRatio': '3:2'},
        },
    }
    data = json.dumps(payload).encode('utf-8')
    last_error = None
    for attempt in range(1, 4):
        req = urllib.request.Request(endpoint, data=data, method='POST', headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.load(resp)
            image_part = None
            for part in body.get('candidates', [{}])[0].get('content', {}).get('parts', []):
                image_part = part.get('inlineData') or part.get('inline_data')
                if image_part and image_part.get('data'):
                    break
            if not image_part or not image_part.get('data'):
                raise RuntimeError('Gemini response contained no image')
            raw = base64.b64decode(image_part['data'])
            path = OUT_DIR / f'{slug}.png'
            path.write_bytes(raw)
            return {'slug': slug, 'path': str(path), 'bytes': len(raw), 'attempt': attempt, 'mime_type': image_part.get('mimeType') or image_part.get('mime_type')}
        except urllib.error.HTTPError as exc:
            last_error = f'HTTP {exc.code}'
            if exc.code not in (429, 503) or attempt == 3:
                raise RuntimeError(f'Gemini image generation failed for {slug}: {last_error}') from exc
            time.sleep(5 * attempt)
        except Exception as exc:
            last_error = str(exc)
            if attempt == 3:
                raise
            time.sleep(3 * attempt)
    raise RuntimeError(last_error or 'unknown generation failure')


def main() -> None:
    key = get_api_key()
    results = []
    for slug, prompt in BRIEFS.items():
        results.append(generate(key, slug, prompt))
    print(json.dumps({'ok': True, 'model': MODEL, 'results': results}, ensure_ascii=False))


if __name__ == '__main__':
    main()
