"""Development-only SQLite online backup with verification; no cloud server connection."""
from pathlib import Path
import datetime as dt
import sqlite3
import sys

root=Path(__file__).resolve().parents[1]
source=root/'ciftlik.db'
if not source.exists():
    print('Veritabani henuz olusturulmadi. Uygulamayi once acin.',file=sys.stderr)
    sys.exit(1)
backup_dir=Path.home()/'Documents'/'KUZUCU_ERP_Yedekler'
backup_dir.mkdir(parents=True,exist_ok=True)
name=f'kuzucu_erp_local_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.sqlite3'
dest=backup_dir/name
try:
    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(dest)) as tgt:
        src.backup(tgt)
    with sqlite3.connect(str(dest)) as con:
        check=con.execute('PRAGMA integrity_check').fetchone()[0]
    if check!='ok':
        dest.unlink(missing_ok=True)
        raise RuntimeError('Yedek butunluk kontrolu basarisiz')
    print('Yedek:',dest)
except Exception as ex:
    print('HATA:',ex,file=sys.stderr)
    sys.exit(1)
