@echo off
start cmd /k "cd /d %~dp0 && python run_server.py"
echo backend started: http://localhost:5000
