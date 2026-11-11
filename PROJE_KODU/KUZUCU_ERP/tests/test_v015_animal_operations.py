"""Toplu hayvan işlemlerinde kimlik, yetki, kayıt bütünlüğü ve çıkış geçmişi."""
from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import animal_operations as ops, security
from app.db import Base, get_db
from app.models import Animal, Pen, Weighing


@pytest.fixture
def pilot(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'animals.db'), connect_args={'check_same_thread': False})
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        app.state.auth_session_factory = maker
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(security.router)
    app.include_router(ops.router)
    app.middleware('http')(security.auth_middleware)

    def local_db():
        with maker() as db:
            yield db

    app.dependency_overrides[get_db] = local_db
    with TestClient(app) as client:
        with maker() as db:
            pens = [Pen(code='01', capacity=2), Pen(code='02', capacity=1), Pen(code='03', capacity=2)]
            db.add_all(pens)
            db.flush()
            animals = [Animal(ear_tag=f'TR000{i + 1}', farm_ear_tag=f'00{i + 1}', breed='Simental',
                              arrival_date=ops.today_local() - timedelta(days=30), entry_weight_kg=Decimal('150'),
                              pen_id=pens[0 if i < 2 else 1].id, status='active') for i in range(3)]
            db.add_all(animals)
            db.commit()
            ids = [a.id for a in animals]
            groups = [p.id for p in pens]
        yield client, maker, app, ids, groups
    engine.dispose()


def day(offset=-1):
    return (ops.today_local() + timedelta(days=offset)).isoformat()


def test_lookup_uses_whole_database_and_preserves_ear_identity(pilot):
    client, maker, _, ids, groups = pilot
    with maker() as db:
        db.add_all([Animal(ear_tag=f'FILL-{i}', arrival_date=ops.today_local(), entry_weight_kg=1,
                           pen_id=groups[2], status='active') for i in range(510)])
        db.commit()
    result = client.post('/api/animal-operations/lookup', json={'tags': '001, TR0002'}).json()
    assert result['valid'] and [r['id'] for r in result['rows']] == ids[:2]
    assert result['rows'][0]['farm_ear_tag'] == '001'
    assert result['rows'][0]['tr_ear_tag'] == 'TR0001'
    duplicate = client.post('/api/animal-operations/lookup', json={'tags': '001, TR0001, YOK'}).json()
    assert duplicate['count'] == 1
    assert {w['code'] for w in duplicate['warnings']} == {'duplicate', 'unknown'}


def test_lookup_flags_ambiguous_and_exited_without_guessing(pilot):
    client, maker, _, ids, _ = pilot
    with maker() as db:
        db.get(Animal, ids[1]).farm_ear_tag = 'TR0001'
        db.get(Animal, ids[2]).status = 'exited'
        db.commit()
    result = client.post('/api/animal-operations/lookup', json={'tags': 'TR0001, 003'}).json()
    assert not result['rows']
    assert {w['code'] for w in result['warnings']} == {'ambiguous', 'inactive'}
    # A single animal using the same text in its two identity fields is still one match.
    with maker() as db:
        db.get(Animal, ids[0]).farm_ear_tag = 'tr0001'
        db.get(Animal, ids[1]).farm_ear_tag = '002'
        db.commit()
    assert client.post('/api/animal-operations/lookup', json={'tags': 'TR0001'}).json()['valid']


def test_weighing_batch_is_atomic_and_repeated_submission_is_rejected(pilot):
    client, maker, _, ids, _ = pilot
    payload = {'measured_at': day(), 'entries': [{'animal_id': ids[0], 'weight_kg': '302.125'},
                                                {'animal_id': 99999, 'weight_kg': '310'}]}
    assert client.post('/api/animal-operations/bulk-weighings', json=payload).status_code == 404
    with maker() as db:
        assert db.scalar(select(func.count(Weighing.id))) == 0
    payload['entries'][1]['animal_id'] = ids[1]
    assert client.post('/api/animal-operations/bulk-weighings', json=payload).status_code == 201
    assert client.post('/api/animal-operations/bulk-weighings', json=payload).status_code == 409
    with maker() as db:
        records = db.scalars(select(Weighing).order_by(Weighing.animal_id)).all()
        assert len(records) == 2 and records[0].weight_kg == Decimal('302.125')
        events = db.scalars(select(security.AuditEvent).where(security.AuditEvent.table_name == 'weighings')).all()
        assert all('legacytester' in e.actor for e in events)


