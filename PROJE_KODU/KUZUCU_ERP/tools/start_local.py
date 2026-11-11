"""Mac/Windows yerel başlatma: doğru sunucuyu bulur, hazır olmadan tarayıcı açmaz."""
from hashlib import sha256
import ast
from contextlib import redirect_stderr
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import traceback
import urllib.error
import urllib.request
import webbrowser

HOST = '127.0.0.1'
PORT = 8000
ROOT = Path(__file__).resolve().parents[1]


def instance_id(project):
    return sha256(str(Path(project).resolve()).encode('utf-8')).hexdigest()


def expected_version(project):
    """Sürümü uygulamayı veya veritabanını başlatmadan kaynak dosyadan okur."""
    try:
        tree = ast.parse((Path(project) / 'app' / 'main.py').read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'APP_VERSION' for t in node.targets):
                value = ast.literal_eval(node.value)
                return value if isinstance(value, str) else None
    except (OSError, SyntaxError, ValueError, TypeError):
        pass
    return None


def read_health(port=PORT):
    """Yerel istek, sistemde tanımlı dış vekil sunucudan geçirilmez."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f'http://{HOST}:{port}/api/health', timeout=1) as response:
            payload = response.read(65537)
            if response.status != 200 or len(payload) > 65536:
                return None
            data = json.loads(payload)
            return data if isinstance(data, dict) else None
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
        return None


def is_project_server(data, project):
    version = expected_version(project)
    return bool(version and data and data.get('status') == 'ok' and data.get('version') == version
                and data.get('instance_id') == instance_id(project))


def port_in_use(port=PORT):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
            check.settimeout(0.5)
            return check.connect_ex((HOST, port)) == 0
    except OSError:
        # Denetlenemeyen bağlantı noktasında ikinci bir sunucu başlatma.
        return True


def listener_cwd(port=PORT):
    """Unix'te erişilebiliyorsa dinleyen sürecin klasörünü salt okunur kontrol eder."""
    if os.name == 'nt':
        return None
    try:
        result = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'],
                                capture_output=True, text=True, timeout=2, check=False)
        ids = set(result.stdout.split())
        if len(ids) != 1 or not next(iter(ids)).isdigit():
            return None
        pid = next(iter(ids))
        proc = Path('/proc') / pid / 'cwd'
        if proc.exists():
            return proc.resolve()
        result = subprocess.run(['lsof', '-a', '-p', pid, '-d', 'cwd', '-Fn'],
                                capture_output=True, text=True, timeout=2, check=False)
        paths = [line[1:] for line in result.stdout.splitlines() if line.startswith('n/')]
        return Path(paths[0]).resolve() if len(paths) == 1 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def open_page(port=PORT):
    try:
        if webbrowser.open(f'http://{HOST}:{port}'):
            return
    except Exception:
        pass
    print(f'Tarayıcı açılamadı. Tarayıcınıza http://{HOST}:{port} yazın.', flush=True)


def reuse_existing(project=ROOT, port=PORT):
    """Dönüş: 0 doğru sunucu açıldı; 1 farklı/bozuk sunucu; 2 bağlantı noktası boş."""
    if not port_in_use(port):
        return 2
    health = read_health(port)
    cwd = listener_cwd(port)
    if is_project_server(health, project) and (cwd is None or cwd == Path(project).resolve()):
        print('KUZUCU ERP bu klasörden zaten çalışıyor. Mevcut uygulama açılıyor.', flush=True)
        open_page(port)
        return 0
    print(f'{port} bağlantı noktası başka veya doğrulanamayan bir program tarafından kullanılıyor.', flush=True)
    print('KUZUCU ERP’nin eski Terminal penceresinde Control + C yapın; kapanmasını bekleyip yeniden başlatın.', flush=True)
    print('Eski pencereyi bulamıyorsanız bu uyarıyı destek için paylaşın. Çalışan program otomatik kapatılmadı.', flush=True)
    if cwd is not None:
        print('Çalışan programın klasörü:', cwd, flush=True)
    return 1


def wait_and_open(project, stopped, port=PORT, attempts=120):
    for _ in range(attempts):
        if stopped.is_set():
            return
        if is_project_server(read_health(port), project):
            print(f'Program hazır: http://{HOST}:{port}', flush=True)
            print('Bu pencereyi açık bırakın. Durdurmak için Control + C yapın.', flush=True)
            open_page(port)
            return
        if stopped.wait(0.5):
            return
    if not stopped.is_set():
        print('Program henüz hazır değil. Bu penceredeki uyarıları kontrol edin; tarayıcı otomatik açılmadı.', flush=True)


def start(project=ROOT, port=PORT):
    project = Path(project).resolve()
    os.chdir(project)
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    previous = reuse_existing(project, port)
    if previous != 2:
        return previous
    listener = None
    stopped = threading.Event()
    watcher = None
    server = None
    try:
        # Önce bağlantı noktasını al: uygulama/yedek başlamadan olası çakışma anlaşılır.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind((HOST, port))
        listener.listen(128)
        print('KUZUCU ERP açılıyor. Veritabanı ve açılış yedeği kontrol ediliyor...', flush=True)
        log_dir = project / 'gunlukler'
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / 'baslatma.log').open('a', encoding='utf-8') as error_log, redirect_stderr(error_log):
            try:
                import uvicorn
                config = uvicorn.Config('app.main:app', host=HOST, port=port, log_level='critical',
                                        access_log=False, reload=False)
                server = uvicorn.Server(config)
                watcher = threading.Thread(target=wait_and_open, args=(project, stopped, port), daemon=True)
                watcher.start()
                server.run(sockets=[listener])
            except (Exception, SystemExit):
                traceback.print_exc(file=error_log)
                print('Program başlatılamadı. Ayrıntılar: gunlukler/baslatma.log', flush=True)
                return 1
        if not server.started:
            print('Program başlatılamadı. Klasör erişimini ve kurulum dosyalarını kontrol edin. Ayrıntılar: gunlukler/baslatma.log', flush=True)
            return 1
        print('KUZUCU ERP kapatıldı.', flush=True)
        return 0
    except KeyboardInterrupt:
        print('KUZUCU ERP kapatıldı.' if server is not None and server.started else 'Başlatma durduruldu.', flush=True)
        return 0
    except OSError:
        print('Program bağlantı noktasını açamadı. Eski uygulamanın kapanmasını bekleyip yeniden deneyin.', flush=True)
        return 1
    except (ImportError, RuntimeError, SystemExit):
        print('Program başlatılamadı. Kurulumu yeniden çalıştırın ve hata sürerse destek isteyin.', flush=True)
        return 1
    finally:
        stopped.set()
        if listener is not None:
            listener.close()
        if watcher is not None:
            watcher.join(timeout=2)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ['--check-existing']:
        return reuse_existing()
    if args:
        print('Başlatmak için: python tools/start_local.py', flush=True)
        return 2
    return start()


if __name__ == '__main__':
    raise SystemExit(main())
