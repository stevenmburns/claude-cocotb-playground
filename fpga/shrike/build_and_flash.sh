#!/bin/bash
# build_and_flash.sh — end-to-end FPGA build, flash, and test
#
# Usage: ./build_and_flash.sh <ffpga_project_path> [micropython_script]
#
# Steps:
#   1. Synthesize .ffpga project (via synth.sh / xdotool)
#   2. Copy bitstream to RP2040 filesystem
#   3. Flash the FPGA
#   4. Optionally run a MicroPython test script
#
# Example:
#   ./build_and_flash.sh fpga/shrike/uart_gcd/shrike_project/uart_echo/uart_echo.ffpga \
#       fpga/shrike/uart_gcd/micropython/echo_test.py

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"
SERIAL_PORT="${SHRIKE_PORT:-/dev/ttyACM0}"

if [ -z "$1" ]; then
    echo "Usage: $0 <ffpga_project_path> [micropython_script]"
    exit 1
fi

FFPGA_PATH="$(realpath "$1")"
TEST_SCRIPT="${2:+$(realpath "$2")}"

if [ ! -f "$FFPGA_PATH" ]; then
    echo "Error: $FFPGA_PATH not found"
    exit 1
fi

# Derive bitstream path
PROJECT_DIR="$(dirname "$FFPGA_PATH")"
BITSTREAM="$PROJECT_DIR/ffpga/build/bitstream/FPGA_bitstream_MCU.bin"

# Activate venv for mpremote
source "$VENV/bin/activate"

# ── Step 1: Synthesize ────────────────────────────────────────────────
echo "═══ Step 1: Synthesize ═══"
"$SCRIPT_DIR/synth.sh" "$FFPGA_PATH"

if [ ! -f "$BITSTREAM" ]; then
    echo "Error: Bitstream not found at $BITSTREAM"
    exit 1
fi

# ── Step 2: Copy bitstream to RP2040 ─────────────────────────────────
echo ""
echo "═══ Step 2: Copy bitstream to RP2040 ═══"
mpremote connect "$SERIAL_PORT" cp "$BITSTREAM" :FPGA_bitstream_MCU.bin
echo "Bitstream copied."

# ── Step 3: Flash the FPGA ───────────────────────────────────────────
echo ""
echo "═══ Step 3: Flash FPGA ═══"
mpremote connect "$SERIAL_PORT" exec "
import shrike
shrike.flash('/FPGA_bitstream_MCU.bin')
print('FPGA flashed successfully.')
"

# ── Step 4: Run test script (optional) ───────────────────────────────
if [ -n "$TEST_SCRIPT" ]; then
    if [ ! -f "$TEST_SCRIPT" ]; then
        echo "Error: Test script not found: $TEST_SCRIPT"
        exit 1
    fi
    echo ""
    echo "═══ Step 4: Run test ═══"
    # Brief delay for FPGA to start up
    sleep 1
    mpremote connect "$SERIAL_PORT" run "$TEST_SCRIPT"
fi

echo ""
echo "═══ Done ═══"
