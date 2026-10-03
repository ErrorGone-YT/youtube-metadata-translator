@echo off
setlocal
python "%~dp0webui.py"
if errorlevel 1 pause
