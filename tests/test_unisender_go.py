"""Offline contract tests; never contact UniSender or require a real key."""
import contextlib
import importlib.util
import io
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/unisender-go/scripts/unisender_go.py'
spec = importlib.util.spec_from_file_location('unisender_go', SCRIPT)
client = importlib.util.module_from_spec(spec)
if SCRIPT.exists():
    spec.loader.exec_module(client)

MESSAGE = {'message': {'from_email': 'robot@example.com', 'subject': 'Заказ',
    'body': {'plaintext': 'Заказ принят'}, 'recipients': [{'email': 'buyer@example.org'}],
    'idempotence_key': 'order-42-confirmation-v1'}}

class Transport:
    def __init__(self, data=None, error=None):
        self.data = data if data is not None else {'status': 'success', 'user_id': 42}
        self.error = error
        self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.data).encode())

class ClientTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory(prefix='unisender-test-home-')
        self.addCleanup(self.home.cleanup)
        self.home_patch = patch.object(client.Path, 'home', return_value=Path(self.home.name))
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.env = patch.dict(os.environ, {'UNISENDER_GO_API_KEY': 'test-secret-key'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.transport = Transport()
        self.net = patch.object(client, 'build_opener', return_value=self.transport, create=True)
        self.net.start()
        self.addCleanup(self.net.stop)

    def key_file(self, name='api-key', text='file-secret-key\n', mode=0o600):
        path = Path(self.home.name) / '.config/unisender-go' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        path.chmod(mode)
        return path

    def test_default_file_supplies_header_and_response_redaction(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        self.key_file()
        self.transport.data = {'status':'success','message':'echo file-secret-key'}
        result = client.call_api('system/info')
        self.assertEqual(self.transport.requests[0].get_header('X-api-key'), 'file-secret-key')
        self.assertNotIn('file-secret-key', json.dumps(result))

    def test_environment_overrides_default_file(self):
        self.key_file()
        client.call_api('system/info')
        self.assertEqual(self.transport.requests[0].get_header('X-api-key'), 'test-secret-key')

    def test_explicit_file_overrides_environment_for_project_selection(self):
        key_file = self.key_file('project-key', 'project-secret\n')
        client.call_api('system/info', key_file=str(key_file))
        self.assertEqual(self.transport.requests[0].get_header('X-api-key'), 'project-secret')

    def test_bad_key_files_fail_without_network_or_secret_output(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        for text, mode in [('',0o600), ('file-secret-key\nsecond-key',0o600),
                           ('file-secret-key',0o644), ('x'*4097,0o600)]:
            with self.subTest(mode=mode, length=len(text)):
                self.key_file(text=text, mode=mode)
                with self.assertRaises(client.ClientError) as caught:
                    client.call_api('system/info')
                self.assertNotIn('file-secret-key',str(caught.exception))
        self.assertEqual(self.transport.requests, [])

    def test_missing_explicit_file_does_not_fall_back_to_environment(self):
        with self.assertRaises(client.ClientError):
            client.call_api('system/info', key_file=str(Path(self.home.name)/'absent'))
        self.assertEqual(self.transport.requests, [])

    def test_preview_does_not_open_credential_file(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        # An unsafe or empty file must not prevent offline preparation.
        self.key_file(text='',mode=0o644)
        self.assertTrue(client.call_api('email/send',MESSAGE)['dry_run'])

    def test_cli_key_file_is_used_and_http_error_masks_its_value(self):
        key_file = self.key_file('project-key','file-secret-key\n')
        self.transport.error = HTTPError('url',401,'Unauthorized',{},
            io.BytesIO(b'{"status":"error","message":"bad file-secret-key"}'))
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = client.main(['call','system/info','--key-file',str(key_file)])
        self.assertEqual(code,1)
        self.assertNotIn('file-secret-key',err.getvalue())
        self.assertEqual(json.loads(err.getvalue())['http_status'],401)

    def test_config_reads_named_key_from_vault_note(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        path = self.key_file('vault-note', '# Credentials\nother: value\napi_key: "vault-secret" # Go\n')
        (path.parent/'config.json').write_text(json.dumps({'key_file':str(path)}))
        client.call_api('system/info')
        self.assertEqual(self.transport.requests[0].get_header('X-api-key'), 'vault-secret')

    def test_duplicate_named_keys_are_ambiguous(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        self.key_file(text='api_key: first\napi_key: second\n')
        with self.assertRaises(client.ClientError):
            client.call_api('system/info')
        self.assertEqual(self.transport.requests, [])

    def test_empty_named_key_does_not_consume_the_following_line(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        self.key_file(text='api_key:\nnotes\n')
        with self.assertRaises(client.ClientError):
            client.call_api('system/info')
        self.assertEqual(self.transport.requests, [])

    def test_preview_send_has_no_network_or_key_requirement(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        result = client.call_api('email/send', MESSAGE)
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['body'], MESSAGE)
        self.assertEqual(self.transport.requests, [])

    def test_hidden_domain_mutations_and_resubscription_default_to_preview(self):
        for method, body in [('domain/get-dns-records', {'domain':'example.com'}),
                             ('domain/get-sandbox-domain', {}),
                             ('domain/validate-dkim', {'domain':'example.com'}),
                             ('email/subscribe', {'from_email':'x@example.com','from_name':'X','to_email':'y@example.org'}),
                             ('confirmed-email/create', {'email':'x@example.com'})]:
            with self.subTest(method=method):
                self.assertTrue(client.call_api(method, body)['dry_run'])
        self.assertEqual(self.transport.requests, [])

    def test_read_uses_post_header_auth_and_utf8(self):
        client.call_api('system/info')
        req = self.transport.requests[0]
        self.assertEqual(req.full_url, 'https://goapi.unisender.ru/ru/transactional/api/v1/system/info.json')
        self.assertEqual(req.get_method(), 'POST')
        self.assertEqual(req.get_header('X-api-key'), 'test-secret-key')
        self.assertEqual(json.loads(req.data), {})
        self.assertNotIn('test-secret-key', req.full_url)

    def test_execute_preserves_idempotency_and_partial_failures(self):
        self.transport.data = {'status':'success','job_id':'job-1','emails':['buyer@example.org'],
                               'failed_emails': {'bad@example.org':'invalid'}}
        r = client.call_api('email/send', MESSAGE, execute=True)
        self.assertEqual(r['response']['job_id'], 'job-1')
        self.assertEqual(r['response']['failed_emails'], {'bad@example.org':'invalid'})
        self.assertEqual(json.loads(self.transport.requests[0].data), MESSAGE)

    def test_explicit_dry_run_wins_over_execute(self):
        self.assertTrue(client.call_api('email/send', MESSAGE, execute=True, dry_run=True)['dry_run'])
        self.assertEqual(self.transport.requests, [])

    def test_project_keys_and_active_key_are_redacted_recursively(self):
        # Synthetic credentials deliberately exercise recursive redaction.
        self.transport.data = {'status':'success','projects':[{'id':'p1','api_key':'new-secret',  # pragma: allowlist secret
            'nested':{'project_api_key':'another-secret'}}], 'message':'echo test-secret-key'}  # pragma: allowlist secret
        r = client.call_api('project/list')
        s = json.dumps(r)
        for key in ['new-secret','another-secret','test-secret-key']:
            self.assertNotIn(key,s)
        self.assertEqual(r['response']['projects'][0]['id'],'p1')

    def test_invalid_payloads_fail_before_network(self):
        cases = [([], 'system/info'), ({'api_key':'leak'},'system/info'),  # pragma: allowlist secret
                 ({'message':{'recipients':[]}},'email/send'),
                 ({'message':{'recipients':[{'email':'x@example.org'}]}},'email/send'),
                 ({'message':{**MESSAGE['message'],'recipients':[{'email':'x@example.org'}]*501}},'email/send'),
                 ({'message':{**MESSAGE['message'],'idempotence_key':'x'*65}},'email/send'),
                 ({'start_time':'2026-10-25 00:00:00','aggregate':'day_status','filter':{'job_id':'j'}},'event-dump/create')]
        for body, method in cases:
            with self.subTest(method=method,body=str(body)[:80]):
                with self.assertRaises(client.ClientError):
                    client.call_api(method, body, execute=True)
        self.assertEqual(self.transport.requests, [])

    def test_template_send_does_not_require_body_overrides(self):
        r = client.call_api('email/send', {'message':{'template_id':'template-id',
                            'recipients':[{'email':'x@example.org'}]}})
        self.assertTrue(r['dry_run'])

    def test_secret_not_accepted_in_payload_at_any_depth(self):
        with self.assertRaises(client.ClientError):
            client.call_api('email/send', {'message':{**MESSAGE['message'],'api_key':'oops'}})  # pragma: allowlist secret

    def test_classic_api_arbitrary_hosts_and_redirect_targets_are_rejected(self):
        for base in ['https://api.unisender.com/ru/api','http://goapi.unisender.ru/ru/transactional/api/v1',
                     'https://evil.example/ru/transactional/api/v1',
                     'https://goapi.unisender.ru/ru/transactional/api/v1?key=secret',
                     'https://user:pass@goapi.unisender.ru/ru/transactional/api/v1']:  # pragma: allowlist secret
            with self.subTest(base=base):
                with self.assertRaises(client.ClientError):
                    client.call_api('system/info', base_url=base)
        with self.assertRaises(HTTPError):
            client.NoRedirect().redirect_request(None, None, 302, 'Found', {}, 'https://evil.example')
        self.assertEqual(self.transport.requests, [])

    def test_dc_override_and_method_validation(self):
        client.call_api('system/ping.json', base_url='https://go2.unisender.ru/ru/transactional/api/v1/')
        self.assertIn('go2.unisender.ru',self.transport.requests[0].full_url)
        for method in ['../email/send','https://evil.example','callback/format','createCampaign','unsubscribed/set']:
            with self.subTest(method=method):
                with self.assertRaises(client.ClientError):
                    client.call_api(method)

    def test_http_error_retains_api_code_without_leaking_key(self):
        self.transport.error = HTTPError('url',401,'Unauthorized',{},
            io.BytesIO(b'{"status":"error","code":100,"message":"bad test-secret-key"}'))
        with self.assertRaises(client.ClientError) as caught:
            client.call_api('system/info')
        self.assertEqual(caught.exception.details['http_status'],401)
        self.assertEqual(caught.exception.details['response']['code'],100)
        self.assertNotIn('test-secret-key',str(caught.exception))

    def test_timeout_is_one_attempt_with_uncertain_send_outcome(self):
        self.transport.error = socket.timeout('test-secret-key')
        with self.assertRaises(client.ClientError) as caught:
            client.call_api('email/send', MESSAGE, execute=True)
        self.assertEqual(len(self.transport.requests),1)
        self.assertTrue(caught.exception.details['outcome_unknown'])
        self.assertNotIn('test-secret-key',str(caught.exception))

    def test_application_error_even_on_http_200_is_failure(self):
        self.transport.data = {'status':'error','code':204,'message':'No recipients accepted'}
        with self.assertRaises(client.ClientError) as caught:
            client.call_api('email/send',MESSAGE,execute=True)
        self.assertEqual(caught.exception.details['response']['code'],204)

    def test_non_json_response_is_not_a_success(self):
        self.transport.open = lambda request, timeout: io.BytesIO(b'<html>Proxy error</html>')
        with self.assertRaises(client.ClientError) as caught:
            client.call_api('email/send',MESSAGE,execute=True)
        self.assertTrue(caught.exception.details['outcome_unknown'])

    def test_request_size_limit_is_utf8_bytes(self):
        body={'message':{**MESSAGE['message'],'body':{'plaintext':'я'*5_000_001}}}
        with self.assertRaises(client.ClientError):
            client.call_api('email/send',body)
        self.assertEqual(self.transport.requests,[])

    def test_missing_key_does_not_print_environment(self):
        os.environ.pop('UNISENDER_GO_API_KEY')
        with self.assertRaises(client.ClientError) as caught:
            client.call_api('system/info')
        self.assertIn('UNISENDER_GO_API_KEY',str(caught.exception))
        self.assertEqual(self.transport.requests,[])

    def test_webhook_partial_update_accepts_optional_events_omission(self):
        r = client.call_api('webhook/set', {'url':'https://example.com/hook','status':'disabled'})
        self.assertTrue(r['dry_run'])

    def test_truncated_response_marks_send_outcome_unknown(self):
        self.transport.error = IncompleteRead(b'{"status":', 30)
        with self.assertRaises(client.ClientError) as caught:
            client.call_api('email/send', MESSAGE, execute=True)
        self.assertTrue(caught.exception.details['outcome_unknown'])
        self.assertEqual(len(self.transport.requests), 1)

    def test_cli_stdin_preview_and_partial_exit(self):
        with patch('sys.stdin',io.StringIO(json.dumps(MESSAGE))), contextlib.redirect_stdout(io.StringIO()) as out:
            code=client.main(['call','email/send','--data-file','-'])
        self.assertEqual(code,0)
        self.assertTrue(json.loads(out.getvalue())['dry_run'])
        self.transport.data={'status':'success','job_id':'j','failed_emails':{'x@example.org':'invalid'}}
        with patch('sys.stdin',io.StringIO(json.dumps(MESSAGE))), contextlib.redirect_stdout(io.StringIO()):
            code=client.main(['call','email/send','--data-file','-','--execute'])
        self.assertEqual(code,3)

if __name__ == '__main__':
    unittest.main()
