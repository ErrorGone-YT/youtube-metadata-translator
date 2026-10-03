@echo off
setlocal
python "%~dp0gui_app.py"
if errorlevel 1 pause
