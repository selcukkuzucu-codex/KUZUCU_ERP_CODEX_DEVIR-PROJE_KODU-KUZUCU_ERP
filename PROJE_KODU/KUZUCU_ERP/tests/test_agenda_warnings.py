from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import main
from app.agenda import LOCAL_TZ, next_due_date, month_at
from app.db import get_db


def test_month_end_repeat_and_weekly():
    def row(start, frequency, completed=None):
        return SimpleNamespace(start_date=start, frequency=frequency, last_completed_date=completed, is_active=True)
    assert month_at(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert month_at(date(2028, 1, 31), 1) == date(2028, 2, 29)
    r = row(date(2026, 1, 31), 'monthly', date(2026, 1, 31))
    assert next_due_date(r) == date(2026, 2, 28)
    r.last_completed_date = date(2026, 2, 28)
    assert next_due_date(r) == date(2026, 3, 31)
    assert next_due_date(row(date(2026, 10, 1), 'weekly', date(2026, 10, 1))) == date(2026, 10, 8)
    assert next_due_date(row(date(2026, 10, 1), 'daily', date(2026, 10, 1))) == date(2026, 10, 2)
    assert next_due_date(row(date(2026, 10, 1), 'once', date(2026, 10, 1))) is None


def test_reminders_crud_recurring_alert_and_validation(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "test_erp.db"}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    Session = sessionmaker(bind=engine)
    def local_db():
        with Session() as db: yield db
    main.app.dependency_overrides[get_db] = local_db
    try:
        today = datetime.now(LOCAL_TZ).date()
        with TestClient(main.app) as c:
            creation={
                'title':'  Günlük yem kontrolü  ', 'notes':'Depo ve kantar',
                'category':'Stok', 'frequency':'daily',
                'start_date':(today-timedelta(days=3)).isoformat(),
                'remind_time':'00:00',
            }
            r=c.post('/api/reminders', json=creation)
            assert r.status_code==201, r.text
            pk=r.json()['id']
            assert r.json()['title']=='Günlük yem kontrolü'
            assert r.json()['due'] is True
            due=c.get('/api/reminders/due').json()
            assert len(due)==1 and due[0]['id']==pk
            assert len(c.get('/api/reminders').json())==1
            r=c.post(f'/api/reminders/{pk}/complete')
            assert r.status_code==200, r.text
            assert r.json()['due'] is False
            assert r.json()['next_due_date']==(today+timedelta(days=1)).isoformat()
            assert c.post(f'/api/reminders/{pk}/complete').status_code==409
            assert c.get('/api/reminders/due').json()==[]
            # Future reminders cannot be marked completed ahead of time.
            future=c.post('/api/reminders',json={**creation,'start_date':(today+timedelta(days=3)).isoformat()}).json()['id']
            assert c.post(f'/api/reminders/{future}/complete').status_code==409
            edited=c.put(f'/api/reminders/{pk}',json={**creation,'title':'Haftalık yem kontrolü', 'frequency':'weekly'})
            assert edited.status_code==200 and edited.json()['title']=='Haftalık yem kontrolü'
            assert edited.json()['last_completed_date'] is None
            assert c.patch(f'/api/reminders/{pk}/active',json={'is_active':False}).json()['status']=='paused'
            assert c.patch(f'/api/reminders/{pk}/active',json={'is_active':True}).status_code==200
            assert c.post('/api/reminders',json={**creation,'remind_time':'25:00'}).status_code==422
            assert c.post('/api/reminders',json={**creation,'title':'    '}).status_code==422
            assert c.post('/api/reminders',json={**creation,'frequency':'hourly'}).status_code==422
            assert c.post('/api/reminders',json={**creation,'category':'Invalid'}).status_code==422
            assert c.get('/api/reminders/99').status_code==405  # no get-by-id route
            assert c.delete(f'/api/reminders/{future}').status_code==204
            assert c.delete('/api/reminders/99999').status_code==404
            assert len(c.get('/api/reminders').json())==1
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_duplicate_stock_reference_rejected(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "test_erp.db"}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    Session = sessionmaker(bind=engine)
    def local_db():
        with Session() as db: yield db
    main.app.dependency_overrides[get_db] = local_db
    try:
        with TestClient(main.app) as c:
            item = c.post('/api/items',json={'code':'ARP','name':'Arpa','unit':'kg'}).json()['id']
            d={'item_id':item,'type':'IN','quantity':'30000','movement_date':'2026-11-04','reference':'FTR-123'}
            assert c.post('/api/stock-movements',json=d).status_code==201
            duplicate=c.post('/api/stock-movements',json=d)
            assert duplicate.status_code==409 and 'Mükerrer' in duplicate.json()['detail']
            assert c.post('/api/stock-movements',json={**d,'quantity':'35000'}).status_code==201
            assert c.post('/api/stock-movements',json={**d,'type':'OUT','quantity':'100000'}).status_code==409
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_agenda_screen_ends_with_live_refresh():
    html=Path(__file__).resolve().parents[1].joinpath('app/static/index.html').read_text()
    for marker in ('Ajanda / Hatırlatmalar','setInterval(()=>{if(erpSession','data-edit-reminder','data-complete-reminder','checkLargeStock','humanError'):
        assert marker in html
