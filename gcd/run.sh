#!/usr/bin/env bash
# Run cocotb tests via pytest.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$SCRIPT_DIR/../.venv/bin:/home/smburns/.local/bin:$PATH"
exec python -m pytest test_runner.py -v "$@"
