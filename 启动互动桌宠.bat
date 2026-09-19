@echo off
setlocal
chcp 65001 >nul
set "PET_DIR=%~dp0"
set "CODEX_PY_DIR=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python"
set "CODEX_PY=%CODEX_PY_DIR%\python.exe"
set "CODEX_PYW=%CODEX_PY_DIR%\pythonw.exe"
set "PET_SCRIPT=%PET_DIR%interactive_pet.py"
set "PET_LOG=%PET_DIR%启动日志.txt"

if exist "%CODEX_PYW%" (
  "%CODEX_PY%" -B "%PET_SCRIPT%" --self-test >"%PET_LOG%" 2>&1
  if errorlevel 1 goto launch_failed
  start "" "%CODEX_PYW%" -B "%PET_SCRIPT%" 1>>"%PET_LOG%" 2>>&1
  exit /b 0
)

where pyw.exe >nul 2>nul
if not errorlevel 1 (
  py.exe -3 -B "%PET_SCRIPT%" --self-test >"%PET_LOG%" 2>&1
  if errorlevel 1 goto launch_failed
  start "" pyw.exe -3 -B "%PET_SCRIPT%" 1>>"%PET_LOG%" 2>>&1
  exit /b 0
)

echo 未找到 Python。请从 Codex 中重新运行本项目，或安装 Python 3 和 Pillow。
pause
exit /b 1

:launch_failed
echo 互动桌宠启动前检查失败，错误如下：
type "%PET_LOG%"
echo.
echo 日志保存在：%PET_LOG%
pause
exit /b 1
