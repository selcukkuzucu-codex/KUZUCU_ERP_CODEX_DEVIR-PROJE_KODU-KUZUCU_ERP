"""Yerel başlangıç ve açık onayla hesap kurtarma davranışları."""
from datetime import timedelta
from pathlib import Path
import sqlite3
import sys
import threading
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Pen, utc_now
from app.security import AuditEvent, LoginSession, User, password_hash, verify_password
from tools import reset_password, start_local


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'boşluk içeren proje'
    (root / 'app').mkdir(parents=True)
    (root / 'app' / 'main.py').write_text("APP_VERSION = '0.15.0'\nraise RuntimeError('İçe aktarılmamalı')\n", encoding='utf-8')
    return root


def ready(project, **extra):
    return {'status': 'ok', 'version': '0.15.0', 'instance_id': start_local.instance_id(project), **extra}


def test_identity_requires_matching_project_version_and_valid_health(project, tmp_path):
    assert start_local.expected_version(project) == '0.15.0'
    assert start_local.is_project_server(ready(project), project)
    assert not start_local.is_project_server(ready(project, version='0.14.0'), project)
    assert not start_local.is_project_server(ready(project, status='error'), project)
    assert not start_local.is_project_server(ready(tmp_path), project)
    assert not start_local.is_project_server({'status': 'ok'}, project)
    assert start_local.expected_version(tmp_path) is None


def test_reuse_only_correct_instance_and_cwd(project, tmp_path, monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(start_local, 'port_in_use', lambda port: True)
    monkeypatch.setattr(start_local, 'read_health', lambda port: ready(project))
    monkeypatch.setattr(start_local, 'listener_cwd', lambda port: project.resolve())
    monkeypatch.setattr(start_local, 'open_page', opened.append)
    assert start_local.reuse_existing(project, 8123) == 0
    assert opened == [8123]
    opened.clear()
    monkeypatch.setattr(start_local, 'listener_cwd', lambda port: tmp_path.resolve())
    assert start_local.reuse_existing(project, 8123) == 1
    assert opened == []
    assert 'otomatik kapatılmadı' in capsys.readouterr().out
    monkeypatch.setattr(start_local, 'port_in_use', lambda port: False)
    assert start_local.reuse_existing(project, 8123) == 2
    assert opened == []


def test_watcher_waits_for_ready_and_stops_without_opening(project, monkeypatch):
    opened, waits = [], []
    replies = iter([None, {'status': 'ok'}, ready(project)])
    monkeypatch.setattr(start_local, 'read_health', lambda port: next(replies))
    monkeypatch.setattr(start_local, 'open_page', opened.append)
    event = SimpleNamespace(is_set=lambda: False, wait=lambda delay: waits.append(delay) or False)
    start_local.wait_and_open(project, event, port=8123, attempts=3)
    assert opened == [8123] and len(waits) == 2
    opened.clear()
    stopped = threading.Event(); stopped.set()
    start_local.wait_and_open(project, stopped, attempts=1)
    assert opened == []


def test_watcher_timeout_does_not_open_browser(project, monkeypatch, capsys):
    monkeypatch.setattr(start_local, 'read_health', lambda port: None)
    monkeypatch.setattr(start_local, 'open_page', lambda *args: pytest.fail('Hazır olmadan tarayıcı açıldı'))
    event = SimpleNamespace(is_set=lambda: False, wait=lambda delay: False)
    start_local.wait_and_open(project, event, attempts=2)
    assert 'tarayıcı otomatik açılmadı' in capsys.readouterr().out


def test_start_reserves_port_before_loading_app_and_logs_technical_failure(project, monkeypatch, capsys):
    calls = []
    class Socket:
        def bind(self, address): calls.append('bind')
        def listen(self, backlog): calls.append('listen')
        def close(self): calls.append('close')
    class Thread:
        def __init__(self, *args, **kwargs): calls.append('watcher')
        def start(self): calls.append('watch')
        def join(self, timeout): calls.append('join')
    def config(*args, **kwargs):
        calls.append('load')
        raise RuntimeError('Technical server failure')
    monkeypatch.chdir(project)
    monkeypatch.setattr(start_local, 'reuse_existing', lambda *args: 2)
    monkeypatch.setattr(start_local.socket, 'socket', lambda *args: Socket())
    monkeypatch.setattr(start_local.threading, 'Thread', Thread)
    monkeypatch.setitem(sys.modules, 'uvicorn', SimpleNamespace(Config=config))
    assert start_local.start(project, 8123) == 1
    assert calls == ['bind', 'listen', 'load', 'close']
    assert 'Technical server failure' not in capsys.readouterr().out
    assert 'Technical server failure' in (project / 'gunlukler' / 'baslatma.log').read_text()


def test_start_does_nothing_when_port_is_not_ours(project, monkeypatch):
    monkeypatch.chdir(project)
    monkeypatch.setattr(start_local, 'reuse_existing', lambda *args: 1)
    monkeypatch.setattr(start_local.socket, 'socket', lambda *args: pytest.fail('Başka programın bağlantı noktasına girildi'))
    assert start_local.start(project) == 1


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'kullanıcılar.db'))
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setenv('KUZUCU_BACKUP_DIR', str(tmp_path / 'yedekler'))
    with maker() as db:
        user = User(username='calisan', display_name='Çalışan', department='Besi', password_hash=password_hash('OldPasswordTest2026'), is_admin=False, is_active=True, permissions_json='["hayvanlar.kart.view"]')
        other = User(username='yonetici', display_name='Yönetici', password_hash=password_hash('OtherPasswordTest2026'), is_admin=True, is_active=True, permissions_json='[]')
        db.add_all([user, other, Pen(code='G-01', capacity=20)]); db.commit()
        db.add_all([LoginSession(user_id=user.id, token_hash='a' * 64, csrf_token='b' * 64, expires_at=utc_now() + timedelta(hours=2)),
                    LoginSession(user_id=other.id, token_hash='c' * 64, csrf_token='d' * 64, expires_at=utc_now() + timedelta(hours=2))]); db.commit()
        user_id, other_id = user.id, other.id
    yield engine, maker, user_id, other_id
    engine.dispose()


