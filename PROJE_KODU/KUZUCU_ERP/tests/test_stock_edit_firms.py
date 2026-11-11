from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import main
from app.db import get_db


def local_client(tmp_path, monkeypatch):
    db_path = tmp_path / 'pilot.db'
    engine = create_engine(f'sqlite:///{db_path}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    Session = sessionmaker(bind=engine)
    def get_local():
        with Session() as db:
            yield db
    main.app.dependency_overrides[get_db] = get_local
    return TestClient(main.app), engine


def test_edit_stock_and_audit(tmp_path, monkeypatch):
    client, engine = local_client(tmp_path, monkeypatch)
    try:
        with client as c:
            item = c.post('/api/items', json={'code': 'ARP', 'name': 'Arpa', 'unit': 'kg'}).json()['id']
            other = c.post('/api/items', json={'code': 'YEM', 'name': 'Yem', 'unit': 'kg'}).json()['id']
            # A previously mis-entered 30.000.000 kg can be corrected to 30.000 kg.
            move = c.post('/api/stock-movements', json={'item_id':item,'type':'IN','quantity':'30000000','movement_date':'2026-11-04'}).json()['id']
            modified = {'item_id':item,'type':'IN','quantity':'30000','movement_date':'2026-11-02','reference':'Kantar 14','reason':'Yanlış sıfırlar düzeltildi'}
            r = c.put(f'/api/stock-movements/{move}', json=modified)
            assert r.status_code == 200, r.text
            assert r.json()['quantity'] == '30000.000'
            hist = c.get('/api/stock-movements/history').json()
            assert next(g for g in hist['groups'] if g['item_id']==item)['balance'] == '30000.000'
            revisions = c.get(f'/api/stock-movements/{move}/revisions').json()
            assert len(revisions) == 1
            assert revisions[0]['old_quantity'] == '30000000.000'
            assert revisions[0]['new_quantity'] == '30000.000'
            assert revisions[0]['reason'] == 'Yanlış sıfırlar düzeltildi'
            outgoing = c.post('/api/stock-movements', json={'item_id':item,'type':'OUT','quantity':'20000','movement_date':'2026-11-05'}).json()['id']
            # Can't accidentally change the original incoming 30k to 10k with 20k already issued.
            bad = c.put(f'/api/stock-movements/{move}', json={**modified,'quantity':'10000'})
            assert bad.status_code == 409
            assert c.get(f'/api/stock-movements/{move}/revisions').json()[0]['new_quantity']=='30000.000'
            # Can't move the incoming item to a different stock code if it leaves original negative.
            bad2 = c.put(f'/api/stock-movements/{move}', json={**modified,'item_id':other})
            assert bad2.status_code == 409
            # Can adjust an OUT movement, and changes appear in totals.
            edit_out = c.put(f'/api/stock-movements/{outgoing}', json={'item_id':item,'type':'OUT','quantity':'5000','movement_date':'2026-11-06','reference':'Tüketim','reason':'Fiili tüketim düzeltildi'})
            assert edit_out.status_code == 200
            assert next(g for g in c.get('/api/stock-movements/history').json()['groups'] if g['item_id']==item)['balance']=='25000.000'
            assert c.put('/api/stock-movements/99999', json=modified).status_code==404
            assert c.put(f'/api/stock-movements/{move}', json={**modified,'reason':' '}).status_code==422
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_firms_create_edit_search_fields(tmp_path, monkeypatch):
    client, engine = local_client(tmp_path, monkeypatch)
    try:
        with client as c:
            created=c.post('/api/firms',json={'name':'  Örnek Yem Ltd. ','tax_no':'1234567890','phone':'0352 222 22 22','address':'Kayseri / Türkiye'})
            assert created.status_code==201,created.text
            pk=created.json()['id']
            assert created.json()['name']=='Örnek Yem Ltd.'
            assert c.get('/api/firms').json()[0]['tax_no']=='1234567890'
            assert c.post('/api/firms',json={'name':'İkinci','tax_no':'1234567890'}).status_code==409
            assert c.post('/api/firms',json={'name':'Üçüncü','tax_no':'123'}).status_code==422
            updated=c.put(f'/api/firms/{pk}',json={'name':'Örnek Yem A.Ş.','tax_no':'1234567890','phone':'0532 123 45 67','address':'Yeni adres'})
            assert updated.status_code==200
            assert updated.json()['phone']=='0532 123 45 67'
            assert updated.json()['address']=='Yeni adres'
            assert c.put('/api/firms/99999',json={'name':'Yok'}).status_code==404
        with engine.connect() as conn:
            assert 'firms' in {x[0] for x in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
            assert 'stock_movement_revisions' in {x[0] for x in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
