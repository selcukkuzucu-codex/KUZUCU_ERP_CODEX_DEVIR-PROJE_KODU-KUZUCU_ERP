#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -f .venv/bin/python ]; then echo 'Once BASLAT_MAC.command dosyasini calistirin.'; read -r -p 'Enter: ' _; exit 1; fi
.venv/bin/python tools/backup_sqlite.py
read -r -p 'Kapatmak icin Enter: ' _
