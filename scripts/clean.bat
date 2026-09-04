@echo off
setlocal
cd /d "%~dp0.."
if exist build-v2 rmdir /s /q build-v2
endlocal