def test_batch_rejects_duplicate_animals_and_dates_before_arrival(pilot):
    client, maker, _, ids, _ = pilot
    for payload in [
        {'measured_at': day(), 'entries': [{'animal_id': ids[0], 'weight_kg': 300}] * 2},
        {'measured_at': day(-31), 'entries': [{'animal_id': ids[0], 'weight_kg': 300}]},
        {'measured_at': day(1), 'entries': [{'animal_id': ids[0], 'weight_kg': 300}]},
    ]:
        assert client.post('/api/animal-operations/bulk-weighings', json=payload).status_code in (409, 422)
    with maker() as db:
        assert db.scalar(select(func.count(Weighing.id))) == 0


def test_transfer_checks_final_capacity_and_keeps_history(pilot):
    client, maker, _, ids, groups = pilot
    payload = {'transferred_on': day(), 'entries': [{'animal_id': ids[0], 'pen_id': groups[1]}]}
    assert client.post('/api/animal-operations/bulk-transfer', json=payload).status_code == 409
    with maker() as db:
        assert db.get(Animal, ids[0]).pen_id == groups[0]
        assert db.scalar(select(func.count(ops.AnimalGroupTransfer.id))) == 0
    payload['entries'].append({'animal_id': ids[2], 'pen_id': groups[0]})
    assert client.post('/api/animal-operations/bulk-transfer', json=payload).status_code == 200
    with maker() as db:
        assert db.get(Animal, ids[0]).pen_id == groups[1]
        assert db.get(Animal, ids[2]).pen_id == groups[0]
        assert db.scalar(select(func.count(ops.AnimalGroupTransfer.id))) == 2
    payload = {'transferred_on': day(-2), 'entries': [{'animal_id': ids[0], 'pen_id': groups[2]}]}
    assert client.post('/api/animal-operations/bulk-transfer', json=payload).status_code == 422


def test_new_entry_validates_both_identity_namespaces_and_capacity(pilot):
    client, maker, _, _, groups = pilot
    def entry(tag, farm=None):
        return {'tr_ear_tag': tag, 'farm_ear_tag': farm, 'pen_id': groups[2], 'entry_weight_kg': '125.5',
                'sex': 'female', 'breed': 'Montofon', 'birth_date': day(-50)}
    for entries in [
        [entry('TR100'), entry('TR100')],
        [entry('TR100'), entry('TR101', 'TR100')],
        [entry('001')],  # An existing farm tag cannot become another animal's TR tag.
        [entry('TR100'), entry('TR101'), entry('TR102')],
    ]:
        assert client.post('/api/animal-operations/bulk-create', json={'arrival_date': day(), 'entries': entries}).status_code == 409
    with maker() as db:
        assert db.scalar(select(func.count(Animal.id))) == 3
    response = client.post('/api/animal-operations/bulk-create', json={'arrival_date': day(),
                            'entries': [entry('TR0100', '000100'), entry('TR0101', '000101')]})
    assert response.status_code == 201, response.text
    assert response.json()['rows'][0]['farm_ear_tag'] == '000100'
    with maker() as db:
        assert db.scalar(select(Animal).where(Animal.ear_tag == 'TR0100')).entry_weight_kg == Decimal('125.500')


