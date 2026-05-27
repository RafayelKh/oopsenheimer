#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-3000}"
CLI_MODE=""
CLI_FLUKA_BIN=""
SETUP_ONLY=0
SKIP_INSTALL=0
OOPSENHEIMER_MODE_WAS_SET=0

if [[ -n "${OOPSENHEIMER_SIM_MODE+x}" ]]; then
  OOPSENHEIMER_MODE_WAS_SET=1
fi

usage() {
  cat <<'USAGE'
Usage: scripts/setup_and_run.sh [options]

Sets up and runs Oops-enheimer locally:
  - creates/uses .venv
  - installs Python editable packages
  - installs Next.js dependencies
  - starts FastAPI on 127.0.0.1:8000
  - starts Next.js on 127.0.0.1:3000

Options:
  --mode auto|mock|fluka   Simulation mode. Default: auto-detect FLUKA.
  --fluka-bin PATH         FLUKA bin directory, e.g. /Users/admin/Downloads/fluka4-5.1/bin
  --api-port PORT          API port. Default: 8000
  --web-port PORT          Web port. Default: 3000
  --setup-only             Install dependencies and exit.
  --no-install             Skip dependency installation.
  -h, --help               Show this help.

Environment overrides:
  API_HOST, API_PORT, WEB_HOST, WEB_PORT, STORAGE_ROOT, VENV_DIR, FLUKA_BIN
USAGE
}

log() {
  printf '[oops-enheimer] %s\n' "$*"
}

die() {
  printf '[oops-enheimer] error: %s\n' "$*" >&2
  exit 1
}

resolve_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s\n' "$ROOT_DIR/$1" ;;
  esac
}

source_env_file() {
  local env_file="$ROOT_DIR/.env"
  if [[ -f "$env_file" ]]; then
    log "Loading $env_file"
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
  elif [[ -f "$ROOT_DIR/.env.example" ]]; then
    log "No .env found; using defaults plus .env.example as a reference"
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}

print_port_owner() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local attempts=60
  local i=0

  if ! command -v curl >/dev/null 2>&1; then
    log "curl not found; skipping $name readiness check"
    return
  fi

  while (( i < attempts )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$name is ready at $url"
      return
    fi
    i=$((i + 1))
    sleep 1
  done

  die "$name did not become ready at $url"
}

check_python_version() {
  python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required")
PY
}

install_python_deps() {
  require_command python3
  check_python_version

  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtualenv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1091
  . "$VENV_DIR/bin/activate"
  log "Installing Python packages"
  python -m pip install --upgrade pip
  python -m pip install -e "$ROOT_DIR/packages/compiler" -e "$ROOT_DIR/workers/fluka_runner" -e "$ROOT_DIR/apps/api"
}

install_web_deps() {
  require_command npm
  log "Installing web dependencies"
  if [[ -f "$ROOT_DIR/apps/web/package-lock.json" ]]; then
    npm --prefix "$ROOT_DIR/apps/web" ci
  else
    npm --prefix "$ROOT_DIR/apps/web" install
  fi
}

ensure_runtime_env() {
  STORAGE_ROOT="$(resolve_path "${STORAGE_ROOT:-storage}")"
  export STORAGE_ROOT
  mkdir -p "$STORAGE_ROOT/jobs" "$STORAGE_ROOT/scenes" "$STORAGE_ROOT/logs"

  if [[ -z "${FLUKA_BIN:-}" && -d "/Users/admin/Downloads/fluka4-5.1/bin" ]]; then
    FLUKA_BIN="/Users/admin/Downloads/fluka4-5.1/bin"
  fi

  local selected_mode="$CLI_MODE"
  if [[ -z "$selected_mode" && "$OOPSENHEIMER_MODE_WAS_SET" -eq 1 ]]; then
    selected_mode="${OOPSENHEIMER_SIM_MODE:-}"
  fi
  if [[ -z "$selected_mode" ]]; then
    selected_mode="auto"
  fi

  case "$selected_mode" in
    auto)
      if [[ -n "${FLUKA_BIN:-}" && -x "$FLUKA_BIN/rfluka" ]]; then
        OOPSENHEIMER_SIM_MODE="fluka"
      else
        OOPSENHEIMER_SIM_MODE="mock"
      fi
      ;;
    mock|fluka)
      OOPSENHEIMER_SIM_MODE="$selected_mode"
      ;;
    *)
      die "--mode must be one of: auto, mock, fluka"
      ;;
  esac

  if [[ "$OOPSENHEIMER_SIM_MODE" == "fluka" ]]; then
    [[ -n "${FLUKA_BIN:-}" ]] || die "FLUKA_BIN is required in fluka mode"
    [[ -x "$FLUKA_BIN/rfluka" ]] || die "missing executable: $FLUKA_BIN/rfluka"
    [[ -x "$FLUKA_BIN/usbsuw" ]] || die "missing executable: $FLUKA_BIN/usbsuw"
    [[ -x "$FLUKA_BIN/usbrea" ]] || die "missing executable: $FLUKA_BIN/usbrea"
    export FLUKA_BIN
  fi

  export OOPSENHEIMER_SIM_MODE
  export NEXT_PUBLIC_API_BASE_URL="http://$API_HOST:$API_PORT"

  log "Simulation mode: $OOPSENHEIMER_SIM_MODE"
  if [[ "$OOPSENHEIMER_SIM_MODE" == "fluka" ]]; then
    log "FLUKA_BIN: $FLUKA_BIN"
  fi
  log "Storage: $STORAGE_ROOT"
}

