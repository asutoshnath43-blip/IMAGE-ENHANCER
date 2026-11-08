@echo off
title ClearScale 1080p - Image Enhancer
cd /d "%~dp0"
echo Starting ClearScale 1080p Image Enhancer...
python start.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error. Make sure Python 3.9+ is installed.
    pause
)
