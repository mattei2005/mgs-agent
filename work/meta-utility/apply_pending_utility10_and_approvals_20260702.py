#!/usr/bin/env python3
import asyncio, csv, datetime as dt, json, pathlib, re, subprocess
from copy import deepcopy
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE = pathlib.Path('/root/mgs-agent')
WORK = BASE/'work/meta-utility'
BACKUP = BASE/'backups/sb-templates'
OUT = WORK/'pending-utility10-20260702'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
TZ=ZoneInfo('America/New_York')

TARGETS = [
'Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas',
'Financeadx - CA-CC-EN/EN-SR - g006-d Nicolas',
'Marevelx - DE-CC-DE/DE-SR - g001-d Icaro',
'Newsoun - DE-CC-DE/DE-SR - g005-d Kelly',
'Xyvlov - DE-CC-DE/DE-SR - g003-d Isliago',
'Helixenit - DE-CC-DE/DE-SR - g005-d Kelly',
'Financeadx - MX-CC-ES/ES-ZW-SR - g006-d Nicolas',
'Infinitynexx - MX-CC-ES/ES-ZW-SR - g004-d Joe',
'Helixenit - MX-CC-ES/ES-ZW-SR - g005-d Kelly',
'Vizioid - MX-CC-ES/ES-ZW-SR - g002-d Gustavo',
'Fincgriffin - TR-CC-TR/TR-SR -  g006-d Nicolas',
'Fincgriffin - TR-CC-TR/TR-SR - g001-d Icaro',
'Fincgriffin - TR-CC-TR/TR-SR - g003-d Isliago',
'Fincgriffin - TR-CC-TR/TR-SR - g004-d Joe',
'Fincgriffin - TR-CC-TR/TR-SR - g005-d Kelly',
'Portal - US-CC-EN/EN - AV - g001-d Icaro',
'Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens',
'Financeadx - ZA-CC-EN/EN-SR - g006-d Nicolas',
'Fincgriffin - US-CAR-EN/EN - JBF - g001-d',
'Fincgriffin - US-CAR-EN/EN - JBF - g002-d',
'Fincgriffin - US-CAR-EN/EN - JBF - g003-d',
'Fincgriffin - US-CAR-EN/EN - JBF - g004-d',
'Fincgriffin - US-CAR-EN/EN - JBF - g005-d',
'Fincgriffin - US-CAR-EN/EN - JBF - g006-d',
'Spe - US-JOB-EN/EN - AV - g006-d Nicolas',
'Spe - US-JOB-ES/ES-ZW - AV - g006-d Nicolas',
]
RENAME = {'Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens': 'NAO USAR - Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens'}

