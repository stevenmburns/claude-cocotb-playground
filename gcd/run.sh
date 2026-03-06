#!/usr/bin/env bash
# Run cocotb tests with the project venv and locally-installed verilator.
# Usage:
#   ./run.sh              → pytest (default)
#   ./run.sh make         → GNU Make / Verilator Makefile
#   ./run.sh make clean   → clean build artefacts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$SCRIPT_DIR/../.venv/bin:/home/smburns/.local/bin:$PATH"

if [[ "${1}" == "make" ]]; then
    shift
    exec make "$@"
else
    exec python -m pytest test_runner.py -v "$@"
fi
