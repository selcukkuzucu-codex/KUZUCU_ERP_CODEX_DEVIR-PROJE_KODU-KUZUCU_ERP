#!/bin/bash
set -e
cd "$(dirname "$0")"
echo 'KUZUCU ERP — Mac yerel pilot v0.14'
# Mac sistem Python 3.9'u kullanabilir; kurulu Python 3.12'yi otomatik bul.
PYTHON=""
for candidate in "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" "/opt/homebrew/bin/python3.12" "/usr/local/bin/python3.12" "$(command -v python3 2>/dev/null || true)"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ] && "$candidate" -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,14)' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo 'Python 3.11-3.13 bulunamadi. Mac icin Python 3.12 kurun: https://www.python.org/downloads/macos/'
  read -r -p 'Kapatmak icin Enter: ' _; exit 1
fi
echo "Python: $($PYTHON --version) ($PYTHON)"
if [ -e .venv/bin/python ] && ! .venv/bin/python -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,14)' >/dev/null 2>&1; then
  echo 'Eski Python ile oluşturulmuş .venv mevcut; kaybetmemek için eski ortam yeniden adlandırılacak.'
  mv .venv ".venv_eski_$(date +%Y%m%d_%H%M%S)"
fi
if [ ! -x .venv/bin/python ]; then
  echo '[1/3] Mac Python ortami hazirlaniyor...'
  "$PYTHON" -m venv .venv
fi
echo '[2/3] Gereksinimler kontrol ediliyor...'
.venv/bin/python -m pip install -r requirements.txt -c requirements.constraints.txt || { echo 'Kütüphaneler yüklenemedi. İnternet bağlantısını ve Terminal uyarısını kontrol edin.'; read -r -p 'Kapatmak için Enter: ' _; exit 1; }
echo '[3/3] Program aciliyor...'
(sleep 3; open 'http://127.0.0.1:8000') &
echo 'Adres: http://127.0.0.1:8000'
echo 'Bu pencereyi acik birakin. Durdurmak icin Ctrl+C.'
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
