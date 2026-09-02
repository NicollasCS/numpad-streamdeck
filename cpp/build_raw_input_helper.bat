@echo off
setlocal

REM Build this file inside a Visual Studio Developer Command Prompt.
REM Example:
REM   "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
REM   cl /EHsc /std:c++17 raw_input_filter.cpp /link user32.lib /OUT:raw_input_filter.exe

if "%VSCMD_VER%"=="" (
    echo This build script expects a Visual Studio Developer Command Prompt.
    echo Open one and run:
    echo   cl /EHsc /std:c++17 raw_input_filter.cpp /link user32.lib /OUT:raw_input_filter.exe
    exit /b 1
)

cl /EHsc /std:c++17 raw_input_filter.cpp /link user32.lib /OUT:raw_input_filter.exe
if errorlevel 1 exit /b 1

echo Build complete: raw_input_filter.exe
