"""Yerel bilgisayarda, açık onay ve doğrulanmış yedekle mevcut hesap parolası yeniler.

Parola komut satırından alınmaz, yazdırılmaz ve ağ üzerinden gönderilmez.
"""
import getpass
import json
import os
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class RecoveryError(Exception):
    pass


def database_path(engine):
    if engine.dialect.name != 'sqlite' or not engine.url.database or engine.url.database == ':memory:':
        raise RecoveryError('Bu araç yalnızca mevcut yerel SQLite veritabanı için kullanılabilir.')
    path = Path(engine.url.database).resolve()
    if not path.is_file():
        raise RecoveryError('Mevcut veritabanı bulunamadı. Boş veritabanı oluşturulmadı.')
    return path


def find_account(maker, username):
    from sqlalchemy import select
    from sqlalchemy.exc import SQLAlchemyError
    from app.security import User
    try:
        with maker() as db:
            user = db.scalar(select(User).where(User.username == username.strip().lower()))
            if user is None:
                raise RecoveryError('Bu kullanıcı adı bulunamadı. Ad soyad yerine girişte kullanılan kullanıcı adını yazın.')
            if not user.is_active:
                raise RecoveryError('Bu hesap pasif. Önce mevcut yönetici hesabıyla etkinleştirin; bu araç hesabı etkinleştirmez.')
            return user.id, user.username, user.display_name
    except SQLAlchemyError as error:
        raise RecoveryError('Kullanıcı kayıtları okunamadı. Doğru proje klasörünü ve veritabanını kontrol edin.') from error


def reset_account(engine, maker, username, new_password, backup_fn=None):
    from sqlalchemy import delete, select
    from app.backup import backup_db
    from app.security import AuditEvent, LoginSession, User, actor_context, password_hash
    database_path(engine)
    account_id, _, _ = find_account(maker, username)
    if not 10 <= len(new_password) <= 200:
        raise RecoveryError('Yeni parola 10 ile 200 karakter arasında olmalıdır.')
    hashed = password_hash(new_password)
    backup = (backup_fn or backup_db)(engine, force=True, label='yerel-parola-oncesi')
    if not backup or not Path(backup).is_file():
        raise RecoveryError('Güvenli yedek alınamadı. Parola değiştirilmedi.')
    try:
        with sqlite3.connect(Path(backup).resolve().as_uri() + '?mode=ro', uri=True) as checked:
            if checked.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RecoveryError('Yedek bütünlük kontrolü başarısız. Parola değiştirilmedi.')
    except (sqlite3.Error, OSError) as error:
        raise RecoveryError('Yedek doğrulanamadı. Parola değiştirilmedi.') from error
    marker = actor_context.set('yerel hesap kurtarma')
    try:
        with maker() as db:
            user = db.scalar(select(User).where(User.id == account_id, User.is_active.is_(True)))
            if user is None:
                raise RecoveryError('Hesap değişti veya pasifleşti. İşlem yapılmadı.')
            user.password_hash = hashed
            db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
            db.add(AuditEvent(actor='yerel hesap kurtarma', table_name='erp_users', record_id=str(user.id),
                              action='DUZENLE', changes_json=json.dumps({
                                  'local_password_reset': {'once': None, 'new': 'Parola yenilendi ve açık oturumlar kapatıldı.'}
                              }, ensure_ascii=False)))
            db.commit()
    except RecoveryError:
        raise
    except Exception as error:
        raise RecoveryError('Parola kaydedilemedi. İşlem geri alındı; yedeğiniz korundu.') from error
    finally:
        actor_context.reset(marker)
    return Path(backup)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1 or (args and args[0].startswith('-')):
        print('Kullanım: python tools/reset_password.py [kullanıcı_adı]')
        print('Parola yalnızca gizli yerel giriş alanından sorulur; komuta yazmayın.')
        return 2
    os.chdir(ROOT)
    from tools.start_local import port_in_use
    if port_in_use():
        print('Önce KUZUCU ERP’nin Terminal penceresinde Control + C yapıp programı kapatın.')
        print('Program açıkken parola değiştirilmedi.')
        return 1
    if not sys.stdin.isatty():
        print('Parola yenileme yalnızca bilgisayardaki etkileşimli Terminal penceresinde yapılabilir.')
        return 1
    from app.db import engine, SessionLocal
    try:
        path = database_path(engine)
        username = args[0] if args else input('Girişte kullandığınız kullanıcı adı: ').strip()
        _, account, name = find_account(SessionLocal, username)
        print('Veritabanı:', path)
        print(f'Parolası yenilenecek hesap: {account} ({name})')
        print('Diğer kayıtlar ve yetkiler korunur. Bu hesabın açık oturumları kapatılır.')
        new_password = getpass.getpass('Yeni parola (en az 10 karakter; yazarken görünmez): ')
        repeated = getpass.getpass('Yeni parolayı tekrar yazın: ')
        if new_password != repeated:
            raise RecoveryError('İki parola eşleşmiyor. Hiçbir değişiklik yapılmadı.')
        if input('Yedek alıp bu hesabın parolasını yenilemek için ONAY yazın: ').strip() != 'ONAY':
            print('İşlem iptal edildi. Hiçbir değişiklik yapılmadı.')
            return 0
        backup = reset_account(engine, SessionLocal, account, new_password)
        print('Parola yenilendi. Programı yeniden açıp yeni parolanızla giriş yapın.')
        print('İşlem öncesi güvenli yedek:', backup)
        return 0
    except RecoveryError as error:
        print('Uyarı:', error)
        return 1
    except (EOFError, KeyboardInterrupt):
        print('\nİşlem iptal edildi. Hiçbir değişiklik yapılmadı.')
        return 1
    except Exception:
        print('Kullanıcı kayıtlarına erişilemedi. Doğru proje klasörünü ve yerel veritabanını kontrol edin.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