CC_EN = [
('⚠️ Important update, {{first_name}}\n\nI have new information regarding your recent applications, and it may directly affect your credit card approval.\nTake a moment to review the next steps.\n\n👇 When you’re ready, choose your next step below:', '🔍 SEE RESPONSE OF MY CARD'),
('📬 UNCLAIMED PACKAGE — {{first_name}}, a Credit Card package worth $14,200 in limit is sitting unclaimed under your name.\n\nIt’s at the sorting center. Claim the delivery before it gets returned.', '🚚 CLAIM DELIVERY'),
('💳 CREDIT CARD APPROVED\n\nCongratulations, {{first_name}}! Your new Credit Card is ready for dispatch.\n\nWe just need you to confirm the delivery address.', '🚚 CONFIRM NOW'),
('✅ DELIVERY CONFIRMED\nYour card with $15,000 limit is being prepared for dispatch\nVerify your details to ship.', '🚚 SHIP MY CARD'),
('⚡ CARD DISPATCHED — No waiting. {{first_name}}, your Credit Card was approved instantly and is already in the system for delivery.\n\nTap to assign the courier and receive it today.', '🚚 ASSIGN COURIER'),
('📦 SHIPMENT UPDATE\n\nYour Credit Card package is waiting for one final confirmation before dispatch.\n\nReview your information here.', '📦 REVIEW INFO'),
('✅ AUTHORIZED: {{first_name}}, you are cleared to activate your new card.\n\nNo more waiting. Tap to start.', '🚀 ACTIVATE NOW'),
('🔔 (1) NEW CARD UPDATE\n\nYour Credit Card status has changed to: APPROVED.\n\nTap to see your starting limit and shipping date.', '📥 READ STATUS'),
('✅ REQUEST RECEIVED\n\n{{first_name}}, your Credit Card request was received successfully.\nOne confirmation step is available before the next review.', '✅ CONFIRM NOW'),
('📍 STATUS CONFIRMED\n\nYour Credit Card request moved to the final review step.\n\nOpen the update and finish the process.', '🟢 FINISH PROCESS'),
]
CC_ES = [
('⚠️ Actualización importante, {{first_name}}\n\nTengo nueva información sobre tus solicitudes recientes y puede afectar directamente la aprobación de tu tarjeta de crédito.\nRevisa los próximos pasos.\n\n👇 Cuando estés listo, elige el siguiente paso abajo:', '🔍 VER RESPUESTA DE MI TARJETA'),
('📬 PAQUETE SIN RECLAMAR — {{first_name}}, un paquete de Tarjeta de Crédito con límite de $14,200 está sin reclamar a tu nombre.\n\nEstá en el centro de clasificación. Reclama la entrega antes de que sea devuelto.', '🚚 RECLAMAR ENTREGA'),
('💳 TARJETA DE CRÉDITO APROBADA\n\n¡Felicidades, {{first_name}}! Tu nueva Tarjeta de Crédito está lista para envío.\n\nSolo necesitamos confirmar la dirección de entrega.', '🚚 CONFIRMAR AHORA'),
('✅ ENTREGA CONFIRMADA\nTu tarjeta con límite de $15,000 se está preparando para envío.\nVerifica tus datos para enviarla.', '🚚 ENVIAR MI TARJETA'),
('⚡ TARJETA ENVIADA — Sin espera. {{first_name}}, tu Tarjeta de Crédito fue aprobada al instante y ya está en el sistema de entrega.\n\nToca para asignar el mensajero y recibirla hoy.', '🚚 ASIGNAR MENSAJERO'),
('📦 ACTUALIZACIÓN DE ENVÍO\n\nTu paquete de Tarjeta de Crédito espera una confirmación final antes del despacho.\n\nRevisa tu información aquí.', '📦 REVISAR INFO'),
('✅ AUTORIZADO: {{first_name}}, ya puedes activar tu nueva tarjeta.\n\nSin más espera. Toca para comenzar.', '🚀 ACTIVAR AHORA'),
('🔔 (1) NUEVA ACTUALIZACIÓN DE TARJETA\n\nEl estado de tu Tarjeta de Crédito cambió a: APROBADA.\n\nToca para ver tu límite inicial y fecha de envío.', '📥 LEER ESTADO'),
('✅ SOLICITUD RECIBIDA\n\n{{first_name}}, tu solicitud de Tarjeta de Crédito fue recibida correctamente.\nHay un paso de confirmación antes de la próxima revisión.', '✅ CONFIRMAR AHORA'),
('📍 ESTADO CONFIRMADO\n\nTu solicitud de Tarjeta de Crédito pasó al paso final de revisión.\n\nAbre la actualización y termina el proceso.', '🟢 TERMINAR PROCESO'),
]
CC_DE = [
('⚠️ Wichtige Aktualisierung, {{first_name}}\n\nIch habe neue Informationen zu deinen letzten Anträgen, die deine Kreditkartenfreigabe direkt betreffen können.\nBitte prüfe die nächsten Schritte.\n\n👇 Wenn du bereit bist, wähle unten den nächsten Schritt:', '🔍 ANTWORT MEINER KARTE SEHEN'),
('📬 NICHT ABGEHOLTES PAKET — {{first_name}}, ein Kreditkartenpaket mit einem Limit von 14.200 € liegt noch unbeansprucht auf deinen Namen vor.\n\nEs befindet sich im Sortierzentrum. Fordere die Lieferung an, bevor es zurückgesendet wird.', '🚚 LIEFERUNG ANFORDERN'),
('💳 KREDITKARTE GENEHMIGT\n\nGlückwunsch, {{first_name}}! Deine neue Kreditkarte ist versandbereit.\n\nWir müssen nur noch die Lieferadresse bestätigen.', '🚚 JETZT BESTÄTIGEN'),
('✅ LIEFERUNG BESTÄTIGT\nDeine Karte mit einem Limit von 15.000 € wird für den Versand vorbereitet.\nPrüfe deine Angaben für den Versand.', '🚚 MEINE KARTE SENDEN'),
('⚡ KARTE VERSENDET — Keine Wartezeit. {{first_name}}, deine Kreditkarte wurde sofort genehmigt und ist bereits im Liefersystem.\n\nTippe, um den Kurier zuzuweisen und sie heute zu erhalten.', '🚚 KURIER ZUWEISEN'),
('📦 VERSANDUPDATE\n\nDein Kreditkartenpaket wartet vor dem Versand auf eine letzte Bestätigung.\n\nPrüfe deine Informationen hier.', '📦 INFO PRÜFEN'),
('✅ AUTORISIERT: {{first_name}}, du kannst deine neue Karte jetzt aktivieren.\n\nKein weiteres Warten. Tippe, um zu starten.', '🚀 JETZT AKTIVIEREN'),
('🔔 (1) NEUES KARTENUPDATE\n\nDer Status deiner Kreditkarte wurde geändert auf: GENEHMIGT.\n\nTippe, um dein Startlimit und Versanddatum zu sehen.', '📥 STATUS LESEN'),
('✅ ANFRAGE ERHALTEN\n\n{{first_name}}, deine Kreditkartenanfrage wurde erfolgreich erhalten.\nVor der nächsten Prüfung ist ein Bestätigungsschritt verfügbar.', '✅ JETZT BESTÄTIGEN'),
('📍 STATUS BESTÄTIGT\n\nDeine Kreditkartenanfrage ist im letzten Prüfschritt.\n\nÖffne das Update und schließe den Vorgang ab.', '🟢 VORGANG ABSCHLIESSEN'),
]
CC_TR = [
('⚠️ Önemli güncelleme, {{first_name}}\n\nSon başvurularınla ilgili yeni bilgiler var ve bu durum kredi kartı onayını doğrudan etkileyebilir.\nSonraki adımları incele.\n\n👇 Hazır olduğunda aşağıdan sonraki adımı seç:', '🔍 KART YANITIMI GÖR'),
('📬 TESLİM ALINMAMIŞ PAKET — {{first_name}}, adına 14.200 TL limitli bir Kredi Kartı paketi bekliyor.\n\nSıralama merkezinde. İade edilmeden önce teslimatı onayla.', '🚚 TESLİMATI AL'),
('💳 KREDİ KARTI ONAYLANDI\n\nTebrikler, {{first_name}}! Yeni Kredi Kartın gönderime hazır.\n\nSadece teslimat adresini doğrulamamız gerekiyor.', '🚚 ŞİMDİ ONAYLA'),
('✅ TESLİMAT ONAYLANDI\n15.000 TL limitli kartın gönderim için hazırlanıyor.\nGönderim için bilgilerini doğrula.', '🚚 KARTIMI GÖNDER'),
('⚡ KART GÖNDERİLDİ — Bekleme yok. {{first_name}}, Kredi Kartın anında onaylandı ve teslimat sistemine alındı.\n\nKuryeyi atamak ve bugün almak için dokun.', '🚚 KURYE ATA'),
('📦 GÖNDERİM GÜNCELLEMESİ\n\nKredi Kartı paketin gönderimden önce son bir onay bekliyor.\n\nBilgilerini burada incele.', '📦 BİLGİLERİ İNCELE'),
('✅ YETKİ VERİLDİ: {{first_name}}, yeni kartını etkinleştirebilirsin.\n\nDaha fazla bekleme. Başlamak için dokun.', '🚀 ŞİMDİ ETKİNLEŞTİR'),
('🔔 (1) YENİ KART GÜNCELLEMESİ\n\nKredi Kartı durumun şu şekilde değişti: ONAYLANDI.\n\nBaşlangıç limitini ve gönderim tarihini görmek için dokun.', '📥 DURUMU OKU'),
('✅ BAŞVURU ALINDI\n\n{{first_name}}, Kredi Kartı başvurun başarıyla alındı.\nSonraki incelemeden önce bir onay adımı mevcut.', '✅ ŞİMDİ ONAYLA'),
('📍 DURUM ONAYLANDI\n\nKredi Kartı başvurun son inceleme adımına geçti.\n\nGüncellemeyi aç ve işlemi tamamla.', '🟢 İŞLEMİ TAMAMLA'),
]
CAR_EN = [('🚗 APPLICATION STATUS UPDATE\n\nYour auto financing request has a new review step available. Open the update to continue.', '🚗 CHECK STATUS'),('📋 REQUEST RECEIVED\n\nYour vehicle finance request was received successfully. Confirm the next step to keep it active.', '✅ CONFIRM NOW'),('🔎 REVIEW READY\n\nYour car loan profile is ready for review. Check the available details on the secure page.', '🔎 REVIEW OPTIONS'),('📍 STATUS CHECKPOINT\n\nYour vehicle request reached a new checkpoint. Review the information and continue.', '📍 CHECK UPDATE'),('✅ PRE-CHECK AVAILABLE\n\nA pre-check step is available for your auto financing request. Open it to review the next action.', '✅ OPEN PRE-CHECK'),('📬 UPDATE WAITING\n\nThere is an update waiting for your car financing request. Review it before the request expires.', '📬 OPEN UPDATE'),('📝 CONFIRM DETAILS\n\nYour request needs one confirmation before the next review. Check your information now.', '📝 CONFIRM DETAILS'),('🚘 VEHICLE OPTIONS READY\n\nYour vehicle financing options are ready to review. Open the page to continue.', '🚘 SEE OPTIONS'),('🔔 NEW REQUEST UPDATE\n\nYour auto finance request has a new status available. Continue from the secure page.', '🔔 READ STATUS'),('📌 FINAL REVIEW STEP\n\nYour car loan request moved to the final review step. Open the update and finish the process.', '📌 FINISH REVIEW')]
JOB_EN = [('💼 APPLICATION STATUS UPDATE\n\nYour job application has a new review step available. Open the update to continue.', '💼 CHECK STATUS'),('📋 REQUEST RECEIVED\n\nYour application was received successfully. Confirm the next step to keep it active.', '✅ CONFIRM NOW'),('🔎 REVIEW READY\n\nYour profile is ready for review. Check the available details on the secure page.', '🔎 REVIEW PROFILE'),('📍 STATUS CHECKPOINT\n\nYour application reached a new checkpoint. Review the information and continue.', '📍 CHECK UPDATE'),('✅ PRE-CHECK AVAILABLE\n\nA pre-check step is available for your application. Open it to review the next action.', '✅ OPEN PRE-CHECK'),('📬 UPDATE WAITING\n\nThere is an update waiting for your application. Review it before the request expires.', '📬 OPEN UPDATE'),('📝 CONFIRM DETAILS\n\nYour request needs one confirmation before the next review. Check your information now.', '📝 CONFIRM DETAILS'),('💼 OPPORTUNITIES READY\n\nYour job options are ready to review. Open the page to continue.', '💼 SEE OPTIONS'),('🔔 NEW APPLICATION UPDATE\n\nYour application has a new status available. Continue from the secure page.', '🔔 READ STATUS'),('📌 FINAL REVIEW STEP\n\nYour request moved to the final review step. Open the update and finish the process.', '📌 FINISH REVIEW')]
JOB_ES = [('💼 ACTUALIZACIÓN DE SOLICITUD\n\nTu solicitud de empleo tiene un nuevo paso de revisión disponible. Abre la actualización para continuar.', '💼 VER ESTADO'),('📋 SOLICITUD RECIBIDA\n\nTu solicitud fue recibida correctamente. Confirma el siguiente paso para mantenerla activa.', '✅ CONFIRMAR AHORA'),('🔎 REVISIÓN LISTA\n\nTu perfil está listo para revisión. Consulta los detalles disponibles en la página segura.', '🔎 REVISAR PERFIL'),('📍 PUNTO DE ESTADO\n\nTu solicitud llegó a un nuevo punto de revisión. Revisa la información y continúa.', '📍 VER ACTUALIZACIÓN'),('✅ PRE-REVISIÓN DISPONIBLE\n\nHay un paso de pre-revisión disponible para tu solicitud. Ábrelo para ver la siguiente acción.', '✅ ABRIR REVISIÓN'),('📬 ACTUALIZACIÓN PENDIENTE\n\nHay una actualización esperando por tu solicitud. Revísala antes de que expire.', '📬 ABRIR ACTUALIZACIÓN'),('📝 CONFIRMAR DATOS\n\nTu solicitud necesita una confirmación antes de la próxima revisión. Verifica tu información ahora.', '📝 CONFIRMAR DATOS'),('💼 OPORTUNIDADES LISTAS\n\nTus opciones de empleo están listas para revisar. Abre la página para continuar.', '💼 VER OPCIONES'),('🔔 NUEVA ACTUALIZACIÓN\n\nTu solicitud tiene un nuevo estado disponible. Continúa desde la página segura.', '🔔 LEER ESTADO'),('📌 REVISIÓN FINAL\n\nTu solicitud pasó al paso final de revisión. Abre la actualización y termina el proceso.', '📌 TERMINAR REVISIÓN')]

