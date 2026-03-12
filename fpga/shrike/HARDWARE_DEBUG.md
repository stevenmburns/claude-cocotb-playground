# Shrike Hardware Debug Plan

## Key Finding: Shrike Repo Examples Use Wrong Pins

The UART/SPI examples in the Shrike repo (`uart_sum`, `uart_led`, `spi_loopback_led`) use
the **left-side** IOB pins (`xy[0:*]`) for their communication interfaces. These map to
**external header connector pins**, not the internal RP2040↔FPGA PCB traces.

| Design | RX pin | TX pin | Path |
|---|---|---|---|
| `uart_sum` (repo) | `xy[0:23]_in0` | `xy[0:10]_out0` | External header |
| `uart_led` (repo) | `xy[0:23]_in0` | — | External header |
| **our `uart_gcd`** | `xy[31:8]_in0` | `xy[31:22]_out0` | RP2040 GPIO0/GPIO1 |

Failing with `uart_sum` via MicroPython tells you nothing about the RP2040↔FPGA UART path —
those bytes never reach the FPGA's `rx` input.

---

## Debug Ladder

### Level 0 — Flash sanity (confirmed working)
- `blink_fpga.py` with `led_blink.bin` → LED blinks
- Confirms: flashing works, FPGA comes up, on-board LED (`xy[31:6]`) is reachable

### Level 1 — RP2040 TX → FPGA RX (one-way) ❌ FAILED
Re-synthesized `uart_led` with `rx` remapped to `xy[31:8]_in0` (GPIO15, PIN 6). Bitstream
on RP2040 confirmed identical to synthesized output. LED did not change at 115200 baud or
9600 baud.

**Next step**: attach logic analyzer to GPIO14 [PIN 5] (`dbg_rx_valid`) to see if the
uart_rx module is firing at all. `uart_led/ffpga/src/top.v` already has `dbg_rx_valid` +
`dbg_rx_valid_oe` ports — resynth and map to GPIO14_OUT/GPIO14_OE [PIN 5] in I/O Planner.

If `dbg_rx_valid` never pulses → FPGA is not receiving the bytes (pin or framing issue).
If it pulses but LED doesn't change → bug in the LED control logic.

### Level 2 — Confirm uart_gcd bitstream path
Verify the bitstream was actually generated and is being flashed from the right path:

```
fpga/shrike/uart_gcd/shrike_project/uart_gcd/ffpga/build/bitstream/FPGA_bitstream_MCU.bin
```

When calling `shrike.flash(...)` from MicroPython, either copy the file to the RP2040
filesystem first or confirm the path is correct.

### Level 3 — Full round-trip via SPI (use spi_gcd bitstream)
Requires soldered pin headers + jumper wires (MISO and SS_N need external connections).

**IMPORTANT**: The existing `spi_gcd.ffpga` has WRONG pin assignments — `xy[31:15]` and
`xy[31:29]` map to internal BRAM config pins, not external GPIOs. Must fix in GUI first:

| Signal | Correct I/O Planner assignment |
|---|---|
| `spi_sck` | GPIO15_IN [PIN 6] |
| `spi_mosi` | GPIO13_IN [PIN 4] |
| `spi_miso` | GPIO14_OUT [PIN 5] + GPIO14_OE [PIN 5] |
| `spi_ss_n` | GPIO12_IN [PIN 3] |
| `result_ready` | GPIO16_OUT [PIN 7] + GPIO16_OE [PIN 7] |

Flash `spi_gcd` and run the SPI MicroPython client. If SPI round-trips work but UART
doesn't, the fault is isolated to the UART RTL or clock/baud rate.

### Level 4 — Clock / baud rate validation
`CLKS_PER_BIT = 434` assumes exactly 50 MHz. The ForgeFPGA on-chip oscillator has a
tolerance that could shift the baud rate enough to fail on hardware while passing in
simulation.

Try these in `gcd_client.py`:
- Increase `TIMEOUT_MS` to 10000 to rule out timing issues
- Test with `gcd(1, 1)` first — minimal GCD computation, fastest possible response
- If you have a logic analyzer, probe the FPGA `uart_tx` line to see if any bits appear

---

## RTL Notes (for reference)

- `gcd_top.v` has a built-in 16-cycle power-on reset — no external reset pin needed
- `uart_tx.v` is self-contained; once `tx_start` fires, it completes independently
- `CLKS_PER_BIT = 434` = 50 MHz / 115200 ≈ 434.03 — correct for nominal clock
- The `gcd_client.py` does not toggle a reset pin (unlike `uart_sum.py`) — this is fine
  because `gcd_top.v` handles POR internally
