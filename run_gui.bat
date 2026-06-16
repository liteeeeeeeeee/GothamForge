@echo off
rem GothamForge launcher - double-click to open the mod studio.
cd /d "%~dp0"
python gothamforge_gui.py
if errorlevel 1 (
    echo.
    echo GothamForge could not start. Make sure Python 3 is installed and run:
    echo     pip install pillow numpy
    echo.
    pause
)
