"""Coordinate existing Zeus SB read sessions without changing login credentials.
Reuse one browser for a bounded SPA refresh; preserve exact company scope gates.
"""
from __future__ import annotations
import asyncio
import fcntl
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path


@asynccontextmanager
async def session_lease(state_path, timeout=90):
    lock = Path(str(state_path) + '.session.lock')
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        started = time.monotonic()
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - started >= timeout:
                    raise RuntimeError('SB session lease timeout; no concurrent state writer started')
                await asyncio.sleep(0.5)
        yield
    finally:
        os.close(fd)


def auth_wall(page):
    # Do not print URLs: Auth0 URLs may contain credential/session material.
    url = str(page.url).split('?', 1)[0].lower()
    return '/login' in url or 'auth0.com/' in url or '/authorize' in url


def request_headers(headers):
    h = {k: v for k, v in headers.items() if k.lower() in {'authorization', 'accept', 'content-type'}}
    h.update({'origin': 'https://app.smartbiddingdigital.com', 'referer': 'https://app.smartbiddingdigital.com/'})
    return h


async def company_probe(ctx, page, headers, ready):
    if auth_wall(page):
        raise RuntimeError('SB canonical login required; existing session reached authentication wall; no credential changed')
    try:
        await asyncio.wait_for(ready.wait(), timeout=12)
    except asyncio.TimeoutError:
        if auth_wall(page):
            raise RuntimeError('SB canonical login required; no authenticated API header; no credential changed') from None
        raise RuntimeError('SB authenticated-header timeout; scope not fetched') from None
    h = request_headers(headers)
    endpoint = 'https://api.jbfdigital.com.br/company'
    response = await ctx.request.get(endpoint, headers=h, timeout=120000)
    if response.status != 401:
        return response, h
    # One real read-only SPA reload in the SAME context, not three identical
    # cold starts. Auth0 itself handles its existing-session refresh if valid.
    old_auth = next((v for k, v in h.items() if k.lower() == 'authorization'), None)
    headers.clear(); ready.clear()
    await page.reload(wait_until='domcontentloaded', timeout=60000)
    if auth_wall(page):
        raise RuntimeError('SB canonical login required after401; session expired; no credential changed')
    try:
        await asyncio.wait_for(ready.wait(), timeout=12)
    except asyncio.TimeoutError:
        raise RuntimeError('SB canonical login required after401; SPA did not restore authenticated headers') from None
    h = request_headers(headers)
    response = await ctx.request.get(endpoint, headers=h, timeout=120000)
    if response.status == 401:
        unchanged = old_auth == next((v for k, v in h.items() if k.lower() == 'authorization'), None)
        reason = 'SPA did not advance authentication' if unchanged else 'refreshed authentication rejected'
        raise RuntimeError('SB canonical login required after bounded refresh: ' + reason + '; no credential changed')
    return response, h
