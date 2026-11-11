from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app import main, personnel
from app.agenda import migrate_v015, next_due_date
from app.db import get_db
from app.security import AuditEvent


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 9)


@pytest.fixture
def site(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'personnel.db'), connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(personnel, 'date', FixedDate)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR', str(tmp_path / 'reports'))
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    def localdb():
        with maker() as db:
            yield db
    monkeypatch.setitem(main.app.dependency_overrides, get_db, localdb)
    try:
        with TestClient(main.app) as client:
            yield client, maker
    finally:
        engine.dispose()


def employee(client, **extra):
    data = {'employee_no': 'P-001', 'full_name': 'Deneme Çalışanı', 'department': 'Besi', 'start_date': '2026-01-01'}
    data.update(extra)
    response = client.post('/api/personnel/employees', json=data)
    assert response.status_code == 201, response.text
    return response.json(), data


def test_personnel_card_overtime_edit_exit_and_audit(site):
    client, maker = site
    person, card = employee(client)
    assert person['status_label'] == 'Çalışıyor'
    assert client.post('/api/personnel/employees', json=card).status_code == 409
    response = client.post('/api/personnel/overtime', json={'employee_id': person['id'], 'worked_on': '2026-11-01', 'hours': '2.50', 'notes': 'Akşam işi'})
    assert response.status_code == 201, response.text
    overtime_id = response.json()['id']
    assert client.post('/api/personnel/overtime', json={'employee_id': person['id'], 'worked_on': '2026-11-01', 'hours': '1'}).status_code == 409
    assert client.put(f'/api/personnel/overtime/{overtime_id}', json={'employee_id': person['id'], 'worked_on': '2026-11-01', 'hours': '3.25'}).status_code == 200
    bad = client.put(f'/api/personnel/employees/{person["id"]}', json={**card, 'end_date': '2026-10-31'})
    assert bad.status_code == 409
    assert client.get('/api/personnel/employees').json()[0]['end_date'] is None
    exited = client.put(f'/api/personnel/employees/{person["id"]}', json={**card, 'end_date': '2026-11-05'})
    assert exited.status_code == 200 and exited.json()['status'] == 'left'
    assert len(client.get('/api/personnel/employees?status=left').json()) == 1
    assert client.get('/api/personnel/employees?status=active').json() == []
    assert len(client.get('/api/personnel/overtime?employee_id=' + str(person['id'])).json()) == 1
    assert client.post('/api/personnel/overtime', json={'employee_id': person['id'], 'worked_on': '2026-11-06', 'hours': '1'}).status_code == 409
    with maker() as db:
        audit = list(db.scalars(select(AuditEvent).where(AuditEvent.table_name.in_(['personnel_employees', 'personnel_overtime']))))
        assert any(row.action == 'EKLE' and row.actor == 'Test Yöneticisi (legacytester)' for row in audit)
        assert any(row.action == 'DUZENLE' and row.table_name == 'personnel_employees' for row in audit)
    assert client.delete(f'/api/personnel/overtime/{overtime_id}').status_code == 204
    assert client.get('/api/personnel/employees?status=left').json()[0]['id'] == person['id']


@pytest.mark.parametrize('patch', [{'hours': 0}, {'hours': '24.01'}, {'hours': '1.125'}, {'worked_on': '2025-12-31'}, {'worked_on': '2027-01-01'}])
def test_invalid_overtime_is_atomic(site, patch):
    client, maker = site
    person, _ = employee(client)
    response = client.post('/api/personnel/overtime', json={'employee_id': person['id'], 'worked_on': '2026-11-01', 'hours': '2', **patch})
    assert response.status_code in (409, 422), response.text
    assert client.get('/api/personnel/overtime').json() == []
    with maker() as db:
        assert list(db.scalars(select(AuditEvent).where(AuditEvent.table_name == 'personnel_overtime'))) == []


