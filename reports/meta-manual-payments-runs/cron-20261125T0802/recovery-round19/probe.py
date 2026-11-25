"""Same-operation round19 diagnostic; no browser input or business mutation."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round17' / 'probe.py'
exec(compile(source.read_text(), str(source), 'exec'), globals())
status, context = m.discord_api(token, 'GET', '/channels/1563926766286803004/messages/1563960022252392459')
assert status == 200 and context['id'] == '1563960022252392459'
assert context['channel_id'] == '1563926766286803004' and context['author']['id'] == '1496296175014252634'
save('original-command-context.json', {'status': status, 'id': context['id'], 'channel_id': context['channel_id'], 'author_id': context['author']['id'], 'content': context['content']})
print('Original approved proposal context retrieved and identity verified.')