def test_reset_uses_integrity_checked_backup_and_revokes_only_target_sessions(accounts):
    engine, maker, user_id, other_id = accounts
    backup = reset_password.reset_account(engine, maker, ' CALISAN ', 'NewPasswordTest2026')
    with sqlite3.connect(backup) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert verify_password('OldPasswordTest2026', db.execute('select password_hash from erp_users where id=?', (user_id,)).fetchone()[0])
    with maker() as db:
        user = db.get(User, user_id)
        assert verify_password('NewPasswordTest2026', user.password_hash)
        assert not verify_password('OldPasswordTest2026', user.password_hash)
        assert user.department == 'Besi' and user.permissions_json == '["hayvanlar.kart.view"]' and not user.is_admin
        assert db.scalars(select(LoginSession.user_id)).all() == [other_id]
        assert db.scalar(select(Pen.code)) == 'G-01'
        events = db.scalars(select(AuditEvent).where(AuditEvent.actor == 'yerel hesap kurtarma')).all()
        assert len(events) == 1
        assert 'NewPasswordTest2026' not in events[0].changes_json and 'OldPasswordTest2026' not in events[0].changes_json


def test_failed_or_invalid_backup_leaves_password_and_sessions_unchanged(accounts, tmp_path):
    engine, maker, user_id, _ = accounts
    with pytest.raises(reset_password.RecoveryError, match='yedek alınamadı'):
        reset_password.reset_account(engine, maker, 'calisan', 'NewPasswordTest2026', backup_fn=lambda *a, **k: None)
    bad = tmp_path / 'bozuk.sqlite3'; bad.write_text('Güvenli yedek değil')
    with pytest.raises(reset_password.RecoveryError, match='doğrulanamadı'):
        reset_password.reset_account(engine, maker, 'calisan', 'NewPasswordTest2026', backup_fn=lambda *a, **k: bad)
    with maker() as db:
        assert verify_password('OldPasswordTest2026', db.get(User, user_id).password_hash)
        assert len(db.scalars(select(LoginSession)).all()) == 2


