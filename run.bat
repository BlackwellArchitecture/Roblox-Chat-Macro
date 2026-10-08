@echo off
title Roblox Chat Macro
echo Starting Roblox Chat Macro...
py main.py
if %errorlevel% neq 0 (
    python main.py
)
pause
