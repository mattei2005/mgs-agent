#!/usr/bin/env python3
import asyncio, importlib.util, json, pathlib, re, hashlib, datetime, tempfile, os
from copy import deepcopy
from zoneinfo import ZoneInfo

BASE=pathlib.Path('/root/mgs-agent')
TZ=ZoneInfo('America/New_York')
spec=importlib.util.spec_from_file_location('rollout', BASE/'scripts/sb-utility-rollout-manager.py')
rollout=importlib.util.module_from_spec(spec); spec.loader.exec_module(rollout)
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

def now(): return datetime.datetime.now(TZ).isoformat(timespec='seconds')
def stamp(): return datetime.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')
def safe(s): return rollout.safe_name(s)
def visible(s): return re.sub('[\u200b\u200c\u200d\ufeff\u2060]', '', s or '')
def clean(s): return re.sub(r'\s+', ' ', visible(s).strip().lower())
def no_dash(s): return s.replace('-', ' ').replace('–',' ').replace('—',' ')
def zw_text(s):
    parts=re.split(r'(\s+)',s); out=[]; words=0
    for part in parts:
        out.append(part)
        if part.strip() and not part.isspace():
            words += 1
            if words % 2 == 0: out.append('\u200b')
    return ''.join(out)
def parse_vertical(name):
    m=re.search(r'\b([A-Z]{2})[-_ ]([A-Z0-9]{2,8})[-_ ]([A-Z]{2})\b', name.upper())
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ''
CTAS={
 'EN_CC':['REVIEW CARD','CHECK STATUS','SEE OPTIONS','CONTINUE','REVIEW UPDATE','OPEN REVIEW','CONFIRM DETAILS','VIEW RESULT','SEE CARD OPTIONS','OPEN STATUS','REVIEW PROFILE','CHECK MATCH','VIEW OPTIONS','CONFIRM REVIEW','OPEN DETAILS','SEE RESULT','CONTINUE REVIEW','VIEW UPDATE','CHECK OPTIONS','OPEN CARD REVIEW'],
 'ES_CC':['REVISAR TARJETA','VER ESTADO','VER OPCIONES','CONTINUAR','VER ACTUALIZACIÓN','ABRIR REVISIÓN','CONFIRMAR DATOS','VER RESULTADO','VER OPCIONES DE TARJETA','ABRIR ESTADO','REVISAR PERFIL','VER COMPATIBILIDAD','CONSULTAR OPCIONES','CONFIRMAR REVISIÓN','ABRIR DETALLES','VER RESPUESTA','CONTINUAR REVISIÓN','VER UPDATE','REVISAR OPCIONES','ABRIR TARJETA'],
 'DE_CC':['KARTE PRÜFEN','STATUS ANSEHEN','OPTIONEN SEHEN','WEITER','UPDATE ANSEHEN','PRÜFUNG ÖFFNEN','DATEN BESTÄTIGEN','ERGEBNIS SEHEN','KARTENOPTIONEN SEHEN','STATUS ÖFFNEN','PROFIL PRÜFEN','TREFFER ANSEHEN','OPTIONEN PRÜFEN','PRÜFUNG BESTÄTIGEN','DETAILS ÖFFNEN','ANTWORT SEHEN','PRÜFUNG FORTSETZEN','UPDATE ÖFFNEN','OPTIONEN ÖFFNEN','KARTENSTATUS SEHEN'],
 'JOB_ES':['VER OFERTA','VER ESTADO','VER OPCIONES','CONTINUAR','ABRIR ACTUALIZACIÓN','REVISAR VACANTE','CONFIRMAR DATOS','VER DETALLES','VER PERFIL','ABRIR ESTADO','REVISAR RESULTADO','CONTINUAR REVISIÓN','VER PUESTO','ABRIR DETALLES','CONFIRMAR PERFIL','VER RESPUESTA','REVISAR OPCIONES','ABRIR SOLICITUD','SEGUIR REVISIÓN','VER ACTUALIZACIÓN'],
 'CAR_EN':['REVIEW OFFER','CHECK STATUS','SEE OPTIONS','CONTINUE','OPEN REVIEW','VIEW DETAILS','CONFIRM DETAILS','SEE RESULT','REVIEW VEHICLE','OPEN STATUS','SEE AUTO OPTIONS','CHECK MATCH','VIEW OFFER','CONFIRM REVIEW','OPEN DETAILS','SEE UPDATE','CONTINUE REVIEW','VIEW RESULT','CHECK OPTIONS','OPEN OFFER'],
}
HEADS={
 'EN_CC':['CARD REVIEW UPDATE','CARD REQUEST STATUS','CARD OPTIONS READY','CARD REVIEW AVAILABLE','APPLICATION STEP READY','CARD MATCH UPDATE','REVIEW STEP OPEN','CARD PROFILE UPDATE','CARD OPTION NOTICE','CARD STATUS READY','PROFILE MATCH READY','CARD CHECK OPEN','REQUEST REVIEW READY','CARD DETAILS AVAILABLE','OPTION CHECK READY','PROFILE REVIEW UPDATE','CARD SELECTION STEP','STATUS CONFIRMATION','CARD RESULT NOTICE','REVIEW CONTINUATION'],
 'ES_CC':['ACTUALIZACIÓN DE TARJETA','ESTADO DE SOLICITUD','OPCIONES DE TARJETA','REVISIÓN DISPONIBLE','PASO DE CONFIRMACIÓN','RESULTADO DE TARJETA','REVISIÓN ABIERTA','PERFIL ACTUALIZADO','AVISO DE TARJETA','ESTADO LISTO','PERFIL COMPATIBLE','CONSULTA ABIERTA','SOLICITUD EN REVISIÓN','DETALLES DISPONIBLES','OPCIONES ABIERTAS','REVISIÓN DE PERFIL','SELECCIÓN DE TARJETA','CONFIRMACIÓN DE ESTADO','RESULTADO DISPONIBLE','CONTINUACIÓN DE REVISIÓN'],
 'DE_CC':['KARTEN UPDATE','ANFRAGE STATUS','KARTEN OPTIONEN','PRÜFUNG VERFÜGBAR','BESTÄTIGUNG BEREIT','KARTEN ERGEBNIS','PRÜFUNG OFFEN','PROFIL UPDATE','KARTEN HINWEIS','STATUS BEREIT','PROFIL TREFFER','PRÜFUNG STARTEN','ANFRAGE PRÜFUNG','DETAILS VERFÜGBAR','OPTIONEN OFFEN','PROFIL PRÜFUNG','KARTENAUSWAHL','STATUS BESTÄTIGUNG','ERGEBNIS BEREIT','PRÜFUNG FORTSETZEN'],
 'JOB_ES':['ACTUALIZACIÓN DE VACANTE','REVISIÓN DISPONIBLE','OPCIONES DE TRABAJO','PASO DE SOLICITUD','ESTADO DE POSTULACIÓN','DETALLES ABIERTOS','PERFIL LABORAL','CONTINUAR REVISIÓN','AVISO DE EMPLEO','ESTADO LISTO','PERFIL COMPATIBLE','VACANTE ABIERTA','SOLICITUD EN REVISIÓN','DETALLES DISPONIBLES','OPCIONES ABIERTAS','REVISIÓN DE PERFIL','PUESTO DISPONIBLE','CONFIRMACIÓN DE DATOS','RESULTADO LABORAL','SIGUIENTE PASO'],
 'CAR_EN':['VEHICLE OFFER UPDATE','AUTO REQUEST STATUS','CAR OPTIONS READY','REVIEW AVAILABLE','CONFIRMATION STEP','VEHICLE MATCH UPDATE','DETAILS READY','AUTO PROFILE UPDATE','OFFER NOTICE','STATUS READY','PROFILE MATCH READY','VEHICLE CHECK OPEN','AUTO REVIEW READY','DETAILS AVAILABLE','OPTION CHECK READY','PROFILE REVIEW UPDATE','VEHICLE SELECTION STEP','STATUS CONFIRMATION','AUTO RESULT NOTICE','REVIEW CONTINUATION'],
}
BODIES={
 'EN_CC':['Your card request has a review step ready. Open the page to continue with the available options.','A status check is available for your card profile. Review the details before moving forward.','Your card options are ready to compare. Open the update and confirm the next step.','The card recommendation flow has new details available. Check the page to continue.','Your profile review is ready for confirmation. Open the card update to see the result.','A card selection step is available now. Review the page and continue from there.','Your card request moved to the next review point. Open the status page for details.','The card option summary is ready. Confirm the information on the review page.','A new card profile update is available. Check the options and continue safely.','Your card match has an available result. Open the update to review the details.','The request review page is ready. Continue there to confirm your card information.','A card status update is waiting. Open the page and check the available path.','Your card profile has a fresh option review. See the details before continuing.','The card recommendation page has a confirmation step. Review it to proceed.','A card review result is available. Open the update and see the next instruction.','Your card options page is ready for a quick check. Continue from the review screen.','The card request status changed to a review step. Open the page to verify it.','A new card detail screen is available. Review the information and keep going.','Your card profile review has another step open. Check the update to continue.','The card selection review is ready. Open the page and confirm the next action.'],
 'ES_CC':['Tu solicitud de tarjeta tiene una revisión lista. Abre la página para continuar con las opciones disponibles.','Hay una verificación disponible para tu perfil de tarjeta. Revisa los detalles antes de avanzar.','Tus opciones de tarjeta están listas para comparar. Abre la actualización y confirma el siguiente paso.','El flujo de recomendación de tarjeta tiene nuevos detalles disponibles. Consulta la página para continuar.','La revisión de tu perfil está lista para confirmación. Abre la actualización de tarjeta para ver el resultado.','Hay un paso de selección de tarjeta disponible ahora. Revisa la página y continúa desde ahí.','Tu solicitud de tarjeta pasó al siguiente punto de revisión. Abre la página de estado para ver detalles.','El resumen de opciones de tarjeta está listo. Confirma la información en la página de revisión.','Hay una nueva actualización de perfil de tarjeta disponible. Revisa las opciones y continúa.','Tu compatibilidad de tarjeta tiene un resultado disponible. Abre la actualización para revisar los detalles.','La página de revisión de solicitud está lista. Continúa allí para confirmar la información de tarjeta.','Hay una actualización de estado de tarjeta esperando. Abre la página y revisa el camino disponible.','Tu perfil de tarjeta tiene una nueva revisión de opciones. Mira los detalles antes de continuar.','La página de recomendación de tarjeta tiene un paso de confirmación. Revísalo para proceder.','Hay un resultado de revisión de tarjeta disponible. Abre la actualización y mira la siguiente indicación.','La página de opciones de tarjeta está lista para una revisión rápida. Continúa desde la pantalla de revisión.','El estado de la solicitud de tarjeta cambió a un paso de revisión. Abre la página para verificarlo.','Hay una nueva pantalla de detalles de tarjeta disponible. Revisa la información y sigue.','La revisión de tu perfil de tarjeta tiene otro paso abierto. Consulta la actualización para continuar.','La revisión de selección de tarjeta está lista. Abre la página y confirma la siguiente acción.'],
 'DE_CC':['Deine Kartenanfrage hat einen Prüfschritt bereit. Öffne die Seite und sieh dir die verfügbaren Optionen an.','Für dein Kartenprofil ist eine Statusprüfung verfügbar. Prüfe die Details bevor du fortfährst.','Deine Kartenoptionen sind zum Vergleich bereit. Öffne das Update und bestätige den nächsten Schritt.','Der Kartenempfehlungsprozess hat neue Details verfügbar. Öffne die Seite um weiterzumachen.','Deine Profilprüfung ist zur Bestätigung bereit. Öffne das Karten Update und sieh dir das Ergebnis an.','Ein Schritt zur Kartenauswahl ist jetzt verfügbar. Prüfe die Seite und fahre dort fort.','Deine Kartenanfrage ist beim nächsten Prüfpunkt angekommen. Öffne die Statusseite für Details.','Die Zusammenfassung der Kartenoptionen ist bereit. Bestätige die Angaben auf der Prüfseite.','Ein neues Update für dein Kartenprofil ist verfügbar. Prüfe die Optionen und fahre fort.','Dein Karten Treffer hat ein verfügbares Ergebnis. Öffne das Update und prüfe die Details.','Die Seite zur Anfrageprüfung ist bereit. Fahre dort fort und bestätige deine Kartendaten.','Ein Kartenstatus Update wartet. Öffne die Seite und prüfe den verfügbaren Weg.','Dein Kartenprofil hat eine neue Optionsprüfung. Sieh dir die Details an bevor du fortfährst.','Die Kartenempfehlungsseite hat einen Bestätigungsschritt. Prüfe ihn um weiterzumachen.','Ein Ergebnis der Kartenprüfung ist verfügbar. Öffne das Update und sieh den nächsten Hinweis.','Die Seite mit Kartenoptionen ist für eine schnelle Prüfung bereit. Fahre über die Prüfseite fort.','Der Status deiner Kartenanfrage wechselte zu einem Prüfschritt. Öffne die Seite zur Kontrolle.','Eine neue Detailseite zur Karte ist verfügbar. Prüfe die Informationen und fahre fort.','Deine Kartenprofilprüfung hat einen weiteren Schritt offen. Öffne das Update zum Fortfahren.','Die Prüfung der Kartenauswahl ist bereit. Öffne die Seite und bestätige die nächste Aktion.'],
 'JOB_ES':['Tu solicitud de empleo tiene una revisión lista. Abre la página para continuar con las opciones disponibles.','Hay una verificación disponible para tu perfil laboral. Revisa los detalles antes de avanzar.','Tus opciones de trabajo están listas para comparar. Abre la actualización y confirma el siguiente paso.','El flujo de recomendación laboral tiene nuevos detalles disponibles. Consulta la página para continuar.','La revisión de tu perfil está lista para confirmación. Abre la actualización laboral para ver el resultado.','Hay un paso de selección de vacante disponible ahora. Revisa la página y continúa desde ahí.','Tu solicitud pasó al siguiente punto de revisión. Abre la página de estado para ver detalles.','El resumen de opciones laborales está listo. Confirma la información en la página de revisión.','Hay una nueva actualización de perfil laboral disponible. Revisa las opciones y continúa.','Tu compatibilidad con la vacante tiene un resultado disponible. Abre la actualización para revisar los detalles.','La página de revisión de solicitud está lista. Continúa allí para confirmar la información de perfil.','Hay una actualización de estado laboral esperando. Abre la página y revisa el camino disponible.','Tu perfil laboral tiene una nueva revisión de opciones. Mira los detalles antes de continuar.','La página de recomendación laboral tiene un paso de confirmación. Revísalo para proceder.','Hay un resultado de revisión de vacante disponible. Abre la actualización y mira la siguiente indicación.','La página de opciones de trabajo está lista para una revisión rápida. Continúa desde la pantalla de revisión.','El estado de la postulación cambió a un paso de revisión. Abre la página para verificarlo.','Hay una nueva pantalla de detalles laborales disponible. Revisa la información y sigue.','La revisión de tu perfil laboral tiene otro paso abierto. Consulta la actualización para continuar.','La revisión de selección de empleo está lista. Abre la página y confirma la siguiente acción.'],
 'CAR_EN':['Your vehicle request has a review step ready. Open the page to continue with the available options.','A status check is available for your auto profile. Review the details before moving forward.','Your vehicle options are ready to compare. Open the update and confirm the next step.','The auto recommendation flow has new details available. Check the page to continue.','Your profile review is ready for confirmation. Open the vehicle update to see the result.','A vehicle selection step is available now. Review the page and continue from there.','Your auto request moved to the next review point. Open the status page for details.','The vehicle option summary is ready. Confirm the information on the review page.','A new auto profile update is available. Check the options and continue safely.','Your vehicle match has an available result. Open the update to review the details.','The request review page is ready. Continue there to confirm your auto information.','An auto status update is waiting. Open the page and check the available path.','Your vehicle profile has a fresh option review. See the details before continuing.','The auto recommendation page has a confirmation step. Review it to proceed.','A vehicle review result is available. Open the update and see the next instruction.','Your auto options page is ready for a quick check. Continue from the review screen.','The vehicle request status changed to a review step. Open the page to verify it.','A new auto detail screen is available. Review the information and keep going.','Your auto profile review has another step open. Check the update to continue.','The vehicle selection review is ready. Open the page and confirm the next action.'],
}
def family(vertical):
    if 'JOB' in vertical: return 'JOB_ES'
    if 'CAR' in vertical: return 'CAR_EN'
    if vertical.endswith('-DE'): return 'DE_CC'
    if vertical.endswith('-ES'): return 'ES_CC'
    return 'EN_CC'