def test_reset_rejects_missing_inactive_or_invalid_password_without_backup(accounts):
    engine, maker, user_id, _ = accounts
    def forbidden(*args, **kwargs): pytest.fail('Doğrulamadan yedek alınmamalı')
    with pytest.raises(reset_password.RecoveryError, match='bulunamadı'):
        reset_password.reset_account(engine, maker, 'eksik', 'NewPasswordTest2026', backup_fn=forbidden)
    with pytest.raises(reset_password.RecoveryError, match='10 ile 200'):
        reset_password.reset_account(engine, maker, 'calisan', 'kısa', backup_fn=forbidden)
    with maker() as db:
        db.get(User, user_id).is_active = False; db.commit()
    with pytest.raises(reset_password.RecoveryError, match='pasif'):
        reset_password.reset_account(engine, maker, 'calisan', 'NewPasswordTest2026', backup_fn=forbidden)


def test_reset_cli_refuses_non_interactive_input_without_reading_password(monkeypatch, capsys):
    monkeypatch.setattr(start_local, 'port_in_use', lambda *args: False)
    monkeypatch.setattr(sys, 'stdin', SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(reset_password.getpass, 'getpass', lambda *args: pytest.fail('Parola sorulmamalı'))
    assert reset_password.main(['calisan']) == 1
    assert 'etkileşimli Terminal' in capsys.readouterr().out


def test_launcher_scripts_use_guarded_helper_without_early_browser_commands():
    root = Path(__file__).resolve().parents[1]
    mac = (root / 'BASLAT_MAC.command').read_text(encoding='utf-8')
    windows = (root / 'BASLAT_WINDOWS.bat').read_text(encoding='utf-8')
    for source in (mac, windows):
        assert source.index('--check-existing') < source.index('-m pip install')
        assert 'v0.15' in source and 'gunlukler' in source and 'requirements.constraints.txt' in source
        assert '-m uvicorn' not in source and 'sleep 3' not in source
    assert 'open \'http://' not in mac and 'start "" http://' not in windows


def test_real_linux_helper_opens_only_ready_matching_project(tmp_path):
    """Gerçek HTTP/soket: tarayıcı kancası açılış sağlığı tamamlandıktan sonra çalışır."""
    import os
    import socket
    import subprocess
    import time
    source = Path(__file__).resolve().parents[1]
    project = tmp_path / 'gerçek başlangıç'
    (project / 'app').mkdir(parents=True)
    (project / 'app' / '__init__.py').write_text('')
    (project / 'app' / 'main.py').write_text('''from pathlib import Path
from hashlib import sha256
from contextlib import asynccontextmanager
from fastapi import FastAPI
APP_VERSION = '0.15.0'
@asynccontextmanager
async def lifespan(app):
    yield
    (Path(__file__).resolve().parent.parent / 'kapanis-tamam').write_text('tamam')
app = FastAPI(lifespan=lifespan)
@app.get('/api/health')
def health():
    return {'status':'ok','version':APP_VERSION,'instance_id':sha256(str(Path(__file__).resolve().parent.parent).encode('utf-8')).hexdigest()}
''', encoding='utf-8')
    marker = tmp_path / 'acilan-adres.txt'
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
    code = ("import sys; from pathlib import Path; "
            f"sys.path.insert(0,{str(source)!r}); "
            "from tools import start_local; "
            f"start_local.webbrowser.open=lambda url: bool(Path({str(marker)!r}).write_text(url)); "
            f"raise SystemExit(start_local.start({str(project)!r},{port}))")
    process = subprocess.Popen([sys.executable, '-B', '-c', code], cwd=tmp_path, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    try:
        until = time.monotonic() + 15
        while time.monotonic() < until and process.poll() is None and not marker.exists():
            time.sleep(0.1)
        assert marker.exists(), 'Program hazır olup tarayıcı açılmadı.'
        assert marker.read_text() == f'http://127.0.0.1:{port}'
        data = start_local.read_health(port)
        assert start_local.is_project_server(data, project)
        assert not (tmp_path / 'ciftlik.db').exists()
    finally:
        if process.poll() is None:
            process.send_signal(__import__('signal').SIGINT)
        try:
            out, err = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); out, err = process.communicate(timeout=5)
            pytest.fail('Yerel sunucu güvenli kapatma isteğine yanıt vermedi.')
    assert process.returncode == 0
    assert err == ''
    assert 'Program hazır:' in out and 'KUZUCU ERP kapatıldı.' in out
    assert (project / 'kapanis-tamam').read_text() == 'tamam'
