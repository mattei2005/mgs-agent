#!/usr/bin/env python3
import asyncio, importlib.util, pathlib, json, datetime, re, hashlib
BASE=pathlib.Path('/root/mgs-agent')
spec=importlib.util.spec_from_file_location('rollout', BASE/'scripts/sb-utility-rollout-manager.py')
rollout=importlib.util.module_from_spec(spec); spec.loader.exec_module(rollout)
TARGETS=[
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
CTA_EN_CC=['🔍 REVIEW CARD','✅ CHECK STATUS','📋 SEE OPTIONS','➡️ CONTINUE','💳 REVIEW UPDATE','🔎 OPEN REVIEW','✅ CONFIRM DETAILS','📌 VIEW RESULT']
CTA_ES_CC=['🔍 REVISAR TARJETA','✅ VER ESTADO','📋 VER OPCIONES','➡️ CONTINUAR','💳 VER ACTUALIZACIÓN','🔎 ABRIR REVISIÓN','✅ CONFIRMAR DATOS','📌 VER RESULTADO']
CTA_DE_CC=['🔍 KARTE PRÜFEN','✅ STATUS ANSEHEN','📋 OPTIONEN SEHEN','➡️ WEITER','💳 UPDATE ANSEHEN','🔎 PRÜFUNG ÖFFNEN','✅ DATEN BESTÄTIGEN','📌 ERGEBNIS SEHEN']
CTA_JOB_ES=['🔍 VER OFERTA','✅ VER ESTADO','📋 VER OPCIONES','➡️ CONTINUAR','📌 ABRIR ACTUALIZACIÓN','🔎 REVISAR VACANTE','✅ CONFIRMAR DATOS','📄 VER DETALLES']
CTA_CAR_EN=['🚗 REVIEW OFFER','✅ CHECK STATUS','📋 SEE OPTIONS','➡️ CONTINUE','🔎 OPEN REVIEW','📌 VIEW DETAILS','✅ CONFIRM DETAILS','🚘 SEE RESULT']

def zw_text(s):
    # Insert U+200B after every 2 words, preserving paragraphs lightly.
    parts=re.split(r'(\s+)', s)
    out=[]; words=0
    for part in parts:
        out.append(part)
        if part.strip() and not part.isspace():
            words += 1
            if words % 2 == 0:
                out.append('\u200b')
    return ''.join(out)

def parse_vertical(name):
    m=re.search(r'\b([A-Z]{2})[-_ ]([A-Z0-9]{2,8})[-_ ]([A-Z]{2})\b', name.upper())
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ''

def no_dash(s):
    return s.replace('-', ' ').replace('–',' ').replace('—',' ')

def cc_en(i,country='US'):
    heads=['💳 CARD REVIEW UPDATE','📋 CARD REQUEST STATUS','🔎 CARD OPTIONS READY','✅ CARD REVIEW AVAILABLE','📌 APPLICATION STEP READY','💬 CARD MATCH UPDATE','📄 REVIEW STEP OPEN','🔔 CARD PROFILE UPDATE']
    bodies=[
      'Your card request has a new review step available. Open the update to continue with the available options.',
      'A card status check is ready for review. Use the next screen to confirm the details and continue.',
      'Your credit profile has card options available to review. Open the update and check the next step.',
      'The card recommendation flow has a new result ready. Review the details before continuing.',
      'A pending card review needs confirmation. Open the page to see the available card options.',
      'Your application review is ready for the next step. Check the status and continue from the secure page.',
      'There is an update on your card request. Review the current option and confirm the next detail.',
      'Your card selection step is available now. Open the update to review the current recommendation.'
    ]
    return f"{heads[i%len(heads)]}\n\n{bodies[(i//len(heads)+i)%len(bodies)]}", CTA_EN_CC[i%len(CTA_EN_CC)]

def cc_es(i):
    heads=['💳 ACTUALIZACIÓN DE TARJETA','📋 ESTADO DE SOLICITUD','🔎 OPCIONES DE TARJETA','✅ REVISIÓN DISPONIBLE','📌 PASO DE CONFIRMACIÓN','💬 RESULTADO DE TARJETA','📄 REVISIÓN ABIERTA','🔔 PERFIL ACTUALIZADO']
    bodies=[
      'Tu solicitud de tarjeta tiene una nueva revisión disponible. Abre la actualización para continuar con las opciones.',
      'El estado de tu tarjeta está listo para revisar. Confirma los datos en la siguiente pantalla y continúa.',
      'Tu perfil tiene opciones de tarjeta disponibles. Abre la revisión para ver el próximo paso.',
      'El flujo de recomendación de tarjeta tiene un resultado listo. Revisa los detalles antes de continuar.',
      'Hay una revisión pendiente de tu tarjeta. Abre la página para confirmar la información actual.',
      'Tu proceso de tarjeta está listo para el próximo paso. Revisa el estado y continúa desde la página segura.',
      'Hay una actualización sobre tu solicitud de tarjeta. Revisa la opción actual y confirma los datos.',
      'Tu paso de selección de tarjeta está disponible. Abre la actualización para ver la recomendación actual.'
    ]
    return zw_text(no_dash(f"{heads[i%len(heads)]}\n\n{bodies[(i//len(heads)+i)%len(bodies)]}")), CTA_ES_CC[i%len(CTA_ES_CC)]

def cc_de(i):
    heads=['💳 KARTEN UPDATE','📋 ANFRAGE STATUS','🔎 KARTEN OPTIONEN','✅ PRÜFUNG VERFÜGBAR','📌 BESTÄTIGUNG BEREIT','💬 KARTEN ERGEBNIS','📄 PRÜFUNG OFFEN','🔔 PROFIL UPDATE']
    bodies=[
      'Für deine Kartenanfrage ist ein neuer Prüfschritt verfügbar. Öffne das Update und sieh dir die Optionen an.',
      'Der Status deiner Karte ist zur Prüfung bereit. Bestätige die Angaben auf der nächsten Seite.',
      'Für dein Profil stehen Kartenoptionen zur Prüfung bereit. Öffne die Übersicht für den nächsten Schritt.',
      'Der Kartenempfehlungsprozess hat ein Ergebnis bereit. Prüfe die Details bevor du fortfährst.',
      'Eine Kartenprüfung wartet auf Bestätigung. Öffne die Seite und bestätige die aktuellen Angaben.',
      'Dein Kartenprozess ist für den nächsten Schritt bereit. Sieh dir den Status an und fahre fort.',
      'Es gibt ein Update zu deiner Kartenanfrage. Prüfe die aktuelle Option und bestätige die Angaben.',
      'Der Auswahlschritt für deine Karte ist verfügbar. Öffne das Update und prüfe die Empfehlung.'
    ]
    return no_dash(f"{heads[i%len(heads)]}\n\n{bodies[(i//len(heads)+i)%len(bodies)]}"), CTA_DE_CC[i%len(CTA_DE_CC)]

def job_es(i):
    heads=['📋 ACTUALIZACIÓN DE VACANTE','✅ REVISIÓN DISPONIBLE','🔎 OPCIONES DE TRABAJO','📌 PASO DE SOLICITUD','💬 ESTADO DE POSTULACIÓN','📄 DETALLES ABIERTOS','🔔 PERFIL LABORAL','➡️ CONTINUAR REVISIÓN']
    bodies=[
      'Hay una actualización disponible para tu solicitud de empleo. Abre la revisión para ver el próximo paso.',
      'Tu perfil laboral tiene una opción lista para revisar. Confirma los datos y continúa desde la página.',
      'Una vacante relacionada con tu perfil está lista para revisión. Abre los detalles para continuar.',
      'El estado de tu postulación necesita una revisión rápida. Consulta la información actualizada.',
      'Hay un nuevo paso disponible en tu proceso de empleo. Revisa los detalles antes de continuar.',
      'Tu revisión de oportunidad laboral está abierta. Verifica la información y confirma el siguiente paso.',
      'Se actualizó el estado de tu perfil. Abre la página para revisar las opciones disponibles.',
      'Tu solicitud tiene detalles listos para confirmar. Continúa para ver la información actual.'
    ]
    return zw_text(no_dash(f"{heads[i%len(heads)]}\n\n{bodies[(i//len(heads)+i)%len(bodies)]}")), CTA_JOB_ES[i%len(CTA_JOB_ES)]

def car_en(i):
    heads=['🚗 VEHICLE OFFER UPDATE','📋 AUTO REQUEST STATUS','🔎 CAR OPTIONS READY','✅ REVIEW AVAILABLE','📌 CONFIRMATION STEP','🚘 VEHICLE MATCH UPDATE','📄 DETAILS READY','🔔 AUTO PROFILE UPDATE']
    bodies=[
      'Your vehicle request has a new review step available. Open the update to continue with the options.',
      'An auto offer status check is ready for review. Confirm the details on the next page.',
      'Your profile has vehicle options available to review. Open the update and check the next step.',
      'The car offer flow has a result ready. Review the details before continuing.',
      'A pending vehicle review needs confirmation. Open the page to see the available options.',
      'Your auto request is ready for the next step. Check the status and continue from the secure page.',
      'There is an update on your vehicle request. Review the current option and confirm the next detail.',
      'Your vehicle selection step is available now. Open the update to review the current match.'
    ]
    return no_dash(f"{heads[i%len(heads)]}\n\n{bodies[(i//len(heads)+i)%len(bodies)]}"), CTA_CAR_EN[i%len(CTA_CAR_EN)]

def make_replacement(vertical, idx):
    if vertical.endswith('-ES') and 'JOB' not in vertical:
        return cc_es(idx)
    if vertical.endswith('-DE'):
        return cc_de(idx)
    if 'JOB' in vertical:
        return job_es(idx)
    if 'CAR' in vertical:
        return car_en(idx)
    return cc_en(idx)

def digest(msgs):
    slim=[{'id':m.get('MESSAGE_ID'),'text':m.get('TEXT'),'cta':m.get('CTA_1') or m.get('CTA 1'),'link':m.get('LINK_1') or m.get('LINK 1')} for m in msgs]
    return hashlib.sha256(json.dumps(slim,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

async def main():
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    outdir=BASE/f'work/meta-utility/replace-gray-red-test-templates-{stamp}'
    backup=BASE/'backups/sb-templates'/f'replace-gray-red-test-templates-{stamp}'
    outdir.mkdir(parents=True,exist_ok=True); backup.mkdir(parents=True,exist_ok=True)
    p,b,ctx,page,rows,headers,post_url=await rollout.capture_rows_headers()
    results=[]
    try:
        by={r.get('NAME'):r for r in rows}
        for name in TARGETS:
            row=by.get(name)
            if not row: raise RuntimeError(f'not found {name}')
            vertical=parse_vertical(name)
            current=sorted(rollout.parse_messages(row), key=lambda m:int(m.get('MESSAGE_ID') or 0))
            rollout.save_json(backup/(rollout.safe_name(name)+'-before.json'), row)
            new=[]; replaced=[]; seq=0
            for m in current:
                color=rollout.status_color(rollout.status_of(m))
                slot=dict(m)
                if color in ('vermelho','cinza'):
                    text,cta=make_replacement(vertical, seq); seq += 1
                    slot['TEXT']=text
                    slot['CTA_1']=cta
                    slot.pop('CTA 1', None)
                    for k in ['APPROVED','INVALID_FORMAT','REJECTED','ERROR','REJECTED_REASON']:
                        slot.pop(k, None)
                    replaced.append({'message_id':slot.get('MESSAGE_ID'),'old_color':color,'new_text':text[:120],'new_cta':cta})
                # keep green as is
                new.append(slot)
            payload=dict(row); payload['MESSAGES']=json.dumps(new,ensure_ascii=False,separators=(',',':'))
            resp=await ctx.request.post(post_url,headers=headers,data=json.dumps(payload,ensure_ascii=False))
            err='' if resp.status<300 else (await resp.text())[:500]
            ok=resp.status<300
            attempts=[]; approval_ok=False
            if ok:
                tid=row.get('ID') or row.get('id')
                for url in [f'https://api.jbfdigital.com.br/broadcast/messenger/{tid}/approve', f'https://api.jbfdigital.com.br/broadcast/Messenger/{tid}/approve']:
                    ar=await ctx.request.post(url,headers=headers)
                    txt='' if ar.status<300 else (await ar.text())[:300]
                    attempts.append({'url':url,'status':ar.status,'error':txt})
                    if ar.status<300:
                        approval_ok=True; break
            results.append({'template':name,'vertical':vertical,'before_messages':len(current),'replaced':len(replaced),'post_status':resp.status,'post_error':err,'approval_ok':approval_ok,'approval_attempts':attempts,'digest':digest(new),'backup':str(backup/(rollout.safe_name(name)+'-before.json')),'replaced_rows':replaced})
            if not ok: raise RuntimeError(f'POST failed {name} {resp.status} {err}')
        await b.close(); await p.stop()
        # readback
        p2,b2,ctx2,page2,rows2,headers2,post_url2=await rollout.capture_rows_headers()
        try:
            by2={r.get('NAME'):r for r in rows2}
            for r in results:
                live=by2.get(r['template'])
                msgs=sorted(rollout.parse_messages(live), key=lambda m:int(m.get('MESSAGE_ID') or 0)) if live else []
                r['readback_messages']=len(msgs)
                r['readback_digest']=digest(msgs) if msgs else ''
                r['readback_ok']=len(msgs)==20 and r['readback_digest']==r['digest']
        finally:
            await b2.close(); await p2.stop()
        (outdir/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print('OUT',outdir)
        print('BACKUP',backup)
        print('templates',len(results),'replaced_total',sum(r['replaced'] for r in results),'post_ok',sum(1 for r in results if r['post_status']<300),'approval_ok',sum(1 for r in results if r['approval_ok']),'readback_ok',sum(1 for r in results if r.get('readback_ok')))
        for r in results:
            print(f"{r['vertical']}\treplace={r['replaced']}\tpost={r['post_status']}\tapproval={r['approval_ok']}\treadback={r.get('readback_ok')}\t{r['template']}")
    finally:
        try: await b.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass
asyncio.run(main())
