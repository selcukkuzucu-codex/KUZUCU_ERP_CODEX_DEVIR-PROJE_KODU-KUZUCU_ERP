"""Süreli sağlık planı: gerçek onay ve uygulama geçmişinden ayrı planlama."""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import sqlite3
import subprocess

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app import animal_health, main
from app.db import get_db
from app.models import HealthCase, HealthDailyLog


@pytest.fixture
def health_client(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "health-v015.db"}', connect_args={'check_same_thread': False})
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR', str(tmp_path / 'reports'))
    def localdb():
        with maker() as db:
            yield db
    main.app.dependency_overrides[get_db] = localdb
    monkeypatch.setattr(animal_health, 'today_local', lambda: date(2026, 12, 31))
    try:
        with TestClient(main.app) as client:
            pen = client.post('/api/pens', json={'code': 'SAGLIK-GRUP', 'capacity': 30})
            assert pen.status_code == 201, pen.text
            animal = client.post('/api/animals', json={
                'tr_ear_tag': 'TR-SAGLIK-15', 'farm_ear_tag': 'IS-SAGLIK-15',
                'arrival_date': '2026-01-01', 'entry_weight_kg': '250', 'pen_id': pen.json()['id']})
            assert animal.status_code == 201, animal.text
            yield client, animal.json()['id'], maker, engine
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def payload(animal, **values):
    return {'animal_id': animal, 'condition_name': 'Süreli sağlık takibi', 'record_type': 'treatment',
            'product_name': 'Kullanıcının kayıtlı ürünü', 'duration_days': 3, 'notes': 'Günlük takip', **values}


def pdf_text(source):
    return ' '.join(' '.join(page.extract_text() for page in PdfReader(source).pages).split())


@pytest.mark.parametrize('days,expected_end', [(1, '2026-12-31'), (3, '2027-01-02')])
def test_duration_daily_scope_has_no_fabricated_approval_or_application(health_client, days, expected_end):
    client, animal, maker, _ = health_client
    result = client.post('/api/animal-health/cases', json=payload(animal, duration_days=days,
                           start_date='2000-01-01', planned_end_date='2000-01-02'))
    assert result.status_code == 201, result.text
    case = result.json()
    assert case['start_date'] == '2026-12-31' and case['planned_end_date'] == expected_end
    assert case['duration_days'] == days and case['vet_approved'] is False
    assert case['farm_ear_tag'] == 'IS-SAGLIK-15'
    for offset in range(-1, days + 1):
        day = date(2026, 12, 31) + timedelta(days=offset)
        rows = client.get('/api/animal-health/daily', params={'on': day.isoformat()}).json()['cases']
        assert any(row['case_id'] == case['id'] for row in rows) is (0 <= offset < days)
        if rows:
            assert rows[0]['status'] == 'due' and rows[0]['performed_count'] == 0
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(HealthDailyLog)) == 0
        stored = db.get(HealthCase, case['id'])
        assert stored.status == 'active' and stored.outcome is None and not stored.vet_approved
    pdf = client.get('/api/animal-health/daily.pdf', params={'on': expected_end})
    assert pdf.status_code == 200 and 'Süreli sağlık' in pdf_text(BytesIO(pdf.content))
    after = (date.fromisoformat(expected_end) + timedelta(days=1)).isoformat()
    pdf = client.get('/api/animal-health/daily.pdf', params={'on': after})
    assert 'Süreli sağlık' not in pdf_text(BytesIO(pdf.content))


@pytest.mark.parametrize('invalid', [0, -1, 1.5, '3', True, 10**30])
def test_duration_rejects_non_positive_or_non_integer_days(health_client, invalid):
    client, animal, maker, _ = health_client
    response = client.post('/api/animal-health/cases', json=payload(animal, duration_days=invalid))
    assert response.status_code == 422, response.text
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(HealthCase)) == 0


