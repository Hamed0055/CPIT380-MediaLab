@echo off
setlocal
pushd "%~dp0" || exit /b 1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run main.py %*
) else (
    python -m streamlit run main.py %*
)
set "LAUNCH_STATUS=%errorlevel%"
popd
exit /b %LAUNCH_STATUS%
