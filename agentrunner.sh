#!/usr/bin/env bash
# agentrunner - Universal AI agent orchestration CLI
set -euo pipefail

REPO_URL="https://github.com/Audumla/AgentRunner.git"
RUNTIME_DIR="$HOME/.agent-system/runtime"
INSTALLER="$RUNTIME_DIR/agent_system/install.py"
WORKSPACE_SELECTOR="$RUNTIME_DIR/agent_system/core/tools/workspace_install_selector.py"

show_help() {
    echo "AgentRunner CLI"
    echo "Usage: agentrunner <command> [args]"
    echo ""
    echo "Commands:"
    echo "  install [name]  Bootstrap a new project in a new directory"
    echo "  update          Update the global AgentRunner core and current project"
    echo "  start           Launch the monitoring dashboard for the current project"
    echo "  auth [--fix]    Check or fix AI provider authentication"
    echo "  detect          Detect installed AI providers and update config"
    echo "  permissions     Configure provider permission prompts"
    echo "  local-llm       Manage local LLM (status|start|stop|configure|configure-project)"
    echo "  help            Show this help message"
}

ensure_runtime() {
    local bootstrap=0
    if [ ! -d "$RUNTIME_DIR" ]; then
        bootstrap=1
    elif [ -z "$(ls -A "$RUNTIME_DIR" 2>/dev/null)" ]; then
        bootstrap=1
    fi

    if [ "$bootstrap" -eq 1 ]; then
        echo "[agentrunner] Downloading core runtime to $RUNTIME_DIR..."
        rm -rf "$RUNTIME_DIR"
        mkdir -p "$(dirname "$RUNTIME_DIR")"
        git clone "$REPO_URL" "$RUNTIME_DIR"
    fi
}

refresh_local_launchers() {
    local latest_sh="$RUNTIME_DIR/agent_system/scripts/agentrunner.sh"
    local latest_ps1="$RUNTIME_DIR/agent_system/scripts/agentrunner.ps1"
    local latest_cmd="$RUNTIME_DIR/agent_system/scripts/agentrunner.cmd"
    if [ -f "$latest_sh" ]; then
        cp "$latest_sh" "."
        chmod +x "./agentrunner.sh" || true
    fi
    if [ -f "$latest_ps1" ]; then
        cp "$latest_ps1" "."
    fi
    if [ -f "$latest_cmd" ]; then
        cp "$latest_cmd" "."
    fi
}

repair_runtime() {
    local ts
    ts="$(date +%Y%m%d%H%M%S)"
    local broken_dir="$RUNTIME_DIR.broken-$ts"

    if [ -d "$RUNTIME_DIR" ]; then
        echo "[agentrunner] Runtime repo is conflicted. Moving it to:"
        echo "  $broken_dir"
        mv "$RUNTIME_DIR" "$broken_dir"
    fi

    mkdir -p "$(dirname "$RUNTIME_DIR")"
    echo "[agentrunner] Cloning a clean runtime to $RUNTIME_DIR ..."
    git clone "$REPO_URL" "$RUNTIME_DIR"
    INSTALLER="$RUNTIME_DIR/agent_system/install.py"
}

update_runtime_core() {
    local py_cmd="$1"
    if ! "$py_cmd" "$INSTALLER" update --workspace . --no-workspace-refresh --autostash; then
        echo "WARNING: [agentrunner] Runtime update failed; attempting runtime self-repair..." >&2
        repair_runtime
        if ! "$py_cmd" "$INSTALLER" update --workspace . --no-workspace-refresh --autostash; then
            echo "ERROR: [agentrunner] Runtime update still failed after self-repair." >&2
            return 1
        fi
    fi
}

get_python() {
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
    elif command -v python >/dev/null 2>&1; then
        echo "python"
    else
        echo "ERROR: Python 3.9+ is required." >&2
        exit 1
    fi
}

get_repo_root() {
    local workspace="${1:-.}"
    git -C "$workspace" rev-parse --show-toplevel 2>/dev/null || true
}

