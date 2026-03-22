#!/bin/bash
# synth.sh — automate ForgeFPGA synthesis via xdotool
#
# Usage: ./synth.sh path/to/project.ffpga
#
# Launches GPLauncher, clicks through to the synthesis panel,
# runs synthesis, generates the bitstream, and closes GPLauncher.

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 path/to/project.ffpga"
    exit 1
fi

FFPGA_PATH="$(realpath "$1")"
if [ ! -f "$FFPGA_PATH" ]; then
    echo "Error: $FFPGA_PATH not found"
    exit 1
fi

# Derive build directory and expected output files
PROJECT_DIR="$(dirname "$FFPGA_PATH")"
BUILD_DIR="$PROJECT_DIR/ffpga/build"
NETLIST="$BUILD_DIR/netlist.edif"
BITSTREAM="$BUILD_DIR/bitstream/FPGA_bitstream_MCU.bin"

# Button coordinates (from xdotool getmouselocation)
OK_X=662
OK_Y=489
FPGA_X=648
FPGA_Y=382
SYNTH_X=210
SYNTH_Y=951
BITSTREAM_X=202
BITSTREAM_Y=980
BITSTREAM_OK_X=575
BITSTREAM_OK_Y=728

SYNTH_TIMEOUT=120   # max seconds to wait for synthesis
BITSTREAM_TIMEOUT=1200  # max seconds to wait for bitstream (includes P&R)

# Wait for a file to be newer than a reference time
# Usage: wait_for_file FILE REFERENCE_TIME DESCRIPTION
wait_for_file() {
    local file="$1"
    local ref_time="$2"
    local desc="$3"
    local timeout="${4:-120}"
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if [ -f "$file" ]; then
            local file_time
            file_time=$(stat -c %Y "$file" 2>/dev/null || echo 0)
            if [ "$file_time" -gt "$ref_time" ]; then
                echo "$desc completed (${elapsed}s)"
                return 0
            fi
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    echo "Timeout waiting for $desc after ${timeout}s"
    return 1
}

# Record timestamps before we start
NOW=$(date +%s)

# Kill any existing GP6 instances first
pkill -9 -f "GP6.*--no-update" 2>/dev/null || true
pkill -9 -f "QtWebEngineProcess.*ForgeFPGA" 2>/dev/null || true
sleep 1

echo "Opening $FFPGA_PATH..."
/usr/local/go-configure-sw-hub/bin/GPLauncher "$FFPGA_PATH" &
LAUNCHER_PID=$!
sleep 8

# Find the GP6 child process so we can kill it cleanly later
GP6_PID=$(pgrep -f "GP6.*--no-update" | head -1)

# Click OK on the startup dialog
echo "Clicking OK..."
xdotool mousemove --sync $OK_X $OK_Y
xdotool click 1
sleep 2

# Double-click to open synthesis panel
echo "Opening synthesis panel..."
xdotool mousemove --sync $FPGA_X $FPGA_Y
xdotool click --repeat 2 --delay 100 1
sleep 2

# Click Synthesize
echo "Clicking Synthesize..."
xdotool mousemove --sync $SYNTH_X $SYNTH_Y
xdotool click 1

# Wait for netlist.edif to be updated (synthesis complete)
echo "Waiting for synthesis..."
wait_for_file "$NETLIST" "$NOW" "Synthesis" "$SYNTH_TIMEOUT"
sleep 1

# Click Generate Bitstream
echo "Clicking Generate Bitstream..."
xdotool mousemove --sync $BITSTREAM_X $BITSTREAM_Y
xdotool click 1

# Dismiss bitstream dialog
sleep 3
echo "Dismissing dialog..."
xdotool mousemove --sync $BITSTREAM_OK_X $BITSTREAM_OK_Y
xdotool click 1

# Wait for bitstream to be updated
echo "Waiting for bitstream generation..."
wait_for_file "$BITSTREAM" "$NOW" "Bitstream generation" "$BITSTREAM_TIMEOUT"
sleep 1

# Close GPLauncher — kill the GP6 process tree
echo "Closing GPLauncher..."
if [ -n "$GP6_PID" ]; then
    # Kill GP6 and all its children
    kill -9 -- -$(ps -o pgid= -p "$GP6_PID" | tr -d ' ') 2>/dev/null || true
fi
kill -9 $LAUNCHER_PID 2>/dev/null || true
wait $LAUNCHER_PID 2>/dev/null || true

echo "Done. Bitstream: $BITSTREAM"
