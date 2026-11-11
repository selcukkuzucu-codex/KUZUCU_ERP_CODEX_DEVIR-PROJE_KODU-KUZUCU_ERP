#!/bin/bash
set -e
cd "$(dirname "$0")"
echo 'Windows bilgisayardan alinmis .sqlite3 yedek dosyasinin tam yolunu girin.'
echo 'Ipucu: Finder icinden dosyayi bu pencereye surukleyip birakin, Enter tusuna basin.'
read -r -p 'Yedek dosyasi: ' source
source="${source/#\~/$HOME}"
source="${source%\'}"; source="${source#\'}"
source="${source%\"}"; source="${source#\"}"
if [ -f .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
"$PY" tools/mac_restore.py "$source"
read -r -p 'Kapatmak icin Enter: ' _