def test_duration_edit_keeps_start_and_medical_history_and_blocks_lost_logs(health_client, monkeypatch):
    client, animal, maker, _ = health_client
    old = client.post('/api/animal-health/cases', json={
        'animal_id': animal, 'record_type': 'treatment', 'condition_name': 'Eski sağlık kaydı',
        'symptoms': 'Korunacak klinik bilgi', 'veterinarian': 'Kayıtlı Veteriner', 'vet_approved': True,
        'start_date': '2026-12-29', 'planned_end_date': '2026-12-31', 'withdrawal_end_date': '2027-01-10',
        'product_name': 'Geçmiş ürün', 'applications_per_day': 1})
    assert old.status_code == 201, old.text
    case_id = old.json()['id']
    log = client.post(f'/api/animal-health/cases/{case_id}/logs', json={'performed_on': '2026-12-31', 'performed_by': 'Deneme Personeli'})
    assert log.status_code == 201, log.text
    # Yeni form gizlenen metadata'yı göndermez. Düzenleme gününe taşınmamalı.
    monkeypatch.setattr(animal_health, 'today_local', lambda: date(2027, 1, 5))
    edit = payload(animal, condition_name='Güncellenen sağlık kaydı', product_name='Geçmiş ürün', duration_days=4)
    response = client.put(f'/api/animal-health/cases/{case_id}', json=edit)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated['start_date'] == '2026-12-29' and updated['planned_end_date'] == '2027-01-01'
    assert updated['symptoms'] == 'Korunacak klinik bilgi'
    assert updated['vet_approved'] is True and updated['veterinarian'] == 'Kayıtlı Veteriner'
    assert updated['withdrawal_end_date'] == '2027-01-10'
    denied = client.put(f'/api/animal-health/cases/{case_id}', json={**edit, 'duration_days': 1})
    assert denied.status_code == 409 and 'geçmiş uygulama' in denied.json()['detail']
    with maker() as db:
        assert db.get(HealthCase, case_id).duration_days == 4
        assert db.scalar(select(func.count()).select_from(HealthDailyLog)) == 1


def test_duration_allows_real_logs_without_fake_veterinary_approval_and_preserves_repeat_warning(health_client):
    client, animal, maker, _ = health_client
    one = client.post('/api/animal-health/cases', json=payload(animal)).json()
    log = {'performed_on': '2026-12-31', 'performed_by': 'Deneme Personeli'}
    assert client.post(f'/api/animal-health/cases/{one["id"]}/logs', json=log).status_code == 201
    blocked = client.post('/api/animal-health/cases', json=payload(animal))
    assert blocked.status_code == 409
    assert blocked.json()['detail']['code'] == 'SAME_MEDICATION_WITHIN_10_DAYS'
    approved_review = client.post('/api/animal-health/cases', json=payload(animal, repeat_review_confirmed=True))
    assert approved_review.status_code == 201, approved_review.text
    assert approved_review.json()['vet_approved'] is False
    assert approved_review.json()['repeat_review_confirmed'] is True
    assert client.post(f'/api/animal-health/cases/{approved_review.json()["id"]}/logs', json=log).status_code == 201
    closed = client.post(f'/api/animal-health/cases/{one["id"]}/close', json={'closed_date': '2026-12-31', 'outcome': 'improved'})
    assert closed.status_code == 200, closed.text
    insight = client.get('/api/animal-health/insights', params={'condition': 'Süreli sağlık takibi'}).json()
    assert insight['completed_vet_approved_cases'] == 0
    with maker() as db:
        assert not db.get(HealthCase, one['id']).vet_approved


