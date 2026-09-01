from faster_whisper import WhisperModel
from pathlib import Path
import json

video = Path('/root/mgs-agent/work/nicolas-video-20260831/analysis/20260901T021545Z/videos/2223b0dc663246cc.mp4')
out_dir = Path('/root/mgs-agent/work/nicolas-video-20260831/transcript')
out_dir.mkdir(parents=True, exist_ok=True)
model = WhisperModel('small', device='cpu', compute_type='int8')
segments, info = model.transcribe(
    str(video),
    language='pt',
    beam_size=5,
    vad_filter=True,
    word_timestamps=True,
    initial_prompt='Explicação do Nicolas sobre Smart Bidding, Meta Ads, páginas, campanhas Messenger, LEADS, data e atualização de métricas.',
)
rows = []
for seg in segments:
    rows.append({
        'start': round(seg.start, 3),
        'end': round(seg.end, 3),
        'text': seg.text.strip(),
        'words': [
            {'start': round(w.start, 3), 'end': round(w.end, 3), 'word': w.word, 'probability': round(w.probability, 4)}
            for w in (seg.words or [])
        ],
    })
result = {
    'language': info.language,
    'language_probability': info.language_probability,
    'duration': info.duration,
    'segments': rows,
}
(out_dir / 'transcript.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
(out_dir / 'transcript.txt').write_text('\n'.join(f"[{r['start']:06.1f}-{r['end']:06.1f}] {r['text']}" for r in rows) + '\n', encoding='utf-8')
print(json.dumps({'language': info.language, 'language_probability': info.language_probability, 'duration': info.duration, 'segments': len(rows), 'json': str(out_dir / 'transcript.json'), 'text': str(out_dir / 'transcript.txt')}, ensure_ascii=False, indent=2))
