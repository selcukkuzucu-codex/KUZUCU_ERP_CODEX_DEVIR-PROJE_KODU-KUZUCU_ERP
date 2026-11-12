"""v0.15: buzağı grubu, litre tüketimi, bireysel çıkış ve eski veri koruması."""
import csv
from datetime import datetime, timedelta
from decimal import Decimal
import io
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app import main
from app.db import get_db
from app.models import Calf, CalfConsumption


def today():
    return datetime.now(ZoneInfo('Europe/Istanbul')).date()


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "calves.db"}',
                           connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR', str(tmp_path / 'reports'))
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def local_db():
        with maker() as db:
            yield db

    monkeypatch.setitem(main.app.dependency_overrides, get_db, local_db)
    try:
        with TestClient(main.app) as client:
            yield SimpleNamespace(client=client, maker=maker, engine=engine)
    finally:
        engine.dispose()


def calf_payload(tag='001', **overrides):
    return {'tr_ear_tag': f'TR{tag}', 'farm_ear_tag': tag, 'sex': 'male',
            'entry_date': (today() - timedelta(days=45)).isoformat(),
            'entry_kg': '50', 'breed': 'Simental', **overrides}


def add_calf(pilot, tag='001', **overrides):
    r = pilot.client.post('/api/calves', json=calf_payload(tag, **overrides))
    assert r.status_code == 201, r.text
    return r.json()


def bulk_payload(ids, **overrides):
    return {'consumed_on': today().isoformat(), 'group_no': 'G01',
            'milk_litres': '3', 'feed_kg': '1', 'calf_ids': ids, **overrides}


def consumption_count(pilot):
    with pilot.maker() as db:
        return db.scalar(select(func.count()).select_from(CalfConsumption))


def test_card_price_group_and_milk_phase_are_saved_without_kg_price_multiplication(pilot):
    c = add_calf(pilot, group_no='001', purchase_price_tl='12500.50', milk_phase=True)
    assert c['group_no'] == '001'
    assert Decimal(c['purchase_price_tl']) == Decimal('12500.50')
    assert c['milk_phase'] is True
    r = pilot.client.put(f'/api/calves/{c["id"]}', json=calf_payload(
        group_no='G02', purchase_price_tl='13000.75', milk_phase=False))
    assert r.status_code == 200, r.text
    assert r.json()['group_no'] == 'G02' and r.json()['milk_phase'] is False
    assert Decimal(r.json()['purchase_price_tl']) == Decimal('13000.75')


def test_legacy_card_fields_stay_unknown_and_omitted_new_fields_are_preserved(pilot):
    old = add_calf(pilot)
    assert old['group_no'] is None and old['purchase_price_tl'] is None
    assert old['milk_phase'] is None
    updated = pilot.client.put(f'/api/calves/{old["id"]}', json=calf_payload(
        group_no='G01', purchase_price_tl='100.25', milk_phase=True))
    assert updated.status_code == 200
    legacy_edit = pilot.client.put(f'/api/calves/{old["id"]}', json=calf_payload(notes='Eski istemci düzenlemesi'))
    assert legacy_edit.status_code == 200, legacy_edit.text
    assert legacy_edit.json()['group_no'] == 'G01'
    assert Decimal(legacy_edit.json()['purchase_price_tl']) == Decimal('100.25')
    assert legacy_edit.json()['milk_phase'] is True


@pytest.mark.parametrize('price', ['-1', '12.345', 'gecersiz'])
def test_invalid_purchase_price_does_not_create_a_calf(pilot, price):
    r = pilot.client.post('/api/calves', json=calf_payload(purchase_price_tl=price))
    assert r.status_code == 422, r.text
    assert pilot.client.get('/api/calves').json() == []


def test_group_members_returns_all_twenty_and_keeps_other_groups_and_exits_out(pilot):
    ids = [add_calf(pilot, str(i).zfill(3), group_no='G01')['id'] for i in range(20)]
    add_calf(pilot, 'OTHER', group_no='G02')
    out = add_calf(pilot, 'OUT', group_no='G01')
    assert pilot.client.post(f'/api/calves/{out["id"]}/exit', json={
        'exit_date': today().isoformat(), 'exit_kg': '90'}).status_code == 200
    r = pilot.client.get('/api/calves/group-members', params={'group_no': 'G01', 'on': today().isoformat()})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['count'] == 20 and data['eligible_count'] == 20
    assert {x['id'] for x in data['rows']} == set(ids)
    assert all(x['eligible'] and not x['has_consumption'] for x in data['rows'])


