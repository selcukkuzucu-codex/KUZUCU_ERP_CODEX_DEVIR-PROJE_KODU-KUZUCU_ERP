"""SQLite online backups, checking integrity; no silent deletion of user data."""
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
import os

BACKUP_INTERVAL=30*60

def backup_db(engine,force=False,label='otomatik'):
    if engine.dialect.name!='sqlite' or not engine.url.database:return None
    src=Path(engine.url.database).resolve()
    if not src.is_file():return None
    # Home Documents is outside version folder, so upgrading/renaming code does not remove backups.
    backup_dir=Path(os.getenv('KUZUCU_BACKUP_DIR',str(Path.home()/'Documents'/'KUZUCU_ERP_Yedekler')))
    backup_dir.mkdir(parents=True,exist_ok=True)
    # Never fail the app just because a backup target is unavailable; surface a clear log message.
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    tmp=backup_dir / f'kuzucu_{label}_{stamp}.part'
    target=backup_dir / f'kuzucu_{label}_{stamp}.sqlite3'
    try:
        with sqlite3.connect(src) as a,sqlite3.connect(tmp) as b:a.backup(b)
        with sqlite3.connect(tmp) as conn:
            if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Yedek bütünlük kontrolü başarısız.')
        tmp.replace(target)
        print('KUZUCU ERP güvenli yedek:',target,flush=True)
        return target
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        print('KUZUCU ERP YEDEK UYARISI: Otomatik yedek alınamadı:',exc,flush=True)
        return None

async def periodic_backup(engine):
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        await asyncio.to_thread(backup_db,engine)
