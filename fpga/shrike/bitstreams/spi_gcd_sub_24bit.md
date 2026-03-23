---
project: spi_gcd
gcd_module: gcd (subtraction)
width: 24
source_commit: 3a37559
build_date: 2026-03-22
---

# spi_gcd_sub_24bit.bin

24-bit subtraction-based GCD (Euclidean) over SPI, targeting the Vicharak
Shrike SLG47910V FPGA.

## Protocol

SPI Mode 0 (CPOL=0, CPHA=0), MSB-first bits, LSB-first bytes, 1 MHz.

1. Transaction 1 (6 bytes, SS_N held low):
   a[7:0], a[15:8], a[23:16], b[7:0], b[15:8], b[23:16]
2. GCD starts when SS_N deasserts; wait for `result_ready` rising edge (RP_IO1 IRQ)
3. Transaction 2 (3 bytes, SS_N held low):
   MOSI ignored; MISO returns r[7:0], r[15:8], r[23:16]

## Pin Mapping

| Signal         | FPGA GPIO | FPGA PIN | IOB xy  | RP2040       | Connection  |
|----------------|-----------|----------|---------|--------------|-------------|
| clk            | —         | —        | CLK W   | —            | on-chip osc |
| clk_en         | —         | —        | [0:25]  | —            | OSC_EN      |
| ext_rst        | GPIO15    | 6        | [31:8]  | GPIO0 (RP_IO0)  | PCB trace   |
| spi_sck        | GPIO0     | 13       | [0:6]   | GPIO10 (RP_IO10) | jumper wire |
| spi_mosi       | GPIO1     | 14       | [0:7]   | GPIO11 (RP_IO11) | jumper wire |
| spi_miso       | GPIO2     | 15       | [0:8]   | GPIO8 (RP_IO8)   | jumper wire |
| spi_ss_n       | GPIO7     | 20       | [0:24]  | GPIO9 (RP_IO9)   | jumper wire |
| result_ready   | GPIO13    | 4        | [31:22] | GPIO1 (RP_IO1)   | PCB trace   |

RP2040 uses hardware SPI1: SCK=GPIO10, MOSI=GPIO11, MISO=GPIO8, CSn=GPIO9 (manual).

## Source Files

- `fpga/shrike/spi_gcd/spi_gcd_top.v` — top-level FSM (6-byte RX, 3-byte TX)
- `fpga/shrike/spi_gcd/spi_target.v` — Vicharak SPI target reference design
- `gcd/gcd.v` — subtraction-based Euclidean GCD, WIDTH=24

## gen_ffpga.py Command

```sh
python fpga/shrike/gen_ffpga.py spi_gcd \
    --src fpga/shrike/spi_gcd/spi_gcd_top.v \
    --src fpga/shrike/spi_gcd/spi_target.v \
    --src gcd/gcd.v \
    --pin clk:CLK --pin clk_en:OSC_EN \
    --pin ext_rst:GPIO15_IN \
    --pin spi_sck:GPIO0_IN \
    --pin spi_mosi:GPIO1_IN \
    --pin spi_miso:GPIO2_OUT0 --pin spi_miso_oe:GPIO2_OUT1 \
    --pin spi_ss_n:GPIO7_IN \
    --pin result_ready:GPIO13_OUT0 --pin result_ready_oe:GPIO13_OUT1 \
    --out fpga/shrike/spi_gcd/shrike_project
```

## Hardware Test Results

Not yet tested on hardware.

## Flash Procedure

```sh
# Using mpremote:
mpremote cp fpga/shrike/bitstreams/spi_gcd_sub_24bit.bin :FPGA_bitstream_MCU.bin
mpremote exec "import shrike; shrike.flash('/FPGA_bitstream_MCU.bin')"
```
