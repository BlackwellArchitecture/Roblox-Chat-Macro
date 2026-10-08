@echo off
title Build Roblox Chat Macro Standalone EXE
echo ========================================================
echo Building Roblox Chat Macro Standalone EXE with PyInstaller...
echo ========================================================

py -m PyInstaller --noconsole --onefile --collect-all customtkinter --name "RobloxChatMacro" main.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo Build Successful! 
    echo Your standalone executable is located in: dist\RobloxChatMacro.exe
    echo ========================================================
) else (
    echo.
    echo Build failed. Check the error messages above.
)
pause
