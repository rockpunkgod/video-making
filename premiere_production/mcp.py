"""Thin MCP transport; Premiere execution stays in leancoderkavy's installed server."""
import json
from urllib.request import Request, build_opener, ProxyHandler
from urllib.parse import urlsplit


class PremiereMcpError(RuntimeError):
    pass


class PremiereMcpClient:
    def __init__(self, endpoint, token):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1'
                or parsed.username is not None or parsed.password is not None
                or parsed.path != '/mcp' or parsed.query or parsed.fragment
                or parsed.port is None):
            raise ValueError('Premiere MCP must be local loopback')
        self.endpoint = endpoint
        self.token = token
        self.session = None
        self.sequence = 0
        self.protocol = '2024-11-05'
        self.opener = build_opener(ProxyHandler({}))

    def rpc(self, method, params=None, timeout=150, notification=False):
        # Callers serialize host work. A timeout is not retried: inspect host state first.
        self.sequence += 1
        payload = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
        if not notification:
            payload['id'] = self.sequence
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            'Authorization': 'Bearer ' + self.token,
            'MCP-Protocol-Version': self.protocol,
        }
        if self.session:
            headers['Mcp-Session-Id'] = self.session
        request = Request(self.endpoint, json.dumps(payload).encode(), headers)
        with self.opener.open(request, timeout=timeout) as response:
            if response.headers.get('Mcp-Session-Id'):
                self.session = response.headers['Mcp-Session-Id']
            raw = response.read().decode('utf-8')
        if notification:
            return None
        if raw.startswith('event:') or raw.startswith('data:'):
            chunks = [json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
            result = next((r for r in chunks if r.get('id') == self.sequence), None)
        else:
            result = json.loads(raw)
        if not result or result.get('id') != self.sequence or 'error' in result:
            raise PremiereMcpError(str(result))
        return result['result']

    def initialize(self):
        result = self.rpc('initialize', {
            'protocolVersion': self.protocol,
            'capabilities': {},
            'clientInfo': {'name': 'video-os-editorial', 'version': '0.1.0'},
        })
        self.protocol = result['protocolVersion']
        self.rpc('notifications/initialized', notification=True)
        return result

    def tools(self):
        return self.rpc('tools/list')

    def call(self, name, args=None, timeout=150):
        result = self.rpc('tools/call', {'name': name, 'arguments': args or {}}, timeout)
        texts = []
        for block in result.get('content', []):
            if block.get('type') != 'text':
                continue
            try:
                texts.append(json.loads(block['text']))
            except json.JSONDecodeError:
                texts.append(block['text'])
        value = result.get('structuredContent', texts[0] if len(texts) == 1 else texts)
        failed = isinstance(value, dict) and (value.get('success') is False or value.get('ok') is False)
        if result.get('isError') or failed:
            raise PremiereMcpError(json.dumps(value, ensure_ascii=False))
        if isinstance(value, dict) and value.get('ok') is True and 'data' in value:
            return value['data']
        return value