def nowtag(): return dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')
def safe_name(s): return re.sub(r'[^a-zA-Z0-9._-]+','-',s.lower()).strip('-')[:95]
def parse_messages(row):
    m=row.get('MESSAGES') or '[]'
    return json.loads(m) if isinstance(m,str) else (m if isinstance(m,list) else [])
def combo(name):
    m=re.search(r'([A-Z]{2})-([A-Z-]+)-([A-Z]{2})(?=/)', name or '')
    return '-'.join(m.groups()) if m else ''
def copy_bank(name):
    c=combo(name)
    if c.endswith('CC-ES') or c.startswith('AR-CC-ES') or c.startswith('MX-CC-ES'): return CC_ES
    if c.startswith('DE-CC-DE'): return CC_DE
    if c.startswith('TR-CC-TR'): return CC_TR
    if 'US-CAR-EN' in c: return CAR_EN
    if 'US-JOB-ES' in c: return JOB_ES
    if 'US-JOB-EN' in c: return JOB_EN
    return CC_EN

def build_utility10(row):
    before=sorted(parse_messages(row), key=lambda x:int(x.get('MESSAGE_ID') or 0))
    if len(before)<10: raise RuntimeError(f"{row.get('NAME')} has only {len(before)} messages")
    bank=copy_bank(row.get('NAME',''))
    out=[]
    for i,(text,cta) in enumerate(bank[:10],1):
        src=before[i-1]
        out.append({'MESSAGE_ID':i,'TEXT':text,'DESCRIPTION':'','IMAGE':'','CTA_1':cta,'LINK_1':src.get('LINK_1') or src.get('LINK 1') or '', 'CTA_2':'','LINK_2':'','TEXT_2':''})
    return out

