"""Parsel kaydı: Türkçe sayı, mükerrer kod ve boşluk düzeltmeleri (11.11.2026 incelemesi)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main
from app.db import get_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "parcel.db"}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR', str(tmp_path / 'reports'))
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def local_db():
        with maker() as db:
            yield db

    monkeypatch.setitem(main.app.dependency_overrides, get_db, local_db)
    try:
        with TestClient(main.app) as c:
            yield c
    finally:
        engine.dispose()


def add(client, code, area='12.5', ada='101', name='Tarla'):
    return client.post('/api/fields', json={'ada_no': ada, 'code': code, 'name': name, 'area_decare': area})


def test_code_and_text_are_trimmed_and_empty_ada_is_null(client):
    r = add(client, '  P-1  ', ada='  ', name='  Kuzey  ')
    assert r.status_code == 201, r.text
    assert r.json()['code'] == 'P-1' and r.json()['ada_no'] is None and r.json()['name'] == 'Kuzey'
    assert add(client, '   ').status_code == 422


@pytest.mark.parametrize('variant', ['P-1', ' P-1 ', 'p-1', 'P - 1'])
def test_duplicate_code_variants_rejected_in_turkish(client, variant):
    assert add(client, 'P-1').status_code == 201
    r = add(client, variant)
    assert r.status_code == 409
    assert 'Parsel kodu zaten kayıtlı: P-1' in r.json()['detail']
    assert len(client.get('/api/fields').json()) == 1


def test_turkish_dotted_i_variants_are_same_code(client):
    assert add(client, 'KIRIK-1').status_code == 201
    assert add(client, 'kırık-1').status_code == 409
    assert add(client, 'KİRİK-1').status_code == 409


def test_more_than_three_decimals_is_rejected_not_rounded(client):
    r = add(client, 'P-2', area='3.12345')
    assert r.status_code == 422
    assert 'Alan (dekar)' in r.json()['detail']
    assert client.get('/api/fields').json() == []


def test_edit_keeps_own_code_and_blocks_other_parcel_code(client):
    a = add(client, 'P-1').json()
    add(client, 'P-2')
    same = client.put(f"/api/fields/{a['id']}", json={'ada_no': '', 'code': 'p-1 ', 'name': 'Tarla', 'area_decare': '1250'})
    assert same.status_code == 200 and same.json()['area_decare'] == '1250.000' and same.json()['ada_no'] is None
    other = client.put(f"/api/fields/{a['id']}", json={'ada_no': '1', 'code': 'p-2', 'name': 'Tarla', 'area_decare': '5'})
    assert other.status_code == 409


def test_frontend_area_inputs_use_turkish_decimal_box():
    from pathlib import Path
    static = Path(main.__file__).parent / 'static'
    parcels = (static / 'parcels.js').read_text(encoding='utf-8')
    index = (static / 'index.html').read_text(encoding='utf-8')
    # Tarayıcının sayı kutusu 12,5'i 125 yapıyordu; parsel alanı artık Türkçe metin kutusu.
    assert 'type="number"' not in parcels
    assert "type:'trDecimal'" in parcels and 'convertTrDecimals(e.target,d)' in parcels
    assert "inp('weight_kg','Canlı ağırlık (kg)','number')" not in index
    assert "document.addEventListener('invalid'" in index
    assert 'clearTimeout(messageTimer)' in index
