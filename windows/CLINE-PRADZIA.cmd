@echo off
rem CLINE - PRADZIA - atidaro atminti (00_START_HERE.md) ir jos aplanka.
setlocal
set "ATMINTIS=C:\Users\M\CLINE"
if not exist "%ATMINTIS%\00_START_HERE.md" (
  echo.
  echo Nerandu failo: %ATMINTIS%\00_START_HERE.md
  echo.
  echo Ka daryti: paleisk irasyma sitokia eilute PowerShell lange:
  echo   iex (irm https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta/windows/irasyk.ps1)
  echo.
  pause
  exit /b 1
)
start "" notepad "%ATMINTIS%\00_START_HERE.md"
start "" explorer "%ATMINTIS%"
endlocal