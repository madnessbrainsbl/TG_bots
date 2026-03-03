@echo off
chcp 65001 > nul
echo ========================================
echo   🤖 ЗАПУСК RELAY BOT
echo ========================================
echo.
if "%RELAY_BOT_TOKEN%"=="" (
  echo [ERROR] Set RELAY_BOT_TOKEN before start
  pause
  exit /b 1
)
if not exist "relay_config.json" (
  echo [ERROR] relay_config.json not found
  echo Copy relay_config.example.json to relay_config.json and fill values
  pause
  exit /b 1
)
python relay_bot.py
pause
