#!/usr/bin/env python3
"""Temporary 3h Utility canary approval loop.

Rules from Rodolfo 2026-07-07:
- green: register/lock, keep
- gray: retry approval 3 times only if the current message never went green
- gray after ever-green: keep forever
- red: replace that slot immediately
- purple: diagnostic only
- every observation updates the durable message bank before decisions
"""
import asyncio, datetime as dt, hashlib, importlib.util, json, os, pathlib, re, tempfile
from collections import Counter
from zoneinfo import ZoneInfo

BASE = pathlib.Path('/root/mgs-agent')
BANK_PATH = BASE / 'data/utility-message-bank.json'
STATE_PATH = BASE / 'data/utility-canary-approval-state.json'
LOCK_PATH = pathlib.Path('/tmp/utility-canary-approval-loop.lock')
TZ = ZoneInfo('America/New_York')
MAX_GRAY_ATTEMPTS = 3

spec = importlib.util.spec_from_file_location('rollout', BASE / 'scripts/sb-utility-rollout-manager.py')
assert spec and spec.loader
rollout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollout)

TARGETS = [
 'Teste-CA-CC-EN-Financeadx-Varya Stonebridge-1102378912948290-22028',
 'Teste-DE-CC-DE-Newsoun-Ramona Dreher-1029582290242361-19329',
 'Teste-GB-CC-EN-Zytiva-Sabrina Ellsworth-1179604071896296-22064',
 'Teste-ES-CC-ES-Openzed-Elena Santana-990898360783030-22091',
 'Teste-MX-CC-ES-Financeadx-Carolina Cruz-1025593570646416-19333',
 'Teste-US-CAR-EN-Fincgriffin-Trust Car Offers-1033507496517692-22079',
 'Teste-US-CC-EN-Newsoun-Iona Brookfield-952051961334613-19225',
 'Teste-US-CC-ES-Newsoun-Carla Ramírez-873273395865880-13992',
 'Teste-US-JOB-ES-Spe-Maria Tisocco-177067078834007-8283',
 'Teste-ZA-CC-EN-Financeadx-Margaret Smith-699254556615476-5459',
 'Teste-AR-CC-ES-Financeadx-Teresa Camacho-1063903433472026-19337',
]

CTA = {
 'EN_CC': ['🔍 REVIEW CARD','✅ CHECK STATUS','📋 SEE OPTIONS','➡️ CONTINUE','💳 REVIEW UPDATE','🔎 OPEN REVIEW','✅ CONFIRM DETAILS','📌 VIEW RESULT'],
 'ES_CC': ['🔍 REVISAR TARJETA','✅ VER ESTADO','📋 VER OPCIONES','➡️ CONTINUAR','💳 VER ACTUALIZACIÓN','🔎 ABRIR REVISIÓN','✅ CONFIRMAR DATOS','📌 VER RESULTADO'],
 'DE_CC': ['🔍 KARTE PRÜFEN','✅ STATUS ANSEHEN','📋 OPTIONEN SEHEN','➡️ WEITER','💳 UPDATE ANSEHEN','🔎 PRÜFUNG ÖFFNEN','✅ DATEN BESTÄTIGEN','📌 ERGEBNIS SEHEN'],
 'JOB_ES': ['🔍 VER OFERTA','✅ VER ESTADO','📋 VER OPCIONES','➡️ CONTINUAR','📌 ABRIR ACTUALIZACIÓN','🔎 REVISAR VACANTE','✅ CONFIRMAR DATOS','📄 VER DETALLES'],
 'CAR_EN': ['🚗 REVIEW OFFER','✅ CHECK STATUS','📋 SEE OPTIONS','➡️ CONTINUE','🔎 OPEN REVIEW','📌 VIEW DETAILS','✅ CONFIRM DETAILS','🚘 SEE RESULT'],
}

def now(): return dt.datetime.now(TZ).isoformat(timespec='seconds')
def today_stamp(): return dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name+'.', dir=str(path.parent))
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, path)

def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return default

def visible(s):
    return re.sub('[\u200b\u200c\u200d\ufeff\u2060]', '', s or '')

