@echo off
rem start-n8n.cmd - starts the main n8n server on port 5678 (broker 5679)
rem ASCII only on purpose: cmd.exe uses the OEM codepage and breaks diacritics.
rem Real logic lives in start-n8n.ps1 so there is a single source of truth.
setlocal

set "N8N_TOOLS_DIR_DEFAULT=C:\Users\M\CLINE\tools\n8n"
if defined N8N_TOOLS_DIR (set "TOOLS=%N8N_TOOLS_DIR%") else (set "TOOLS=%N8N_TOOLS_DIR_DEFAULT%")

if not exist "%TOOLS%\start-n8n.ps1" (
  echo [start-n8n] NOT FOUND: %TOOLS%\start-n8n.ps1
  echo [start-n8n] Set N8N_TOOLS_DIR to the folder that holds tools\n8n
  exit /b 2
)

powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%TOOLS%\start-n8n.ps1" %*
set "RC=%ERRORLEVEL%"

endlocal & exit /b %RC%
