"""v0.14: kullanıcıya görünen doğrulama ve mükerrer kayıt mesajları."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main
from app.db import get_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "validation.db"}',
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
        # Ortak test fixture'ı yalnızca bu geçici DB'de test yöneticisi açar.
        with TestClient(main.app) as signed_in:
            yield signed_in
    finally:
        engine.dispose()


@pytest.mark.parametrize('endpoint,payload,label,technical_name', [
    ('/api/fields', {'code': 'P-01', 'name': 'Deneme', 'area_decare': '0'}, 'Alan (dekar)', 'area_decare'),
    ('/api/fields', {'code': '', 'name': 'Deneme', 'area_decare': '12.5'}, 'Kod', 'code'),
    ('/api/fields', {'code': 'P-01', 'name': 'Deneme', 'area_decare': '12.5', 'ada_no': '1' * 41}, 'Ada No', 'ada_no'),
    ('/api/pens', {'code': 'P-01', 'capacity': 0}, 'Padok kapasitesi', 'capacity'),
    ('/api/seasons', {'field_id': 1, 'year': 1999, 'crop': 'Buğday'}, 'Üretim yılı', 'year'),
    ('/api/animals', {'ear_tag': 'TR-01', 'pen_id': 1, 'arrival_date': '2026-11-06', 'entry_weight_kg': 0}, 'Giriş kilosu', 'entry_weight_kg'),
    ('/api/receiving/weighings', {'supplier_tax_id': '1234567890', 'item_id': 1, 'weigh_ticket_no': 'F-01', 'gross_kg': 0, 'tare_kg': 0}, 'Brüt kilo', 'gross_kg'),
    ('/api/reports/query', {'query': 'a'}, 'Rapor isteği', 'query'),
    ('/api/calves/bulk-exit', {'exit_date': '2026-11-06', 'entries': [{'calf_id': 1, 'exit_kg': -1}]}, 'Çıkış kilosu', 'exit_kg'),
])
def test_invalid_inputs_show_turkish_field_labels(client, endpoint, payload, label, technical_name):
    result = client.post(endpoint, json=payload)
    assert result.status_code == 422, result.text
    detail = result.json()['detail']
    assert label in detail
    assert technical_name not in detail
    assert 'Input should' not in detail
    assert client.get('/api/fields').json() == []


def test_invalid_path_parameter_has_turkish_label(client):
    result = client.get('/api/fields/gecersiz/satellite-image')
    assert result.status_code == 422
    assert 'Parsel' in result.json()['detail']
    assert 'field_id' not in result.json()['detail']


def test_nested_draft_error_does_not_expose_internal_or_user_supplied_keys(client):
    result = client.put('/api/auth/drafts/deneme', json={'values': {'internal_secret_field': []}})
    assert result.status_code == 422
    detail = result.json()['detail']
    assert 'Taslak bilgileri' in detail
    assert 'internal_secret_field' not in detail
    assert 'str' not in detail and 'float' not in detail and 'bool' not in detail
    assert detail.count('Taslak bilgileri') == 1
    assert client.get('/api/auth/drafts/deneme').json()['values'] == {}


def test_malformed_body_has_a_safe_turkish_fallback(client):
    result = client.post('/api/fields', content='{"internal_secret_field":',
                         headers={'Content-Type': 'application/json'})
    assert result.status_code == 422
    assert result.json() == {
        'detail': 'Eksik veya geçersiz bilgi: Girilen bilgiler. Alanları kontrol edin.'
    }
    assert client.get('/api/fields').json() == []


@pytest.mark.parametrize('endpoint,payload,label', [
    ('/api/fields', {'code': 'P-01', 'name': 'Deneme', 'area_decare': '12.5'}, 'Parsel kodu'),
    ('/api/pens', {'code': 'P-01', 'capacity': 10}, 'Padok kodu'),
    ('/api/items', {'code': 'ARPA', 'name': 'Arpa', 'unit': 'kg'}, 'Ürün kodu'),
    ('/api/firms', {'name': 'Deneme Firması', 'tax_no': '1234567890'}, 'Vergi numarası'),
])
def test_duplicate_record_messages_identify_the_field_in_turkish(client, endpoint, payload, label):
    assert client.post(endpoint, json=payload).status_code == 201
    duplicate = client.post(endpoint, json=payload)
    assert duplicate.status_code == 409, duplicate.text
    detail = duplicate.json()['detail']
    assert label in detail and 'zaten kayıtlı' in detail
    assert 'code' not in detail and 'tax_no' not in detail
    assert len(client.get(endpoint).json()) == 1


def test_duplicate_animal_message_uses_turkish_ear_tag_label(client):
    pen = client.post('/api/pens', json={'code': 'P-01', 'capacity': 10}).json()['id']
    animal = {'ear_tag': 'TR-01', 'pen_id': pen, 'arrival_date': '2026-11-06', 'entry_weight_kg': '100'}
    assert client.post('/api/animals', json=animal).status_code == 201
    duplicate = client.post('/api/animals', json=animal)
    assert duplicate.status_code == 409
    assert duplicate.json()['detail'] == 'TR küpe numarası zaten kayıtlı.'
    assert len(client.get('/api/animals').json()) == 1


def test_release_version_is_consistent_in_api(client):
    assert client.get('/api/health').json() == {'status': 'ok', 'version': '0.14.0'}
    assert client.get('/openapi.json').json()['info']['version'] == '0.14.0'


def test_invalid_stock_direction_uses_visible_turkish_choices(client):
    item = client.post('/api/items', json={'code': 'ARPA', 'name': 'Arpa', 'unit': 'kg'}).json()['id']
    invalid = {'item_id': item, 'type': 'ADJUST', 'quantity': '10'}
    result = client.post('/api/stock-movements', json=invalid)
    assert result.status_code == 422
    expected = {'detail': 'Hareket türü Giriş veya Çıkış olmalı.'}
    assert result.json() == expected
    movement = client.post('/api/stock-movements', json={**invalid, 'type': 'IN'}).json()['id']
    result = client.put(f'/api/stock-movements/{movement}', json={**invalid, 'reason': 'Düzeltme denemesi'})
    assert result.status_code == 422 and result.json() == expected
    assert client.get('/api/stock').json()[0]['balance'] == '10.000'