start_servers() {
  local api_log="$STORAGE_ROOT/logs/api.log"
  local web_log="$STORAGE_ROOT/logs/web.log"
  local api_pid=""
  local web_pid=""

  if port_in_use "$API_PORT"; then
    print_port_owner "$API_PORT"
    die "API port $API_PORT is already in use"
  fi
  if port_in_use "$WEB_PORT"; then
    print_port_owner "$WEB_PORT"
    die "Web port $WEB_PORT is already in use"
  fi

  # shellcheck disable=SC1091
  . "$VENV_DIR/bin/activate"

  log "Starting API; log: $api_log"
  (
    cd "$ROOT_DIR/apps/api"
    exec python -m uvicorn app.main:app --host "$API_HOST" --port "$API_PORT"
  ) >"$api_log" 2>&1 &
  api_pid="$!"

  log "Starting web app; log: $web_log"
  (
    cd "$ROOT_DIR/apps/web"
    exec npm run dev -- --hostname "$WEB_HOST" --port "$WEB_PORT"
  ) >"$web_log" 2>&1 &
  web_pid="$!"

  cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    if [[ -n "$api_pid" ]] && kill -0 "$api_pid" >/dev/null 2>&1; then
      kill "$api_pid" >/dev/null 2>&1 || true
    fi
    if [[ -n "$web_pid" ]] && kill -0 "$web_pid" >/dev/null 2>&1; then
      kill "$web_pid" >/dev/null 2>&1 || true
    fi
    wait "$api_pid" >/dev/null 2>&1 || true
    wait "$web_pid" >/dev/null 2>&1 || true
    exit "$exit_code"
  }
  trap cleanup EXIT INT TERM

  wait_for_url "http://$API_HOST:$API_PORT/health" "API"
  wait_for_url "http://$WEB_HOST:$WEB_PORT" "Web"

  log "Oops-enheimer is running"
  log "Open: http://$WEB_HOST:$WEB_PORT"
  log "Press Ctrl+C to stop both servers"

  while true; do
    if ! kill -0 "$api_pid" >/dev/null 2>&1; then
      wait "$api_pid"
      die "API exited; see $api_log"
    fi
    if ! kill -0 "$web_pid" >/dev/null 2>&1; then
      wait "$web_pid"
      die "Web app exited; see $web_log"
    fi
    sleep 1
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      CLI_MODE="${2:-}"
      [[ -n "$CLI_MODE" ]] || die "--mode requires a value"
      shift 2
      ;;
    --fluka-bin)
      CLI_FLUKA_BIN="${2:-}"
      [[ -n "$CLI_FLUKA_BIN" ]] || die "--fluka-bin requires a path"
      shift 2
      ;;
    --api-port)
      API_PORT="${2:-}"
      [[ -n "$API_PORT" ]] || die "--api-port requires a value"
      shift 2
      ;;
    --web-port)
      WEB_PORT="${2:-}"
      [[ -n "$WEB_PORT" ]] || die "--web-port requires a value"
      shift 2
      ;;
    --setup-only)
      SETUP_ONLY=1
      shift
      ;;
    --no-install)
      SKIP_INSTALL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

cd "$ROOT_DIR"
source_env_file
if [[ -n "$CLI_FLUKA_BIN" ]]; then
  FLUKA_BIN="$CLI_FLUKA_BIN"
fi
ensure_runtime_env

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  install_python_deps
  install_web_deps
else
  log "Skipping dependency installation"
fi

if [[ "$SETUP_ONLY" -eq 1 ]]; then
  log "Setup complete"
  exit 0
fi

start_servers