def test_annual_allowance_used_planned_remaining_and_weekly_independence(site):
    client, _ = site
    person, _ = employee(client)
    pk = person['id']
    leave = {'employee_id': pk, 'kind': 'annual', 'starts_on': '2026-10-01', 'ends_on': '2026-10-03'}
    assert client.post('/api/personnel/leaves', json=leave).status_code == 409
    assert client.put(f'/api/personnel/allowances/{pk}/2026', json={'days': 14}).status_code == 200
    first = client.post('/api/personnel/leaves', json=leave)
    assert first.status_code == 201 and first.json()['days'] == 3
    future = client.post('/api/personnel/leaves', json={**leave, 'starts_on': '2026-12-01', 'ends_on': '2026-12-02'})
    assert future.status_code == 201
    weekly = client.post('/api/personnel/leaves', json={**leave, 'kind': 'weekly', 'starts_on': '2026-10-04', 'ends_on': '2026-10-04'})
    assert weekly.status_code == 201
    state = client.get(f'/api/personnel/balances?employee_id={pk}&year=2026').json()[0]
    assert (state['allocated_days'], state['used_days'], state['planned_days'], state['remaining_days']) == (14, 3, 2, 9)
    assert client.put(f'/api/personnel/allowances/{pk}/2026', json={'days': 4}).status_code == 409
    assert client.post('/api/personnel/leaves', json={**leave, 'starts_on': '2026-10-10', 'ends_on': '2026-10-20'}).status_code == 409
    assert len(client.get('/api/personnel/leaves').json()) == 3
    assert client.put(f'/api/personnel/leaves/{first.json()["id"]}', json={**leave, 'ends_on': '2026-10-02'}).status_code == 200
    assert client.get(f'/api/personnel/balances?employee_id={pk}&year=2026').json()[0]['remaining_days'] == 10
    assert client.delete(f'/api/personnel/leaves/{future.json()["id"]}').status_code == 204
    assert client.get(f'/api/personnel/balances?employee_id={pk}&year=2026').json()[0]['remaining_days'] == 12


def test_leave_overlap_overtime_conflict_and_reversed_dates_do_not_write(site):
    client, _ = site
    person, _ = employee(client)
    pk = person['id']
    first = {'employee_id': pk, 'kind': 'weekly', 'starts_on': '2026-10-01', 'ends_on': '2026-10-02'}
    assert client.post('/api/personnel/leaves', json=first).status_code == 201
    assert client.post('/api/personnel/leaves', json={**first, 'starts_on': '2026-10-02', 'ends_on': '2026-10-03'}).status_code == 409
    assert client.post('/api/personnel/leaves', json={**first, 'starts_on': '2026-10-05', 'ends_on': '2026-10-03'}).status_code == 422
    assert client.post('/api/personnel/overtime', json={'employee_id': pk, 'worked_on': '2026-10-01', 'hours': '1'}).status_code == 409
    assert client.post('/api/personnel/overtime', json={'employee_id': pk, 'worked_on': '2026-10-05', 'hours': '1'}).status_code == 201
    assert client.post('/api/personnel/leaves', json={**first, 'starts_on': '2026-10-05', 'ends_on': '2026-10-05'}).status_code == 409
    assert len(client.get('/api/personnel/leaves').json()) == 1
    assert len(client.get('/api/personnel/overtime').json()) == 1


def test_cross_year_leave_requires_both_allocations_before_any_write(site):
    client, _ = site
    person, _ = employee(client)
    pk = person['id']
    assert client.put(f'/api/personnel/allowances/{pk}/2026', json={'days': 2}).status_code == 200
    assert client.put(f'/api/personnel/allowances/{pk}/2027', json={'days': 1}).status_code == 200
    data = {'employee_id': pk, 'kind': 'annual', 'starts_on': '2026-12-30', 'ends_on': '2027-01-02'}
    assert client.post('/api/personnel/leaves', json=data).status_code == 409
    assert client.get('/api/personnel/leaves').json() == []
    assert client.put(f'/api/personnel/allowances/{pk}/2027', json={'days': 2}).status_code == 200
    assert client.post('/api/personnel/leaves', json=data).status_code == 201
    for year in (2026, 2027):
        state = client.get(f'/api/personnel/balances?employee_id={pk}&year={year}').json()[0]
        assert state['planned_days'] == 2 and state['remaining_days'] == 0


