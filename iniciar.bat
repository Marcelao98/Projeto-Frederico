@echo off
rem Liga o Frederico: cria o ambiente na primeira vez e abre o painel.
cd /d "%~dp0"
where ffmpeg >nul 2>nul || (echo Preciso do ffmpeg no PATH. O mesmo que a Natty usa serve. & pause & exit /b 1)
if not exist .venv (
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q --upgrade -r requirements.txt
python -m frederico
pause
