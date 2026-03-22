---
project: uart_gcd
gcd_module: binary_gcd
width: 24
source_commit: 99a93bc
build_date: 2026-03-22
utilization: 96% logic, 90% LUT, 29% FF
cells: 819 (319 FDRE, 52 CARRY4, 55 INV, 393 LUT)
p_and_r_time: ~642s
---

# uart_gcd_binary_24bit.bin

24-bit binary GCD (Knuth Algorithm B) over UART, targeting the Vicharak
Shrike SLG47910V FPGA.

## Protocol

8N1 @ 115200 baud. All values LSB first.

1. Host → FPGA: 3 bytes (operand a)
2. Host → FPGA: 3 bytes (operand b)
3. FPGA → Host: 3 bytes (result = gcd(a, b))

## Pin Mapping

| Signal     | FPGA GPIO | FPGA PIN | IOB xy  | RP2040       | Connection  |
|------------|-----------|----------|---------|--------------|-------------|
| clk        | —         | —        | CLK W   | —            | on-chip osc |
| clk_en     | —         | —        | [0:25]  | —            | OSC_EN      |
| ext_rst    | GPIO3     | 16       | [0:9]   | GPIO2        | PCB trace   |
| uart_rx    | GPIO0     | 13       | [0:6]   | GPIO8 (TX)   | jumper wire |
| uart_tx    | GPIO1     | 14       | [0:7]   | GPIO9 (RX)   | jumper wire |
| uart_tx_oe | GPIO1     | 14       | [0:7]   | —            | (OE)        |

## Source Files

- `fpga/shrike/uart_gcd/gcd_top.v` — top-level FSM
- `fpga/shrike/uart_gcd/uart_rx.v` — 8N1 UART receiver
- `fpga/shrike/uart_gcd/uart_tx.v` — 8N1 UART transmitter (FDRE-only)
- `gcd/binary_gcd.v` — Knuth binary GCD, WIDTH=24

## gen_ffpga.py Command

```sh
python fpga/shrike/gen_ffpga.py uart_gcd \
    --src fpga/shrike/uart_gcd/gcd_top.v \
    --src fpga/shrike/uart_gcd/uart_rx.v \
    --src fpga/shrike/uart_gcd/uart_tx.v \
    --src gcd/binary_gcd.v \
    --pin clk:CLK --pin clk_en:OSC_EN \
    --pin ext_rst:GPIO3_IN \
    --pin uart_rx:GPIO0_IN \
    --pin uart_tx:GPIO1_OUT0 --pin uart_tx_oe:GPIO1_OUT1 \
    --out fpga/shrike/uart_gcd/shrike_project
```

## Hardware Test Results

9/9 passed (MicroPython `gcd_test.py`):

```
gcd(6, 4) = 2
gcd(48, 18) = 6
gcd(100, 75) = 25
gcd(255, 255) = 255
gcd(1000000, 750000) = 250000
gcd(16777215, 16777215) = 16777215
gcd(123456, 7890) = 6
gcd(0, 42) = 42
gcd(16777215, 1) = 1    ← worst case, near-instantaneous with binary GCD
```

## Flash Procedure

```sh
# Using mpremote:
mpremote cp fpga/shrike/bitstreams/uart_gcd_binary_24bit.bin :FPGA_bitstream_MCU.bin
mpremote exec "import shrike; shrike.flash('/FPGA_bitstream_MCU.bin')"

# Or via build_and_flash.sh (rebuilds from source):
./fpga/shrike/build_and_flash.sh \
    fpga/shrike/uart_gcd/shrike_project/uart_gcd/uart_gcd.ffpga \
    fpga/shrike/uart_gcd/micropython/gcd_test.py
```
