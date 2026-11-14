@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0Setup.ps1"
if errorlevel 1 pause
