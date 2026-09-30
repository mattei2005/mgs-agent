#!/usr/bin/env python3
import html
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path('/root/mgs-agent/work/atena-yolokfx-fashion-trends-seo-20260930')
DRAFT_DIR = ROOT / 'drafts'
ANALYSIS = Path('/root/.hermes/profiles/atena/cache/scratch/yolokfx-category-analysis.json')
EXPECTED = {
    'polka.json': {
        'category': 'fashion',
        'slug': 'how-to-style-polka-dots-2026',
        'internal_links': [
            'https://yolokfx.com/match-clothing-colors-without-overthinking/',
            'https://yolokfx.com/fashion-trends-2026-real-life/',
        ],
        'sources': ['https://blog.google/products-and-platforms/products/search/spring-2026-fashion-beauty-trends/'],
        'word_range': (1025, 1125),
    },
    'lace.json': {
        'category': 'fashion',
        'slug': 'how-to-style-a-lace-midi-skirt',
        'internal_links': [
            'https://yolokfx.com/make-simple-clothes-look-elegant/',
            'https://yolokfx.com/wedding-guest-dresses-elegant-easy/',
        ],
        'sources': ['https://blog.google/products-and-platforms/products/search/spring-2026-fashion-beauty-trends/'],
        'word_range': (1025, 1125),
    },
    'slow-decorating.json': {
        'category': 'trends',
        'slug': 'slow-decorating-2026',
        'internal_links': [
            'https://yolokfx.com/shop-smarter-without-buying-more-than-needed/',
            'https://yolokfx.com/everyday-products-routine-easier/',
        ],
        'sources': [
            'https://www.goodhousekeeping.com/home/decorating-ideas/a71550746/slow-decorating-trend',
            'https://www.goodhousekeeping.com/home/decorating-ideas/g69637005/interior-design-trends-2026/',
        ],
        'word_range': (975, 1075),
    },
    'analog-hobbies.json': {
        'category': 'trends',
        'slug': 'analog-hobbies-2026',
        'internal_links': [
            'https://yolokfx.com/digital-habits-daily-life-organized/',
            'https://yolokfx.com/how-ai-shows-up-everyday-life-2026/',
        ],
        'sources': ['https://business.pinterest.com/en-gb/pdf/pinterest-predicts/2026-trend-report/'],
        'word_range': (975, 1075),
    },
}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignore = 0
        self.text = []
        self.paragraphs = []
        self.headings = []
        self.links = []
        self.tags = Counter()
        self.current_p = None
        self.current_h = None
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self.tags[tag] += 1
        if tag in ('script', 'style', 'noscript'):
            self.ignore += 1
        if self.ignore:
            return
        if tag == 'p':
            self.current_p = []
        if re.fullmatch(r'h[1-6]', tag):
            self.current_h = [tag, []]
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ('script', 'style', 'noscript'):
            self.ignore = max(0, self.ignore - 1)
            return
        if self.ignore:
            return
        if tag == 'p' and self.current_p is not None:
            self.paragraphs.append(' '.join(' '.join(self.current_p).split()))
            self.current_p = None
        if self.current_h is not None and tag == self.current_h[0]:
            self.headings.append((tag, ' '.join(' '.join(self.current_h[1]).split())))
            self.current_h = None
    def handle_data(self, data):
        if self.ignore:
            return
        value = ' '.join(data.split())
        if not value:
            return
        self.text.append(value)
        if self.current_p is not None:
            self.current_p.append(value)
        if self.current_h is not None:
            self.current_h[1].append(value)

def words(text):
    return re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE)

def norm(text):
    return re.sub(r'[^a-z0-9]+', ' ', html.unescape(text).lower()).strip()

