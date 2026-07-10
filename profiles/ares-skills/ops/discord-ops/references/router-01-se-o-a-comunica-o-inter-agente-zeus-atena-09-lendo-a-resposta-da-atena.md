### Lendo a resposta da Atena

```bash
ls -t /root/.hermes/profiles/atena/sessions/session_*.json | head -1
python3 -c "
import json
with open('/root/.hermes/profiles/atena/sessions/session_XXXXXXXX.json') as f:
    s = json.load(f)
for m in s.get('messages', []):
    if m.get('role') == 'assistant':
        content = m.get('content','')
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'text':
                    print(c['text'])
        elif content:
            print(content)
"
```

