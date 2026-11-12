@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Oncelikle BASLAT_WINDOWS.bat dosyasini calistirin.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" tools\backup_sqlite.py
if errorlevel 1 echo YEDEK BASARISIZ! Sorunu inceleyin.
echo Yedek konumu: %%USERPROFILE%%\Documents\KUZUCU_ERP_Yedekler
pause
