"""v0.16 kolay güncelleme: kayıtlar yerinde kalır, önce tam yedek alınır, açık programda durur."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import update_install  # noqa: E402


def old_install(root: Path, version='0.15.0') -> Path:
    target = root / 'Desktop' / 'KUZUCU_ERP'
    (target / 'app').mkdir(parents=True)
    (target / 'app' / 'main.py').write_text(f"APP_VERSION = '{version}'\n", encoding='utf-8')
    (target / 'app' / 'eski_modul.py').write_text('# kaldırılmış eski dosya\n', encoding='utf-8')
    with sqlite3.connect(target / 'ciftlik.db') as db:
        db.execute('CREATE TABLE kayit (ad TEXT)')
        db.execute("INSERT INTO kayit VALUES ('gerçek kayıt')")
    (target / 'data' / 'parcel_images').mkdir(parents=True)
    (target / 'data' / 'parcel_images' / 'tarla.jpg').write_bytes(b'gorsel')
    (target / 'raporlar').mkdir()
    (target / 'raporlar' / 'rapor.pdf').write_bytes(b'pdf')
    (target / '.venv').mkdir()
    (target / '.venv' / 'isaret').write_text('ortam', encoding='utf-8')
    return target


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'Yedekler'))
    monkeypatch.setattr(update_install, 'server_running', lambda port=8000: False)
    return tmp_path


def test_update_keeps_records_and_takes_full_backup(env):
    target = old_install(env)
    assert update_install.run(['--target', str(target), '--yes']) == 0
    assert update_install.version_of(target) == update_install.version_of(update_install.SOURCE) == '0.16.0'
    assert not (target / 'app' / 'eski_modul.py').exists()
    assert (target / 'app' / 'v16.py').is_file() and (target / 'GUNCELLE_MAC.command').is_file()
    with sqlite3.connect(target / 'ciftlik.db') as db:
        assert db.execute('SELECT ad FROM kayit').fetchall() == [('gerçek kayıt',)]
    assert (target / 'data' / 'parcel_images' / 'tarla.jpg').read_bytes() == b'gorsel'
    assert (target / 'raporlar' / 'rapor.pdf').is_file() and (target / '.venv' / 'isaret').is_file()
    backups = list((env / 'Yedekler').glob('surum_oncesi_v0.15.0_*'))
    assert len(backups) == 1
    saved = backups[0]
    assert (saved / 'app' / 'eski_modul.py').is_file() and (saved / 'data' / 'parcel_images' / 'tarla.jpg').is_file()
    assert not (saved / '.venv').exists()
    with sqlite3.connect(saved / 'ciftlik.db') as db:
        assert db.execute('SELECT ad FROM kayit').fetchall() == [('gerçek kayıt',)]


def test_update_refuses_when_program_is_running(env, monkeypatch, capsys):
    target = old_install(env)
    monkeypatch.setattr(update_install, 'server_running', lambda port=8000: True)
    assert update_install.run(['--target', str(target), '--yes']) == 2
    assert 'Control+C' in capsys.readouterr().out
    assert update_install.version_of(target) == '0.15.0' and not (env / 'Yedekler').exists()


def test_update_refuses_downgrade_and_missing_target(env, capsys):
    newer = old_install(env, version='9.0.0')
    assert update_install.run(['--target', str(newer), '--yes']) == 1
    assert update_install.version_of(newer) == '9.0.0'
    assert update_install.run(['--target', str(env / 'yok'), '--yes']) == 1
    assert 'bulunamadı' in capsys.readouterr().out


def test_update_scripts_present_and_use_helper():
    root = Path(update_install.SOURCE)
    mac = (root / 'GUNCELLE_MAC.command').read_text(encoding='utf-8')
    win = (root / 'GUNCELLE_WINDOWS.bat').read_text(encoding='utf-8')
    for text in (mac, win):
        assert 'update_install.py' in text and 'v0.16' in text
    assert 'BASLAT_MAC.command' in mac and 'BASLAT_WINDOWS.bat' in win
