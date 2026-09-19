@echo off
setlocal
set "PET_DIR=%~dp0"
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"

if exist "%CODEX_PY%" (
  start "" "%CODEX_PY%" "%PET_DIR%interactive_pet.py"
  exit /b 0
)

where pyw.exe >nul 2>nul
if %errorlevel% equ 0 (
  start "" pyw.exe -3 "%PET_DIR%interactive_pet.py"
  exit /b 0
)

where pythonw.exe >nul 2>nul
if %errorlevel% equ 0 (
  start "" pythonw.exe "%PET_DIR%interactive_pet.py"
  exit /b 0
)

echo 未找到 Python。请从 Codex 中重新运行本项目，或安装 Python 3 和 Pillow。
pause