def test_twenty_selected_calves_each_receive_full_amount_and_retry_does_not_duplicate(pilot):
    ids = [add_calf(pilot, str(i).zfill(3), group_no='G01')['id'] for i in range(20)]
    payload = bulk_payload(ids)
    r = pilot.client.post('/api/calves/bulk-consumptions', json=payload)
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data['count'] == 20
    assert Decimal(data['per_animal']['milk_litres']) == 3
    assert Decimal(data['per_animal']['feed_kg']) == 1
    assert Decimal(data['totals']['milk_litres']) == 60
    assert Decimal(data['totals']['feed_kg']) == 20
    with pilot.maker() as db:
        rows = db.scalars(select(CalfConsumption)).all()
        assert len(rows) == 20
        assert {r.calf_id for r in rows} == set(ids)
        assert all(r.milk_litres == 3 and r.feed_kg == 1 and r.milk_kg == 0 for r in rows)
        assert all(r.group_no_snapshot == 'G01' for r in rows)
    repeat = pilot.client.post('/api/calves/bulk-consumptions', json=payload)
    assert repeat.status_code == 409, repeat.text
    assert consumption_count(pilot) == 20


def test_bulk_consumption_subset_leaves_unselected_members_untouched(pilot):
    ids = [add_calf(pilot, str(i), group_no='G01')['id'] for i in range(5)]
    selected = ids[1:4]
    r = pilot.client.post('/api/calves/bulk-consumptions', json=bulk_payload(selected, milk_litres='2.5', feed_kg='0.750'))
    assert r.status_code in (200, 201), r.text
    with pilot.maker() as db:
        rows = db.scalars(select(CalfConsumption)).all()
        assert {x.calf_id for x in rows} == set(selected)
        assert all(x.milk_litres == Decimal('2.5') and x.feed_kg == Decimal('0.750') for x in rows)


@pytest.mark.parametrize('failure', ['duplicate_id', 'wrong_group', 'inactive', 'missing', 'future', 'before_entry', 'empty', 'zero'])
def test_invalid_bulk_consumption_is_atomic(pilot, failure):
    first = add_calf(pilot, '001', group_no='G01')
    other = add_calf(pilot, '002', group_no='G02' if failure == 'wrong_group' else 'G01')
    ids = [first['id'], other['id']]
    overrides = {}
    if failure == 'duplicate_id':
        ids.append(first['id'])
    elif failure == 'inactive':
        assert pilot.client.post(f'/api/calves/{other["id"]}/exit', json={
            'exit_date': today().isoformat(), 'exit_kg': '80'}).status_code == 200
    elif failure == 'missing':
        ids.append(9999999)
    elif failure == 'future':
        overrides['consumed_on'] = (today() + timedelta(days=1)).isoformat()
    elif failure == 'before_entry':
        overrides['consumed_on'] = (today() - timedelta(days=46)).isoformat()
    elif failure == 'empty':
        ids = []
    elif failure == 'zero':
        overrides.update(milk_litres='0', feed_kg='0')
    r = pilot.client.post('/api/calves/bulk-consumptions', json=bulk_payload(ids, **overrides))
    assert r.status_code in (404, 409, 422), r.text
    assert consumption_count(pilot) == 0


def test_existing_daily_record_rejects_every_new_row_in_the_batch(pilot):
    first = add_calf(pilot, '001', group_no='G01')
    second = add_calf(pilot, '002', group_no='G01')
    old = pilot.client.post(f'/api/calves/{second["id"]}/consumptions', json={
        'consumed_on': today().isoformat(), 'milk_kg': '4', 'feed_kg': '1'})
    assert old.status_code == 201
    r = pilot.client.post('/api/calves/bulk-consumptions', json=bulk_payload([first['id'], second['id']]))
    assert r.status_code == 409, r.text
    assert consumption_count(pilot) == 1
    assert pilot.client.get(f'/api/calves/{first["id"]}/consumptions').json() == []
    members = pilot.client.get('/api/calves/group-members', params={'group_no': 'G01', 'on': today().isoformat()}).json()
    second_row = next(x for x in members['rows'] if x['id'] == second['id'])
    assert second_row['has_consumption'] and not second_row['eligible']


def test_litres_and_legacy_kg_stay_separate_and_group_snapshot_survives_card_edit(pilot):
    c = add_calf(pilot, group_no='G01')
    yesterday = (today() - timedelta(days=1)).isoformat()
    r = pilot.client.post(f'/api/calves/{c["id"]}/consumptions', json={
        'consumed_on': yesterday, 'milk_kg': '5', 'feed_kg': '2'})
    assert r.status_code == 201
    assert pilot.client.post('/api/calves/bulk-consumptions', json=bulk_payload([c['id']])).status_code in (200, 201)
    row = pilot.client.get('/api/calves').json()[0]
    assert Decimal(row['milk_total_kg']) == 5
    assert Decimal(row['milk_total_litres']) == 3
    assert Decimal(row['feed_total_kg']) == 3
    assert pilot.client.put(f'/api/calves/{c["id"]}', json=calf_payload(group_no='G02')).status_code == 200
    with pilot.maker() as db:
        records = db.scalars(select(CalfConsumption).order_by(CalfConsumption.consumed_on)).all()
        assert records[0].milk_kg == 5 and records[0].milk_litres is None
        assert records[1].milk_litres == 3 and records[1].group_no_snapshot == 'G01'


