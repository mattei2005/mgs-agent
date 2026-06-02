import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from honcho import Honcho

WORKSPACE = os.getenv("HONCHO_WORKSPACE", "mgs-agents")
API_KEY = os.getenv("HONCHO_API_KEY")
if not API_KEY:
    print("BLOCKED: HONCHO_API_KEY missing")
    sys.exit(2)

BASE = Path(__file__).resolve().parent
ROOT = Path('/root/mgs-agent')
PROFILES = Path('/root/.hermes/profiles')

SECRET_PATTERNS = [
    r'hch-v3-[A-Za-z0-9]+',
    r'sk-[A-Za-z0-9_\-]+',
    r'github_pat_[A-Za-z0-9_]+',
    r'ghp_[A-Za-z0-9_]+',
    r'xox[baprs]-[A-Za-z0-9_\-]+',
    r'AKIA[A-Za-z0-9]{16}',
    r'(?i)(password|token|secret|api[_-]?key|authorization)[=:]\s*\S+',
]

def redact(s: str) -> str:
    s = re.sub(r'hch-v3-[A-Za-z0-9]+', '[REDACTED_HONCHO_KEY]', s)
    s = re.sub(r'(sk-|xox[baprs]-|ghp_|github_pat_|AKIA)[A-Za-z0-9_\-]{8,}', '[REDACTED_TOKEN]', s)
    s = re.sub(r'(?i)(password|token|secret|api[_-]?key|authorization)[=:]\s*\S+', '[REDACTED_CREDENTIAL_FIELD]', s)
    s = re.sub(r'(?i)[A-Z0-9_]*(PASSWORD|TOKEN|SECRET|API_KEY)[A-Z0-9_]*=\*+', '[REDACTED_CREDENTIAL_FIELD]', s)
    s = re.sub(r'https?://[^\s@]+:[^\s@]+@', 'https://[REDACTED_CREDS]@', s)
    s = re.sub(r'<@[0-9]{12,25}>', '<@USER_ID>', s)
    if len(s) > 600:
        s = s[:600] + '... [TRUNCATED]'
    return s

def safe_scan(text: str):
    hits=[]
    for pat in SECRET_PATTERNS:
        if re.search(pat, text, re.I):
            hits.append(pat)
    return hits

def read_lines(path: Path, tail=None):
    if not path.exists():
        return []
    lines = path.read_text(errors='replace').splitlines()
    return lines[-tail:] if tail else lines

def collect_auth():
    items=[]
    audit=ROOT/'logs/events-audit.jsonl'
    for raw in read_lines(audit):
        line=raw.strip()
        if not line: continue
        try:
            obj=json.loads(line)
        except Exception:
            if any(w in line.lower() for w in ['auth','authoriz','approval','approve','deny','pending']):
                items.append({'source':'events-audit','text':redact(line)})
            continue
        text=json.dumps(obj, ensure_ascii=False)
        if any(w in text.lower() for w in ['auth','authoriz','approval','approve','deny','pending','unauthorized']):
            keep={}
            for k,v in obj.items():
                if k.lower() in {'timestamp','ts','event','type','agent','status','action','decision','scope','reason','user_id','discord_id'}:
                    keep[k]=('[ID]' if 'id' in k.lower() else v)
                elif k.lower() in {'request','message','content','prompt'}:
                    keep[k+'_present']=True
            items.append({'source':'events-audit','data':keep or {'event_summary':'authorization-related event'}})
    auth_json=ROOT/'data/authorized-users.json'
    if auth_json.exists():
        try:
            obj=json.loads(auth_json.read_text())
            summary={}
            def summarize(x):
                if isinstance(x, dict):
                    return {'keys': list(x.keys())[:20], 'count': len(x)}
                if isinstance(x, list):
                    return {'count': len(x)}
                return type(x).__name__
            for k,v in obj.items(): summary[k]=summarize(v)
            items.append({'source':'authorized-users.json','data':summary})
        except Exception as e:
            items.append({'source':'authorized-users.json','data':{'read_error':type(e).__name__}})
    return items[-80:]

