# uart_test.py — simple UART TX/RX test on external pins
#
# TX test: sends 0xAA every second on GPIO8 (UART1 TX)
# RX test: prints any bytes received on GPIO9 (UART1 RX)
#
# Wire GPIO8 → FPGA_IO0, GPIO9 → FPGA_IO1
# Watch both on the logic analyser.

from machine import UART, Pin
import time

uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))

print("UART1 TX=GPIO8 RX=GPIO9 @ 115200")
print("Sending 0xAA every second. Ctrl-C to stop.\n")

try:
    while True:
        uart.write(bytes([0xAA]))
        print("sent 0xAA")
        if uart.any():
            data = uart.read()
            print(f"  received: {[hex(b) for b in data]}")
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopped.")
