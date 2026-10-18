@echo off
setlocal
rem Build di Auto Sub ReTimer.
rem   build\build.bat            exe + motore + pacchetto in dist\
rem   build\build.bat app        solo l'exe (app\)
rem   build\build.bat engine     solo il motore CPU (engine\)
rem   build\build.bat engine --force      rifa' da 0 il motore CPU
rem   build\build.bat release    solo il pacchetto (dist\)
rem   build\build.bat release --no-zip    --no-zip non crea lo zip
rem   build\build.bat scan       elenca gli import delle Fasi

cd /d "%~dp0.."
set "PIP_DISABLE_PIP_VERSION_CHECK=1"

if not exist "python\python.exe" (
    echo ERROR: python\python.exe not found. The build needs the base Python in the "python" folder.
    exit /b 1
)

rem build\venv vale solo sul PC e nella cartella dove e' stato creato (pyvenv.cfg contiene
rem il percorso assoluto di python\): se arriva da un altro PC o da un'altra cartella si rifa'.
if exist "build\venv\pyvenv.cfg" (
    "python\python.exe" -c "import os,sys; h=[l.split('=',1)[1].strip() for l in open(r'build\venv\pyvenv.cfg') if l.split('=')[0].strip()=='home']; sys.exit(0 if h and os.path.normcase(os.path.abspath(h[0]))==os.path.normcase(os.path.abspath('python')) else 1)"
    if errorlevel 1 (
        echo build\venv was created in another folder or on another PC: recreating it ...
        rmdir /s /q "build\venv"
    )
)

if not exist "build\venv\Scripts\python.exe" (
    echo Creating build\venv ...
    "python\python.exe" -m venv "build\venv" || exit /b 1
    "build\venv\Scripts\python.exe" -m pip install --quiet pip==25.2 || exit /b 1
)

echo Checking build\venv packages ...
"build\venv\Scripts\python.exe" -m pip install --quiet -r "build\requirements-app.txt" -r "build\requirements-build.txt" || exit /b 1

"build\venv\Scripts\python.exe" "build\build.py" %*
exit /b %errorlevel%
