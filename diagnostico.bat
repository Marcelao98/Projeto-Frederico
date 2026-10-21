@echo off
rem Confere cada peça do Frederico e mostra o erro inteiro do que falhar.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m frederico.diagnostico %*
pause
