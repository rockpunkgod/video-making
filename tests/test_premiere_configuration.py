import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from premiere_production.configuration import CORE_TOOLS, configure_codex
from premiere_production.mcp import PremiereMcpClient, PremiereMcpError


class PremiereConfigurationTests(unittest.TestCase):
    def test_long_export_stream_may_start_with_keepalive_comments(self):
        import io
        client = PremiereMcpClient('http://127.0.0.1:11489/mcp', 'test-only')
        response = io.BytesIO(b': ping\n\nevent: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"written":true}}\n\n')
        response.headers = {}
        with patch.object(client.opener, 'open', return_value=response) as opened:
            self.assertEqual(client.rpc('tools/call'), {'written':True})
            self.assertEqual(opened.call_count, 1)

    def test_config_preserves_other_servers_and_environment_and_is_idempotent(self):
        import tomllib
        original = ('model = "existing-model"\n[mcp_servers.other]\ncommand = "other"\n'
                    '[mcp_servers.premiere-pro]\ncommand = "node"\n'
                    'args = ["local/runtime/index.js"]\nenabled_tools = [\n"unsafe_script"\n]\n'
                    'tool_timeout_sec = 10\n[mcp_servers.premiere-pro.env]\n'
                    'PREMIERE_TEMP_DIR = "private-bridge"\n')
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.toml'
            backup = Path(directory) / 'backup.toml'
            config.write_text(original, encoding='utf-8')
            configure_codex(config, backup=backup)
            first = config.read_text(encoding='utf-8')
            configure_codex(config, backup=backup)
            self.assertEqual(config.read_text(encoding='utf-8'), first)
            self.assertEqual(backup.read_text(encoding='utf-8'), original)
            parsed = tomllib.loads(first)
            self.assertEqual(parsed['mcp_servers']['other']['command'], 'other')
            server = parsed['mcp_servers']['premiere-pro']
            self.assertEqual(server['env']['PREMIERE_TEMP_DIR'], 'private-bridge')
            self.assertEqual(server['enabled_tools'], list(CORE_TOOLS))
            self.assertEqual(server['tool_timeout_sec'], 180)

    def test_missing_registration_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.toml'
            config.write_text('model = "existing"', encoding='utf-8')
            with self.assertRaises(ValueError):
                configure_codex(config, backup=Path(directory) / 'backup')
            self.assertEqual(config.read_text(), 'model = "existing"')

    def test_remote_endpoint_rejected(self):
        for endpoint in ('http://evil.example/mcp', 'http://127.0.0.1:80@evil.example/mcp'):
            with self.assertRaises(ValueError):
                PremiereMcpClient(endpoint, 'test-only')

    def test_structured_failure_is_failure_even_without_iserror(self):
        client = PremiereMcpClient('http://127.0.0.1:11489/mcp', 'test-only')
        with patch.object(client, 'rpc', return_value={'structuredContent': {'ok': False, 'error': 'caption unsupported'}}):
            with self.assertRaises(PremiereMcpError):
                client.call('read_sequence_captions')

    def test_accepted_caption_is_not_promoted_to_verified(self):
        client = PremiereMcpClient('http://127.0.0.1:11489/mcp', 'test-only')
        payload = {'accepted': True, 'verified': False, 'renderVerified': False}
        with patch.object(client, 'rpc', return_value={'structuredContent': {'ok': True, 'data': payload}}):
            self.assertEqual(client.call('create_caption_track'), payload)

    def test_error_text_and_legacy_failure_not_ignored(self):
        client = PremiereMcpClient('http://127.0.0.1:11489/mcp', 'test-only')
        for result in ({'isError': True, 'content': [{'type': 'text', 'text': 'No preset found'}]},
                       {'content': [{'type': 'text', 'text': '{"success": false}'}]}):
            with patch.object(client, 'rpc', return_value=result):
                with self.assertRaises(PremiereMcpError):
                    client.call('validate_export_preset')


if __name__ == '__main__':
    unittest.main()
