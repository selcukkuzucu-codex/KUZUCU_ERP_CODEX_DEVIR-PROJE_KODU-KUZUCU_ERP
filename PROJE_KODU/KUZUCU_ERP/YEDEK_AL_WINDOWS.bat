@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Once BASLAT_WINDOWS.bat dosyasini calistirin.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" tools\backup_sqlite.py
if errorlevel 1 (
 echo Yedekleme basarisiz.
 pause
 exit /b 1
)
echo Yedekleme tamamlandi.
pause
