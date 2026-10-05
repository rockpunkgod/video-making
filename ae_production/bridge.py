"""Thin client of JUNKDOGE's public MCP surface. This is not a second AE bridge."""
import json
from urllib.request import Request, build_opener, ProxyHandler


class BridgeError(RuntimeError):
    pass


class JunkdogeClient:
    def __init__(self, endpoint='http://127.0.0.1:11488/mcp'):
        if not endpoint.startswith('http://127.0.0.1:') or not endpoint.endswith('/mcp'):
            raise ValueError('Only the local JUNKDOGE MCP endpoint is supported')
        self.endpoint=endpoint; self.session=None; self.seq=0
        self.protocol='2024-11-05'
        self.opener=build_opener(ProxyHandler({}))

    def rpc(self, method, params=None, timeout=60, notification=False):
        self.seq+=1
        payload={'jsonrpc':'2.0','method':method,'params':params or {}}
        if not notification: payload['id']=self.seq
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':self.protocol}
        if self.session: headers['Mcp-Session-Id']=self.session
        req=Request(self.endpoint,json.dumps(payload).encode(),headers)
        with self.opener.open(req,timeout=timeout) as response:
            if response.headers.get('Mcp-Session-Id'): self.session=response.headers['Mcp-Session-Id']
            raw=response.read().decode('utf-8')
        if notification: return None
        if raw.startswith('event:') or raw.startswith('data:'):
            chunks=[json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
            answer=next((x for x in chunks if x.get('id')==self.seq),None)
        else: answer=json.loads(raw)
        if not answer or 'error' in answer: raise BridgeError(str(answer))
        return answer['result']

    def initialize(self):
        result=self.rpc('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'video-os-v8','version':'0.1.0'}})
        self.protocol=result['protocolVersion']
        self.rpc('notifications/initialized',notification=True)
        return result

    def tools(self): return self.rpc('tools/list')

    def call(self,name,args=None,timeout=60):
        result=self.rpc('tools/call',{'name':name,'arguments':args or {}},timeout)
        texts=[json.loads(c['text']) for c in result.get('content',[]) if c.get('type')=='text']
        value=texts[0] if len(texts)==1 else texts
        if result.get('isError') or isinstance(value,dict) and value.get('ok') is False:
            raise BridgeError(json.dumps(value,ensure_ascii=False))
        return value
