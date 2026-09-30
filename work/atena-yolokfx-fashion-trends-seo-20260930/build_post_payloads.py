#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path('/root/mgs-agent/work/atena-yolokfx-fashion-trends-seo-20260930')
OUT = ROOT / 'payloads'
OUT.mkdir(parents=True, exist_ok=True)

specs = {
    'polka': {
        'draft': 'polka.json',
        'category': 'Fashion',
        'media_key': 'polka',
        'tags': ['us', 'lang_en', 'seo', 'atena_agent', 'fashion', 'fashion trends 2026', 'outfit ideas', 'polka dots'],
    },
    'lace': {
        'draft': 'lace.json',
        'category': 'Fashion',
        'media_key': 'lace',
        'tags': ['us', 'lang_en', 'seo', 'atena_agent', 'fashion', 'fashion trends 2026', 'outfit ideas', 'lace midi skirt'],
    },
    'slow-decorating': {
        'draft': 'slow-decorating.json',
        'category': 'Trends',
        'media_key': 'slow-decorating',
        'tags': ['us', 'lang_en', 'seo', 'atena_agent', 'trends', 'lifestyle', 'home decor', 'slow decorating'],
    },
    'analog-hobbies': {
        'draft': 'analog-hobbies.json',
        'category': 'Trends',
        'media_key': 'analog-hobbies',
        'tags': ['us', 'lang_en', 'seo', 'atena_agent', 'trends', 'lifestyle', 'analog hobbies', 'offline activities'],
    },
}
terms = json.loads((ROOT / 'terms-results.json').read_text(encoding='utf-8'))['terms']
term_ids = {(x['taxonomy'], x['name']): int(x['id']) for x in terms}
media_rows = json.loads((ROOT / 'media-upload-results.json').read_text(encoding='utf-8'))['media']
media_by_key = {x['key']: x for x in media_rows}
media_details = json.loads((ROOT / 'media-public-readback.json').read_text(encoding='utf-8'))
media_by_id = {int(x['id']): x for x in media_details}
manifest = []
for key, spec in specs.items():
    draft = json.loads((ROOT / 'drafts' / spec['draft']).read_text(encoding='utf-8'))
    media = media_by_key[spec['media_key']]
    details = media_by_id[int(media['id'])]
    large = details['large']
    image_block = (
        f'<!-- wp:image {{"id":{media["id"]},"sizeSlug":"large","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-large"><img src="{large["source_url"]}" alt="{draft["image_alt"]}" class="wp-image-{media["id"]}"/></figure>\n'
        '<!-- /wp:image -->'
    )
    content = draft['body_html'].replace('{{IMAGE_BLOCK}}', image_block)
    if '{{IMAGE_BLOCK}}' in content:
        raise RuntimeError(f'{key}: image placeholder remained')
    category_id = term_ids[('categories', spec['category'])]
    tag_ids = [term_ids[('tags', name)] for name in spec['tags']]
    meta = {
        '_yoast_wpseo_title': draft['seo_title'],
        '_yoast_wpseo_metadesc': draft['meta_description'],
        '_yoast_wpseo_focuskw': draft['focus_keyphrase'],
    }
    payload = {
        'title': draft['title'],
        'slug': draft['slug'],
        'content': content,
        'excerpt': '',
        'status': 'draft',
        'author': 11,
        'categories': [category_id],
        'tags': tag_ids,
        'featured_media': int(media['id']),
        'meta': meta,
    }
    yoast = {'title': draft['title'], 'content': content, 'meta': meta}
    (OUT / f'{key}-post.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / f'{key}-yoast.json').write_text(json.dumps(yoast, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest.append({
        'key': key,
        'draft_file': spec['draft'],
        'post_payload': str(OUT / f'{key}-post.json'),
        'yoast_payload': str(OUT / f'{key}-yoast.json'),
        'title': draft['title'],
        'slug': draft['slug'],
        'category': spec['category'],
        'category_id': category_id,
        'tag_names': spec['tags'],
        'tag_ids': tag_ids,
        'featured_media': int(media['id']),
        'featured_source_url': media['source_url'],
        'body_image_url': large['source_url'],
        'image_alt': draft['image_alt'],
        'focus_keyphrase': draft['focus_keyphrase'],
        'seo_title': draft['seo_title'],
        'meta_description': draft['meta_description'],
        'status': 'draft',
        'author': 11,
    })
(ROOT / 'post-build-manifest.json').write_text(json.dumps({'status':'built','site_key':'yolokfx','posts':manifest}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status':'built','posts':manifest}, ensure_ascii=False, indent=2))
