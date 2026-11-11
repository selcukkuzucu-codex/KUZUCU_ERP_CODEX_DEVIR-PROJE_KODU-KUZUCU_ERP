from fastapi.testclient import TestClient
from app.main import app

def test_preview_does_not_create_animals():
    with TestClient(app) as client:
        before=len(client.get('/api/animals').json())
        res=client.post('/api/imports/animals/preview', content='kupe_no;irk;giris_tarihi;giris_kilosu;padok\nDEMO-01;Simental;2026-10-01;350;P01\nDEMO-01;Simental;2026-10-01;350;P01\n'.encode(),headers={'content-type':'text/csv'})
        assert res.status_code==200,res.text
        assert res.json()['counts']['duplicate_in_file']==1
        assert len(client.get('/api/animals').json())==before
