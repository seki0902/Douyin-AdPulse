@echo off
setlocal
set "PROJECT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%scripts\open_dashboard.ps1"
if errorlevel 1 (
  echo.
  echo Could not open the local dashboard.
  pause
)
endlocal