def test_exit_batch_is_atomic_preserves_snapshots_and_rejects_repeat(pilot):
    client, maker, _, ids, groups = pilot
    payload = {'exit_date': day(), 'reason': 'sale', 'destination': 'Merkez Çiftlik',
               'entries': [{'animal_id': ids[0], 'exit_kg': '350.5'}, {'animal_id': ids[1]}]}
    assert client.post('/api/animal-operations/bulk-exit', json=payload).status_code == 422
    with maker() as db:
        assert db.scalar(select(func.count(ops.AnimalExit.id))) == 0
        assert db.get(Animal, ids[0]).status == 'active'
    payload['entries'][1]['exit_kg'] = '360'
    assert client.post('/api/animal-operations/bulk-exit', json=payload).status_code == 200
    assert client.post('/api/animal-operations/bulk-exit', json=payload).status_code == 409
    with maker() as db:
        assert db.get(Animal, ids[0]).status == 'exited'
        db.get(Animal, ids[0]).ear_tag = 'SONRA-DEGISTI'
        db.get(Animal, ids[0]).pen_id = groups[2]
        db.commit()
    rows = client.get('/api/animal-operations/exits?reason=sale').json()['rows']
    first = next(r for r in rows if r['animal_id'] == ids[0])
    assert first['tr_ear_tag'] == 'TR0001' and first['group_no'] == '01'
    assert first['reason_label'] == 'Satış' and first['exit_kg'] == '350.500'
    text = client.get('/api/animal-operations/exits.csv').text
    assert 'Çıkış Nedeni' in text and 'Satış' in text and 'sale' not in text


def test_death_keeps_unknown_weight_null_and_exit_cannot_precede_last_weighing(pilot):
    client, maker, _, ids, _ = pilot
    assert client.post('/api/animal-operations/bulk-weighings', json={'measured_at': day(),
                       'entries': [{'animal_id': ids[0], 'weight_kg': '300'}]}).status_code == 201
    payload = {'exit_date': day(-2), 'reason': 'death', 'entries': [{'animal_id': ids[0]}]}
    assert client.post('/api/animal-operations/bulk-exit', json=payload).status_code == 422
    payload['exit_date'] = day()
    assert client.post('/api/animal-operations/bulk-exit', json=payload).status_code == 200
    with maker() as db:
        record = db.scalar(select(ops.AnimalExit))
        assert record.exit_kg is None and record.destination == ''
    assert client.get('/api/animal-operations/exits').json()['rows'][0]['reason_label'] == 'Ölüm'


def test_handler_permissions_and_csrf_are_enforced(pilot):
    admin, maker, app, ids, groups = pilot
    created = admin.post('/api/auth/users', json={'username': 'weigher', 'password': 'WeigherPassword2026',
        'display_name': 'Tartım Sorumlusu', 'permissions': ['hayvanlar.tartim.create']})
    assert created.status_code == 201, created.text
    with TestClient(app) as operator:
        login = operator.post('/api/auth/login', json={'username': 'weigher', 'password': 'WeigherPassword2026'})
        operator.headers['X-CSRF-Token'] = login.json()['csrf_token']
        assert operator.post('/api/animal-operations/lookup', json={'tags': '001'}).status_code == 200
        assert operator.get('/api/animal-operations/groups').status_code == 403
        assert operator.get('/api/animal-operations/exits').status_code == 403
        assert operator.get('/api/animal-operations/exits.csv').status_code == 403
        assert operator.post('/api/animal-operations/bulk-transfer', json={'transferred_on': day(),
            'entries': [{'animal_id': ids[0], 'pen_id': groups[2]}]}).status_code == 403
        payload = {'measured_at': day(), 'entries': [{'animal_id': ids[0], 'weight_kg': '300'}]}
        operator.headers.pop('X-CSRF-Token')
        assert operator.post('/api/animal-operations/bulk-weighings', json=payload).status_code == 403
        operator.headers['X-CSRF-Token'] = login.json()['csrf_token']
        assert operator.post('/api/animal-operations/bulk-weighings', json=payload).status_code == 201
    with maker() as db:
        assert db.scalar(select(func.count(Weighing.id))) == 1
    anonymous = TestClient(app)
    try:
        assert anonymous.post('/api/animal-operations/lookup', json={'tags': '001'}).status_code == 401
    finally:
        anonymous.close()