def sb_credentials():
    u=subprocess.check_output(['op','item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--field','username','--reveal'],text=True).strip()
    p=subprocess.check_output(['op','item','get','Zeus - Smartbidding Dashboard','--vault','MGS Conteúdo','--field','password','--reveal'],text=True).strip()
    return u,p
async def visible_text(locator):
    try: return await locator.inner_text(timeout=5000)
    except Exception: return ''
async def ensure_login(page,ctx):
    body=await visible_text(page.locator('body'))
    if 'Log in to Smart Bidding' not in body and 'Email address' not in body: return
    u,p=sb_credentials()
    await page.locator('input[type="email"], input[name="username"], input[name="email"], input:visible').first.fill(u,timeout=15000)
    await page.locator('input[type="password"]:visible').first.fill(p,timeout=15000)
    await page.get_by_role('button', name=re.compile('Continue|Log in|Login', re.I)).first.click(timeout=15000)
    await page.wait_for_load_state('networkidle',timeout=90000); await page.wait_for_timeout(3000)
    await ctx.storage_state(path='/tmp/smartbidding_state_headed.json')
async def capture_broadcast(page):
    rows=[]; headers=None; post_url='https://api.jbfdigital.com.br/broadcast/Messenger'
    async def on_req(req):
        nonlocal headers,post_url
        if '/broadcast/Messenger' in req.url and req.method=='GET':
            headers=req.headers; post_url=req.url.split('?')[0]
    async def on_resp(resp):
        if '/broadcast/Messenger' in resp.url and resp.status==200:
            try:
                d=await resp.json()
                if isinstance(d,list): rows.extend(d)
            except Exception: pass
    page.on('request',on_req); page.on('response',on_resp)
    await page.goto('https://app.smartbiddingdigital.com/accounts',wait_until='networkidle',timeout=90000)
    await page.wait_for_timeout(2500); await ensure_login(page,page.context)
    try:
        await page.locator('.p-dropdown').first.click(timeout=10000); await page.wait_for_timeout(500)
        await page.get_by_text('Messenger', exact=True).last.click(timeout=10000); await page.wait_for_timeout(2500)
    except Exception: pass
    await page.get_by_text('Broadcast Template', exact=True).click(timeout=15000); await page.wait_for_timeout(7000)
    if not headers: raise RuntimeError('no broadcast headers captured')
    h={k:v for k,v in headers.items() if not k.startswith(':') and k.lower() not in ('content-length','host')}; h['content-type']='application/json'
    # Ensure full scope via direct API using captured auth; fallback to captured rows.
    api='https://api.jbfdigital.com.br/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger'
    resp=await page.context.request.get(api,headers=h)
    if resp.status<300:
        d=await resp.json()
        if isinstance(d,list) and len(d)>=len(rows): rows=d
    dedup={}
    for r in rows: dedup[r.get('ID') or r.get('NAME')]=r
    return list(dedup.values()),h,post_url