def test_resolve_exit_tags_keeps_zeros_uses_exact_matches_and_deduplicates_animal(pilot):
    a = add_calf(pilot, '0001', group_no='G01')
    b = add_calf(pilot, '00010', group_no='G01', sex='female')
    payload = {'exit_date': today().isoformat(), 'group_no': 'G01',
               'tr_ear_tags': '  TR0001, TR00010  ', 'farm_ear_tags': ''}
    r = pilot.client.post('/api/calves/resolve-exit-tags', json=payload)
    assert r.status_code == 200, r.text
    assert r.json()['valid'] and {x['id'] for x in r.json()['rows']} == {a['id'], b['id']}
    assert {x['farm_ear_tag'] for x in r.json()['rows']} == {'0001', '00010'}
    repeated = pilot.client.post('/api/calves/resolve-exit-tags', json={
        **payload, 'tr_ear_tags': 'TR0001, TR0001', 'farm_ear_tags': '0001'})
    assert repeated.status_code == 200
    assert [x['id'] for x in repeated.json()['rows']] == [a['id']]
    assert repeated.json()['warnings']
    partial = pilot.client.post('/api/calves/resolve-exit-tags', json={**payload, 'tr_ear_tags': 'TR000'})
    assert partial.status_code == 200 and not partial.json()['valid']
    assert partial.json()['rows'] == [] and partial.json()['warnings']


@pytest.mark.parametrize('failure', ['unknown', 'wrong_group', 'exited', 'incomplete'])
def test_resolve_exit_tags_explains_bad_numbers_without_changing_records(pilot, failure):
    c = add_calf(pilot, '0001', group_no='G01')
    payload = {'exit_date': today().isoformat(), 'group_no': 'G01', 'tr_ear_tags': 'TR0001', 'farm_ear_tags': ''}
    if failure == 'unknown':
        payload['tr_ear_tags'] = 'TR0001, BULUNMADI'
    elif failure == 'wrong_group':
        payload['group_no'] = 'G02'
    elif failure == 'exited':
        assert pilot.client.post(f'/api/calves/{c["id"]}/exit', json={
            'exit_date': today().isoformat(), 'exit_kg': '80'}).status_code == 200
    elif failure == 'incomplete':
        payload['tr_ear_tags'] = 'TR0001, '
    r = pilot.client.post('/api/calves/resolve-exit-tags', json=payload)
    assert r.status_code == 200, r.text
    assert not r.json()['valid'] and r.json()['warnings']
    current = pilot.client.get('/api/calves').json()[0]
    assert current['exit_date'] == (today().isoformat() if failure == 'exited' else None)


def test_bulk_exit_needs_no_exit_number_and_keeps_individual_weights_and_group_history(pilot):
    a = add_calf(pilot, '001', group_no='G01')
    b = add_calf(pilot, '002', group_no='G01', sex='female')
    payload = {'exit_date': today().isoformat(), 'group_no': 'G01',
               'entries': [{'calf_id': a['id'], 'exit_kg': '95'}, {'calf_id': b['id'], 'exit_kg': '105'}]}
    result = pilot.client.post('/api/calves/bulk-exit', json=payload)
    assert result.status_code == 200, result.text
    assert result.json()['count'] == 2
    rows = pilot.client.get('/api/calves').json()
    assert {x['tr_ear_tag']: Decimal(x['exit_kg']) for x in rows} == {'TR001': Decimal('95'), 'TR002': Decimal('105')}
    assert all(not x['exit_group_no'] for x in rows)
    assert all(x['days'] == 45 and x['adg_kg_day'] is not None for x in rows)
    assert pilot.client.post('/api/calves/bulk-exit', json=payload).status_code == 409
    assert pilot.client.put(f'/api/calves/{a["id"]}', json=calf_payload('001', group_no='G02')).status_code == 200
    report = pilot.client.get('/api/calves/exit-report', params={'group_no': 'G01'}).json()
    assert report['summary']['count'] == 2
    with pilot.maker() as db:
        assert db.get(Calf, a['id']).exit_group_snapshot == 'G01'
    assert pilot.client.get('/api/calves/exit-report', params={'group_no': 'G02'}).json()['summary']['count'] == 0


