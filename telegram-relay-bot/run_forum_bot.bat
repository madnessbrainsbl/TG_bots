@echo off
chcp 65001 > nul
echo ========================================
echo   FORUM RELAY BOT - ZAPUSK
echo ========================================
echo.
if "%FORUM_BOT_TOKEN%"=="" (
  echo [ERROR] Set FORUM_BOT_TOKEN before start
  pause
  exit /b 1
)
if not exist "forum_relay_config.json" (
  echo [ERROR] forum_relay_config.json not found
  echo Copy forum_relay_config.example.json to forum_relay_config.json and fill values
  pause
  exit /b 1
)
python forum_relay_bot.py
pause
