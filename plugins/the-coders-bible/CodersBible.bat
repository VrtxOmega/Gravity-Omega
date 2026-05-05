@echo off
title Coder's Bible — Knowledge Engine
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║  CODER'S BIBLE — Knowledge Engine v1.0      ║
echo  ║  Starting on http://127.0.0.1:5090          ║
echo  ╚══════════════════════════════════════════════╝
echo.
cd /d "%~dp0"
python backend\app.py
pause
