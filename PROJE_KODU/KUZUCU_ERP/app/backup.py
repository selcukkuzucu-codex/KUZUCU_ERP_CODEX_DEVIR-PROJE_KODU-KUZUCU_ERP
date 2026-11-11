"""SQLite online backups, checking integrity; no silent deletion of user data."""
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
import os
import logging

BACKUP_INTERVAL=30*60
# Saklama kuralı (disk dolmasın, geçmiş kaybolmasın):
# - son FULL_DAYS gündeki tüm yedekler,
# - KEEP_DAYS güne kadar her günün en yeni yedeği,
# - daha eskilerde her ayın en yeni yedeği,
# - her durumda en yeni KEEP_MIN yedek korunur.
# Yalnızca programın kendi kuzucu_*.sqlite3 yedekleri silinir.
FULL_DAYS=2
KEEP_DAYS=30
KEEP_MIN=20
LAST_STATUS={'ok':None,'at':None,'path':None,'label':None,'message':'Bu oturumda henüz yedek alınmadı.'}

def backup_dir():
    return Path(os.getenv('KUZUCU_BACKUP_DIR',str(Path.home()/'Documents'/'KUZUCU_ERP_Yedekler')))

def prune_backups(directory=None,now=None):
    """Eski yedekleri saklama kuralına göre temizler; silinen dosya sayısını döner."""
    directory=Path(directory or backup_dir())
    now=now or datetime.now()
    try:files=sorted(directory.glob('kuzucu_*.sqlite3'),key=lambda p:p.stat().st_mtime,reverse=True)
    except OSError:return 0
    keep=set(files[:KEEP_MIN])
    seen_days=set();seen_months=set()
    for f in files:  # en yeniden eskiye
        modified=datetime.fromtimestamp(f.stat().st_mtime)
        age=(now-modified).days
        if age<FULL_DAYS:keep.add(f);continue
        if age<KEEP_DAYS:
            if modified.date() not in seen_days:seen_days.add(modified.date());keep.add(f)
            continue
        key=(modified.year,modified.month)
        if key not in seen_months:seen_months.add(key);keep.add(f)
    removed=0
    for f in files:
        if f in keep:continue
        try:f.unlink();removed+=1
        except OSError:logging.getLogger('kuzucu.erp').warning('Eski yedek silinemedi: %s',f)
    return removed

def backup_status():
    directory=backup_dir()
    latest=None
    try:
        files=sorted(directory.glob('kuzucu_*.sqlite3'),key=lambda p:p.stat().st_mtime,reverse=True)
        if files:latest=files[0]
    except OSError:files=[]
    return {**LAST_STATUS,'directory':str(directory),
            'latest_file':latest.name if latest else None,
            'latest_at':datetime.fromtimestamp(latest.stat().st_mtime).isoformat(timespec='seconds') if latest else None,
            'count':len(files)}

def backup_db(engine,force=False,label='otomatik'):
    if engine.dialect.name!='sqlite' or not engine.url.database:return None
    src=Path(engine.url.database).resolve()
    if not src.is_file():return None
    # Home Documents is outside version folder, so upgrading/renaming code does not remove backups.
    backup_dir_path=backup_dir()
    # Never fail the app just because a backup target is unavailable; surface a clear log message.
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    tmp=backup_dir_path / f'kuzucu_{label}_{stamp}.part'
    target=backup_dir_path / f'kuzucu_{label}_{stamp}.sqlite3'
    try:
        backup_dir_path.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(src) as a,sqlite3.connect(tmp) as b:a.backup(b)
        with sqlite3.connect(tmp) as conn:
            if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Yedek bütünlük kontrolü başarısız.')
        tmp.replace(target)
        print('KUZUCU ERP güvenli yedek:',target,flush=True)
        LAST_STATUS.update(ok=True,at=datetime.now().isoformat(timespec='seconds'),path=str(target),label=label,message='Yedek alındı.')
        try:prune_backups(backup_dir_path)
        except Exception:logging.getLogger('kuzucu.erp').exception('Eski yedek temizliği yapılamadı')
        return target
    except Exception as exc:
        try:tmp.unlink(missing_ok=True)
        except OSError:pass
        logging.getLogger('kuzucu.erp').exception('Yedek alınamadı; teknik ayrıntı',exc_info=exc)
        print('KUZUCU ERP YEDEK UYARISI: Otomatik yedek alınamadı. Yedek klasörünün erişimini ve boş alanı kontrol edin.',flush=True)
        LAST_STATUS.update(ok=False,at=datetime.now().isoformat(timespec='seconds'),path=None,label=label,
                           message='Yedek alınamadı. Yedek klasörünün erişimini ve bilgisayardaki boş alanı kontrol edin.')
        return None

async def periodic_backup(engine):
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        await asyncio.to_thread(backup_db,engine)
