@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [KUZUCU ERP] Ilk kurulum baslatiliyor...
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3.11 -m venv .venv 2>nul
    if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
  ) else (
    where python >nul 2>&1
    if errorlevel 1 (
      echo Python bulunamadi. Lutfen Python 3.11 veya 3.12 kurun ve PATH secenegini isaretleyin.
      echo https://www.python.org/downloads/windows/
      pause
      exit /b 1
    )
    python -m venv .venv
  )
  if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam olusturulamadi.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -c requirements.constraints.txt
  if errorlevel 1 (
    echo Kutuphane yuklemesi basarisiz. Internet baglantisini kontrol edin.
    pause
    exit /b 1
  )
)
echo [KUZUCU ERP] Kutuphaneler kontrol ediliyor...
".venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt" -c "%~dp0requirements.constraints.txt"
if errorlevel 1 (
 echo Kutuphane kurulumu basarisiz.
 pause
 exit /b 1
)
echo.
echo KUZUCU ERP v0.14 yerel pilot: http://127.0.0.1:8000
start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 echo Uygulama baslatilamadi. 8000 portu baska program tarafindan kullaniliyor olabilir.
pause