def norm_text(s):
    return re.sub(r'\s+', ' ', visible(s).strip().lower())

def text_cta_hash(text, cta):
    return hashlib.sha256(json.dumps([norm_text(text), norm_text(cta)], ensure_ascii=False).encode()).hexdigest()

def msg_hash(m):
    return text_cta_hash(m.get('TEXT') or '', m.get('CTA_1') or m.get('CTA 1') or '')

def parse_vertical(name):
    m = re.search(r'\b([A-Z]{2})[-_ ]([A-Z0-9]{2,8})[-_ ]([A-Z]{2})\b', name.upper())
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ''

def country_lang(vertical):
    parts = vertical.split('-')
    return (parts[0] if len(parts)>0 else '', parts[-1] if len(parts)>1 else '')

def zw_text(s):
    parts = re.split(r'(\s+)', s)
    out=[]; words=0
    for part in parts:
        out.append(part)
        if part.strip() and not part.isspace():
            words += 1
            if words % 2 == 0:
                out.append('\u200b')
    return ''.join(out)

def no_dash(s): return s.replace('-', ' ').replace('–',' ').replace('—',' ')

def generated_copy(vertical, idx):
    if 'JOB' in vertical:
        heads=['📋 ACTUALIZACIÓN DE VACANTE','✅ REVISIÓN DISPONIBLE','🔎 OPCIONES DE TRABAJO','📌 PASO DE SOLICITUD','💬 ESTADO DE POSTULACIÓN','📄 DETALLES ABIERTOS','🔔 PERFIL LABORAL','➡️ CONTINUAR REVISIÓN']
        bodies=['Hay una actualización disponible para tu solicitud de empleo. Abre la revisión para ver el próximo paso.','Tu perfil laboral tiene una opción lista para revisar. Confirma los datos y continúa desde la página.','Una vacante relacionada con tu perfil está lista para revisión. Abre los detalles para continuar.','El estado de tu postulación necesita una revisión rápida. Consulta la información actualizada.']
        return zw_text(no_dash(f"{heads[idx%len(heads)]}\n\n{bodies[(idx//len(heads)+idx)%len(bodies)]}")), CTA['JOB_ES'][idx%len(CTA['JOB_ES'])]
    if 'CAR' in vertical:
        heads=['🚗 VEHICLE OFFER UPDATE','📋 AUTO REQUEST STATUS','🔎 CAR OPTIONS READY','✅ REVIEW AVAILABLE','📌 CONFIRMATION STEP','🚘 VEHICLE MATCH UPDATE','📄 DETAILS READY','🔔 AUTO PROFILE UPDATE']
        bodies=['Your vehicle request has a new review step available. Open the update to continue with the options.','An auto offer status check is ready for review. Confirm the details on the next page.','Your profile has vehicle options available to review. Open the update and check the next step.','The car offer flow has a result ready. Review the details before continuing.']
        return no_dash(f"{heads[idx%len(heads)]}\n\n{bodies[(idx//len(heads)+idx)%len(bodies)]}"), CTA['CAR_EN'][idx%len(CTA['CAR_EN'])]
    if vertical.endswith('-DE'):
        heads=['💳 KARTEN UPDATE','📋 ANFRAGE STATUS','🔎 KARTEN OPTIONEN','✅ PRÜFUNG VERFÜGBAR','📌 BESTÄTIGUNG BEREIT','💬 KARTEN ERGEBNIS','📄 PRÜFUNG OFFEN','🔔 PROFIL UPDATE']
        bodies=['Für deine Kartenanfrage ist ein neuer Prüfschritt verfügbar. Öffne das Update und sieh dir die Optionen an.','Der Status deiner Karte ist zur Prüfung bereit. Bestätige die Angaben auf der nächsten Seite.','Für dein Profil stehen Kartenoptionen zur Prüfung bereit. Öffne die Übersicht für den nächsten Schritt.','Der Kartenempfehlungsprozess hat ein Ergebnis bereit. Prüfe die Details bevor du fortfährst.']
        return no_dash(f"{heads[idx%len(heads)]}\n\n{bodies[(idx//len(heads)+idx)%len(bodies)]}"), CTA['DE_CC'][idx%len(CTA['DE_CC'])]
    if vertical.endswith('-ES'):
        heads=['💳 ACTUALIZACIÓN DE TARJETA','📋 ESTADO DE SOLICITUD','🔎 OPCIONES DE TARJETA','✅ REVISIÓN DISPONIBLE','📌 PASO DE CONFIRMACIÓN','💬 RESULTADO DE TARJETA','📄 REVISIÓN ABIERTA','🔔 PERFIL ACTUALIZADO']
        bodies=['Tu solicitud de tarjeta tiene una nueva revisión disponible. Abre la actualización para continuar con las opciones.','El estado de tu tarjeta está listo para revisar. Confirma los datos en la siguiente pantalla y continúa.','Tu perfil tiene opciones de tarjeta disponibles. Abre la revisión para ver el próximo paso.','El flujo de recomendación de tarjeta tiene un resultado listo. Revisa los detalles antes de continuar.']
        return zw_text(no_dash(f"{heads[idx%len(heads)]}\n\n{bodies[(idx//len(heads)+idx)%len(bodies)]}")), CTA['ES_CC'][idx%len(CTA['ES_CC'])]
    heads=['💳 CARD REVIEW UPDATE','📋 CARD REQUEST STATUS','🔎 CARD OPTIONS READY','✅ CARD REVIEW AVAILABLE','📌 APPLICATION STEP READY','💬 CARD MATCH UPDATE','📄 REVIEW STEP OPEN','🔔 CARD PROFILE UPDATE']
    bodies=['Your card request has a new review step available. Open the update to continue with the available options.','A card status check is ready for review. Use the next screen to confirm the details and continue.','Your credit profile has card options available to review. Open the update and check the next step.','The card recommendation flow has a new result ready. Review the details before continuing.']
    return no_dash(f"{heads[idx%len(heads)]}\n\n{bodies[(idx//len(heads)+idx)%len(bodies)]}"), CTA['EN_CC'][idx%len(CTA['EN_CC'])]

