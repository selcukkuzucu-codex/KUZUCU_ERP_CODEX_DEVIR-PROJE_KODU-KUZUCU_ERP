"""KUZUCU ERP kolay güncelleme: yeni sürüm kodunu mevcut kurulum klasörüne aktarır.

Kayıtlar (ciftlik.db, data, raporlar, gunlukler) yerinde kalır; hiçbir kayıt silinmez.
Önce eski klasörün tam kopyası Belgeler/KUZUCU_ERP_Yedekler altına alınır ve
veritabanı kopyasının bütünlüğü doğrulanır. Eski program açıksa güncelleme yapılmaz.
Yalnızca Python standart kütüphanesini kullanır.
"""
import argparse
import ast
import os
import shutil
import sqlite3
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
CODE_DIRS = ('app', 'tools', 'tests', 'templates')
# Kullanıcının kayıtları ve çalışma ortamı: asla üzerine yazılmaz veya silinmez.
KEEP = {'ciftlik.db', 'ciftlik.db-wal', 'ciftlik.db-shm', 'data', 'raporlar', 'reports', 'gunlukler', 'uploads',
        'documents', '.venv', '.env'}
SKIP_NAMES = {'__pycache__', '.pytest_cache', '.git', 'node_modules'}


def say(text=''):
    print(text, flush=True)


def version_of(folder: Path):
    try:
        tree = ast.parse((folder / 'app' / 'main.py').read_text(encoding='utf-8'))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'APP_VERSION' for t in node.targets):
            return node.value.value
    return None


def as_tuple(version):
    try:
        return tuple(int(x) for x in str(version).split('.'))
    except ValueError:
        return (0,)


def default_target():
    return Path.home() / 'Desktop' / 'KUZUCU_ERP'


def backup_root():
    return Path(os.getenv('KUZUCU_BACKUP_DIR', str(Path.home() / 'Documents' / 'KUZUCU_ERP_Yedekler')))


def server_running(port=8000):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/api/health', timeout=1):
            return True
    except Exception:
        return False


def ignore(_dir, names):
    return [n for n in names if n in SKIP_NAMES or n == '.venv' or n.startswith('.venv_eski_')]


def copy_backup(target: Path, old_version: str) -> Path:
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = backup_root() / f'surum_oncesi_v{old_version or "bilinmiyor"}_{stamp}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(target, dest, ignore=ignore)
    db = target / 'ciftlik.db'
    if db.is_file():
        # Açık olmayan programın veritabanı dosya kopyası yerine SQLite'ın güvenli yedeği alınır.
        (dest / 'ciftlik.db').unlink(missing_ok=True)
        with sqlite3.connect(db) as src, sqlite3.connect(dest / 'ciftlik.db') as out:
            src.backup(out)
        with sqlite3.connect(dest / 'ciftlik.db') as check:
            if check.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Yedeklenen veritabanının bütünlük kontrolü başarısız.')
    return dest


def install(source: Path, target: Path):
    for name in CODE_DIRS:
        src = source / name
        if not src.is_dir():
            continue
        dst = target / name
        staging = target / f'.{name}_yeni'
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(src, staging, ignore=ignore)
        old = target / f'.{name}_eski'
        if old.exists():
            shutil.rmtree(old)
        if dst.exists():
            dst.rename(old)
        staging.rename(dst)
        if old.exists():
            shutil.rmtree(old)
    for path in source.iterdir():
        if path.is_file() and path.name not in KEEP and not path.name.startswith('.'):
            shutil.copy2(path, target / path.name)
            if path.suffix in ('.command', '.sh'):
                os.chmod(target / path.name, 0o755)


def run(argv=None):
    parser = argparse.ArgumentParser(description='KUZUCU ERP yeni sürümünü mevcut kuruluma aktarır.')
    parser.add_argument('--target', type=Path, default=None, help='Mevcut KUZUCU_ERP klasörü (varsayılan: Masaüstü/KUZUCU_ERP)')
    parser.add_argument('--yes', action='store_true', help='Onay sormadan devam et')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args(argv)
    target = (args.target or default_target()).expanduser().resolve()
    source = SOURCE
    new_version = version_of(source)
    say(f'KUZUCU ERP güncelleme — yeni sürüm v{new_version}')
    if not (target / 'app' / 'main.py').is_file():
        say(f'Mevcut kurulum bulunamadı: {target}')
        say('Eski KUZUCU_ERP klasörünü Masaüstüne koyun veya --target ile yolunu yazın.')
        return 1
    if target == source:
        say('Bu klasör zaten kurulu program klasörü. Yeni sürüm ZIP\'ini ayrı bir yere açıp oradaki güncelleme dosyasını çalıştırın.')
        return 1
    old_version = version_of(target)
    say(f'Mevcut kurulum: {target} (v{old_version})')
    if as_tuple(old_version) > as_tuple(new_version):
        say('Mevcut kurulum bu paketten daha yeni. Eski sürüme geri dönülmez; işlem yapılmadı.')
        return 1
    if server_running(args.port):
        say('Eski program şu an açık. Önce program penceresinde Control+C ile kapatın, sonra güncellemeyi yeniden başlatın.')
        return 2
    if not args.yes:
        answer = input('Güncellemeye devam edilsin mi? Kayıtlarınız korunur. (E/H): ').strip().casefold()
        if answer not in ('e', 'evet', 'y', 'yes'):
            say('Güncelleme iptal edildi. Hiçbir şey değiştirilmedi.')
            return 1
    say('[1/3] Mevcut kurulumun tam yedeği alınıyor...')
    try:
        saved = copy_backup(target, old_version)
    except Exception as error:
        say(f'Yedek alınamadı; güncelleme yapılmadı. Boş alanı ve klasör izinlerini kontrol edin. ({error.__class__.__name__})')
        return 1
    say(f'      Yedek: {saved}')
    say('[2/3] Yeni program dosyaları kopyalanıyor (kayıtlar yerinde kalıyor)...')
    try:
        install(source, target)
    except Exception as error:
        say(f'Dosyalar kopyalanamadı ({error.__class__.__name__}). Eski hali yedekte: {saved}')
        return 1
    installed = version_of(target)
    if installed != new_version:
        say(f'Kurulum doğrulanamadı (bulunan sürüm: v{installed}). Eski hali yedekte: {saved}')
        return 1
    say(f'[3/3] Kurulum tamam: v{old_version} → v{installed}. Kayıtlarınıza dokunulmadı.')
    return 0


if __name__ == '__main__':
    sys.exit(run())
