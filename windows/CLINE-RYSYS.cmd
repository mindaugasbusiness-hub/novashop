@echo off
rem CLINE RYSYS - dvigubu paspaudimu paleidziamas rysys.
rem Visa logika: CLINE-RYSYS.ps1 (tame paciame aplanke).
title CLINE RYSYS
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CLINE-RYSYS.ps1" %*
if errorlevel 1 pause