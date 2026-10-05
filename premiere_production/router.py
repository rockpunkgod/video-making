"""Small production facade over the upstream server. Never silently change backend."""
from typing import Protocol
from video_contracts import sha
from .configuration import CORE_TOOLS


class PremiereBackend(Protocol):
    name: str
    def inspect_sequence(self) -> dict: ...
    def execute(self, tool: str, arguments: dict) -> dict: ...


class UpstreamBackend:
    def __init__(self, client, name, advertised_tools, tool_mapping=None):
        self.client = client
        self.name = name
        self.tools = advertised_tools
        # UXP adapters must supply explicit tested mappings; generic CEP commands are
        # never silently substituted for a UXP operation.
        self.mapping = tool_mapping or ({t: t for t in CORE_TOOLS} if name == 'cep' else {})

    def execute(self, tool, arguments):
        mapped = self.mapping.get(tool)
        if tool not in CORE_TOOLS or mapped not in self.tools:
            raise ValueError(f'capability_unavailable:{self.name}:{tool}')
        return self.client.call(mapped, arguments)

    def inspect_sequence(self):
        return self.execute('get_active_sequence', {})


class BackendRouter:
    def __init__(self, client, preferred=None, uxp_mapping=None):
        capabilities = client.call('get_capabilities')
        connection = client.call('verify_premiere_connection')
        live = connection.get('backend')
        if connection.get('overall') != 'ready' or live not in ('cep', 'uxp'):
            raise ValueError('Current Premiere host/project/sequence not ready')
        if preferred and preferred != live:
            raise ValueError('Requested backend has no verified live connection')
        if live not in capabilities.get('backends', {}):
            raise ValueError('Live backend missing from capability report')
        tools = {t['name'] for t in client.tools()['tools']}
        self.capability_sha = sha(capabilities)
        self.connection = connection
        self.backend = UpstreamBackend(client, live, tools, uxp_mapping)
        self.receipts = []
        self.uncertain = False

    def execute(self, tool, inputs, *, sequence_id=None, verify=None):
        if self.uncertain:
            raise ValueError('Previous operation uncertain; inspect and reconcile before further edits')
        if sequence_id is not None:
            current = self.backend.inspect_sequence()
            if current.get('id', current.get('sequenceID')) != sequence_id:
                raise ValueError('Active sequence changed before edit')
        record = {'edit_id': f'edit-{len(self.receipts)+1:03d}', 'sequence_id': sequence_id,
                  'operation': tool, 'inputs': inputs, 'backend': self.backend.name,
                  'capability': self.capability_sha, 'verification': 'not_run'}
        try:
            result = self.backend.execute(tool, inputs)
            record['result'] = result
            record['verification'] = verify(result) if verify else 'accepted_not_creative_approval'
        except Exception as error:
            record['result'] = {'error_type': type(error).__name__, 'outcome': 'uncertain'}
            self.receipts.append(record)
            self.uncertain = True
            raise
        self.receipts.append(record)
        return result