def collect_content():
    items=[]
    files=[ROOT/'logs/generate-rec.log', ROOT/'logs/publish-wordpress.log', PROFILES/'atena/logs/agent.log', PROFILES/'atena/logs/errors.log']
    categories={
        'image_quality_or_lookup': ['image', 'card image', 'featured', 'audit-featured-image', 'low_quality', 'crop width', 'gemini'],
        'wordpress_publish_or_rest': ['wordpress', 'wp-json', 'public get failed', 'rest', 'create-post', 'publish', 'draft'],
        'yoast_quality_gate': ['yoast', 'readability', 'seo='],
        'official_source_or_data': ['official url', 'official source', 'no usable product content', 'missing', 'card_cache', 'no such table', 'no such column'],
        'runner_failures': ['mgs-p1-runner', 'mgs-rec-runner', 'runner', 'ok\\": false', 'success\\": false'],
        'dependency_or_tooling': ['modulenotfounderror', 'no module named', 'bs4', 'pil', 'numpy'],
        'comparison_table_gate': ['comparative table', 'competitor cards', 'generic placeholders'],
        'provider_ttfb': ['codex stream produced no bytes', 'ttfb cutoff'],
    }
    counts={k:0 for k in categories}
    examples={k:[] for k in categories}
    for p in files:
        for line in read_lines(p, tail=900):
            low=line.lower()
            for cat, kws in categories.items():
                if any(k in low for k in kws):
                    counts[cat]+=1
                    if len(examples[cat]) < 4:
                        examples[cat].append(redact(line.strip()))
    for cat,count in counts.items():
        if count:
            items.append({'source':'content-aggregate', 'data':{'category':cat,'count_in_tail':count,'examples':examples[cat]}})
    raw=[]
    keywords=['rec','p1','publish','wordpress','wp-json','yoast','image','gemini','card','runner','draft','post','slug','readability','seo']
    for p in files:
        for line in read_lines(p, tail=250):
            low=line.lower()
            if any(k in low for k in keywords):
                raw.append({'source':str(p).replace('/root/','~/'), 'text':redact(line.strip())})
    items.extend(raw[-35:])
    return items

def collect_gateway():
    items=[]
    categories={
        'gateway_lifecycle': ['gateway running', 'connected as', 'shutdown', 'restart', 'exiting with code', 'sigterm'],
        'discord_rate_or_http': ['rate limited', 'discord.http', '429', 'interaction failed'],
        'provider_ttfb_or_retry': ['codex stream produced no bytes', 'ttfb cutoff', 'retrying request', 'internalservererror', '503'],
        'tool_errors': ['tool ', 'returned error', 'tool_executor'],
        'credential_safety_blocks': ['discord_bot_token', 'env passthrough', 'credential', 'blocklist'],
        'session_context': ['session expiry', 'history=0', 'stored system prompt', 'prefix cache'],
        'lsp_diagnostics': ['lsp[', 'pyright', 'diagnostics timed out'],
    }
    for agent in ['zeus','atena','ares']:
        counts={k:0 for k in categories}
        examples={k:[] for k in categories}
        for logname in ['errors.log','agent.log']:
            p=PROFILES/agent/'logs'/logname
            for line in read_lines(p, tail=700):
                low=line.lower()
                for cat,kws in categories.items():
                    if any(k in low for k in kws):
                        counts[cat]+=1
                        if len(examples[cat]) < 3:
                            examples[cat].append(redact(line.strip()))
        items.append({'agent':agent,'source':f'{agent}/aggregate','data':{'counts_in_tail':counts,'examples':examples}})
        raw=[]
        for logname in ['errors.log','agent.log']:
            p=PROFILES/agent/'logs'/logname
            for line in read_lines(p, tail=180):
                low=line.lower()
                if any(k in low for k in ['error','warning','exception','traceback','gateway','discord','rate limited','retry','timeout','shutdown','restart','connected as','response ready']):
                    raw.append({'agent':agent,'source':f'{agent}/{logname}','text':redact(line.strip())})
        items.extend(raw[-20:])
    return items