def test_personnel_filters_reports_csv_and_independent_permissions(site):
    client, _ = site
    first, _ = employee(client, full_name='=TOPLA(A1:A2)')
    employee(client, employee_no='P-002', full_name='Ayrılan Çalışan', end_date='2026-02-01')
    assert client.post('/api/personnel/overtime', json={'employee_id': first['id'], 'worked_on': '2026-10-01', 'hours': '2.5'}).status_code == 201
    report = client.get('/api/personnel/reports?kind=overtime&date_from=2026-10-01&date_to=2026-10-31')
    assert report.status_code == 200 and report.json()['row_count'] == 1
    assert report.json()['rows'][0][4] == '2,50'
    assert client.get('/api/personnel/reports?kind=employment&status=left&date_from=2026-02-01&date_to=2026-02-01').json()['rows'][0][3] == 'İşten ayrılış'
    assert client.get('/api/personnel/overtime?date_from=2026-11-01').json() == []
    assert client.get('/api/personnel/reports?date_from=2026-11-02&date_to=2026-11-01').status_code == 422
    csv = client.get('/api/personnel/reports.csv?kind=employees')
    assert csv.status_code == 200 and csv.content.startswith(b'\xef\xbb\xbf')
    assert "'=TOPLA(A1:A2)" in csv.text and 'İşten ayrıldı' in csv.text
    for username, grants in [('personelgor', ['personel.view']), ('raporgor', ['reports.payroll.view']), ('raporaktar', ['reports.payroll.view', 'reports.payroll.export'])]:
        added = client.post('/api/auth/users', json={'username': username, 'password': 'PersonnelTest!2026', 'display_name': 'Deneme Yetkisi', 'permissions': grants})
        assert added.status_code == 201, added.text
        with TestClient(main.app) as operator:
            login = operator.post('/api/auth/login', json={'username': username, 'password': 'PersonnelTest!2026'})
            assert login.status_code == 200
            operator.headers['X-CSRF-Token'] = login.json()['csrf_token']
            assert operator.get('/api/personnel/employees').status_code == (200 if 'personel.view' in grants else 403)
            assert operator.get('/api/personnel/reports').status_code == (200 if 'reports.payroll.view' in grants else 403)
            assert operator.get('/api/personnel/balances').status_code == (200 if 'reports.payroll.view' in grants else 403)
            assert operator.get('/api/personnel/reports.csv').status_code == (200 if 'reports.payroll.export' in grants else 403)
            assert operator.post('/api/personnel/employees', json={'employee_no': 'YOK', 'full_name': 'Yetkisiz', 'start_date': '2026-01-01'}).status_code == 403
    anonymous = TestClient(main.app)
    try:
        assert anonymous.get('/api/personnel/employees').status_code == 401
        assert anonymous.get('/api/personnel/reports').status_code == 401
    finally:
        anonymous.close()


@pytest.mark.parametrize('frequency,interval,start,completed,expected', [
    ('daily', 3, '2026-01-01', '2026-01-01', '2026-01-04'),
    ('weekly', 2, '2026-01-01', '2026-01-01', '2026-01-15'),
    ('weekly', 2, '2026-01-01', '2026-01-17', '2026-01-29'),
    ('monthly', 5, '2026-01-31', '2026-01-31', '2026-06-30'),
    ('monthly', 5, '2026-01-31', '2026-06-30', '2026-11-30'),
    ('monthly', 12, '2024-02-29', '2027-02-28', '2028-02-29'),
    ('monthly', 1, '2028-01-31', '2028-01-31', '2028-02-29'),
    ('monthly', 1, '2028-01-31', '2028-02-29', '2028-03-31'),
])
def test_numbered_reminders_keep_original_calendar_anchor(frequency, interval, start, completed, expected):
    reminder = SimpleNamespace(frequency=frequency, interval_count=interval, start_date=date.fromisoformat(start),
                               last_completed_date=date.fromisoformat(completed), is_active=True)
    assert next_due_date(reminder) == date.fromisoformat(expected)


def test_interval_api_validation_edit_reset_and_next_due(site):
    client, _ = site
    today = date.today()
    creation = {'title': 'İki haftada bir kontrol', 'frequency': 'weekly', 'interval_count': 2,
                'start_date': (today - timedelta(days=14)).isoformat(), 'remind_time': '00:00'}
    created = client.post('/api/reminders', json=creation)
    assert created.status_code == 201 and created.json()['interval_count'] == 2
    pk = created.json()['id']
    completed = client.post(f'/api/reminders/{pk}/complete')
    assert completed.status_code == 200 and completed.json()['next_due_date'] == (today + timedelta(days=14)).isoformat()
    assert client.post(f'/api/reminders/{pk}/complete').status_code == 409
    edited = client.put(f'/api/reminders/{pk}', json={**creation, 'interval_count': 5, 'frequency': 'monthly'})
    assert edited.status_code == 200 and edited.json()['last_completed_date'] is None
    for invalid in [0, -1, 1.5, '2', True]:
        assert client.post('/api/reminders', json={**creation, 'interval_count': invalid}).status_code == 422
    assert len(client.get('/api/reminders').json()) == 1


def test_reminder_interval_migration_is_repeatable_and_preserves_old_rows(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'legacy-reminder.db'))
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE reminders (id INTEGER PRIMARY KEY, title VARCHAR(180), frequency VARCHAR(16))'))
        connection.execute(text("INSERT INTO reminders VALUES (1, 'Eski görev', 'monthly')"))
    migrate_v015(engine)
    migrate_v015(engine)
    with engine.connect() as connection:
        assert connection.execute(text('SELECT title, frequency, interval_count FROM reminders')).fetchone() == ('Eski görev', 'monthly', 1)
        assert sum(row[1] == 'interval_count' for row in connection.execute(text('PRAGMA table_info(reminders)'))) == 1
    engine.dispose()
