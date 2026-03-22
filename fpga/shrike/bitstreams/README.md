# Pre-built FPGA Bitstreams

This directory stores pre-built bitstreams for the Vicharak Shrike
SLG47910V FPGA. Each `.bin` file has a matching `.md` file with metadata:
source commit, pin mapping, build config, and test results.

## Naming Convention

`<project>_<variant>_<width>bit.bin`

## Usage

```sh
# Flash a pre-built bitstream (no synthesis needed):
source .venv/bin/activate
mpremote cp fpga/shrike/bitstreams/<name>.bin :FPGA_bitstream_MCU.bin
mpremote exec "import shrike; shrike.flash('/FPGA_bitstream_MCU.bin')"
```

## Inventory

| Bitstream | Size | Utilization | Tested |
|-----------|------|-------------|--------|
| `uart_gcd_binary_24bit.bin` | 45 KB | 96% logic | 9/9 passed |