assert_project_root() {
    local workspace="${1:-.}"
    local command_name="${2:-command}"
    local workspace_abs
    workspace_abs="$(cd "$workspace" && pwd -P)"
    local git_root
    git_root="$(git -C "$workspace_abs" rev-parse --show-toplevel 2>/dev/null || true)"

    if [ -z "$git_root" ]; then
        echo "ERROR: $command_name must run from the git repository root." >&2
        exit 1
    fi

    git_root="$(cd "$git_root" && pwd -P)"
    if [ "$git_root" != "$workspace_abs" ]; then
        echo "ERROR: $command_name must run from repository root." >&2
        echo "  current: $workspace_abs" >&2
        echo "  root:    $git_root" >&2
        exit 1
    fi
}

invoke_workspace_selector() {
    local sub_command="$1"
    shift || true
    "$PYTHON_BIN" "$WORKSPACE_SELECTOR" \
        --workspace . \
        --runtime-dir "$RUNTIME_DIR" \
        --installer "$INSTALLER" \
        --command "$sub_command" \
        -- "$@"
}

COMMAND="${1:-help}"
PYTHON_BIN="$(get_python)"

case "$COMMAND" in
    install)
        ensure_runtime
        update_runtime_core "$PYTHON_BIN"
        refresh_local_launchers

        PROJ_NAME=""
        INSTALL_EXTRA_ARGS=()
        if [ "$#" -ge 2 ]; then
            if [[ "${2}" == -* ]]; then
                INSTALL_EXTRA_ARGS=("${@:2}")
            else
                PROJ_NAME="${2}"
                if [ "$#" -gt 2 ]; then
                    INSTALL_EXTRA_ARGS=("${@:3}")
                fi
            fi
        fi

        if [ -z "$PROJ_NAME" ]; then
            selector_rc=0
            invoke_workspace_selector install "${INSTALL_EXTRA_ARGS[@]}" || selector_rc=$?
            if [ "$selector_rc" -eq 0 ]; then
                exit 0
            fi
            if [ "$selector_rc" -ne 2 ]; then
                exit "$selector_rc"
            fi

            cwd="$(pwd -P)"
            repo_root="$(get_repo_root ".")"
            if [ -n "$repo_root" ]; then
                repo_root="$(cd "$repo_root" && pwd -P)"
                if [ "$repo_root" = "$cwd" ]; then
                    read -r -p "Detected git project root '$cwd'. Enable AgentRunner for this project? [Y/n]: " confirm
                    case "$confirm" in
                        ""|[Yy]|[Yy][Ee][Ss]) PROJ_NAME="." ;;
                        *) PROJ_NAME="" ;;
                    esac
                fi
            fi
        fi

        if [ -z "$PROJ_NAME" ]; then
            read -r -p "Enter name for your new project: " PROJ_NAME
        fi

        mkdir -p "$PROJ_NAME"
        cd "$PROJ_NAME"
        if [ ! -d ".git" ]; then
            if ! git init >/dev/null; then
                echo "ERROR: Failed to initialize git repository in $PROJ_NAME." >&2
                exit 1
            fi
        fi

        assert_project_root "." "install"
        "$PYTHON_BIN" "$INSTALLER" install --workspace . "${INSTALL_EXTRA_ARGS[@]}"
        ;;
    update)
        ensure_runtime
        refresh_local_launchers
        selector_rc=0
        invoke_workspace_selector update --autostash || selector_rc=$?
        if [ "$selector_rc" -eq 0 ]; then
            exit 0
        fi
        if [ "$selector_rc" -ne 2 ]; then
            exit "$selector_rc"
        fi
        assert_project_root "." "update"
        if ! "$PYTHON_BIN" "$INSTALLER" update --workspace . --autostash; then
            echo "WARNING: [agentrunner] Workspace update failed; repairing runtime clone and retrying..." >&2
            repair_runtime
            "$PYTHON_BIN" "$INSTALLER" update --workspace . --autostash
        fi
        refresh_local_launchers
        ;;
    start)
        ensure_runtime
        refresh_local_launchers
        shift || true
        selector_rc=0
        invoke_workspace_selector start "$@" || selector_rc=$?
        if [ "$selector_rc" -eq 0 ]; then
            exit 0
        fi
        if [ "$selector_rc" -ne 2 ]; then
            exit "$selector_rc"
        fi
        assert_project_root "." "start"
        "$PYTHON_BIN" "$INSTALLER" start --workspace . "$@"
        ;;
    auth)
        ensure_runtime
        refresh_local_launchers
        shift || true
        if [ "$#" -eq 0 ]; then
            set -- --fix
        fi
        selector_rc=0
        invoke_workspace_selector auth "$@" || selector_rc=$?
        if [ "$selector_rc" -eq 0 ]; then
            exit 0
        fi
        if [ "$selector_rc" -ne 2 ]; then
            exit "$selector_rc"
        fi
        assert_project_root "." "auth"
        "$PYTHON_BIN" "$INSTALLER" auth --workspace . "$@"
        ;;
    detect)
        ensure_runtime
        refresh_local_launchers
        shift || true
        selector_rc=0
        invoke_workspace_selector detect "$@" || selector_rc=$?
        if [ "$selector_rc" -eq 0 ]; then
            exit 0
        fi
        if [ "$selector_rc" -ne 2 ]; then
            exit "$selector_rc"
        fi
        assert_project_root "." "detect"
        "$PYTHON_BIN" "$INSTALLER" detect --workspace . "$@"
        ;;
    permissions)
        ensure_runtime
        refresh_local_launchers
        shift || true
        if [ "$#" -eq 0 ]; then
            set -- --mode prompt
        fi
        selector_rc=0
        invoke_workspace_selector permissions "$@" || selector_rc=$?
        if [ "$selector_rc" -eq 0 ]; then
            exit 0
        fi
        if [ "$selector_rc" -ne 2 ]; then
            exit "$selector_rc"
        fi
        assert_project_root "." "permissions"
        "$PYTHON_BIN" "$INSTALLER" permissions --workspace . "$@"
        ;;
    local-llm)
        ensure_runtime
        refresh_local_launchers
        shift || true
        sub_cmd="${1:-status}"
        runner="${2:-}"
        selector_args=()

        case "$sub_cmd" in
            status)
                selector_args=(status)
                ;;
            configure)
                selector_args=(configure)
                ;;
            configure-project)
                selector_args=(configure --project-only)
                ;;
            start)
                if [ -n "$runner" ]; then
                    selector_args=(start --runner "$runner")
                else
                    selector_args=(start)
                fi
                ;;
            stop)
                if [ -n "$runner" ]; then
                    selector_args=(stop --runner "$runner")
                else
                    selector_args=(stop)
                fi
                ;;
            *)
                echo "ERROR: Unknown local-llm command '$sub_cmd'. Use status|start|stop|configure|configure-project." >&2
                exit 1
                ;;
        esac

        selector_rc=0
        invoke_workspace_selector local-llm "${selector_args[@]}" || selector_rc=$?
        if [ "$selector_rc" -eq 0 ]; then
            exit 0
        fi
        if [ "$selector_rc" -ne 2 ]; then
            exit "$selector_rc"
        fi
        assert_project_root "." "local-llm"

        case "$sub_cmd" in
            status)
                "$PYTHON_BIN" "$INSTALLER" local-llm --workspace . status
                ;;
            configure)
                "$PYTHON_BIN" "$INSTALLER" local-llm --workspace . configure
                ;;
            configure-project)
                "$PYTHON_BIN" "$INSTALLER" local-llm --workspace . configure --project-only
                ;;
            start)
                if [ -n "$runner" ]; then
                    "$PYTHON_BIN" "$INSTALLER" local-llm --workspace . start --runner "$runner"
                else
                    "$PYTHON_BIN" "$INSTALLER" local-llm --workspace . start
                fi
                ;;
            stop)
                if [ -n "$runner" ]; then
                    "$PYTHON_BIN" "$INSTALLER" local-llm --workspace . stop --runner "$runner"
                else
                    "$PYTHON_BIN" "$INSTALLER" local-llm --workspace . stop
                fi
                ;;
        esac
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $COMMAND" >&2
        show_help
        exit 1
        ;;
esac
