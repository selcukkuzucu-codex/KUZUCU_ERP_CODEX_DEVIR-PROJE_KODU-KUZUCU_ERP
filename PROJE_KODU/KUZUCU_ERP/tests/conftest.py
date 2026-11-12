"""Legacy pre-login regression tests get an explicit test-only administrator login.
The new authorization tests remain unmodified and verify anonymous denial/CSRF.
"""
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def legacy_signed_in_client(request,monkeypatch):
    if request.module.__name__.endswith('test_v013_security_ui'):
        return
    orig=TestClient.__enter__
    def entered(client):
        result=orig(client)
        setup=result.get('/api/auth/setup')
        if setup.status_code==200 and setup.json()['needs_setup']:
            response=result.post('/api/auth/bootstrap',json={'username':'legacytester',
                'password':'LegacyTestPassword2026','display_name':'Test Yöneticisi'})
        else:
            response=result.post('/api/auth/login',json={'username':'legacytester','password':'LegacyTestPassword2026'})
        if response.status_code!=200:
            raise AssertionError(f'Test kimliği oluşturulamadı: {response.status_code} {response.text}')
        result.headers.update({'X-CSRF-Token':response.json()['csrf_token']})
        return result
    monkeypatch.setattr(TestClient,'__enter__',entered)
