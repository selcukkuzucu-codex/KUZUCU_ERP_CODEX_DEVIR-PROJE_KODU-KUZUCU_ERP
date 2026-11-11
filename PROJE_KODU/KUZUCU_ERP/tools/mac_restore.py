"""Import one verified legacy SQLite backup into an empty Mac local pilot.
Never overwrites an existing database; no network access.
"""
from pathlib import Path
import sqlite3
import sys

root=Path(__file__).resolve().parents[1]
dest=root/'ciftlik.db'
if len(sys.argv)!=2:
    print('Kullanim: python3 tools/mac_restore.py /yol/yedek.sqlite3')
    sys.exit(2)
source=Path(sys.argv[1]).expanduser().resolve()
if not source.is_file():
    print('HATA: Yedek dosyasi bulunamadi:',source);sys.exit(1)
if dest.exists():
    print('HATA: Mac veritabani zaten mevcut. Guvenlik icin ustune yazilmadi:',dest)
    print('Iki veritabani birlestirilemez. Once mevcut Mac verilerinizi ayri yedekleyin ve destek isteyin.')
    sys.exit(1)
try:
    with sqlite3.connect(f'file:{source.as_posix()}?mode=ro',uri=True) as src:
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise RuntimeError('Kaynak SQLite butunluk testi basarisiz')
        tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'animals','pens','fields'}.issubset(tables):
            raise RuntimeError('Bu dosya beklenen KUZUCU ERP veritabani degil (zorunlu tablolar yok).')
        with sqlite3.connect(str(dest)) as target:
            src.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Hedef veritabani butunluk testi basarisiz')
    print('BASARILI: Windows kayitlari Mac icin aktarildi:', dest)
except Exception as exc:
    dest.unlink(missing_ok=True)
    print('HATA:',exc)
    sys.exit(1)
