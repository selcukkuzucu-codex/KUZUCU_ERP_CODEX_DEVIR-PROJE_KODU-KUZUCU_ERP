"""Yeni parsel ve isteğe bağlı görselin birlikte, veri kaybetmeden kaydedilmesi."""
from io import BytesIO
from pathlib import Path
import struct
import zlib

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.db import get_db
from app.models import Field


@pytest.fixture
def parcels(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "parcels.db"}', connect_args={'check_same_thread': False})
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'PARCEL_IMAGE_DIR', tmp_path / 'images')
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'backups'))
    monkeypatch.setenv('KUZUCU_REPORT_DIR', str(tmp_path / 'reports'))
    def localdb():
        with maker() as db:
            yield db
    main.app.dependency_overrides[get_db] = localdb
    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            yield client, maker, tmp_path / 'images'
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def picture(color='green', format='PNG'):
    image = BytesIO()
    Image.new('RGB', (20, 20), color).save(image, format=format)
    return image.getvalue()


def fields(code='PARSEL-15'):
    return {'ada_no': '155', 'code': code, 'name': 'Yeni arazi', 'area_decare': '35.5'}


def test_new_parcel_without_image_and_with_image_and_existing_replacement(parcels):
    client, maker, image_dir = parcels
    empty = client.post('/api/fields/with-image', data=fields('RESIMSIZ'))
    assert empty.status_code == 201 and empty.json()['satellite_image'] is None
    response = client.post('/api/fields/with-image', data=fields(), files={'file': ('../kullanici.png', picture(), 'image/png')})
    assert response.status_code == 201, response.text
    saved = response.json()
    filename = saved['satellite_image']
    assert filename.endswith('.jpg') and '/' not in filename and filename != '../kullanici.png'
    assert saved['area_decare'] == '35.500' and saved['ada_no'] == '155'
    old_file = image_dir / filename
    old_bytes = old_file.read_bytes()
    image = client.get(f'/api/fields/{saved["id"]}/satellite-image')
    assert image.status_code == 200 and image.headers['content-type'] == 'image/jpeg'
    assert image.content == old_bytes
    duplicate = client.post('/api/fields/with-image', data=fields(), files={'file': ('new.png', picture('blue'), 'image/png')})
    assert duplicate.status_code == 409
    assert len(list(image_dir.glob('*.jpg'))) == 1
    replacement = client.post(f'/api/fields/{saved["id"]}/satellite-image', files={'file': ('new.png', picture('blue'), 'image/png')})
    assert replacement.status_code == 200
    now = client.get('/api/fields?search=PARSEL-15').json()[0]
    assert now['satellite_image'] != filename
    assert old_file.read_bytes() == old_bytes, 'Önceki kullanıcı fotoğrafı silinmemeli.'
    assert client.get(f'/api/fields/{saved["id"]}/satellite-image').content != old_bytes
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(Field)) == 2


@pytest.mark.parametrize('file_bytes,expected', [(b'not a picture', 422), (b'x' * (10 * 1024 * 1024 + 1), 413), (picture(format='GIF'), 422)])
def test_invalid_file_keeps_no_parcel_and_retry_is_single_record(parcels, file_bytes, expected):
    client, maker, image_dir = parcels
    denied = client.post('/api/fields/with-image', data=fields(), files={'file': ('image.png', file_bytes, 'image/png')})
    assert denied.status_code == expected, denied.text
    assert not list(image_dir.glob('*'))
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(Field)) == 0
    retried = client.post('/api/fields/with-image', data=fields(), files={'file': ('valid.png', picture(), 'image/png')})
    assert retried.status_code == 201, retried.text
    assert len(client.get('/api/fields').json()) == 1


def test_oversized_resolution_is_rejected_before_decode_without_orphan(parcels):
    client, maker, image_dir = parcels
    png = bytearray(picture())
    # Büyük bir fotoğraf belleğe üretmeden geçerli PNG başlığı: 30 milyon piksel.
    png[16:24] = struct.pack('>II', 6000, 5000)
    png[29:33] = struct.pack('>I', zlib.crc32(png[12:29]) & 0xffffffff)
    result = client.post('/api/fields/with-image', data=fields(), files={'file': ('large.png', bytes(png), 'image/png')})
    assert result.status_code == 422 and 'çözünürlüğü' in result.json()['detail']
    assert client.get('/api/fields').json() == []
    assert not list(image_dir.glob('*'))


def test_form_validation_failure_does_not_write_image(parcels):
    client, maker, image_dir = parcels
    invalid = client.post('/api/fields/with-image', data={**fields(), 'area_decare': '0'}, files={'file': ('valid.png', picture(), 'image/png')})
    assert invalid.status_code == 422
    assert client.get('/api/fields').json() == []
    assert not list(image_dir.glob('*'))


def test_file_write_failure_rolls_back_parcel(parcels):
    client, maker, image_dir = parcels
    image_dir.write_text('Dosya yolu klasör değil; yazma hatasını taklit eder.')
    response = client.post('/api/fields/with-image', data=fields(), files={'file': ('valid.png', picture(), 'image/png')})
    assert response.status_code == 503, response.text
    assert 'kaydedilemedi' in response.json()['detail']
    assert client.get('/api/fields').json() == []
    assert image_dir.read_text().startswith('Dosya yolu')


def test_database_failure_removes_only_new_image_and_rolls_back_row(parcels, monkeypatch):
    client, maker, image_dir = parcels
    image_dir.mkdir()
    previous = image_dir / 'eski-kullanici-gorseli.jpg'
    previous.write_bytes(b'Korunacak dosya')
    original_commit = Session.commit
    def fail_parcel_commit(session):
        if session.info.get('test_fail_parcel_commit') and any(isinstance(row, Field) for row in session.identity_map.values()):
            raise RuntimeError('Deneme veritabanı kayıt hatası')
        return original_commit(session)
    maker.configure(info={'test_fail_parcel_commit': True})
    monkeypatch.setattr(Session, 'commit', fail_parcel_commit)
    response = client.post('/api/fields/with-image', data=fields(), files={'file': ('valid.png', picture(), 'image/png')})
    assert response.status_code == 500, response.text
    assert list(image_dir.iterdir()) == [previous]
    assert previous.read_bytes() == b'Korunacak dosya'
    with maker() as db:
        assert db.scalar(select(func.count()).select_from(Field)) == 0


def test_new_parcel_requires_csrf_and_create_permission(parcels):
    client, maker, image_dir = parcels
    csrf = client.headers.pop('X-CSRF-Token')
    assert client.post('/api/fields/with-image', data=fields()).status_code == 403
    client.headers['X-CSRF-Token'] = csrf
    user = client.post('/api/auth/users', json={'username': 'parcelviewer', 'password': 'ParcelPassword2026', 'display_name': 'Parsel Görüntüleyici', 'permissions': ['tarim.parseller.view']})
    assert user.status_code == 201, user.text
    signed = client.post('/api/auth/login', json={'username': 'parcelviewer', 'password': 'ParcelPassword2026'})
    assert signed.status_code == 200, signed.text
    client.headers['X-CSRF-Token'] = signed.json()['csrf_token']
    assert client.post('/api/fields/with-image', data=fields()).status_code == 403
    assert client.get('/api/fields').json() == []
    assert client.post('/api/auth/logout').status_code == 200
    assert client.post('/api/fields/with-image', data=fields()).status_code == 401
