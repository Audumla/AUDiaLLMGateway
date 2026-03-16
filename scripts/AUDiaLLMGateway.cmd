@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0AUDiaLLMGateway.ps1" %*
endlocal
