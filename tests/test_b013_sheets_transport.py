"""Regression coverage for Sheets transport failures in the live B013 monitor."""
import io
import json
import socket
import unittest
import urllib.error
from email.message import Message
from unittest.mock import patch

from test_b013_profile_removal_alert import load_monitor_module


class SheetsResponse(io.BytesIO):
    status = 200


class B013SheetsTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_monitor_module()

    def response(self):
        return SheetsResponse(json.dumps({'values': [['healthy']]}).encode())

    def test_transport_errors_retry_then_recover(self):
        errors = [
            urllib.error.URLError(ConnectionResetError(104, 'Connection reset by peer')),
            socket.timeout('timed out'),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with patch('urllib.request.urlopen', side_effect=[error, self.response()]) as request:
                    with patch('time.sleep') as sleep:
                        result = self.mod.sheets_request('GET', '/test', 'fixture-token')
                self.assertEqual(result, (200, {'values': [['healthy']]}))
                self.assertEqual(request.call_count, 2)
                sleep.assert_called_once_with(1)

    def test_transport_exhaustion_preserves_cause(self):
        error = urllib.error.URLError(ConnectionResetError(104, 'Connection reset by peer'))
        with patch('urllib.request.urlopen', side_effect=error) as request:
            with patch('time.sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError, 'Sheets transport failed after 3 attempts: URLError') as raised:
                    self.mod.sheets_request('GET', '/test', 'fixture-token')
        self.assertIs(raised.exception.__cause__, error)
        self.assertEqual(request.call_count, 3)
        self.assertEqual([call.args for call in sleep.call_args_list], [(1,), (2,)])

    def test_http_503_retry_then_recover(self):
        error = urllib.error.HTTPError('https://example.invalid', 503, 'Unavailable', Message(), io.BytesIO(b'{}'))
        with patch('urllib.request.urlopen', side_effect=[error, self.response()]) as request:
            with patch('time.sleep'):
                result = self.mod.sheets_request('GET', '/test', 'fixture-token')
        self.assertEqual(result[0], 200)
        self.assertEqual(request.call_count, 2)

    def test_http_403_is_not_retried(self):
        error = urllib.error.HTTPError('https://example.invalid', 403, 'Forbidden', Message(), io.BytesIO(b'{}'))
        with patch('urllib.request.urlopen', side_effect=error) as request:
            with patch('time.sleep') as sleep:
                result = self.mod.sheets_request('GET', '/test', 'fixture-token')
        self.assertEqual(result, (403, {}))
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
