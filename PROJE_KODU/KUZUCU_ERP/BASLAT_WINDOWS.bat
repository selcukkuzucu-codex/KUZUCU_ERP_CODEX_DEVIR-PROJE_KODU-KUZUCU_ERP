@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo KUZUCU ERP — Windows yerel pilot v0.16
if not exist gunlukler mkdir gunlukler >nul 2>&1
if not exist gunlukler (
  echo Günlük klasörü oluşturulamadı. Proje klasörüne yazma izninizi kontrol edin.
  pause
  exit /b 1
)
set "KUZUCU_ENV_OK="
if not exist ".venv\Scripts\python.exe" goto choose_system
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12),(3,13)]" >nul 2>&1
if errorlevel 1 goto choose_system
set "KUZUCU_PYTHON=.venv\Scripts\python.exe"
set "KUZUCU_PY_VERSION="
set "KUZUCU_ENV_OK=1"
goto python_found
:choose_system
where py >nul 2>&1
if errorlevel 1 goto choose_python
py -3.12 -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12),(3,13)]" >nul 2>&1
if not errorlevel 1 (
  set "KUZUCU_PYTHON=py"
  set "KUZUCU_PY_VERSION=-3.12"
  goto python_found
)
py -3.11 -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12),(3,13)]" >nul 2>&1
if not errorlevel 1 (
  set "KUZUCU_PYTHON=py"
  set "KUZUCU_PY_VERSION=-3.11"
  goto python_found
)
py -3.13 -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12),(3,13)]" >nul 2>&1
if not errorlevel 1 (
  set "KUZUCU_PYTHON=py"
  set "KUZUCU_PY_VERSION=-3.13"
  goto python_found
)
:choose_python
where python >nul 2>&1
if errorlevel 1 goto python_missing
python -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12),(3,13)]" >nul 2>&1
if errorlevel 1 goto python_missing
set "KUZUCU_PYTHON=python"
set "KUZUCU_PY_VERSION="
:python_found
"%KUZUCU_PYTHON%" %KUZUCU_PY_VERSION% tools\start_local.py --check-existing
if errorlevel 2 goto prepare_environment
if errorlevel 1 goto failed
exit /b 0
:prepare_environment
if defined KUZUCU_ENV_OK goto install_dependencies
if not exist .venv goto make_environment
:choose_backup_name
set "KUZUCU_OLD_ENV=.venv_eski_%RANDOM%_%RANDOM%"
if exist "%KUZUCU_OLD_ENV%" goto choose_backup_name
echo Eski Python ortamı korunarak yeniden adlandırılıyor.
move .venv "%KUZUCU_OLD_ENV%" >>gunlukler\kurulum.log 2>&1
if errorlevel 1 goto environment_failed
:make_environment
echo [1/3] Python çalışma ortamı hazırlanıyor...
"%KUZUCU_PYTHON%" %KUZUCU_PY_VERSION% -m venv .venv >>gunlukler\kurulum.log 2>&1
if errorlevel 1 goto environment_failed
if not exist ".venv\Scripts\python.exe" goto environment_failed
:install_dependencies
echo [2/3] Gerekli kütüphaneler kontrol ediliyor...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt -c requirements.constraints.txt >>gunlukler\kurulum.log 2>&1
if errorlevel 1 (
  echo Kütüphaneler yüklenemedi. İnternet bağlantısını kontrol edin. Ayrıntılar: gunlukler\kurulum.log
  goto failed
)
echo [3/3] Program açılıyor...
".venv\Scripts\python.exe" tools\start_local.py
if errorlevel 1 goto failed
exit /b 0
:python_missing
echo Python 3.11–3.13 bulunamadı. Python 3.12 kurun ve kurulumda PATH seçeneğini işaretleyin.
echo https://www.python.org/downloads/windows/
goto failed
:environment_failed
echo Çalışma ortamı hazırlanamadı. Ayrıntılar: gunlukler\kurulum.log
:failed
pause
exit /b 1
