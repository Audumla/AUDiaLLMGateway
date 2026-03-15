@echo off
setlocal enabledelayedexpansion

:: agentrunner.cmd - Universal AI agent orchestration CLI for Windows (Legacy)

set "REPO_URL=https://github.com/ExampleOrg/AgentRunner.git"
set "RUNTIME_DIR=%USERPROFILE%\.agent-system\runtime"
set "INSTALLER=%RUNTIME_DIR%\agent_system\install.py"
set "WORKSPACE_SELECTOR=%RUNTIME_DIR%\agent_system\core\tools\workspace_install_selector.py"

if "%~1" == "" goto help
if "%~1" == "help" goto help

:: Find Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 ( echo ERROR: Python 3.9+ is required. & pause & exit /b 1 )
set "PY=python"

:: Bootstrap Runtime
set "BOOTSTRAP=0"
if not exist "%RUNTIME_DIR%" set "BOOTSTRAP=1"
if exist "%RUNTIME_DIR%" (
    dir /b /a "%RUNTIME_DIR%" | findstr . >nul || set "BOOTSTRAP=1"
)

if "%BOOTSTRAP%" == "1" (
    echo [agentrunner] Downloading core runtime to %RUNTIME_DIR%...
    if exist "%RUNTIME_DIR%" rmdir /s /q "%RUNTIME_DIR%"
    mkdir "%USERPROFILE%\.agent-system" >nul 2>nul
    git clone %REPO_URL% "%RUNTIME_DIR%"
)

if "%~1" == "install" goto install
if "%~1" == "update" goto update
if "%~1" == "start" goto start
if "%~1" == "auth" goto auth
if "%~1" == "detect" goto detect
if "%~1" == "permissions" goto permissions
if "%~1" == "local-llm" (
    call :refresh_launchers
    if "%~2" == "" (
        %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- status
    ) else if /I "%~2" == "configure-project" (
        %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- configure --project-only
    ) else if /I "%~2" == "start" (
        if "%~3" == "" (
            %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- start
        ) else (
            %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- start --runner "%~3"
        )
    ) else if /I "%~2" == "stop" (
        if "%~3" == "" (
            %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- stop
        ) else (
            %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- stop --runner "%~3"
        )
    ) else if /I "%~2" == "status" (
        %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- status
    ) else if /I "%~2" == "configure" (
        %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command local-llm -- configure
    ) else (
        echo ERROR: Unknown local-llm command "%~2". Use status^|start^|stop^|configure^|configure-project.
        exit /b 1
    )
    set "SELECTOR_RC=%ERRORLEVEL%"
    if "%SELECTOR_RC%" == "0" goto :eof
    if not "%SELECTOR_RC%" == "2" exit /b %SELECTOR_RC%

    call :ensure_project_root "." "local-llm"
    if %ERRORLEVEL% neq 0 exit /b 1
    if "%~2" == "" (
        %PY% "%INSTALLER%" local-llm --workspace . status
    ) else if /I "%~2" == "configure-project" (
        %PY% "%INSTALLER%" local-llm --workspace . configure --project-only
    ) else if /I "%~2" == "start" (
        if "%~3" == "" (
            %PY% "%INSTALLER%" local-llm --workspace . start
        ) else (
            %PY% "%INSTALLER%" local-llm --workspace . start --runner "%~3"
        )
    ) else if /I "%~2" == "stop" (
        if "%~3" == "" (
            %PY% "%INSTALLER%" local-llm --workspace . stop
        ) else (
            %PY% "%INSTALLER%" local-llm --workspace . stop --runner "%~3"
        )
    ) else if /I "%~2" == "status" (
        %PY% "%INSTALLER%" local-llm --workspace . status
    ) else if /I "%~2" == "configure" (
        %PY% "%INSTALLER%" local-llm --workspace . configure
    ) else (
        echo ERROR: Unknown local-llm command "%~2". Use status^|start^|stop^|configure^|configure-project.
        exit /b 1
    )
    goto :eof
)
goto help

