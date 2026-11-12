from fastapi.testclient import TestClient
from app.main import app

def test_reports_and_sap_page():
    with TestClient(app) as client:
        r=client.post('/api/reports/query',json={'query':'stok durumunu göster'})
        assert r.status_code==200 and r.json()['title']=='Stok durumu'
        r=client.post('/api/reports/query',json={'query':'aktif hayvanları listele'})
        assert r.status_code==200 and 'rows' in r.json()
        r=client.post('/api/reports/query',json={'query':'yarın hava nasıl'})
        assert r.status_code==422
        r=client.post('/api/reports/export.csv',json={'query':'parselleri listele'})
        assert r.status_code==200 and r.content.startswith(b'\xef\xbb\xbf')
        r=client.get('/')
        assert r.status_code==200 and 'KUZUCU ERP' in r.text and 'Entegrasyonlar' in r.text
