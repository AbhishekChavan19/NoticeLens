@echo off
title Install NoticeLens APK
echo Looking for connected devices/emulators...
set ADB="C:\Users\abhis\AppData\Local\Android\Sdk\platform-tools\adb.exe"
%ADB% devices
echo.
echo Installing NoticeLens APK...
%ADB% install -r "c:\Desktop\NLP-Lab\NoticeLens\android\app\build\outputs\apk\debug\app-debug.apk"
echo.
echo Starting NoticeLens on device...
%ADB% shell am start -n com.noticelens.app/.MainActivity
pause
