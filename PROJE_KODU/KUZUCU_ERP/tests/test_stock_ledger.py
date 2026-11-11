from datetime import date
from decimal import Decimal
import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import main
from app.db import get_db


def isolated_client(tmp_path, monkeypatch, legacy=False):
    db_path = tmp_path / 'isolated_stock.db'
    if legacy:
        with sqlite3.connect(db_path) as conn:
            conn.execute('CREATE TABLE items (id INTEGER PRIMARY KEY, code VARCHAR(50), name VARCHAR(120), unit VARCHAR(12))')
            conn.execute('INSERT INTO items (id,code,name,unit) VALUES (1,\'ARP\',\'Arpa\',\'kg\')')
            conn.execute('''CREATE TABLE stock_movements (id INTEGER PRIMARY KEY, item_id INTEGER, type VARCHAR(8), quantity NUMERIC(16,3), reference VARCHAR(100), created_at DATETIME)''')
            conn.execute('''INSERT INTO stock_movements (item_id,type,quantity,reference,created_at) VALUES (1,'IN',30000,'Eski kayıt','2026-11-01 13:00:00')''')
    engine=create_engine(f'sqlite:///{db_path}',connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    local=sessionmaker(bind=engine)
    def get_local():
        with local() as db:
            yield db
    main.app.dependency_overrides[get_db]=get_local
    return TestClient(main.app), engine


def test_stock_history_sorted_and_totals(tmp_path,monkeypatch):
    client,engine=isolated_client(tmp_path,monkeypatch)
    try:
        with client as c:
            arpa=c.post('/api/items',json={'code':'ARP','name':'Arpa','unit':'kg'}).json()['id']
            maya=c.post('/api/items',json={'code':'MAY','name':'Maya','unit':'adet'}).json()['id']
            assert c.post('/api/stock-movements',json={'item_id':arpa,'type':'IN','quantity':'30000','movement_date':'2026-11-02','reference':'kantar 1'}).status_code==201
            assert c.post('/api/stock-movements',json={'item_id':arpa,'type':'OUT','quantity':'5000.500','movement_date':'2026-11-04','reference':'çıkış 1'}).status_code==201
            assert c.post('/api/stock-movements',json={'item_id':arpa,'type':'IN','quantity':'2000','movement_date':'2026-11-03','reference':'kantar 2'}).status_code==201
            assert c.post('/api/stock-movements',json={'item_id':maya,'type':'IN','quantity':'20','movement_date':'2026-11-02'}).status_code==201
            history=c.get('/api/stock-movements/history').json()
            arpa_h=next(g for g in history['groups'] if g['code']=='ARP')
            assert [x['movement_date'] for x in arpa_h['movements']]==['2026-11-04','2026-11-03','2026-11-02']
            assert arpa_h['incoming']=='32000.000'
            assert arpa_h['outgoing']=='5000.500'
            assert arpa_h['balance']=='26999.500'
            assert next(x for x in c.get('/api/stock').json() if x['code']=='ARP')['balance']=='26999.500'
            units={x['unit']:x for x in history['unit_totals']}
            assert units['kg']['balance']=='26999.500'
            assert units['adet']['balance']=='20.000'
            assert c.post('/api/stock-movements',json={'item_id':arpa,'type':'OUT','quantity':'30000','movement_date':'2026-11-05'}).status_code==409
            assert c.post('/api/stock-movements',json={'item_id':arpa,'type':'OUT','quantity':'5','movement_date':'2026-99-99'}).status_code==422
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_legacy_stock_dates_are_migrated_without_changing_amounts(tmp_path,monkeypatch):
    client,engine=isolated_client(tmp_path,monkeypatch,legacy=True)
    try:
        with client as c:
            result=c.get('/api/stock-movements/history').json()
            row=result['groups'][0]
            assert row['movements'][0]['movement_date']=='2026-11-01'
            assert row['movements'][0]['quantity']=='30000.000'
            assert row['balance']=='30000.000'
        with engine.connect() as conn:
            assert 'movement_date' in {r[1] for r in conn.execute(text('PRAGMA table_info(stock_movements)'))}
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