:install
call :refresh_launchers
call :update_runtime_core
if %ERRORLEVEL% neq 0 exit /b 1
:: Parse: if %~2 starts with '-' it is a flag, not a project name
set "PROJ_NAME="
set "INSTALL_FLAGS="
if not "%~2"=="" (
    set "_TMP2=%~2"
    if "!_TMP2:~0,1!"=="-" (
        set "INSTALL_FLAGS=%~2"
        if not "%~3"=="" set "INSTALL_FLAGS=!INSTALL_FLAGS! %~3"
        if not "%~4"=="" set "INSTALL_FLAGS=!INSTALL_FLAGS! %~4"
        if not "%~5"=="" set "INSTALL_FLAGS=!INSTALL_FLAGS! %~5"
        if not "%~6"=="" set "INSTALL_FLAGS=!INSTALL_FLAGS! %~6"
    ) else (
        set "PROJ_NAME=%~2"
        if not "%~3"=="" (
            set "INSTALL_FLAGS=%~3"
            if not "%~4"=="" set "INSTALL_FLAGS=!INSTALL_FLAGS! %~4"
            if not "%~5"=="" set "INSTALL_FLAGS=!INSTALL_FLAGS! %~5"
            if not "%~6"=="" set "INSTALL_FLAGS=!INSTALL_FLAGS! %~6"
        )
    )
)
if "!PROJ_NAME!"=="" (
    if "!INSTALL_FLAGS!"=="" (
        %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%"
    ) else (
        %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" -- !INSTALL_FLAGS!
    )
    set "SELECTOR_RC=!ERRORLEVEL!"
    if "!SELECTOR_RC!"=="0" goto :eof
    if not "!SELECTOR_RC!"=="2" exit /b !SELECTOR_RC!

    call :get_repo_root "." "CURRENT_ROOT"
    for %%I in (".") do set "CURRENT_DIR=%%~fI"
    if defined CURRENT_ROOT (
        for %%I in ("!CURRENT_ROOT!\.") do set "CURRENT_ROOT=%%~fI"
        for %%I in ("!CURRENT_DIR!\.") do set "CURRENT_DIR=%%~fI"
        if /I "!CURRENT_ROOT!"=="!CURRENT_DIR!" (
            set /p "CONFIRM=Detected git project root '!CURRENT_DIR!'. Enable AgentRunner for this project? [Y/n]: "
            if /I "!CONFIRM!"=="n" (
                set "PROJ_NAME="
            ) else if /I "!CONFIRM!"=="no" (
                set "PROJ_NAME="
            ) else (
                set "PROJ_NAME=."
            )
        )
    )
)
if "!PROJ_NAME!"=="" set /p "PROJ_NAME=Enter name for your new project: "
if not exist "!PROJ_NAME!" mkdir "!PROJ_NAME!"
pushd "!PROJ_NAME!"
if not exist ".git" (
    git init
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to initialize git repository in !PROJ_NAME!.
        popd
        exit /b 1
    )
)
call :ensure_project_root "." "install"
if %ERRORLEVEL% neq 0 (
    popd
    exit /b 1
)
if "!INSTALL_FLAGS!"=="" (
    %PY% "%INSTALLER%" install --workspace .
) else (
    %PY% "%INSTALLER%" install --workspace . !INSTALL_FLAGS!
)
popd
goto :eof

:update
call :refresh_launchers
shift
%PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command update -- --autostash %*
set "SELECTOR_RC=%ERRORLEVEL%"
if "%SELECTOR_RC%" == "0" goto :eof
if not "%SELECTOR_RC%" == "2" exit /b %SELECTOR_RC%
call :ensure_project_root "." "update"
if %ERRORLEVEL% neq 0 exit /b 1
%PY% "%INSTALLER%" update --workspace . --autostash %*
if %ERRORLEVEL% neq 0 (
    echo WARNING: [agentrunner] Workspace update failed; repairing runtime clone and retrying...
    call :repair_runtime
    if %ERRORLEVEL% neq 0 exit /b 1
    %PY% "%INSTALLER%" update --workspace . --autostash %*
    if %ERRORLEVEL% neq 0 exit /b 1
)
call :refresh_launchers
goto :eof

:start
call :refresh_launchers
shift
%PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command start -- %*
set "SELECTOR_RC=%ERRORLEVEL%"
if "%SELECTOR_RC%" == "0" goto :eof
if not "%SELECTOR_RC%" == "2" exit /b %SELECTOR_RC%
call :ensure_project_root "." "start"
if %ERRORLEVEL% neq 0 exit /b 1
%PY% "%INSTALLER%" start --workspace . %*
goto :eof

:auth
call :refresh_launchers
shift
if "%~1" == "" (
    %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command auth -- --fix
) else (
    %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command auth -- %*
)
set "SELECTOR_RC=%ERRORLEVEL%"
if "%SELECTOR_RC%" == "0" goto :eof
if not "%SELECTOR_RC%" == "2" exit /b %SELECTOR_RC%
call :ensure_project_root "." "auth"
if %ERRORLEVEL% neq 0 exit /b 1
if "%~1" == "" (
    %PY% "%INSTALLER%" auth --workspace . --fix
) else (
    %PY% "%INSTALLER%" auth --workspace . %*
)
goto :eof

:detect
call :refresh_launchers
shift
%PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command detect -- %*
set "SELECTOR_RC=%ERRORLEVEL%"
if "%SELECTOR_RC%" == "0" goto :eof
if not "%SELECTOR_RC%" == "2" exit /b %SELECTOR_RC%
call :ensure_project_root "." "detect"
if %ERRORLEVEL% neq 0 exit /b 1
%PY% "%INSTALLER%" detect --workspace . %*
goto :eof

:permissions
call :refresh_launchers
shift
if "%~1" == "" (
    %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command permissions -- --mode prompt
) else (
    %PY% "%WORKSPACE_SELECTOR%" --workspace . --runtime-dir "%RUNTIME_DIR%" --installer "%INSTALLER%" --command permissions -- %*
)
set "SELECTOR_RC=%ERRORLEVEL%"
if "%SELECTOR_RC%" == "0" goto :eof
if not "%SELECTOR_RC%" == "2" exit /b %SELECTOR_RC%
call :ensure_project_root "." "permissions"
if %ERRORLEVEL% neq 0 exit /b 1
if "%~1" == "" (
    %PY% "%INSTALLER%" permissions --workspace . --mode prompt
) else (
    %PY% "%INSTALLER%" permissions --workspace . %*
)
goto :eof