def make_msg(vertical, idx, slot):
    fam=family(vertical)
    text=f"{HEADS[fam][idx]}\n\n{BODIES[fam][idx]}"
    text=no_dash(text)
    if fam in ('ES_CC','JOB_ES'): text=zw_text(text)
    out=deepcopy(slot)
    out['MESSAGE_ID']=idx+1
    out['TEXT']=text
    out['CTA_1']=CTAS[fam][idx]
    out.pop('CTA 1', None)
    for k in ['APPROVED','INVALID_FORMAT','REJECTED','ERROR','REJECTED_REASON']:
        out.pop(k, None)
    return out
async def approve(ctx, headers, template_id):
    statuses=[]
    for url in [f'https://api.jbfdigital.com.br/broadcast/messenger/{template_id}/approve', f'https://api.jbfdigital.com.br/broadcast/Messenger/{template_id}/approve']:
        r=await ctx.request.post(url, headers=headers)
        statuses.append(r.status)
        if r.status<300: return True,statuses
    return False,statuses
async def main():
    run_approvals=os.environ.get('RUN_APPROVALS','0')=='1'
    p,browser,ctx,page,rows,headers,post_url=await rollout.capture_rows_headers()
    out=[]; backups=[]
    backup_dir=BASE/'backups/sb-templates'/f'emergency-no-duplicates-{stamp()}'
    report={'started_at':now(),'backup_dir':str(backup_dir),'run_approvals':run_approvals,'templates':[]}
    try:
        by={r.get('NAME'):r for r in rows}
        for name in TARGETS:
            row=by.get(name)
            if not row:
                report['templates'].append({'template':name,'error':'not_found'}); continue
            msgs=sorted(rollout.parse_messages(row), key=lambda m:int(m.get('MESSAGE_ID') or 0))
            if not msgs:
                report['templates'].append({'template':name,'error':'no_messages'}); continue
            # use first 20 slots preserving link sequence; if fewer, cycle last slot
            slots=[]
            for i in range(20): slots.append(msgs[i] if i < len(msgs) else msgs[-1])
            vertical=parse_vertical(name)
            new_msgs=[make_msg(vertical,i,slots[i]) for i in range(20)]
            keys=[clean(m['TEXT']) for m in new_msgs]
            if len(set(keys))!=20:
                report['templates'].append({'template':name,'error':'generated_duplicate_guard_failed'}); continue
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir/(safe(name)+'-before.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
            payload=dict(row); payload['MESSAGES']=json.dumps(new_msgs,ensure_ascii=False,separators=(',',':'))
            resp=await ctx.request.post(post_url, headers=headers, data=json.dumps(payload,ensure_ascii=False))
            item={'template':name,'vertical':vertical,'before_count':len(msgs),'new_count':len(new_msgs),'post_status':resp.status,'duplicates_after':0,'approval_run':False}
            if resp.status>=300:
                item['error']=(await resp.text())[:300]
            else:
                # optional approval after fixing
                if run_approvals:
                    ok,st=await approve(ctx,headers,row.get('ID') or row.get('id'))
                    item['approval_run']=ok; item['approval_statuses']=st
            report['templates'].append(item)
        # fresh readback
        _,_,_,_,rows2,_,_=await rollout.capture_rows_headers()
        by2={r.get('NAME'):r for r in rows2}
        for item in report['templates']:
            name=item.get('template'); row=by2.get(name)
            if not row: continue
            msgs=sorted(rollout.parse_messages(row), key=lambda m:int(m.get('MESSAGE_ID') or 0))
            keys=[clean(m.get('TEXT') or '') for m in msgs]
            item['readback_count']=len(msgs); item['duplicates_after']=len(keys)-len(set(keys)); item['sample_first']=visible(msgs[0].get('TEXT','')).split('\n')[0] if msgs else ''
    finally:
        try: await browser.close()
        except Exception: pass
        try: await p.stop()
        except Exception: pass
    report['finished_at']=now()
    path=BASE/'reports'/f'utility-canary-no-duplicates-fix-{stamp()}.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(path),'templates':len(report['templates']),'posted_ok':sum(1 for t in report['templates'] if t.get('post_status',0)<300),'duplicates_after':sum(t.get('duplicates_after',0) for t in report['templates'])},ensure_ascii=False))
if __name__=='__main__': asyncio.run(main())
