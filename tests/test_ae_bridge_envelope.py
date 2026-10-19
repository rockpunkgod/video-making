import json
import unittest
from unittest.mock import patch, Mock
from pathlib import Path
from tempfile import TemporaryDirectory
from ae_production.bridge import JunkdogeClient,BridgeError

def envelope(*payloads,**extra):
    return {'content':[{'type':'text','text':json.dumps(p)} for p in payloads],**extra}

class AeBridgeEnvelopeTests(unittest.TestCase):
    def test_exited_host_reports_missing_host_without_json_decode_failure(self):
        from ae_production.authored_native import process
        with patch('ae_production.authored_native.subprocess.check_output',return_value=b''),self.assertRaisesRegex(RuntimeError,'host is not running'):
            process('AfterFX')

    def test_project_transition_does_not_enter_v011_undo_group(self):
        from ae_production.authored_native import Host
        host=object.__new__(Host);labels=[]
        def js(code,label=None):
            if label:raise BridgeError('UNDO_GROUP_CONFLICT: project-transition')
            return {'saved':True}
        host.js=js
        def mutate(label,operation,after):labels.append(label);return operation()
        host.mutate=mutate
        self.assertEqual(host.mutation_js('app.newProject();','Build guarded copy'),{'saved':True})
        self.assertEqual(labels,['Build guarded copy'])

    def test_only_identity_read_rebinds_after_registry_lag(self):
        from ae_production.authored_native import Host
        host=object.__new__(Host);host.native_name='AfterFX';host.kind='after_effects';host.folder=Path('.')
        host.c=Mock();host.js=Mock(side_effect=[BridgeError('SOURCE_PROJECT_CHANGED'),
            {'project_path':'','target_id':'none','dirty':False,'rendering':False}])
        with patch('ae_production.authored_native.process',return_value={'Id':123}),patch('ae_production.authored_native.time.sleep'):
            result=host.identity()
        self.assertEqual(result['process_id'],123);self.assertEqual(host.c.bind_current_project.call_count,2)
        self.assertTrue(all(c.args[0].startswith('var a=app.project.activeItem;') for c in host.js.call_args_list))

    def call(self,response):
        client=JunkdogeClient()
        with patch.object(client,'rpc',return_value=response):
            return client,client.call('ae_status')

    def test_legacy_single_payload(self):
        client,value=self.call(envelope({'ok':True,'pluginVersion':'0.10.8'}))
        self.assertEqual(value['pluginVersion'],'0.10.8')
        self.assertIsNone(client.last_execution_source)

    def test_new_provenance_does_not_replace_result(self):
        source={'instance_id':'instance-1','context_id':'context-1'}
        result={'ok':True,'content':'{"project_path":"trial.aep"}','contentType':'text'}
        client,value=self.call(envelope(result,{'execution_source':source}))
        self.assertEqual(value,result)
        self.assertEqual(client.last_execution_source,source)

    def test_error_still_raises_with_provenance(self):
        with self.assertRaises(BridgeError):
            self.call(envelope({'ok':False,'error':'unknown write outcome','recoveryId':'abc123'},{'execution_source':{'context_id':'one'}}))

    def test_other_content_is_not_silently_discarded(self):
        _,value=self.call(envelope({'ok':True},{'warning':'review required'},{'execution_source':{'context_id':'one'}}))
        self.assertEqual(value,[{'ok':True},{'warning':'review required'}])

    def test_ambiguous_provenance_fails(self):
        with self.assertRaises(BridgeError):
            self.call(envelope({'ok':True},{'execution_source':{'context_id':'one'}},{'execution_source':{'context_id':'two'}}))

    def test_legacy_does_not_request_workspace(self):
        client=JunkdogeClient();client.server_version='0.10.8'
        with patch.object(client,'call') as call:
            client.bind_current_project(123,'G:/trial')
            call.assert_not_called()

    def test_project_switch_binds_new_observed_project_without_replaying(self):
        client=JunkdogeClient();client.server_version='0.11.0'
        def instance(project):return {'instances':[{'pid':123,'state':'running','endpoint':client.endpoint,'instanceId':'host','projectPath':project}]}
        responses=[instance(None),{'context_id':'blank'},instance(None),instance('G:/trial.aep'),{'context_id':'trial'}]
        with TemporaryDirectory() as directory,patch.object(client,'call',side_effect=responses) as call:
            for _ in range(3):client.bind_current_project(123,directory)
            operations=[c.args[0] for c in call.call_args_list]
            self.assertEqual(operations,['ae_instances','ae_workspace','ae_instances','ae_instances','ae_workspace'])
            self.assertEqual(call.call_args_list[-1].args[1]['project_path'],'G:/trial.aep')
            self.assertEqual(json.loads((Path(directory)/'ae-workspace-bindings/trial.json').read_text('utf-8'))['context_id'],'trial')
        self.assertEqual(client.context_id,'trial')

    def test_ambiguous_running_host_cannot_bind(self):
        client=JunkdogeClient();client.server_version='0.11.0'
        row={'pid':123,'state':'running','endpoint':client.endpoint,'instanceId':'host','projectPath':None}
        with patch.object(client,'call',return_value={'instances':[row,row]}),self.assertRaises(BridgeError):
            client.bind_current_project(123,'G:/trial')

    def test_execution_uses_bound_context(self):
        client=JunkdogeClient();client.context_id='project-context'
        with patch.object(client,'rpc',return_value=envelope({'ok':True})) as rpc:
            client.call('ae_exec',{'code':'JSON.stringify({ok:true})'})
            self.assertEqual(rpc.call_args.args[1]['arguments']['context_id'],'project-context')

    def test_read_observation_text_preserves_payload_and_source(self):
        client=JunkdogeClient();source={'context_id':'writer-context'}
        response=envelope({'items':[]},{'execution_source':source})
        response['content'].append({'type':'text','text':'Observation for explicit reconciliation: obs_123'})
        with patch.object(client,'rpc',return_value=response):
            self.assertEqual(client.call('ae_read'),{'items':[]})
        self.assertEqual(client.last_execution_source,source)

if __name__=='__main__':unittest.main()