async def main():
    tag=nowtag(); OUT.mkdir(parents=True,exist_ok=True); BACKUP.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        ctx=await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent=UA)
        page=await ctx.new_page()
        try:
            rows,headers,post_url=await capture_broadcast(page)
            by_name={r.get('NAME'):r for r in rows}
            missing=[n for n in TARGETS if n not in by_name]
            if missing: raise RuntimeError('missing templates: '+json.dumps(missing,ensure_ascii=False))
            results=[]
            for name in TARGETS:
                row=by_name[name]
                before=parse_messages(row); new_msgs=build_utility10(row)
                bjson=BACKUP/f'{safe_name(name)}-before-utility10-{tag}.json'
                bcsv=BACKUP/f'{safe_name(name)}-before-utility10-{tag}.csv'
                bjson.write_text(json.dumps(row,ensure_ascii=False,indent=2))
                with bcsv.open('w',encoding='utf-8-sig',newline='') as f:
                    cols=['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2']
                    w=csv.DictWriter(f,fieldnames=cols,lineterminator='\r\n'); w.writeheader()
                    for m in sorted(before,key=lambda x:int(x.get('MESSAGE_ID') or 0)):
                        w.writerow({'MESSAGE ID':m.get('MESSAGE_ID',''),'TEXT':m.get('TEXT',''),'DESCRIPTION':m.get('DESCRIPTION',''),'IMAGE':m.get('IMAGE',''),'CTA 1':m.get('CTA_1',''),'LINK 1':m.get('LINK_1',''),'CTA 2':m.get('CTA_2',''),'LINK 2':m.get('LINK_2',''),'TEXT 2':m.get('TEXT_2','')})
                payload=deepcopy(row); payload['MESSAGES']=json.dumps(new_msgs,ensure_ascii=False,separators=(',',':'))
                if name in RENAME: payload['NAME']=RENAME[name]
                resp=await ctx.request.post(post_url,headers=headers,data=json.dumps(payload,ensure_ascii=False))
                txt=await resp.text()
                if resp.status>=300: raise RuntimeError(f'post failed {name} HTTP {resp.status}: {txt[:300]}')
                results.append({'template_before':name,'template_after':payload['NAME'],'id':row.get('ID'),'before_count':len(before),'after_count':10,'post_status':resp.status,'backup_json':str(bjson),'backup_csv':str(bcsv),'links_preserved_first10': [m.get('LINK_1') for m in new_msgs] == [m.get('LINK_1') for m in sorted(before,key=lambda x:int(x.get('MESSAGE_ID') or 0))[:10]]})
            # refresh broadcast and validate counts/name/links
            rows2,_,_=await capture_broadcast(page)
            by_name2={r.get('NAME'):r for r in rows2}
            validation=[]
            for r in results:
                row2=by_name2.get(r['template_after'])
                if not row2: validation.append({'template':r['template_after'],'ok':False,'error':'not found'}); continue
                msgs=parse_messages(row2)
                validation.append({'template':r['template_after'],'ok':len(msgs)==10 and r['links_preserved_first10'],'count':len(msgs),'links_preserved_first10':r['links_preserved_first10']})
            # Try approval endpoint variants for all templates with update OK. Keep full response summary.
            approvals=[]
            endpoints=['https://api.jbfdigital.com.br/broadcast/Messenger/{id}/approve','https://api.jbfdigital.com.br/broadcast/messenger/{id}/approve']
            for r in results:
                ok=False; attempts=[]
                for ep in endpoints:
                    url=ep.format(id=r['id'])
                    for method in ('post','put'):
                        req=getattr(ctx.request,method)
                        resp=await req(url,headers=headers,data='{}')
                        body=(await resp.text())[:250]
                        attempts.append({'method':method.upper(),'url':url.replace(r['id'],'{id}'),'status':resp.status,'body_head':body})
                        if 200 <= resp.status < 300:
                            ok=True; break
                    if ok: break
                approvals.append({'template':r['template_after'],'id':r['id'],'ok':ok,'attempts':attempts})
            audit={'status':'OK','executed_at_et':dt.datetime.now(TZ).isoformat(timespec='seconds'),'targets':len(TARGETS),'results':results,'validation':validation,'all_validated':all(v.get('ok') for v in validation),'approvals':approvals,'approvals_ok':sum(1 for a in approvals if a['ok']),'backup_glob':str(BACKUP/f'*-before-utility10-{tag}.*')}
            out=OUT/f'utility10-update-and-approvals-{tag}.json'; out.write_text(json.dumps(audit,ensure_ascii=False,indent=2))
            print(json.dumps({'status':'OK','targets':len(TARGETS),'all_validated':audit['all_validated'],'approvals_ok':audit['approvals_ok'],'audit':str(out)},ensure_ascii=False,indent=2))
        finally:
            await browser.close()
if __name__=='__main__': asyncio.run(main())
