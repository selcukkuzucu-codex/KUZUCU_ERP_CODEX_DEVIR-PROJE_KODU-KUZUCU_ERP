#!/bin/bash
# KUZUCU ERP kolay güncelleme (Mac). Yeni sürüm ZIP'ini açtığınız klasörde bu dosyaya çift tıklayın.
cd "$(dirname "$0")"
echo 'KUZUCU ERP — Mac güncelleme (v0.16)'
echo 'Kayıtlarınız (ciftlik.db, data, raporlar) yerinde kalır; önce tam yedek alınır.'
echo
KUZUCU_PYTHON=""
for candidate in "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" "/opt/homebrew/bin/python3.12" "/usr/local/bin/python3.12" "$(command -v python3.12 2>/dev/null || true)" "$(command -v python3.11 2>/dev/null || true)" "$(command -v python3.13 2>/dev/null || true)" "$(command -v python3 2>/dev/null || true)"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ] && "$candidate" -c 'import sys; assert (3,11) <= sys.version_info[:2] < (3,14)' >/dev/null 2>&1; then
    KUZUCU_PYTHON="$candidate"; break
  fi
done
if [ -z "$KUZUCU_PYTHON" ]; then
  echo 'Python 3.11–3.13 bulunamadı. Mac için Python 3.12 kurun: https://www.python.org/downloads/macos/'
  read -r -p 'Kapatmak için Enter: ' _; exit 1
fi
KUZUCU_TARGET="$HOME/Desktop/KUZUCU_ERP"
if [ ! -f "$KUZUCU_TARGET/app/main.py" ]; then
  echo "Masaüstünde KUZUCU_ERP klasörü bulunamadı."
  read -r -p 'Mevcut KUZUCU_ERP klasörünü bu pencereye sürükleyip Enter tuşuna basın: ' KUZUCU_TARGET
  KUZUCU_TARGET="${KUZUCU_TARGET%"${KUZUCU_TARGET##*[![:space:]]}"}"
  KUZUCU_TARGET="${KUZUCU_TARGET%\'}"; KUZUCU_TARGET="${KUZUCU_TARGET#\'}"
  KUZUCU_TARGET="${KUZUCU_TARGET//\\ / }"
fi
if "$KUZUCU_PYTHON" tools/update_install.py --target "$KUZUCU_TARGET"; then
  echo
  echo 'Güncellenmiş program açılıyor...'
  exec bash "$KUZUCU_TARGET/BASLAT_MAC.command"
fi
read -r -p 'Kapatmak için Enter: ' _
exit 1
