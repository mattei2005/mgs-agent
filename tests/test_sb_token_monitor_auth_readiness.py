import asyncio
from contextlib import asynccontextmanager
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

SPEC = importlib.util.spec_from_file_location('token_monitor_auth', Path('/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py'))
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class AuthReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_waits_for_authenticated_request_and_does_not_erase_header(self):
        callback = lambda request: None
        lease_events = []

        @asynccontextmanager
        async def lease(path):
            lease_events.append('enter')
            yield
            lease_events.append('exit')

        def on(event, handler):
            nonlocal callback
            callback = handler

        async def goto(*args, **kwargs):
            callback(SimpleNamespace(url=mod.API_BASE + '/public', headers={'accept':'application/json'}))
            async def later():
                await asyncio.sleep(0)
                callback(SimpleNamespace(url=mod.API_BASE + '/user/validate', headers={'authorization':'fixture-only'}))
                callback(SimpleNamespace(url=mod.API_BASE + '/public', headers={'accept':'application/json'}))
            asyncio.create_task(later())

        calls = []
        async def get(url, headers, timeout):
            calls.append(url)
            self.assertEqual(headers['authorization'], 'fixture-only')
            rows = []
            if url == mod.API_BASE + '/company':
                rows = [{'name':name, 'publishers':[{'publisherId':name + '-publisher'}]} for name in sorted(mod.MGS_COMPANIES)]
            return SimpleNamespace(status=200, json=AsyncMock(return_value=rows))

        page = SimpleNamespace(on=on, goto=goto, locator=lambda _:SimpleNamespace(inner_text=AsyncMock(return_value='Accounts')))
        context = SimpleNamespace(new_page=AsyncMock(return_value=page), request=SimpleNamespace(get=get))
        browser = SimpleNamespace(new_context=AsyncMock(return_value=context), close=AsyncMock())
        playwright = SimpleNamespace(chromium=SimpleNamespace(launch=AsyncMock(return_value=browser)))

        @asynccontextmanager
        async def play():
            yield playwright

        with patch.object(mod, 'session_lease', lease), patch.object(mod, 'async_playwright', play):
            self.assertEqual(await mod.fetch_live(), ([], [], []))
        self.assertEqual(lease_events, ['enter', 'exit'])
        self.assertEqual(len(calls), 4)
        browser.close.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