ROUND_CONFIG = {
    'auth': {
        'collector': collect_auth,
        'session': 'mgs-sanitized-auth-spike-001',
        'target': 'zeus',
        'queries': [
            'From these sanitized authorization events, what access-control risks or pending decisions should Zeus investigate? Mark uncertainty.',
            'Is there evidence of an authorization incident, or only operational state to validate in authorized-users.json?',
        ],
    },
    'content': {
        'collector': collect_content,
        'session': 'mgs-sanitized-content-spike-001',
        'target': 'atena',
        'limit': 80,
        'queries': [
            'From these sanitized REC/P1/content events, what recurring production bottlenecks should Zeus investigate? Mark uncertainty.',
            'What should Zeus validate in canonical logs before telling Rodolfo there is a content pipeline incident?',
        ],
    },
    'gateway': {
        'collector': collect_gateway,
        'session': 'mgs-sanitized-gateway-spike-001',
        'target': 'mgs-system',
        'limit': 90,
        'queries': [
            'From these sanitized Hermes/gateway events by agent, what reliability patterns should Zeus investigate? Mark uncertainty.',
            'Which agent appears riskiest operationally based only on these sanitized events, and what canonical validation is required?',
        ],
    },
}

honcho = Honcho(workspace_id=WORKSPACE, api_key=API_KEY, environment='production')
peers = {name: honcho.peer(name) for name in ['zeus','atena','ares','mgs-system']}

report={
    'created_at': datetime.now(timezone.utc).isoformat(),
    'workspace': WORKSPACE,
    'rounds': {},
}

for name,cfg in ROUND_CONFIG.items():
    items=cfg['collector']()
    limit = cfg.get('limit', 80)
    items = items[-limit:]
    payload=json.dumps({'policy':'sanitized; no secrets; Honcho conclusions are hypotheses only','round':name,'items':items}, ensure_ascii=False, indent=2)
    hits=safe_scan(payload)
    dataset_path=BASE/f'sanitized_{name}_events.json'
    dataset_path.write_text(payload)
    if hits:
        report['rounds'][name]={'status':'blocked_secret_scan','hits':hits,'items':len(items)}
        continue
    session=honcho.session(cfg['session'])
    msgs=[peers['mgs-system'].message(f'Round {name}: sanitized MGS operational data only. Honcho must produce hypotheses; Zeus validates against canonical sources before reporting or acting.')]
    for i,item in enumerate(items,1):
        text = item.get('text') or json.dumps(item.get('data', item), ensure_ascii=False)
        source = item.get('source','unknown')
        agent = item.get('agent')
        content=f'[{name} event {i}] source={source}: {text}'
        if agent in peers:
            peer=peers[agent]
        elif 'atena' in content.lower():
            peer=peers['atena']
        elif 'ares' in content.lower():
            peer=peers['ares']
        elif 'zeus' in content.lower() or name == 'auth':
            peer=peers['zeus']
        else:
            peer=peers['mgs-system']
        msgs.append(peer.message(content))
    session.add_messages(msgs)
    responses=[]
    target=peers[cfg['target']]
    for q in cfg['queries']:
        try:
            resp=peers['zeus'].chat(q, target=target, session=session.id)
        except TypeError:
            try:
                resp=peers['zeus'].chat(q, session=session.id)
            except TypeError:
                resp=peers['zeus'].chat(q)
        responses.append({'query':q,'response':str(getattr(resp,'content',resp))})
    report['rounds'][name]={
        'status':'ok',
        'dataset':str(dataset_path),
        'items':len(items),
        'messages_ingested':len(msgs),
        'session':cfg['session'],
        'responses':responses,
    }

out=BASE/'targeted_rounds_report.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