:help
echo AgentRunner CLI
echo Usage: agentrunner ^<command^> [args]
echo.
echo Commands:
echo   install [name]  Bootstrap a new project in a new directory
echo   update          Update the global AgentRunner core and current project
echo   start           Launch the monitoring dashboard for the current project
echo   auth [--fix]    Check or fix AI provider authentication
echo   detect          Detect installed AI providers and update config
echo   permissions     Configure provider permission prompts
echo   local-llm       Manage local LLM (^status^|start^|stop^|configure^|configure-project^)
echo   help            Show this help message
echo.
echo Install flags (passed through to installer):
echo   --setup-release-please   Set up release-please GitHub Actions workflow
echo   --skip-release-please    Skip release-please setup
echo   --no-interactive         Skip all interactive prompts
echo   --skip-providers         Skip provider detection
echo   --skip-permissions       Skip provider permissions prompt
echo.
echo Update flags (passed through to installer):
echo   --setup-release-please   Set up release-please during this update
goto :eof

:refresh_launchers
set "LATEST_CMD=%RUNTIME_DIR%\agent_system\scripts\agentrunner.cmd"
set "LATEST_PS1=%RUNTIME_DIR%\agent_system\scripts\agentrunner.ps1"
set "LATEST_SH=%RUNTIME_DIR%\agent_system\scripts\agentrunner.sh"
if exist "%LATEST_CMD%" copy /y "%LATEST_CMD%" "." >nul
if exist "%LATEST_PS1%" copy /y "%LATEST_PS1%" "." >nul
if exist "%LATEST_SH%" copy /y "%LATEST_SH%" "." >nul
exit /b 0

:update_runtime_core
%PY% "%INSTALLER%" update --workspace . --no-workspace-refresh --autostash
if %ERRORLEVEL% neq 0 (
    echo WARNING: [agentrunner] Runtime update failed; attempting runtime self-repair...
    call :repair_runtime
    if %ERRORLEVEL% neq 0 exit /b 1
    %PY% "%INSTALLER%" update --workspace . --no-workspace-refresh --autostash
    if %ERRORLEVEL% neq 0 (
        echo ERROR: [agentrunner] Runtime update still failed after self-repair.
        exit /b 1
    )
)
exit /b 0

:repair_runtime
set "TS="
for /f "delims=" %%I in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyyMMddHHmmss\")"') do set "TS=%%I"
if "%TS%"=="" set "TS=%RANDOM%"
set "BROKEN_DIR=%RUNTIME_DIR%.broken-%TS%"
if exist "%RUNTIME_DIR%" (
    echo [agentrunner] Runtime repo is conflicted. Moving it to:
    echo   %BROKEN_DIR%
    move "%RUNTIME_DIR%" "%BROKEN_DIR%" >nul
    if %ERRORLEVEL% neq 0 (
        echo ERROR: [agentrunner] Could not move conflicted runtime directory.
        exit /b 1
    )
)
mkdir "%USERPROFILE%\.agent-system" >nul 2>nul
echo [agentrunner] Cloning a clean runtime to %RUNTIME_DIR% ...
git clone %REPO_URL% "%RUNTIME_DIR%"
if %ERRORLEVEL% neq 0 (
    echo ERROR: [agentrunner] Failed to clone clean runtime.
    exit /b 1
)
set "INSTALLER=%RUNTIME_DIR%\agent_system\install.py"
exit /b 0

:get_repo_root
set "ROOT_INPUT=%~1"
set "ROOT_VAR=%~2"
set "%ROOT_VAR%="
for %%I in ("%ROOT_INPUT%\.") do set "ROOT_ABS=%%~fI"
for /f "delims=" %%I in ('git -C "%ROOT_ABS%" rev-parse --show-toplevel 2^>nul') do set "%ROOT_VAR%=%%~fI"
exit /b 0

:ensure_project_root
set "WS_INPUT=%~1"
set "CMD_NAME=%~2"
if "%CMD_NAME%"=="" set "CMD_NAME=command"
for %%I in ("%WS_INPUT%\.") do set "WS_ABS=%%~fI"
set "GIT_ROOT="
for /f "delims=" %%I in ('git -C "%WS_ABS%" rev-parse --show-toplevel 2^>nul') do set "GIT_ROOT=%%~fI"
if not defined GIT_ROOT (
    echo ERROR: %CMD_NAME% must run from the git repository root.
    exit /b 1
)
for %%I in ("%GIT_ROOT%\.") do set "GIT_ROOT=%%~fI"
if /I not "%GIT_ROOT%"=="%WS_ABS%" (
    echo ERROR: %CMD_NAME% must run from repository root.
    echo   current: %WS_ABS%
    echo   root:    %GIT_ROOT%
    exit /b 1
)
exit /b 0
