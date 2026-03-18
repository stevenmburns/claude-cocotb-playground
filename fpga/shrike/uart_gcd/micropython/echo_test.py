# echo_test.py — test UART echo on FPGA with external reset
#
# Wiring:
#   RP2040 GPIO2  → FPGA GPIO3 (PIN 16) = ext_rst (PCB trace)
#   RP2040 GPIO8  → FPGA GPIO0 (PIN 13) = uart_rx (jumper)
#   RP2040 GPIO9  ← FPGA GPIO1 (PIN 14) = uart_tx (jumper)
#   FPGA GPIO2 (PIN 15) = heartbeat debug (logic analyser)

from machine import UART, Pin
import time

# Hold reset, init UART, then release
rst = Pin(2, Pin.OUT, value=1)
uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))
time.sleep_ms(100)
rst(0)
time.sleep_ms(100)

print("UART echo test — sending bytes, expecting echo")
print("UART1 TX=GPIO8 RX=GPIO9, reset=GPIO2")

test_values = [0x55, 0xAA, 0x00, 0xFF, 0x42]
ok = 0

for val in test_values:
    uart.read()  # flush
    uart.write(bytes([val]))
    time.sleep_ms(50)
    if uart.any():
        got = uart.read(1)[0]
        match = "OK" if got == val else "FAIL"
        print(f"  sent 0x{val:02X}, got 0x{got:02X} — {match}")
        if got == val:
            ok += 1
    else:
        print(f"  sent 0x{val:02X}, no response — FAIL")

print(f"\n{ok}/{len(test_values)} passed")
