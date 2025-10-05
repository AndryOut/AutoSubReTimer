@echo off
setlocal enabledelayedexpansion
chcp 65001
set PYTHONIOENCODING=utf-8

cd /d "%~dp0"

set PIP_DISABLE_PIP_VERSION_CHECK=1
set PIP_QUIET=1

set script_folder=Scripts\GUI
set launcher_file=%script_folder%\GUI.py
set torch_installed_flag=main\.torch_installed

if not exist main (
    echo Creating the "main" folder...
    python\python.exe -m venv main
    echo Installing the necessary inside the "main" folder...
    call main\Scripts\activate.bat
    main\Scripts\python.exe -m pip install --upgrade pip --quiet
    main\Scripts\python.exe -m pip install -r "%script_folder%\requirements.txt" --quiet
    main\Scripts\python.exe -m pip install pysrt --use-pep517 --quiet
)

if not exist "%torch_installed_flag%" (
    :ask_cuda
    echo.
    if exist main (
        echo Virtual environment exists but PyTorch is not configured.
    )
    echo Want to install PyTorch with CUDA to use GPU?
    echo [1] Install the necessary to use the GPU - NVIDIA GPUs only
    echo [2] Use the CPU
    set /p choice="Choice [1/2]: "
    
    if "!choice!"=="1" (
        echo Installing PyTorch with CUDA...
        if not exist main call main\Scripts\activate.bat
        main\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --quiet
        echo. > "%torch_installed_flag%"
        echo Installation complete.
    ) else if "!choice!"=="2" (
        echo CUDA installation skipped.
        echo. > "%torch_installed_flag%"
    ) else (
        echo Invalid choice.
        goto ask_cuda
    )
)

if exist main if exist "%torch_installed_flag%" if not defined IS_MINIMIZED (
    set IS_MINIMIZED=1
    start "" /min cmd /c "%~dpnx0" %*
    exit
)

if exist "%launcher_file%" (
    call main\Scripts\python.exe "%launcher_file%"
) else (
    echo ERROR: Unable to find GUI.py in "%launcher_file%".
)