def test_bulk_exit_wrong_group_is_atomic(pilot):
    a = add_calf(pilot, '001', group_no='G01')
    b = add_calf(pilot, '002', group_no='G02')
    result = pilot.client.post('/api/calves/bulk-exit', json={
        'exit_date': today().isoformat(), 'group_no': 'G01',
        'entries': [{'calf_id': a['id'], 'exit_kg': '95'}, {'calf_id': b['id'], 'exit_kg': '105'}]})
    assert result.status_code in (409, 422), result.text
    assert all(x['exit_date'] is None for x in pilot.client.get('/api/calves').json())


def test_exit_csv_translates_sex_and_labels_legacy_kg_and_new_litres_separately(pilot):
    c = add_calf(pilot, group_no='G01', sex='female')
    assert pilot.client.post('/api/calves/bulk-consumptions', json=bulk_payload([c['id']])).status_code in (200, 201)
    assert pilot.client.post(f'/api/calves/{c["id"]}/exit', json={
        'exit_date': today().isoformat(), 'exit_kg': '90'}).status_code == 200
    result = pilot.client.get('/api/calves/exit-report.csv', params={'group_no': 'G01'})
    assert result.status_code == 200 and result.content.startswith(b'\xef\xbb\xbf')
    rows = list(csv.reader(io.StringIO(result.content.decode('utf-8-sig')), delimiter=';'))
    headers = rows[0]
    assert any('litre' in x.lower() for x in headers)
    assert any('kg' in x.lower() and ('mama' in x.lower() or 'süt' in x.lower()) for x in headers)
    assert 'Dişi' in rows[1]
    assert 'female' not in result.text and 'male' not in result.text


def test_new_consumption_and_tag_resolution_respect_operator_permissions(pilot):
    c = add_calf(pilot, group_no='G01')
    created = pilot.client.post('/api/auth/users', json={
        'username': 'calfviewer', 'password': 'CalfViewerPassword2026', 'display_name': 'Buzağı İzleyici',
        'permissions': ['hayvanlar.buzagi.view']})
    assert created.status_code == 201, created.text
    viewer = TestClient(main.app)
    try:
        r = viewer.post('/api/auth/login', json={'username': 'calfviewer', 'password': 'CalfViewerPassword2026'})
        assert r.status_code == 200
        csrf = {'X-CSRF-Token': r.json()['csrf_token']}
        assert viewer.get('/api/calves/group-members', params={'group_no': 'G01'}).status_code == 200
        resolve = viewer.post('/api/calves/resolve-exit-tags', headers=csrf, json={
            'exit_date': today().isoformat(), 'tr_ear_tags': 'TR001', 'group_no': 'G01'})
        assert resolve.status_code == 200, resolve.text
        assert viewer.post('/api/calves/bulk-consumptions', headers=csrf,
                           json=bulk_payload([c['id']])).status_code == 403
        assert consumption_count(pilot) == 0
    finally:
        viewer.close()


def test_sqlite_migration_is_idempotent_and_does_not_guess_legacy_values(tmp_path):
    from app.calf import migrate_v015

    engine = create_engine(f'sqlite:///{tmp_path / "legacy-calves.db"}')
    try:
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE calves (id INTEGER PRIMARY KEY, tr_ear_tag VARCHAR(60), exit_group_no VARCHAR(80))'))
            conn.execute(text("INSERT INTO calves VALUES (1, 'TR0001', 'ESKI-CIKIS')"))
            conn.execute(text('CREATE TABLE calf_consumptions (id INTEGER PRIMARY KEY, calf_id INTEGER, consumed_on DATE, milk_kg NUMERIC, feed_kg NUMERIC, notes VARCHAR(400))'))
            conn.execute(text("INSERT INTO calf_consumptions VALUES (1, 1, '2026-11-01', 5.5, 1.25, 'Eski not')"))
        migrate_v015(engine)
        migrate_v015(engine)
        with engine.connect() as conn:
            calf = conn.execute(text('SELECT group_no,purchase_price_tl,milk_phase,exit_group_snapshot,exit_group_no FROM calves')).one()
            assert tuple(calf) == (None, None, None, None, 'ESKI-CIKIS')
            consumption = conn.execute(text('SELECT milk_kg,feed_kg,milk_litres,group_no_snapshot,notes FROM calf_consumptions')).one()
            assert tuple(consumption) == (5.5, 1.25, None, None, 'Eski not')
            assert conn.execute(text('SELECT count(*) FROM calves')).scalar_one() == 1
            assert conn.execute(text('SELECT count(*) FROM calf_consumptions')).scalar_one() == 1
    finally:
        engine.dispose()
