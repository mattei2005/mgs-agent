"""Regression coverage for Messenger report body-cache eviction recovery."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock


spec = importlib.util.spec_from_file_location(
    'messenger_sync',
    Path(__file__).resolve().parents[1] / 'scripts/sync-sb-messenger-revenue-sheet.py',
)
if spec is None or spec.loader is None:
    raise RuntimeError('Messenger sync module unavailable')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ReportCaptureTests(unittest.IsolatedAsyncioTestCase):
    def route(self, status=201, data=None):
        payload = {'publishers': ['original'], 'initialDate': '2026-10-22',
                   'finalDate': '2026-10-28', 'currency': 'BRL'}
        response = SimpleNamespace(status=status, headers={'retry-after': '60'},
                                   json=AsyncMock(return_value=data), dispose=AsyncMock())
        return SimpleNamespace(
            request=SimpleNamespace(method='POST', post_data_json=payload),
            fetch=AsyncMock(return_value=response), fulfill=AsyncMock(),
            abort=AsyncMock(), continue_=AsyncMock(),
        ), response, payload

    async def test_native_request_is_fetched_once_and_fulfilled(self):
        rows = [{'PROFILE_NAME': 'Example', 'REVENUE': '1.25'}]
        route, response, original = self.route(data=rows)
        future = asyncio.get_running_loop().create_future()
        payload = {}
        await helper.capture_report_route(route, future, payload)
        self.assertEqual(await future, rows)
        self.assertEqual(payload, original)
        route.fetch.assert_awaited_once_with(max_redirects=0, max_retries=0, timeout=120000)
        route.fulfill.assert_awaited_once_with(response=response)
        response.dispose.assert_awaited_once()
        route.abort.assert_not_awaited()

    async def test_rate_limit_is_not_replayed(self):
        route, response, _ = self.route(status=429)
        future = asyncio.get_running_loop().create_future()
        await helper.capture_report_route(route, future, {})
        with self.assertRaisesRegex(RuntimeError, 'HTTP 429; Retry-After=60'):
            await future
        route.fetch.assert_awaited_once()
        route.fulfill.assert_not_awaited()
        response.json.assert_not_awaited()
        route.abort.assert_awaited_once()
        response.dispose.assert_awaited_once()

    async def test_invalid_json_aborts_without_replay(self):
        route, response, _ = self.route()
        response.json.side_effect = ValueError('invalid JSON')
        future = asyncio.get_running_loop().create_future()
        await helper.capture_report_route(route, future, {})
        with self.assertRaisesRegex(ValueError, 'invalid JSON'):
            await future
        route.fetch.assert_awaited_once()
        route.fulfill.assert_not_awaited()
        response.dispose.assert_awaited_once()

    async def test_preflight_and_completed_future_continue_unchanged(self):
        for completed in (False, True):
            route, _, _ = self.route()
            future = asyncio.get_running_loop().create_future()
            if completed:
                future.set_result([])
            else:
                route.request.method = 'OPTIONS'
            await helper.capture_report_route(route, future, {})
            route.continue_.assert_awaited_once()
            route.fetch.assert_not_awaited()

    async def test_invalid_request_fails_before_network(self):
        route, _, _ = self.route()
        route.request.post_data_json = []
        future = asyncio.get_running_loop().create_future()
        await helper.capture_report_route(route, future, {})
        with self.assertRaisesRegex(RuntimeError, 'request is not an object'):
            await future
        route.fetch.assert_not_awaited()
        route.abort.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
