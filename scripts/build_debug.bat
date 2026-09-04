@echo off
setlocal
cd /d "%~dp0.."
cmake --preset debug
if errorlevel 1 exit /b 1
cmake --build --preset debug-build
if errorlevel 1 exit /b 1
windeployqt --debug --no-translations build-v2\debug\Debug\NumpadStreamDeck.exe
if errorlevel 1 exit /b 1
ctest --preset debug-test
endlocal