def upsert_bank(bank, template, msg, color, status, vertical):
    country, lang = country_lang(vertical)
    h = msg_hash(msg)
    records = bank.setdefault('records', {})
    rec = records.setdefault(h, {
        'text_cta_hash': h, 'vertical': vertical, 'country': country, 'language': lang,
        'text': msg.get('TEXT') or '', 'cta_1': msg.get('CTA_1') or msg.get('CTA 1') or '',
        'first_seen_at': now(), 'last_seen_at': None,
        'first_approved_at': None, 'last_approved_at': None,
        'approved_count': 0, 'rejected_count': 0, 'gray_count': 0, 'purple_count': 0,
        'status': 'testing', 'seen_in': [], 'usage': []
    })
    rec['last_seen_at'] = now()
    if color == 'verde':
        if not rec.get('first_approved_at'): rec['first_approved_at'] = now()
        rec['last_approved_at'] = now(); rec['approved_count'] = int(rec.get('approved_count') or 0) + 1; rec['status'] = 'approved'
    elif color == 'vermelho':
        rec['rejected_count'] = int(rec.get('rejected_count') or 0) + 1
        rec['status'] = 'mixed_history' if rec.get('approved_count') else 'rejected'
    elif color == 'cinza':
        rec['gray_count'] = int(rec.get('gray_count') or 0) + 1
    elif color == 'roxo':
        rec['purple_count'] = int(rec.get('purple_count') or 0) + 1; rec['status'] = 'diagnostic'
    rec.setdefault('seen_in', []).append({'template': template, 'message_id': msg.get('MESSAGE_ID'), 'observed_color': color, 'observed_status': status or 'GRAY', 'observed_at': now()})
    if len(rec['seen_in']) > 50: rec['seen_in'] = rec['seen_in'][-50:]
    return h, rec

