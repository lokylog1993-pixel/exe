
@echo off
setlocal enabledelayedexpansion
echo === BitD GM AI - Windows build ===
where python >nul 2>&1 || (echo Python not found. Install Python 3.10+ and rerun.& pause & exit /b 1)
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller pywebview
echo.
echo Building (onedir, windowed)...
pyinstaller packaging\bitd_gm_ai_win.spec --noconfirm
echo.
echo DONE. Run: dist\BitD_GM_AI\BitD GM AI.exe
pause
