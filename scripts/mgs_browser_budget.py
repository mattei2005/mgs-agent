"""MGS opt-in browser admission budget. Stdlib, process-safe, no secret/session access.

Hold a lease for the entire heavy workflow, not every nested helper. Each admitted
DTR workflow must use local_workers() for its internal Page concurrency. Managed
browser actions hold the same lease only while executing, never while idle.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
import errno
import fcntl
import json
import math
import os
from pathlib import Path
import random
import time

CONFIG = Path('/root/mgs-agent/data/browser-resource-budget.json')


def settings(config_path=CONFIG):
    data = json.loads(Path(config_path).read_text())
    if data.get('schema_version') != 1:
        raise RuntimeError('unsupported browser budget schema')
    for key, low, high in [('slots', 1, 32), ('local_workers', 1, 8)]:
        value = data.get(key)
        if type(value) is not int or not low <= value <= high:
            raise RuntimeError(f'invalid browser budget {key}')
    for key, low, high in [('wait_timeout_seconds', 0.01, 1800), ('poll_seconds', 0.01, 1)]:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise RuntimeError(f'invalid browser budget {key}')
    directory = Path(data.get('lock_dir', ''))
    batch_slots = data.get('batch_slots', max(1, data['slots'] - 1))
    if type(batch_slots) is not int or not 1 <= batch_slots <= data['slots']:
        raise RuntimeError('invalid browser budget batch_slots')
    data['batch_slots'] = batch_slots
    if not directory.is_absolute() or directory.is_symlink():
        raise RuntimeError('invalid browser budget lock directory')
    return data


def local_workers():
    return settings()['local_workers']


class Lease:
    def __init__(self, config_path=CONFIG, timeout=None, batch=False):
        self.data = settings(config_path)
        self.timeout = self.data['wait_timeout_seconds'] if timeout is None else timeout
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)) or not math.isfinite(self.timeout) or self.timeout < 0:
            raise ValueError('invalid lease timeout')
        self.fd = None
        self.slot = None
        self.wait_seconds = 0.0
        self.slot_count = self.data['batch_slots'] if batch else self.data['slots']
        self.directory = Path(self.data['lock_dir'])
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.directory.is_symlink() or self.directory.stat().st_uid != os.getuid():
            raise RuntimeError('untrusted browser budget lock directory')

    def try_acquire(self):
        if self.fd is not None:
            return True
        slots = list(range(self.slot_count))
        random.shuffle(slots)
        for slot in slots:
            flags = os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW
            fd = os.open(self.directory / f'slot-{slot}.lock', flags, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                os.close(fd)
                if exc.errno in (errno.EAGAIN, errno.EACCES):
                    continue
                raise
            self.fd, self.slot = fd, slot
            return True
        return False

    def release(self):
        if self.fd is not None:
            fd, self.fd, self.slot = self.fd, None, None
            os.close(fd)  # Kernel releases the lease even on process death.

    def acquire(self):
        started = time.monotonic()
        while not self.try_acquire():
            elapsed = time.monotonic() - started
            if elapsed >= self.timeout:
                raise TimeoutError(f'browser budget busy after {elapsed:.1f}s; no browser launched')
            time.sleep(min(self.data['poll_seconds'], self.timeout - elapsed))
        self.wait_seconds = time.monotonic() - started
        return self

    async def acquire_async(self):
        started = time.monotonic()
        while not self.try_acquire():
            elapsed = time.monotonic() - started
            if elapsed >= self.timeout:
                raise TimeoutError(f'browser budget busy after {elapsed:.1f}s; no browser launched')
            await asyncio.sleep(min(self.data['poll_seconds'], self.timeout - elapsed))
        self.wait_seconds = time.monotonic() - started
        return self


@contextmanager
def browser_lease(config_path=CONFIG, timeout=None):
    lease = Lease(config_path, timeout)
    try:
        lease.acquire()
        yield lease
    finally:
        lease.release()


@asynccontextmanager
async def async_browser_lease(config_path=CONFIG, timeout=None, batch=False):
    lease = Lease(config_path, timeout, batch=batch)
    try:
        await lease.acquire_async()
        yield lease
    finally:
        lease.release()


@contextmanager
def scheduled_browser_job(consumer, *, enabled=True, config_path=None, timeout=None):
    """Admit one complete scheduled browser workflow, preserving CLI exit codes.

    Disabled mode is for help/fixtures/non-browser maintenance. Telemetry is
    stderr-only and never includes arguments, page data or exception messages.
    """
    if not enabled:
        yield None
        return
    import sys
    label = Path(str(consumer)).name
    lease = Lease(CONFIG if config_path is None else config_path, timeout, batch=True)
    def emit(event, **values):
        print('BROWSER_BUDGET ' + json.dumps({'event': event, 'consumer': label, **values}, separators=(',', ':')), file=sys.stderr, flush=True)
    emit('queued', wait_timeout_seconds=lease.timeout)
    try:
        lease.acquire()
    except BaseException as exc:
        emit('timeout' if isinstance(exc, TimeoutError) else 'admission_failed', error_type=type(exc).__name__)
        lease.release()
        raise
    started = time.monotonic()
    outcome = 'success'
    emit('admitted', slot=lease.slot, wait_seconds=round(lease.wait_seconds, 3))
    try:
        yield lease
    except BaseException as exc:
        outcome = 'success' if isinstance(exc, SystemExit) and exc.code in (None, 0) else type(exc).__name__
        raise
    finally:
        lease.release()
        emit('released', run_seconds=round(time.monotonic() - started, 3), outcome=outcome)


@asynccontextmanager
async def governed_playwright():
    """Same async_playwright context contract, with one shared workflow lease."""
    from playwright.async_api import async_playwright
    async with async_browser_lease(batch=True):
        async with async_playwright() as playwright:
            yield playwright
