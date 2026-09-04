@echo off
setlocal
cd /d "%~dp0.."
cmake --preset release
if errorlevel 1 exit /b 1
cmake --build --preset release-build
if errorlevel 1 exit /b 1
windeployqt --release --no-translations build-v2\release\Release\NumpadStreamDeck.exe
if errorlevel 1 exit /b 1
if exist dist-v2 rmdir /s /q dist-v2
mkdir dist-v2
xcopy /E /I /Y build-v2\release\Release dist-v2 >nul
ctest --preset release-test
endlocal