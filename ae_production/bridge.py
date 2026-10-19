"""Thin client of JUNKDOGE's public MCP surface. This is not a second AE bridge."""
import json
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler


class BridgeError(RuntimeError):
    pass


class JunkdogeClient:
    def __init__(self, endpoint='http://127.0.0.1:11488/mcp'):
        if not endpoint.startswith('http://127.0.0.1:') or not endpoint.endswith('/mcp'):
            raise ValueError('Only the local JUNKDOGE MCP endpoint is supported')
        self.endpoint=endpoint; self.session=None; self.seq=0
        self.protocol='2024-11-05'
        self.last_execution_source=None
        self.context_id=None
        self.server_version=None
        self.bound_project=None
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
        self.server_version=result.get('serverInfo',{}).get('version')
        self.rpc('notifications/initialized',notification=True)
        return result

    def tools(self): return self.rpc('tools/list')

    def bind_current_project(self,pid,work_dir):
        """Bind the observed host for v0.11; native identity is still read next.

        This never opens a project or retries an AE operation. HostOwnership
        independently checks whether the observed project is the expected one.
        """
        if not self.server_version or tuple(int(x) for x in self.server_version.split('.')[:2])<(0,11):return
        rows=self.call('ae_instances',{'action':'list'})['instances']
        rows=[r for r in rows if r.get('pid')==pid and r.get('state')=='running' and r.get('endpoint')==self.endpoint]
        if len(rows)!=1:raise BridgeError('Expected one running AE instance for the observed host PID')
        row=rows[0];project=row.get('projectPath')
        key=(row['instanceId'],project)
        if self.context_id and self.bound_project==key:return
        args={'action':'bind','instance_id':row['instanceId'],'access':'write','work_dir':str(work_dir)}
        if project:args['project_path']=project
        result=self.call('ae_workspace',args)
        context=result.get('context_id')
        if not context:raise BridgeError('AE workspace did not return a context binding: '+json.dumps(result))
        # A transport failure can outlive this Python process. Retain the exact
        # public binding so the same writer can later inspect and reconcile it.
        evidence=Path(work_dir)/'ae-workspace-bindings'
        evidence.mkdir(parents=True,exist_ok=True)
        record=evidence/(context.rsplit(':',1)[-1]+'.json')
        with record.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
        self.context_id=context;self.bound_project=key

    def call(self,name,args=None,timeout=60):
        args=dict(args or {})
        if self.context_id and name in ('ae_exec','ae_execRecover','ae_read','ae_previewFrame','ae_checkpoint','ae_revert','ae_validateExpressions','ae_nativeExec'):
            args.setdefault('context_id',self.context_id)
        result=self.rpc('tools/call',{'name':name,'arguments':args},timeout)
        texts=[]
        for block in result.get('content',[]):
            if block.get('type')!='text':continue
            value=block['text']
            # v0.11 reads add a plain-text observation identifier beside the
            # structured payload. It is not an execution failure or payload.
            if name in ('ae_read','ae_previewFrame') and value.startswith('Observation for explicit reconciliation: obs_'):
                continue
            texts.append(json.loads(value))
        # v0.11 appends routing provenance as a separate content block. Keep
        # it available without changing the operation's return-value shape.
        sources=[x['execution_source'] for x in texts if isinstance(x,dict) and set(x)=={'execution_source'}]
        if len(sources)>1:raise BridgeError('Ambiguous AE execution-source metadata')
        self.last_execution_source=sources[0] if sources else None
        payloads=[x for x in texts if not (isinstance(x,dict) and set(x)=={'execution_source'})]
        value=payloads[0] if len(payloads)==1 else payloads
        if result.get('isError') or any(isinstance(x,dict) and x.get('ok') is False for x in payloads):
            raise BridgeError(json.dumps(value,ensure_ascii=False))
        return value
