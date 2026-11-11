from fastapi.testclient import TestClient
from app.main import app

def test_basic_workflow():
    with TestClient(app) as client:
        pen=client.post('/api/pens',json={'code':'PILOT-P1','capacity':1});assert pen.status_code==201
        p=pen.json()['id']
        a=client.post('/api/animals',json={'ear_tag':'PILOT-1','breed':'Simental','arrival_date':'2026-10-01','entry_weight_kg':'320','pen_id':p})
        assert a.status_code==201
        again=client.post('/api/animals',json={'ear_tag':'PILOT-1','breed':'Simental','arrival_date':'2026-10-01','entry_weight_kg':'320','pen_id':p})
        assert again.status_code==409
        assert client.post(f"/api/animals/{a.json()['id']}/weighings",json={'measured_at':'2026-11-01','weight_kg':'353'}).status_code==201
        item=client.post('/api/items',json={'code':'PILOT-ARPA','name':'Arpa','unit':'kg'}).json()['id']
        assert client.post('/api/stock-movements',json={'item_id':item,'type':'IN','quantity':'100'}).status_code==201
        assert client.post('/api/stock-movements',json={'item_id':item,'type':'OUT','quantity':'110'}).status_code==409
        assert client.post('/api/stock-movements',json={'item_id':item,'type':'OUT','quantity':'25'}).status_code==201
        assert next(i for i in client.get('/api/stock').json() if i['item_id']==item)['balance']=='75.000'
