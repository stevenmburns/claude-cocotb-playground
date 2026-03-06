#!/usr/bin/env bash
# Run cocotb tests with the project venv and locally-installed verilator
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$SCRIPT_DIR/../.venv/bin:/home/smburns/.local/bin:$PATH"
exec make "$@"
