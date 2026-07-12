@echo off
title Stable Diffusion Telegram Bot Launcher
echo ===================================================
echo   Launching Stable Diffusion Telegram Bot...
echo ===================================================
echo.

:: Switch to the correct drive
G:

:: Navigate to your project folder
cd "G:\experiments\img_gen\stable-diffusion-webui"

:: Run the bot using your virtual environment's Python
venv\Scripts\python.exe telegram_bot.py

:: If the bot crashes or stops, keep the window open so you can read the error
echo.
echo Bot has stopped running.
pause