def test_auto_pdf_refreshes_on_new_and_edited_plan_without_printing_or_auto_logs(health_client, tmp_path, monkeypatch):
    client, animal, maker, engine = health_client
    calls = []
    monkeypatch.setattr(animal_health, 'send_to_printer', lambda *args: calls.append(args))
    assert client.put('/api/animal-health/print-settings', json={'daily_time': '00:00', 'auto_generate': True, 'auto_print': False}).status_code == 200
    animal_health.scheduled_daily_tick(engine)
    pdf_path = tmp_path / 'reports' / '2026-12-31_hayvan_sagligi_gunluk.pdf'
    assert pdf_path.is_file()
    created = client.post('/api/animal-health/cases', json=payload(animal, condition_name='Yeni günlük sağlık kaydı'))
    assert created.status_code == 201, created.text
    assert 'Yeni günlük sağlık kaydı' in pdf_text(pdf_path)
    edited = client.put(f'/api/animal-health/cases/{created.json()["id"]}', json=payload(animal, condition_name='Değişen günlük sağlık kaydı', duration_days=1))
    assert edited.status_code == 200, edited.text
    updated_pdf = pdf_text(pdf_path)
    assert 'Değişen günlük sağlık kaydı' in updated_pdf and 'Yeni günlük sağlık kaydı' not in updated_pdf
    assert '31.12.2026 - 31.12.2026' in updated_pdf
    before = pdf_path.stat().st_mtime_ns
    animal_health.scheduled_daily_tick(engine)
    assert pdf_path.stat().st_mtime_ns == before
    assert not calls
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(HealthDailyLog)) == 0


def test_duration_migration_is_additive_and_repeatable(tmp_path):
    path = tmp_path / 'legacy-health.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE health_cases (id INTEGER PRIMARY KEY, symptoms TEXT, vet_approved BOOLEAN, start_date DATE)')
        db.execute("INSERT INTO health_cases VALUES (1, 'Eski klinik bilgi', 1, '2026-11-01')")
    engine = create_engine(f'sqlite:///{path}')
    animal_health.migrate_v015(engine)
    animal_health.migrate_v015(engine)
    with sqlite3.connect(path) as db:
        row = db.execute('SELECT symptoms, vet_approved, start_date, duration_days FROM health_cases WHERE id=1').fetchone()
        assert row == ('Eski klinik bilgi', 1, '2026-11-01', None)
    engine.dispose()


def test_duration_plan_still_requires_session_csrf_and_create_permission(health_client):
    client, animal, maker, _ = health_client
    csrf = client.headers.pop('X-CSRF-Token')
    assert client.post('/api/animal-health/cases', json=payload(animal)).status_code == 403
    client.headers['X-CSRF-Token'] = csrf
    created = client.post('/api/auth/users', json={
        'username': 'healthviewer', 'password': 'ViewerPassword2026', 'display_name': 'Sağlık Görüntüleyici',
        'permissions': ['hayvanlar.saglik.view']})
    assert created.status_code == 201, created.text
    signed = client.post('/api/auth/login', json={'username': 'healthviewer', 'password': 'ViewerPassword2026'})
    assert signed.status_code == 200, signed.text
    client.headers['X-CSRF-Token'] = signed.json()['csrf_token']
    assert client.get('/api/animal-health/daily', params={'on': '2026-12-31'}).status_code == 200
    assert client.post('/api/animal-health/cases', json=payload(animal)).status_code == 403
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(HealthCase)) == 0
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/animal-health/daily', params={'on': '2026-12-31'}).status_code == 401


def test_print_system_messages_are_turkish(monkeypatch, tmp_path):
    monkeypatch.setattr(animal_health.subprocess, 'run', lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, '', 'lp: Error - unknown destination'))
    with pytest.raises(RuntimeError, match='Yazdırma tamamlanamadı') as failure:
        animal_health.send_to_printer(tmp_path / 'test.pdf')
    assert 'unknown destination' not in str(failure.value)
    monkeypatch.setattr(animal_health.subprocess, 'run', lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, 'request id is printer-11', ''))
    assert animal_health.send_to_printer(tmp_path / 'test.pdf') == 'Yazdırma işi yazıcıya gönderildi.'
