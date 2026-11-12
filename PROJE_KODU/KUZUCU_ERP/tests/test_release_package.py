import hashlib
import json
from pathlib import Path
import runpy
import zipfile

import pytest

builder = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tools/build_release.py'))


def sample_repo(tmp_path):
    root = tmp_path / 'source'
    app = root / 'PROJE_KODU/KUZUCU_ERP'
    (app / 'app').mkdir(parents=True)
    (app / 'app/main.py').write_text("APP_VERSION = '0.14.0'\napp = FastAPI(version=APP_VERSION)\n")
    (root / 'GELISTIRME_LISTESI.md').write_text('Geliştirme listesi', encoding='utf-8')
    return root, app


def test_download_package_excludes_private_data_and_verifies_sources(tmp_path):
    root, app = sample_repo(tmp_path)
    for relative in ['ciftlik.db', '.env', 'data/parcel_images/ozel.png', 'data/documents/ozel.jpg',
                     'raporlar/ozel.pdf', 'app/static/ozel.jpg', 'app/static/ozel.png',
                     'app/uploads/ozel.md', 'app/.ozel/bilgi.py',
                     '.venv/private.py', 'app/__pycache__/cached.py', 'app/key.pem', '.git/config']:
        path = app / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('PAKETE_GIRMEMELI')
    result = builder['build_package'](root, tmp_path / 'release.zip')
    with zipfile.ZipFile(result['archive']) as archive:
        assert archive.testzip() is None
        assert 'GELISTIRME_LISTESI.md' in archive.namelist()
        assert all(b'PAKETE_GIRMEMELI' not in archive.read(n) for n in archive.namelist())
        for line in archive.read('DOSYA_DOGRULAMA.sha256').decode().splitlines():
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        metadata = json.loads(archive.read('PAKET_BILGILERI.json'))
        assert metadata['version'] == '0.14.0'
        assert metadata['contains_user_database'] is False
    assert hashlib.sha256(Path(result['archive']).read_bytes()).hexdigest() == result['sha256']


def test_v015_package_declares_schema_change_and_is_reproducible(tmp_path):
    root, app = sample_repo(tmp_path)
    (app / 'app/main.py').write_text("APP_VERSION = '0.15.0'\napp = FastAPI(version=APP_VERSION)\n")
    logo = app / 'app/static/kuzucu_logo.png'
    logo.parent.mkdir()
    logo.write_bytes(b'BRAND')
    photos = root / 'EKRAN_REFERANSLARI'
    photos.mkdir()
    (photos / 'ozel.png').write_bytes(b'BUSINESS_IMAGE')
    first = builder['build_package'](root, tmp_path / 'first.zip')
    second = builder['build_package'](root, tmp_path / 'second.zip')
    assert first['sha256'] == second['sha256']
    with zipfile.ZipFile(first['archive']) as archive:
        metadata = json.loads(archive.read('PAKET_BILGILERI.json'))
        assert metadata['schema_change'] is True
        assert metadata['contains_business_photos'] is False
        assert archive.read('PROJE_KODU/KUZUCU_ERP/app/static/kuzucu_logo.png') == b'BRAND'
        assert all('EKRAN_REFERANSLARI' not in name for name in archive.namelist())


def test_download_package_rejects_symlinked_source(tmp_path):
    root, app = sample_repo(tmp_path)
    outside = tmp_path / 'private.py'
    outside.write_text('SECRET')
    (app / 'app/private.py').symlink_to(outside)
    with pytest.raises(ValueError, match='sembolik'):
        builder['build_package'](root, tmp_path / 'release.zip')
