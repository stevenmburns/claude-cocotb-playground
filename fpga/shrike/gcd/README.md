# GCD on Vicharak Shrike FPGA

Implements the existing `gcd/gcd.v` (12-bit iterative Euclidean GCD) on the
Vicharak Shrike board, which uses a Renesas SLG47910V "Forge FPGA" paired with an
RP2040 USB-to-Serial bridge.

## Protocol

8N1 UART at 9600 baud (50 MHz on-chip oscillator → `CLKS_PER_BIT = 5208`):

1. Host sends byte `a` (0–255)
2. Host sends byte `b` (0–255)
3. FPGA computes `gcd(a, b)` and sends back 1 byte (result)

## Files

| File | Description |
|------|-------------|
| `uart_rx.v` | Standard 8N1 UART receiver |
| `uart_tx.v` | Standard 8N1 UART transmitter |
| `gcd_top.v` | Top-level FSM; instantiates both UARTs and `gcd.v` |
| `../../../gcd/gcd.v` | Existing 12-bit GCD core (no changes) |

## Pin Assignments (SLG47910V)

> **TODO:** Open the `uart_sum` example in Go Configure to read the exact pin
> numbers for UART RX, UART TX, and the on-chip oscillator, then fill in this
> table.

| Signal | Direction | FPGA Pin |
|--------|-----------|----------|
| `clk` | In | On-chip 50 MHz OSC |
| `uart_rx` | In | (see uart_sum example) |
| `uart_tx` | Out | (see uart_sum example) |

## Toolchain: Go Configure

1. Install Go Configure (from Renesas / Vicharak):
   ```sh
   sudo dpkg -i go-configure-sw-hub-v6.52.001-ubuntu-22.04-amd64.deb
   ```

2. Open Go Configure → New Project → device **SLG47910V**

3. Add all four source files (Go Configure needs flat file lists):
   - `uart_rx.v`
   - `uart_tx.v`
   - `gcd_top.v`
   - `gcd.v` (copy or symlink from `../../../gcd/gcd.v`)

4. Set top-level module: **`gcd_top`**

5. Assign pins (matching the table above)

6. Synthesize → Generate bitstream → Program via USB

## Testing

```python
import serial, time

s = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(0.1)

def gcd_fpga(a, b):
    s.write(bytes([a, b]))
    result = s.read(1)
    return result[0] if result else None

# Should return 4
print('gcd(12, 8) =', gcd_fpga(12, 8))

# Should return 1
print('gcd(17, 13) =', gcd_fpga(17, 13))

# Should return 255
print('gcd(255, 0) =', gcd_fpga(255, 0))

s.close()
```

Or interactively with `screen /dev/ttyACM0 9600` (send raw bytes with Ctrl sequences).

## Notes

- Inputs are 8-bit (0–255), zero-extended to 12 bits internally. The GCD core
  supports full 12-bit arithmetic but 8-bit inputs are sufficient for UART demos.
- The `gcd.v` module uses a modulo operation (`%`). Verify that Go Configure's
  synthesis supports this operator; if not, replace with a subtraction-based
  Euclidean loop.
- Power-on reset is generated internally (16-cycle counter); no external reset pin needed.