def main():
    errors = []
    reports = []
    docs = {}
    files = {p.name: p for p in DRAFT_DIR.glob('*.json')}
    if set(files) != set(EXPECTED):
        errors.append(f'draft set mismatch: {sorted(files)}')
    existing = json.loads(ANALYSIS.read_text(encoding='utf-8'))
    existing_titles = [r['title'] for cat in existing.values() for r in cat['posts']]
    all_new_paragraphs = []
    for name, spec in EXPECTED.items():
        path = files.get(name)
        if not path:
            continue
        try:
            doc = json.loads(path.read_text(encoding='utf-8'))
        except Exception as exc:
            errors.append(f'{name}: invalid JSON: {exc}')
            continue
        docs[name] = doc
        required = {'title','slug','focus_keyphrase','seo_title','meta_description','excerpt','body_html','image_prompt','image_alt','source_urls','internal_links'}
        missing = sorted(required - set(doc))
        if missing:
            errors.append(f'{name}: missing keys {missing}')
            continue
        body = doc['body_html']
        parser = Parser(); parser.feed(body.replace('{{IMAGE_BLOCK}}', ''))
        plain = ' '.join(parser.text)
        wc = len(words(plain))
        h2s = [text for tag, text in parser.headings if tag == 'h2']
        opening = parser.paragraphs[0] if parser.paragraphs else ''
        kp = norm(doc['focus_keyphrase'])
        slug_words = norm(doc['slug'].replace('-', ' '))
        title_scores = [(t, SequenceMatcher(None, norm(doc['title']), norm(t)).ratio()) for t in existing_titles]
        closest_title, closest_score = max(title_scores, key=lambda x: x[1])
        checks = {
            'word_count': wc,
            'word_range': list(spec['word_range']),
            'h2_count': len(h2s),
            'paragraph_count': len(parser.paragraphs),
            'seo_title_chars': len(doc['seo_title']),
            'meta_chars': len(doc['meta_description']),
            'excerpt_chars': len(doc['excerpt']),
            'image_placeholder_count': body.count('{{IMAGE_BLOCK}}'),
            'closest_existing_title': closest_title,
            'closest_title_ratio': round(closest_score, 3),
            'links': parser.links,
        }
        if not spec['word_range'][0] <= wc <= spec['word_range'][1]: errors.append(f'{name}: word count {wc}')
        if not 10 <= len(h2s) <= 13: errors.append(f'{name}: H2 count {len(h2s)}')
        if not 25 <= len(parser.paragraphs) <= 50: errors.append(f'{name}: paragraph count {len(parser.paragraphs)}')
        if body.count('{{IMAGE_BLOCK}}') != 1: errors.append(f'{name}: image placeholder count')
        placeholder_pos = body.find('{{IMAGE_BLOCK}}')
        first_close = body.find('<!-- /wp:paragraph -->')
        first_heading = body.find('<!-- wp:heading -->')
        if not (first_close >= 0 and first_close < placeholder_pos < first_heading): errors.append(f'{name}: image placement')
        if parser.tags['h1'] or parser.tags['ul'] or parser.tags['ol'] or parser.tags['table']:
            errors.append(f'{name}: disallowed tag h1/list/table')
        if not (norm(doc['focus_keyphrase']) in norm(doc['title'])): errors.append(f'{name}: keyphrase not in title')
        if kp not in norm(opening): errors.append(f'{name}: keyphrase not in opening')
        if not any(kp in norm(h) for h in h2s): errors.append(f'{name}: keyphrase not in H2')
        if kp not in norm(doc['seo_title']): errors.append(f'{name}: keyphrase not in SEO title')
        if kp not in norm(doc['meta_description']): errors.append(f'{name}: keyphrase not in meta')
        if kp not in slug_words: errors.append(f'{name}: keyphrase not in slug')
        if len(doc['seo_title']) > 60: errors.append(f'{name}: SEO title too long')
        if not 130 <= len(doc['meta_description']) <= 155: errors.append(f'{name}: meta length')
        if not 140 <= len(doc['excerpt']) <= 170: errors.append(f'{name}: excerpt length')
        if doc['slug'] != spec['slug']: errors.append(f'{name}: slug mismatch')
        if doc['internal_links'] != spec['internal_links']: errors.append(f'{name}: internal manifest mismatch')
        if doc['source_urls'] != spec['sources']: errors.append(f'{name}: source manifest mismatch')
        allowed = set(spec['internal_links'] + spec['sources'])
        if set(parser.links) != allowed: errors.append(f'{name}: href allowlist mismatch: {set(parser.links) ^ allowed}')
        for u in spec['internal_links']:
            if parser.links.count(u) != 1: errors.append(f'{name}: internal link count {u}')
        if closest_score >= 0.78: errors.append(f'{name}: title too similar to existing: {closest_title}')
        if re.search(r'lorem|as an ai|i hope this helps|let me know|let[’\']s dive|in conclusion|at the end of the day', body, re.I):
            errors.append(f'{name}: banned filler')
        if '—' in body: errors.append(f'{name}: em dash present')
        if re.search(r'<strong>|<em>', body, re.I): errors.append(f'{name}: emphasis tag present')
        if body.count('<!-- wp:paragraph -->') != body.count('<!-- /wp:paragraph -->'): errors.append(f'{name}: paragraph comments unbalanced')
        if body.count('<!-- wp:heading -->') != body.count('<!-- /wp:heading -->'): errors.append(f'{name}: heading comments unbalanced')
        all_new_paragraphs.extend((name, norm(p)) for p in parser.paragraphs if len(words(p)) >= 8)
        reports.append({'file': name, 'category': spec['category'], 'title': doc['title'], **checks})
    titles = [d['title'] for d in docs.values()]
    slugs = [d['slug'] for d in docs.values()]
    if len(set(titles)) != len(titles): errors.append('duplicate new titles')
    if len(set(slugs)) != len(slugs): errors.append('duplicate new slugs')
    para_seen = {}
    for name, p in all_new_paragraphs:
        if p in para_seen and para_seen[p] != name:
            errors.append(f'duplicate paragraph across {para_seen[p]} and {name}: {p[:80]}')
        para_seen[p] = name
    output = {'status': 'PASS' if not errors else 'FAIL', 'errors': errors, 'articles': reports}
    out_path = ROOT / 'qa-drafts.json'
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

if __name__ == '__main__':
    sys.exit(main())
