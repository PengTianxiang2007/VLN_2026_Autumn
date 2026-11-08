"""CPU-only checks; uses fake credentials and never contacts a provider."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from scripts.run_human_route_choice_glm import AccountBlocked,ENDPOINT,redact,request_model,terminal_account_error


class CredentialTransportTests(unittest.TestCase):
    def config(self):
        return dict(request_deadline_seconds=100,request_timeout_seconds=10,max_network_attempts=8,
                    retry_backoff_cap_seconds=10,retry_backoff_base_seconds=2,retry_jitter_seconds=0)

    def test_redact_complete_key_and_components(self):
        key='fake_identifier.fake_secret'
        value=redact('key '+key+' id fake_identifier secret fake_secret',key)
        self.assertNotIn(key,value);self.assertNotIn('fake_identifier',value);self.assertNotIn('fake_secret',value)

    def test_account_error_is_distinct_from_transient_rate_limit(self):
        self.assertTrue(terminal_account_error(429,dict(code='1113')))
        self.assertTrue(terminal_account_error(401,{}))
        self.assertFalse(terminal_account_error(429,dict(code='1302')))

    def test_balance_failure_is_logged_without_secret_and_never_retried(self):
        key='canary_id.canary_secret'
        body=json.dumps(dict(error=dict(code='1113',message='Unavailable '+key))).encode()
        error=urllib.error.HTTPError(ENDPOINT,429,'limited',{},io.BytesIO(body))
        with tempfile.TemporaryDirectory() as d,patch('urllib.request.build_opener') as opener,patch('time.sleep') as sleep:
            opener.return_value.open.side_effect=error
            target=Path(d)/'transport.jsonl'
            with self.assertRaises(AccountBlocked):request_model(ENDPOINT,dict(model='glm-5.3-flash'),key,self.config(),target)
            self.assertEqual(opener.return_value.open.call_count,1);sleep.assert_not_called()
            self.assertNotIn(key,target.read_text());self.assertNotIn('canary_secret',target.read_text())

    def test_reflected_key_is_removed_before_response_can_be_saved(self):
        key='canary_id.canary_secret'
        stream='data: '+json.dumps(dict(model='glm-5.3-flash',choices=[dict(delta=dict(content=key),finish_reason='stop')]))+'\n\ndata: [DONE]\n'
        with tempfile.TemporaryDirectory() as d,patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=io.BytesIO(stream.encode())
            target=Path(d)/'transport.jsonl'
            result=request_model(ENDPOINT,dict(model='glm-5.3-flash'),key,self.config(),target)
            self.assertNotIn(key,json.dumps(result));self.assertNotIn(key,target.read_text())
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(request.headers['Authorization'],'Bearer '+key)
            self.assertNotIn(key,request.data.decode())


if __name__=='__main__':unittest.main()
