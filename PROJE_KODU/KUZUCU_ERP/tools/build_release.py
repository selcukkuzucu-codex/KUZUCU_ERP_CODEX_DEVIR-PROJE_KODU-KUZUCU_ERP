"""Kaynak paketi oluşturur; veritabanı, şifre ve çalışma çıktıları pakete alınmaz."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import zipfile

RELEASE_TIME = (2026, 11, 12, 0, 0, 0)


def application_version(app_dir):
    tree = ast.parse((app_dir / 'app/main.py').read_text(encoding='utf-8'))
    constants = {target.id: node.value.value for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                 for target in node.targets if isinstance(target, ast.Name)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'FastAPI':
            value = next(k.value for k in node.keywords if k.arg == 'version')
            return constants[value.id] if isinstance(value, ast.Name) else ast.literal_eval(value)
    raise ValueError('Uygulama sürümü bulunamadı.')


def build_package(repo, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    app_dir = repo / 'PROJE_KODU/KUZUCU_ERP'
    version = application_version(app_dir)
    files = {}
    extensions = {'.py', '.html', '.css', '.js', '.cjs', '.mjs', '.csv', '.md'}
    excluded_dirs = {'__pycache__', '.pytest_cache', '.git', 'node_modules', '.venv',
                     'data', 'uploads', 'documents', 'parcel_images', 'raporlar', 'reports', 'logs', 'gunlukler'}

    def include(path):
        parents = path.relative_to(repo).parts
        if any(repo.joinpath(*parents[:index]).is_symlink() for index in range(1, len(parents) + 1)):
            raise ValueError('Paket kaynağında sembolik bağlantı desteklenmiyor: ' + str(path))
        relative = path.relative_to(repo).as_posix()
        if relative in files:
            raise ValueError('Yinelenen paket yolu: ' + relative)
        files[relative] = path.read_bytes()

    for directory in ('app', 'tests', 'templates', 'tools'):
        for path in sorted((app_dir / directory).rglob('*')):
            parts = path.relative_to(app_dir).parts
            if path.is_file() and path.suffix.lower() in extensions and not excluded_dirs.intersection(parts) and not any(part.startswith('.') for part in parts):
                include(path)
    # İşletme fotoğrafları ve ekran görüntüleri kaynak sayılmaz. Yalnızca uygulama amblemi eklenir.
    logo = app_dir / 'app/static/kuzucu_logo.png'
    if logo.is_file():
        include(logo)
    # v0.16: programla birlikte gelen Inter yazı tipi (SIL OFL lisansı ile); internetsiz de çalışır.
    for path in sorted((app_dir / 'app/static/fonts').glob('*')):
        if path.is_file() and path.suffix.lower() in {'.woff2', '.txt'}:
            include(path)
    names = {'pytest.ini', 'requirements.txt', 'requirements.constraints.txt', 'YENI_SURUM_KURULUM.txt'}
    for path in sorted(app_dir.iterdir()):
        if path.is_file() and not path.name.startswith('.') and (path.name in names or path.suffix.lower() in {'.md', '.bat', '.command'}):
            include(path)
    for path in sorted(repo.glob('*.md')):
        if not path.name.startswith('.'):
            include(path)
    metadata = {'version': version, 'stage': 'ön test ve geliştirme',
                'release_date': '2026-11-12',
                'contains_user_database': False, 'contains_business_photos': False,
                # v0.15 eklemeli tablo/sütun geçişi getirdi; v0.16 yeni tablo/sütun eklemez.
                'schema_change': tuple(int(part) for part in version.split('.')[:2]) == (0, 15),
                'migration': ('Mevcut SQLite kayıtlarını koruyan eklemeli geçişler; açılış öncesi yedek.'
                              if tuple(int(part) for part in version.split('.')[:2]) == (0, 15) else
                              'Yeni tablo/sütun yok; önceki eklemeli geçişler korunur, açılış öncesi yedek alınır.'),
                'source_file_count': len(files)}
    files['PAKET_BILGILERI.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode()
    manifest = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name, data in sorted(files.items()))
    files['DOSYA_DOGRULAMA.sha256'] = manifest.encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.part')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=RELEASE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith(('.command', '.bat')) else 0o100644) << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(files):
            raise ValueError('ZIP bütünlük kontrolü başarısız.')
        for name, data in files.items():
            if archive.read(name) != data:
                raise ValueError('ZIP içeriği kaynakla eşleşmiyor: ' + name)
    temporary.replace(output)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(output.name + '.sha256').write_text(f'{checksum}  {output.name}\n', encoding='utf-8')
    return {'version': version, 'files': len(files), 'sha256': checksum, 'archive': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build_package(Path(__file__).resolve().parents[3], args.output), ensure_ascii=False, indent=2))