def approved_candidate(bank, vertical, used_hashes, used_visible_texts=None):
    used_visible_texts = used_visible_texts or set()
    for h, rec in bank.get('records', {}).items():
        if h in used_hashes:
            continue
        if norm_text(rec.get('text') or '') in used_visible_texts:
            continue
        if rec.get('vertical') == vertical and rec.get('status') == 'approved' and rec.get('text') and rec.get('cta_1'):
            return rec
    return None

async def approve(ctx, headers, template_id):
    attempts=[]
    for url in [f'https://api.jbfdigital.com.br/broadcast/messenger/{template_id}/approve', f'https://api.jbfdigital.com.br/broadcast/Messenger/{template_id}/approve']:
        r = await ctx.request.post(url, headers=headers)
        txt = '' if r.status < 300 else (await r.text())[:250]
        attempts.append({'status': r.status, 'error': txt})
        if r.status < 300: return True, attempts
    return False, attempts

async def main():
    if LOCK_PATH.exists():
        print('Utility canary loop: execução anterior ainda em andamento; skip seguro.')
        return
    LOCK_PATH.write_text(str(os.getpid()))
    bank = load_json(BANK_PATH, {'version':1,'created_at_et':now(),'updated_at_et':now(),'records':{}})
    state = load_json(STATE_PATH, {'version':1,'created_at_et':now(),'updated_at_et':now(),'runs':[],'slots':{}})
    stamp = today_stamp()
    backup_dir = BASE / 'backups/sb-templates' / f'utility-canary-loop-{stamp}'
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        p,browser,ctx,page,rows,headers,post_url = await rollout.capture_rows_headers()
        summary=[]; total_replaced=0; approvals=0; all_green=True; errors=[]
        try:
            by = {r.get('NAME'): r for r in rows}
            for name in TARGETS:
                row = by.get(name)
                if not row:
                    errors.append(f'{name}: not_found'); all_green=False; continue
                vertical = parse_vertical(name)
                msgs = sorted(rollout.parse_messages(row), key=lambda m:int(m.get('MESSAGE_ID') or 0))
                counts_before = Counter(rollout.status_color(rollout.status_of(m)) for m in msgs)
                new_msgs=[]; replaced=[]; used={msg_hash(m) for m in msgs}; approval_needed=False
                for m in msgs:
                    mid = int(m.get('MESSAGE_ID') or 0)
                    status = rollout.status_of(m)
                    color = rollout.status_color(status)
                    h, rec = upsert_bank(bank, name, m, color, status, vertical)
                    skey = f'{name}::{mid}'
                    slot = state.setdefault('slots', {}).setdefault(skey, {'template': name, 'message_id': mid, 'text_cta_hash': h, 'ever_green': False, 'gray_attempt_count': 0, 'last_color': '', 'replacements_done': 0, 'approval_runs': []})
                    if slot.get('text_cta_hash') != h:
                        slot.update({'text_cta_hash': h, 'ever_green': False, 'gray_attempt_count': 0})
                    if color == 'verde':
                        slot['ever_green'] = True; slot['gray_attempt_count'] = 0
                    elif color == 'cinza':
                        if slot.get('ever_green') or rec.get('approved_count'):
                            approval_needed = True
                        else:
                            slot['gray_attempt_count'] = int(slot.get('gray_attempt_count') or 0) + 1
                            approval_needed = True
                    elif color == 'vermelho':
                        approval_needed = True
                    elif color == 'roxo':
                        approval_needed = False
                    slot['last_color'] = color
                    m2 = dict(m)
                    should_replace = False
                    if color == 'vermelho': should_replace = True
                    if color == 'cinza' and not slot.get('ever_green') and not rec.get('approved_count') and int(slot.get('gray_attempt_count') or 0) >= MAX_GRAY_ATTEMPTS:
                        should_replace = True
                    if should_replace:
                        cand = approved_candidate(bank, vertical, used)
                        if cand:
                            text, cta = cand['text'], cand['cta_1']
                        else:
                            text, cta = generated_copy(vertical, int(slot.get('replacements_done') or 0) + mid + len(used))
                        m2['TEXT'] = text; m2['CTA_1'] = cta; m2.pop('CTA 1', None)
                        for k in ['APPROVED','INVALID_FORMAT','REJECTED','ERROR','REJECTED_REASON']:
                            m2.pop(k, None)
                        new_hash = msg_hash(m2); used.add(new_hash)
                        slot.update({'text_cta_hash': new_hash, 'ever_green': False, 'gray_attempt_count': 0, 'replacements_done': int(slot.get('replacements_done') or 0) + 1, 'last_color': 'replaced'})
                        # Record installation usage immediately.
                        rec2 = bank.setdefault('records', {}).setdefault(new_hash, {'text_cta_hash':new_hash,'vertical':vertical,'country':country_lang(vertical)[0],'language':country_lang(vertical)[1],'text':text,'cta_1':cta,'first_seen_at':now(),'last_seen_at':now(),'first_approved_at':None,'last_approved_at':None,'approved_count':0,'rejected_count':0,'gray_count':0,'purple_count':0,'status':'testing','seen_in':[],'usage':[]})
                        rec2.setdefault('usage', []).append({'template':name,'message_id':mid,'installed_at':now(),'mode':'canary_loop_replacement'})
                        replaced.append(mid); approval_needed = True
                    new_msgs.append(m2)
                visible_text_keys = [norm_text(m.get('TEXT') or '') for m in new_msgs]
                if len(visible_text_keys) != len(set(visible_text_keys)):
                    errors.append(f'{name}: duplicate_text_guard_blocked_post')
                    summary.append({'template':name,'before':dict(counts_before),'replaced':0,'approval_run':False,'blocked':'duplicate_text_guard'})
                    all_green = False
                    continue
                if replaced:
                    rollout.save_json(backup_dir/(rollout.safe_name(name)+'-before.json'), row)
                    payload=dict(row); payload['MESSAGES']=json.dumps(new_msgs,ensure_ascii=False,separators=(',',':'))
                    resp = await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
                    if resp.status >= 300:
                        errors.append(f'{name}: post_failed_{resp.status}'); continue
                    total_replaced += len(replaced)
                counts_effective = Counter()
                for m in new_msgs:
                    counts_effective[rollout.status_color(rollout.status_of(m))] += 1
                if counts_effective.get('verde',0) < 20:
                    all_green = False
                if approval_needed or replaced:
                    ok, attempts = await approve(ctx, headers, row.get('ID') or row.get('id'))
                    approvals += 1 if ok else 0
                    for mid in range(1,21):
                        skey=f'{name}::{mid}'
                        if skey in state.get('slots',{}): state['slots'][skey].setdefault('approval_runs', []).append(now())
                summary.append({'template':name,'before':dict(counts_before),'replaced':len(replaced),'approval_run':bool(approval_needed or replaced)})
        finally:
            try: await browser.close()
            except Exception: pass
            try: await p.stop()
            except Exception: pass
        bank['updated_at_et'] = now(); state['updated_at_et'] = now()
        state.setdefault('runs', []).append({'at':now(),'summary':summary,'replaced':total_replaced,'approvals':approvals,'all_green':all_green,'errors':errors})
        state['runs'] = state['runs'][-100:]
        atomic_write(BANK_PATH, bank); atomic_write(STATE_PATH, state)
        green_counts = sum(1 for s in summary if s.get('before',{}).get('verde',0) == 20)
        if all_green:
            print(f'Utility canary loop: TODOS VERDES 11/11. approvals={approvals} trocas={total_replaced}')
        else:
            print(f'Utility canary loop: ciclo OK | templates 20/20 verdes agora={green_counts}/11 | approvals={approvals} | trocas={total_replaced} | erros={len(errors)}')
            for s in summary:
                b=s['before']
                print(f"- {parse_vertical(s['template'])}: verde={b.get('verde',0)} cinza={b.get('cinza',0)} vermelho={b.get('vermelho',0)} roxo={b.get('roxo',0)} troca={s['replaced']} approval={s['approval_run']}")
            if errors: print('Erros: ' + '; '.join(errors[:5]))
    finally:
        try: LOCK_PATH.unlink()
        except FileNotFoundError: pass

if __name__ == '__main__':
    asyncio.run(main())
