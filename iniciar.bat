@echo off
title MariFá - Gestion de Setlists
echo.
echo  ==========================================
echo   MariFá - Gestion de Setlists
echo  ==========================================
echo.
echo  Iniciando servidor en http://localhost:5000
echo  Presiona Ctrl+C para detener.
echo.
cd /d "%~dp0"
venv\Scripts\python run.py
pause
