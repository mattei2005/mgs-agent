"""Offline native-path probes. Synthetic credentials only; network and writes blocked."""
import base64
import contextlib
import inspect
import json
import time
from dataclasses import replace
from unittest.mock import patch

import agent.credential_pool as cp
from hermes_cli import auth, auth_codex

def jwt(exp, marker='synthetic'):
    payload={'sub':'synthetic-user','https://api.openai.com/auth':{'chatgpt_account_id':'synthetic-account'},'iat':exp-864000,'exp':exp,'jti':marker}
    b=lambda x:base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip('=')
    return b({'alg':'none'})+'.'+b(payload)+'.synthetic'

def entry(access=None, refresh='synthetic-refresh-old'):
    return cp.PooledCredential.from_dict('openai-codex',{'id':'probe1','label':'offline-probe','auth_type':'oauth','source':'manual:device_code','priority':0,'access_token':access or jwt(int(time.time())-60),'refresh_token':refresh,'last_refresh':'2026-10-06T02:49:08Z'})

def no_io(*a,**kw):
    raise AssertionError('Unexpected real IO blocked')

out=[]
with contextlib.ExitStack() as stack:
    stack.enter_context(patch('socket.socket.connect',side_effect=no_io))
    stack.enter_context(patch.object(cp,'_auth_store_lock',side_effect=lambda *a,**k:contextlib.nullcontext()))
    stack.enter_context(patch.object(cp,'_load_auth_store',return_value={'version':1,'providers':{},'credential_pool':{}}))
    stack.enter_context(patch.object(cp,'_save_auth_store',side_effect=no_io))
    stack.enter_context(patch.object(cp.CredentialPool,'_persist',return_value=None))
    stack.enter_context(patch.object(cp.CredentialPool,'_sync_device_code_entry_to_auth_store',return_value=None))
    stack.enter_context(patch.object(cp,'read_credential_pool',return_value=[]))
    # Baseline: normal expiry with successful upstream refresh must recover.
    e=entry();pool=cp.CredentialPool('openai-codex',[e])
    with patch.object(auth,'refresh_codex_oauth_pure',return_value={'access_token':jwt(int(time.time())+864000,'rotated'),'refresh_token':'synthetic-refresh-new','last_refresh':'2026-10-16T03:40:00Z'}) as post:
        selected=pool.select()
        out.append({'case':'normal_expiry_successful_refresh','refresh_calls':post.call_count,'selected':selected is not None,'rotated':bool(selected and selected.refresh_token=='synthetic-refresh-new')})
    # Repro: a peer rotated the same row and persisted it. This process is stale.
    e=entry();rotated=replace(e,access_token=jwt(int(time.time())+864000,'peer'),refresh_token='synthetic-peer-refresh',last_refresh='2026-10-16T03:40:00Z')
    pool=cp.CredentialPool('openai-codex',[e])
    with patch.object(cp,'read_credential_pool',return_value=[rotated.to_dict()]),patch.object(auth,'refresh_codex_oauth_pure',side_effect=auth.AuthError('synthetic: already consumed',provider='openai-codex',code='refresh_token_reused',relogin_required=True)) as post,patch.object(pool,'_clear_terminal_tokens_state',return_value=None):
        selected=pool._refresh_entry(e,force=False)
        out.append({'case':'peer_rotated_row_stale_process','refresh_calls':post.call_count,'should_be_zero':post.call_count==0,'adopted_peer':bool(selected and selected.refresh_token==rotated.refresh_token),'state':pool._entries[0].last_status if pool._entries else 'removed'})
    # Repro: actual provider wording with the known OpenAI invalidated code.
    e=entry();pool=cp.CredentialPool('openai-codex',[e])
    err=auth.AuthError('Codex token refresh failed: Your session has ended. Please log in again.',provider='openai-codex',code='refresh_token_invalidated',relogin_required=True)
    with patch.object(auth,'refresh_codex_oauth_pure',side_effect=err):
        selected=pool.select()
        state=pool._entries[0]
        out.append({'case':'refresh_token_invalidated_classification','selected':selected is not None,'terminal_classifier':auth._is_terminal_codex_oauth_refresh_error(err),'state':state.last_status,'stored_reason':state.last_error_reason,'stored_message':state.last_error_message})
    # Repro: low-level fallback exposes an expired/exhausted row after pool refusal.
    row=entry().to_dict();row['last_status']='exhausted';row['last_status_at']=time.time()
    with patch.object(auth,'read_credential_pool',return_value=[row]):
        token,url=auth_codex._pool_codex_credential()
        out.append({'case':'expired_exhausted_fallback','returns_expired':bool(token and auth._codex_access_token_is_expiring(token,0))})
print(json.dumps({'fixture':'synthetic-only; native code; real HTTP/filesystem mutation blocked','results':out},indent=2))
