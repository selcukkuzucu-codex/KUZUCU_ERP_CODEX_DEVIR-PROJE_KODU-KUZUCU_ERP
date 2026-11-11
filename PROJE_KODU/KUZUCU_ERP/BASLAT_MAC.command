#!/bin/bash
set -e
cd "$(dirname "$0")"
echo 'KUZUCU ERP — Mac yerel pilot v0.15'
if ! mkdir -p gunlukler 2>/dev/null; then
  echo 'Günlük klasörü oluşturulamadı. Proje klasörüne yazma izninizi kontrol edin.'
  read -r -p 'Kapatmak için Enter: ' _; exit 1
fi
# Kütüphane yüklemesi yapmadan önce mevcut sunucu stdlib ile kontrol edilir.
KUZUCU_PYTHON=""
for candidate in "$PWD/.venv/bin/python" "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" "/opt/homebrew/bin/python3.12" "/usr/local/bin/python3.12" "$(command -v python3.12 2>/dev/null || true)" "$(command -v python3.11 2>/dev/null || true)" "$(command -v python3.13 2>/dev/null || true)" "$(command -v python3 2>/dev/null || true)"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ] && "$candidate" -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,14)' >/dev/null 2>&1; then
    KUZUCU_PYTHON="$candidate"
    break
  fi
done
if [ -z "$KUZUCU_PYTHON" ]; then
  echo 'Python 3.11–3.13 bulunamadı. Mac için Python 3.12 kurun: https://www.python.org/downloads/macos/'
  read -r -p 'Kapatmak için Enter: ' _; exit 1
fi
if "$KUZUCU_PYTHON" tools/start_local.py --check-existing; then
  exit 0
else
  KUZUCU_CHECK_RESULT=$?
  if [ "$KUZUCU_CHECK_RESULT" -ne 2 ]; then
    read -r -p 'Kapatmak için Enter: ' _; exit 1
  fi
fi
if [ -e .venv ] && ! .venv/bin/python -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,14)' >/dev/null 2>&1; then
  echo 'Eski Python ortamı korunarak yeniden adlandırılıyor.'
  KUZUCU_OLD_ENV=".venv_eski_$(date +%Y%m%d_%H%M%S)_$$"
  if ! mv .venv "$KUZUCU_OLD_ENV" >>gunlukler/kurulum.log 2>&1; then
    echo 'Eski ortam taşınamadı. Dosya izinlerini kontrol edin.'
    read -r -p 'Kapatmak için Enter: ' _; exit 1
  fi
fi
if [ ! -x .venv/bin/python ]; then
  echo '[1/3] Python çalışma ortamı hazırlanıyor...'
  if ! "$KUZUCU_PYTHON" -m venv .venv >>gunlukler/kurulum.log 2>&1; then
    echo 'Çalışma ortamı oluşturulamadı. Ayrıntılar: gunlukler/kurulum.log'
    read -r -p 'Kapatmak için Enter: ' _; exit 1
  fi
fi
echo '[2/3] Gerekli kütüphaneler kontrol ediliyor...'
if ! .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt -c requirements.constraints.txt >>gunlukler/kurulum.log 2>&1; then
  echo 'Kütüphaneler yüklenemedi. İnternet bağlantısını kontrol edin. Ayrıntılar: gunlukler/kurulum.log'
  read -r -p 'Kapatmak için Enter: ' _; exit 1
fi
echo '[3/3] Program açılıyor...'
if ! .venv/bin/python tools/start_local.py; then
  echo 'Program açılamadı. Yukarıdaki Türkçe açıklamayı kontrol edin.'
  read -r -p 'Kapatmak için Enter: ' _; exit 1
fi
