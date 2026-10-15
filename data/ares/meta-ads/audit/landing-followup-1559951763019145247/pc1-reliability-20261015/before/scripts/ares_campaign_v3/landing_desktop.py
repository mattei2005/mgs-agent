"""Bounded native UI batches. No raw driver calls, navigation retries or PASS."""
from __future__ import annotations
import json
from pathlib import Path
import time


def identity(w):
    return int(w['pid']), int(w['window_id'])


def windows(call):
    out=call({'action':'list_windows'})
    if not isinstance(out.get('windows'),list):raise ValueError('window discovery failed')
    return out['windows']


def safe_windows(items):
    return [{k:w[k] for k in ('pid','window_id','app_name') if k in w} for w in items]


def all_elements(snapshot):
    if snapshot.get('elements_file'):
        raw=json.loads(Path(snapshot['elements_file']).read_text())
        if isinstance(raw,list):return raw
        if isinstance(raw,dict):return raw.get('elements',[])
    return snapshot.get('elements') or []


def escalates(out):
    return out.get('code')=='background_unavailable' or out.get('effect')=='suspected_noop'


def open_owned(call,url,base_window=None,on_owned=None):
    """Open once in a new private window; return for visual review, never PASS."""
    start=time.monotonic();before=windows(call);known={identity(w) for w in before}
    candidates=[w for w in before if w.get('app_name','').lower()=='chrome.exe' and (base_window is None or int(w['window_id'])==base_window)]
    if len(candidates)!=1:raise ValueError('unique base Chrome window required')
    base=candidates[0]
    call({'action':'capture','mode':'ax','pid':base['pid'],'window_id':base['window_id']})
    out=call({'action':'key','keys':'ctrl+shift+n'})
    after=windows(call)
    new=[w for w in after if w.get('app_name','').lower()=='chrome.exe' and identity(w) not in known]
    if not new and escalates(out):
        # Readback has proved the background hotkey did not create a window.
        call({'action':'capture','mode':'ax','pid':base['pid'],'window_id':base['window_id']})
        call({'action':'key','keys':'ctrl+shift+n','delivery_mode':'foreground','bring_to_front':True})
        after=windows(call);new=[w for w in after if w.get('app_name','').lower()=='chrome.exe' and identity(w) not in known]
    if len(new)!=1:raise ValueError('new window ambiguous; do not repeat open')
    owned=new[0]
    if not known.issubset({identity(w) for w in after}):raise ValueError('baseline changed; preserve all windows')
    proof={'state':'OWNED_BLANK_WINDOW','target':safe_windows([owned])[0],'baseline':safe_windows(before),'new_window_created':True,'url_submission_attempted':False}
    if on_owned:on_owned(proof)
    snap=call({'action':'capture','mode':'ax','pid':owned['pid'],'window_id':owned['window_id']})
    if not any('incognito' in str(e.get('label','')).lower() for e in all_elements(snap)):
        raise ValueError('new private window not confirmed; no typing')
    # A newly created private window has its empty address field focused.
    out=call({'action':'type','text':url})
    snap=call({'action':'capture','mode':'ax','pid':owned['pid'],'window_id':owned['window_id']})
    def typed(s):return url in json.dumps(all_elements(s),ensure_ascii=False)
    if not typed(snap) and escalates(out):
        out=call({'action':'type','text':url,'delivery_mode':'foreground','bring_to_front':True})
        snap=call({'action':'capture','mode':'ax','pid':owned['pid'],'window_id':owned['window_id']})
    if not typed(snap):raise ValueError('exact typed URL unverified; no submit or retry')
    proof['url_submission_attempted']=True
    if on_owned:on_owned(proof)
    out=call({'action':'key','keys':'return'})
    snap=call({'action':'capture','mode':'ax','pid':owned['pid'],'window_id':owned['window_id']})
    if out.get('code')=='background_unavailable':
        # Explicit refusal + fresh readback. Never retry an ambiguous Enter.
        call({'action':'key','keys':'return','delivery_mode':'foreground','bring_to_front':True})
        snap=call({'action':'capture','mode':'ax','pid':owned['pid'],'window_id':owned['window_id']})
    proof.update(state='OPENED_NOT_VISUALLY_VALIDATED',observed_url=url,opening_screenshot=snap.get('screenshot_path'),elapsed_seconds=round(time.monotonic()-start,3))
    if on_owned:on_owned(proof)
    return proof


def close_owned(call,proof,exclusive_reviewed=False):
    """One native Close click on a proven new exclusive window; verify once."""
    if exclusive_reviewed is not True:raise ValueError('agent review of exclusive owned window required')
    target=proof['target'];baseline=proof['baseline'];target_id=identity(target)
    base_ids={identity(w) for w in baseline}
    if target_id in base_ids or proof.get('new_window_created') is not True:raise ValueError('cannot close a baseline or unowned window')
    start=time.monotonic();before=windows(call);before_ids={identity(w) for w in before}
    if target_id not in before_ids:return {'state':'ALREADY_ABSENT_REVIEW_REQUIRED','close_input_sent':False,'target_absent':True}
    if not base_ids.issubset(before_ids):raise ValueError('baseline missing before close')
    if not any(identity(w)==target_id and w.get('app_name','').lower()=='chrome.exe' for w in before):raise ValueError('target browser mismatch')
    snap=call({'action':'capture','mode':'ax','pid':target['pid'],'window_id':target['window_id']})
    controls=[e for e in all_elements(snap) if e.get('role')=='Button' and e.get('label')=='Close' and len(e.get('bounds',[]))==4 and e['bounds'][1]<45 and 0<e['bounds'][3]<=45]
    if len(controls)!=1:raise ValueError('unique native window Close control required')
    # Native caption button, not page content, coordinates, hotkey or process kill.
    call({'action':'click','element':controls[0]['index']})
    after=windows(call);after_ids={identity(w) for w in after}
    if target_id in after_ids:raise ValueError('close uncertain; no retry; reconcile exact window')
    if not (before_ids-{target_id}).issubset(after_ids):raise ValueError('other windows changed; reconcile')
    shot=call({'action':'capture','mode':'vision','app':'screen'})
    if not shot.get('screenshot_path'):raise ValueError('closure screenshot absent; reconcile')
    return {'state':'CLOSED_NOT_PASS','new_tab_identity':target,'tab_closed_verified':True,'other_tabs_preserved':True,'closed_screenshot':shot['screenshot_path'],'close_input_sent':True,'close_method':'fresh_native_caption_button','elapsed_seconds':round(time.monotonic()-start,3),'remaining_windows':safe_windows(after)}
