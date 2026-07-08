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

def copy_family(vertical):
    if 'JOB' in vertical:
        return 'JOB_ES'
    if 'CAR' in vertical:
        return 'CAR_EN'
    if vertical.endswith('-DE'):
        return 'DE_CC'
    if vertical.endswith('-ES'):
        return 'ES_CC'
    return 'EN_CC'

COPY_VARIATIONS = {
 'EN_CC': {
  'cta': ['🔍 REVIEW CARD','✅ CHECK STATUS','📋 SEE OPTIONS','➡️ CONTINUE','💳 REVIEW UPDATE','🔎 OPEN REVIEW','✅ CONFIRM DETAILS','📌 VIEW RESULT','💳 SEE CARD OPTIONS','🔔 OPEN STATUS','📄 REVIEW PROFILE','🔍 CHECK MATCH'],
  'heads': ['💳 CARD REVIEW UPDATE','📋 CARD REQUEST STATUS','🔎 CARD OPTIONS READY','✅ CARD REVIEW AVAILABLE','📌 APPLICATION STEP READY','💬 CARD MATCH UPDATE','📄 REVIEW STEP OPEN','🔔 CARD PROFILE UPDATE','💳 CARD OPTION NOTICE','📋 CARD STATUS READY','🔎 PROFILE MATCH READY','✅ CARD CHECK OPEN','📌 REQUEST REVIEW READY','💬 CARD DETAILS AVAILABLE','📄 OPTION CHECK READY','🔔 PROFILE REVIEW UPDATE','💳 CARD SELECTION STEP','📋 STATUS CONFIRMATION','🔎 CARD RESULT NOTICE','✅ REVIEW CONTINUATION'],
  'bodies': ['Your card request has a review step ready. Open the page to continue with the available options.','A status check is available for your card profile. Review the details before moving forward.','Your card options are ready to compare. Open the update and confirm the next step.','The card recommendation flow has new details available. Check the page to continue.','Your profile review is ready for confirmation. Open the card update to see the result.','A card selection step is available now. Review the page and continue from there.','Your card request moved to the next review point. Open the status page for details.','The card option summary is ready. Confirm the information on the review page.','A new card profile update is available. Check the options and continue safely.','Your card match has an available result. Open the update to review the details.','The request review page is ready. Continue there to confirm your card information.','A card status update is waiting. Open the page and check the available path.']
 },
 'ES_CC': {
  'cta': ['🔍 REVISAR TARJETA','✅ VER ESTADO','📋 VER OPCIONES','➡️ CONTINUAR','💳 VER ACTUALIZACIÓN','🔎 ABRIR REVISIÓN','✅ CONFIRMAR DATOS','📌 VER RESULTADO','💳 VER OPCIONES','🔔 ABRIR ESTADO','📄 REVISAR PERFIL','🔍 VER COMPATIBILIDAD'],
  'heads': ['💳 ACTUALIZACIÓN DE TARJETA','📋 ESTADO DE SOLICITUD','🔎 OPCIONES DE TARJETA','✅ REVISIÓN DISPONIBLE','📌 PASO DE CONFIRMACIÓN','💬 RESULTADO DE TARJETA','📄 REVISIÓN ABIERTA','🔔 PERFIL ACTUALIZADO','💳 AVISO DE TARJETA','📋 ESTADO LISTO','🔎 PERFIL COMPATIBLE','✅ CONSULTA ABIERTA','📌 SOLICITUD EN REVISIÓN','💬 DETALLES DISPONIBLES','📄 OPCIONES ABIERTAS','🔔 REVISIÓN DE PERFIL','💳 SELECCIÓN DE TARJETA','📋 CONFIRMACIÓN DE ESTADO','🔎 RESULTADO DISPONIBLE','✅ CONTINUACIÓN DE REVISIÓN'],
  'bodies': ['Tu solicitud de tarjeta tiene una revisión lista. Abre la página para continuar con las opciones disponibles.','Hay una verificación disponible para tu perfil de tarjeta. Revisa los detalles antes de avanzar.','Tus opciones de tarjeta están listas para comparar. Abre la actualización y confirma el siguiente paso.','El flujo de recomendación de tarjeta tiene nuevos detalles disponibles. Consulta la página para continuar.','La revisión de tu perfil está lista para confirmación. Abre la actualización de tarjeta para ver el resultado.','Hay un paso de selección de tarjeta disponible ahora. Revisa la página y continúa desde ahí.','Tu solicitud de tarjeta pasó al siguiente punto de revisión. Abre la página de estado para ver detalles.','El resumen de opciones de tarjeta está listo. Confirma la información en la página de revisión.','Hay una nueva actualización de perfil de tarjeta disponible. Revisa las opciones y continúa.','Tu compatibilidad de tarjeta tiene un resultado disponible. Abre la actualización para revisar los detalles.','La página de revisión de solicitud está lista. Continúa allí para confirmar la información de tarjeta.','Hay una actualización de estado de tarjeta esperando. Abre la página y revisa el camino disponible.']
 },
 'DE_CC': {
  'cta': ['🔍 KARTE PRÜFEN','✅ STATUS ANSEHEN','📋 OPTIONEN SEHEN','➡️ WEITER','💳 UPDATE ANSEHEN','🔎 PRÜFUNG ÖFFNEN','✅ DATEN BESTÄTIGEN','📌 ERGEBNIS SEHEN','💳 OPTIONEN ÖFFNEN','🔔 STATUS ÖFFNEN','📄 PROFIL PRÜFEN','🔍 TREFFER ANSEHEN'],
  'heads': ['💳 KARTEN UPDATE','📋 ANFRAGE STATUS','🔎 KARTEN OPTIONEN','✅ PRÜFUNG VERFÜGBAR','📌 BESTÄTIGUNG BEREIT','💬 KARTEN ERGEBNIS','📄 PRÜFUNG OFFEN','🔔 PROFIL UPDATE','💳 KARTEN HINWEIS','📋 STATUS BEREIT','🔎 PROFIL TREFFER','✅ PRÜFUNG STARTEN','📌 ANFRAGE PRÜFUNG','💬 DETAILS VERFÜGBAR','📄 OPTIONEN OFFEN','🔔 PROFIL PRÜFUNG','💳 KARTENAUSWAHL','📋 STATUS BESTÄTIGUNG','🔎 ERGEBNIS BEREIT','✅ PRÜFUNG FORTSETZEN'],
  'bodies': ['Deine Kartenanfrage hat einen Prüfschritt bereit. Öffne die Seite und sieh dir die verfügbaren Optionen an.','Für dein Kartenprofil ist eine Statusprüfung verfügbar. Prüfe die Details bevor du fortfährst.','Deine Kartenoptionen sind zum Vergleich bereit. Öffne das Update und bestätige den nächsten Schritt.','Der Kartenempfehlungsprozess hat neue Details verfügbar. Öffne die Seite um weiterzumachen.','Deine Profilprüfung ist zur Bestätigung bereit. Öffne das Karten Update und sieh dir das Ergebnis an.','Ein Schritt zur Kartenauswahl ist jetzt verfügbar. Prüfe die Seite und fahre dort fort.','Deine Kartenanfrage ist beim nächsten Prüfpunkt angekommen. Öffne die Statusseite für Details.','Die Zusammenfassung der Kartenoptionen ist bereit. Bestätige die Angaben auf der Prüfseite.','Ein neues Update für dein Kartenprofil ist verfügbar. Prüfe die Optionen und fahre fort.','Dein Karten Treffer hat ein verfügbares Ergebnis. Öffne das Update und prüfe die Details.','Die Seite zur Anfrageprüfung ist bereit. Fahre dort fort und bestätige deine Kartendaten.','Ein Kartenstatus Update wartet. Öffne die Seite und prüfe den verfügbaren Weg.']
 },
 'JOB_ES': {
  'cta': ['🔍 VER OFERTA','✅ VER ESTADO','📋 VER OPCIONES','➡️ CONTINUAR','📌 ABRIR ACTUALIZACIÓN','🔎 REVISAR VACANTE','✅ CONFIRMAR DATOS','📄 VER DETALLES','💼 VER PERFIL','🔔 ABRIR ESTADO','📋 REVISAR RESULTADO','➡️ SEGUIR REVISIÓN'],
  'heads': ['💼 ACTUALIZACIÓN DE VACANTE','📋 REVISIÓN DISPONIBLE','🔎 OPCIONES DE TRABAJO','✅ PASO DE SOLICITUD','📌 ESTADO DE POSTULACIÓN','💬 DETALLES ABIERTOS','📄 PERFIL LABORAL','🔔 CONTINUAR REVISIÓN','💼 AVISO DE EMPLEO','📋 ESTADO LISTO','🔎 PERFIL COMPATIBLE','✅ VACANTE ABIERTA','📌 SOLICITUD EN REVISIÓN','💬 DETALLES DISPONIBLES','📄 OPCIONES ABIERTAS','🔔 REVISIÓN DE PERFIL','💼 PUESTO DISPONIBLE','📋 CONFIRMACIÓN DE DATOS','🔎 RESULTADO LABORAL','✅ SIGUIENTE PASO'],
  'bodies': ['Tu solicitud de empleo tiene una revisión lista. Abre la página para continuar con las opciones disponibles.','Hay una verificación disponible para tu perfil laboral. Revisa los detalles antes de avanzar.','Tus opciones de trabajo están listas para comparar. Abre la actualización y confirma el siguiente paso.','El flujo de recomendación laboral tiene nuevos detalles disponibles. Consulta la página para continuar.','La revisión de tu perfil está lista para confirmación. Abre la actualización laboral para ver el resultado.','Hay un paso de selección de vacante disponible ahora. Revisa la página y continúa desde ahí.','Tu solicitud pasó al siguiente punto de revisión. Abre la página de estado para ver detalles.','El resumen de opciones laborales está listo. Confirma la información en la página de revisión.','Hay una nueva actualización de perfil laboral disponible. Revisa las opciones y continúa.','Tu compatibilidad con la vacante tiene un resultado disponible. Abre la actualización para revisar los detalles.','La página de revisión de solicitud está lista. Continúa allí para confirmar la información de perfil.','Hay una actualización de estado laboral esperando. Abre la página y revisa el camino disponible.']
 },
 'CAR_EN': {
  'cta': ['🚗 REVIEW OFFER','✅ CHECK STATUS','📋 SEE OPTIONS','➡️ CONTINUE','🔎 OPEN REVIEW','📌 VIEW DETAILS','✅ CONFIRM DETAILS','🚘 SEE RESULT','🚗 REVIEW VEHICLE','🔔 OPEN STATUS','📄 SEE AUTO OPTIONS','🔍 CHECK MATCH'],
  'heads': ['🚗 VEHICLE OFFER UPDATE','📋 AUTO REQUEST STATUS','🔎 CAR OPTIONS READY','✅ REVIEW AVAILABLE','📌 CONFIRMATION STEP','🚘 VEHICLE MATCH UPDATE','📄 DETAILS READY','🔔 AUTO PROFILE UPDATE','🚗 OFFER NOTICE','📋 STATUS READY','🔎 PROFILE MATCH READY','✅ VEHICLE CHECK OPEN','📌 AUTO REVIEW READY','🚘 DETAILS AVAILABLE','📄 OPTION CHECK READY','🔔 PROFILE REVIEW UPDATE','🚗 VEHICLE SELECTION STEP','📋 STATUS CONFIRMATION','🔎 AUTO RESULT NOTICE','✅ REVIEW CONTINUATION'],
  'bodies': ['Your vehicle request has a review step ready. Open the page to continue with the available options.','A status check is available for your auto profile. Review the details before moving forward.','Your vehicle options are ready to compare. Open the update and confirm the next step.','The auto recommendation flow has new details available. Check the page to continue.','Your profile review is ready for confirmation. Open the vehicle update to see the result.','A vehicle selection step is available now. Review the page and continue from there.','Your auto request moved to the next review point. Open the status page for details.','The vehicle option summary is ready. Confirm the information on the review page.','A new auto profile update is available. Check the options and continue safely.','Your vehicle match has an available result. Open the update to review the details.','The request review page is ready. Continue there to confirm your auto information.','An auto status update is waiting. Open the page and check the available path.']
 }
}

def generated_copy(vertical, idx):
    fam = copy_family(vertical)
    cfg = COPY_VARIATIONS[fam]
    head = cfg['heads'][idx % len(cfg['heads'])]
    body = cfg['bodies'][(idx // len(cfg['heads']) + idx) % len(cfg['bodies'])]
    text = no_dash(f"{head}

{body}")
    if fam in ('ES_CC', 'JOB_ES'):
        text = zw_text(text)
    return text, cfg['cta'][idx % len(cfg['cta'])]

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
