@echo off
REM Script de lancement pour Windows
REM Double-cliquez sur ce fichier pour lancer l'application

cd /d "%~dp0"

REM Verifier si python est installe
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python 3 n'est pas installe.
    echo Veuillez l'installer depuis https://www.python.org/downloads/
    echo IMPORTANT : Cochez "Add Python to PATH" lors de l'installation !
    echo.
    echo Appuyez sur une touche pour quitter...
    pause >nul
    exit /b 1
)

REM Lancer l'application
python main.py

REM En cas d'erreur, garder la fenetre ouverte
if %ERRORLEVEL% neq 0 (
    echo.
    echo Une erreur est survenue. Appuyez sur une touche pour quitter...
    pause >nul
)
