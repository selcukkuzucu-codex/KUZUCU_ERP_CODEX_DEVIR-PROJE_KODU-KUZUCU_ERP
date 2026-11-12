@echo off
chcp 65001 >nul
setlocal
rem KUZUCU ERP kolay güncelleme (Windows). Yeni sürüm ZIP'ini açtığınız klasörde bu dosyaya çift tıklayın.
cd /d "%~dp0"
echo KUZUCU ERP — Windows güncelleme (v0.16)
echo Kayıtlarınız (ciftlik.db, data, raporlar) yerinde kalır; önce tam yedek alınır.
echo.
set "KUZUCU_PYTHON="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>&1 && set "KUZUCU_PYTHON=py -3.12"
  if not defined KUZUCU_PYTHON py -3.11 -c "import sys" >nul 2>&1 && set "KUZUCU_PYTHON=py -3.11"
  if not defined KUZUCU_PYTHON py -3.13 -c "import sys" >nul 2>&1 && set "KUZUCU_PYTHON=py -3.13"
)
if not defined KUZUCU_PYTHON (
  python -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12),(3,13)]" >nul 2>&1 && set "KUZUCU_PYTHON=python"
)
if not defined KUZUCU_PYTHON (
  echo Python 3.11–3.13 bulunamadı. Python 3.12 kurun ve kurulumda PATH seçeneğini işaretleyin.
  echo https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
set "KUZUCU_TARGET=%USERPROFILE%\Desktop\KUZUCU_ERP"
if not exist "%KUZUCU_TARGET%\app\main.py" if defined OneDrive if exist "%OneDrive%\Desktop\KUZUCU_ERP\app\main.py" set "KUZUCU_TARGET=%OneDrive%\Desktop\KUZUCU_ERP"
if not exist "%KUZUCU_TARGET%\app\main.py" if defined OneDrive if exist "%OneDrive%\Masaüstü\KUZUCU_ERP\app\main.py" set "KUZUCU_TARGET=%OneDrive%\Masaüstü\KUZUCU_ERP"
if not exist "%KUZUCU_TARGET%\app\main.py" if exist "C:\KUZUCU_ERP\app\main.py" set "KUZUCU_TARGET=C:\KUZUCU_ERP"
if not exist "%KUZUCU_TARGET%\app\main.py" (
  echo Masaüstünde veya C:\KUZUCU_ERP içinde program klasörü bulunamadı.
  set /p "KUZUCU_TARGET=Mevcut KUZUCU_ERP klasörünü bu pencereye sürükleyip Enter tuşuna basın: "
)
set "KUZUCU_TARGET=%KUZUCU_TARGET:"=%"
%KUZUCU_PYTHON% tools\update_install.py --target "%KUZUCU_TARGET%"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo Güncellenmiş program açılıyor...
call "%KUZUCU_TARGET%\BASLAT_WINDOWS.bat"
