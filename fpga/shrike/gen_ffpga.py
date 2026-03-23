#!/usr/bin/env python3
"""
gen_ffpga.py — Generate a ForgeFPGA (.ffpga) project file for Vicharak Shrike (SLG47910V).

The generated file is ready to open in the Renesas Go Configure Software Hub GUI.
Press Synthesize, then Generate Bitstream. The bitstream lands at:
    <project_dir>/ffpga/build/bitstream/FPGA_bitstream_MCU.bin

Flash with shrike-ctl:
    python shrike-ctl.py /dev/ttyACM0 <project_dir>/ffpga/build/bitstream/FPGA_bitstream_MCU.bin

Known IOB pin coordinates for Shrike (verified from pins.csv export in Go Configure):

    Symbolic name     IOB coordinate ID                   Board connection
    ─────────────────────────────────────────────────────────────────────
    CLK               CLK_t[0:0]_W_in0                   50 MHz on-chip OSC
    GPIO0_OUT0        IOB_t[0:0]_xy[0:6]_out0            PIN 13 output (FPGA_IO0)
    GPIO0_OUT1        IOB_t[0:0]_xy[0:6]_out1            PIN 13 output enable
    GPIO0_IN          IOB_t[0:0]_xy[0:6]_in0             PIN 13 input
    GPIO1_OUT0        IOB_t[0:0]_xy[0:7]_out0            PIN 14 output (FPGA_IO1)
    GPIO1_OUT1        IOB_t[0:0]_xy[0:7]_out1            PIN 14 output enable
    GPIO1_IN          IOB_t[0:0]_xy[0:7]_in0             PIN 14 input
    GPIO2_OUT0        IOB_t[0:0]_xy[0:8]_out0            PIN 15 output
    GPIO2_OUT1        IOB_t[0:0]_xy[0:8]_out1            PIN 15 output enable
    GPIO2_IN          IOB_t[0:0]_xy[0:8]_in0             PIN 15 input
    GPIO3_OUT0        IOB_t[0:0]_xy[0:9]_out0            PIN 16 output
    GPIO3_OUT1        IOB_t[0:0]_xy[0:9]_out1            PIN 16 output enable
    GPIO3_IN          IOB_t[0:0]_xy[0:9]_in0             PIN 16 input
    GPIO4_OUT0        IOB_t[0:0]_xy[0:10]_out0           PIN 17 output
    GPIO4_OUT1        IOB_t[0:0]_xy[0:10]_out1           PIN 17 output enable
    GPIO4_IN          IOB_t[0:0]_xy[0:10]_in0            PIN 17 input
    GPIO5_OUT0        IOB_t[0:0]_xy[0:22]_out0           PIN 18 output
    GPIO5_OUT1        IOB_t[0:0]_xy[0:22]_out1           PIN 18 output enable
    GPIO5_IN          IOB_t[0:0]_xy[0:22]_in0            PIN 18 input
    GPIO6_OUT0        IOB_t[0:0]_xy[0:23]_out0           PIN 19 output
    GPIO6_OUT1        IOB_t[0:0]_xy[0:23]_out1           PIN 19 output enable
    GPIO6_IN          IOB_t[0:0]_xy[0:23]_in0            PIN 19 input
    GPIO7_OUT0        IOB_t[0:0]_xy[0:24]_out0           PIN 20 output
    GPIO7_OUT1        IOB_t[0:0]_xy[0:24]_out1           PIN 20 output enable
    GPIO7_IN          IOB_t[0:0]_xy[0:24]_in0            PIN 20 input
    GPIO8_OUT0        IOB_t[0:0]_xy[31:27]_out0          PIN 23 output
    GPIO8_OUT1        IOB_t[0:0]_xy[31:27]_out1          PIN 23 output enable
    GPIO8_IN          IOB_t[0:0]_xy[31:27]_in0           PIN 23 input
    GPIO9_OUT0        IOB_t[0:0]_xy[31:26]_out0          PIN 24 output
    GPIO9_OUT1        IOB_t[0:0]_xy[31:26]_out1          PIN 24 output enable
    GPIO9_IN          IOB_t[0:0]_xy[31:26]_in0           PIN 24 input
    GPIO10_OUT0       IOB_t[0:0]_xy[31:25]_out0          PIN 1 output
    GPIO10_OUT1       IOB_t[0:0]_xy[31:25]_out1          PIN 1 output enable
    GPIO10_IN         IOB_t[0:0]_xy[31:25]_in0           PIN 1 input
    GPIO11_OUT0       IOB_t[0:0]_xy[31:24]_out0          PIN 2 output
    GPIO11_OUT1       IOB_t[0:0]_xy[31:24]_out1          PIN 2 output enable
    GPIO11_IN         IOB_t[0:0]_xy[31:24]_in0           PIN 2 input
    GPIO12_OUT0       IOB_t[0:0]_xy[31:23]_out0          PIN 3 output
    GPIO12_OUT1       IOB_t[0:0]_xy[31:23]_out1          PIN 3 output enable
    GPIO12_IN         IOB_t[0:0]_xy[31:23]_in0           PIN 3 input — SPI SS_N
    GPIO13_OUT0       IOB_t[0:0]_xy[31:22]_out0          PIN 4 → RP2040 GPIO1 (UART RX / I2C SDA out)
    GPIO13_OUT1       IOB_t[0:0]_xy[31:22]_out1          PIN 4 → RP2040 GPIO1 (OE)
    GPIO13_IN         IOB_t[0:0]_xy[31:22]_in0           PIN 4 ← RP2040 GPIO1 (I2C SDA in / SPI MOSI)
    GPIO14_OUT0       IOB_t[0:0]_xy[31:9]_out0           PIN 5 output — SPI MISO / I2C result_ready
    GPIO14_OUT1       IOB_t[0:0]_xy[31:9]_out1           PIN 5 output enable
    GPIO14_IN         IOB_t[0:0]_xy[31:9]_in0            PIN 5 input
    GPIO15_OUT0       IOB_t[0:0]_xy[31:8]_out0           PIN 6 → RP2040 GPIO0 (UART TX / SPI SCK / I2C SCL)
    GPIO15_OUT1       IOB_t[0:0]_xy[31:8]_out1           PIN 6 output enable
    GPIO15_IN         IOB_t[0:0]_xy[31:8]_in0            PIN 6 ← RP2040 GPIO0
    GPIO16_OUT0       IOB_t[0:0]_xy[31:6]_out0           PIN 7 output
    GPIO16_OUT1       IOB_t[0:0]_xy[31:6]_out1           PIN 7 output enable
    GPIO16_IN         IOB_t[0:0]_xy[31:6]_in0            PIN 7 input
    GPIO17_OUT0       IOB_t[0:0]_xy[31:5]_out0           PIN 8 output
    GPIO17_OUT1       IOB_t[0:0]_xy[31:5]_out1           PIN 8 output enable
    GPIO17_IN         IOB_t[0:0]_xy[31:5]_in0            PIN 8 input
    GPIO18_OUT0       IOB_t[0:0]_xy[31:4]_out0           PIN 9 output
    GPIO18_OUT1       IOB_t[0:0]_xy[31:4]_out1           PIN 9 output enable
    GPIO18_IN         IOB_t[0:0]_xy[31:4]_in0            PIN 9 input
    OSC_EN            IOB_t[0:0]_xy[0:25]_out0           Oscillator enable (used for clk_en)

Usage:
    python gen_ffpga.py <project_name> \\
        --src path/to/top.v --src path/to/other.v \\
        --pin clk:CLK --pin uart_rx:GPIO15_IN \\
        --pin uart_tx:GPIO13_OUT0 --pin uart_tx_oe:GPIO13_OUT1 \\
        --pin clk_en:LEFT_P25_OUT0 \\
        --out fpga/shrike/shrike_project

    # Pin values can be symbolic names (above) or raw IOB IDs:
        --pin clk_en:IOB_t[0:0]_xy[0:25]_out0

    # Re-generate the uart_gcd project:
    python fpga/shrike/gen_ffpga.py uart_gcd_gen \\
        --src fpga/shrike/uart_gcd/gcd_top.v \\
        --src fpga/shrike/uart_gcd/uart_rx.v \\
        --src fpga/shrike/uart_gcd/uart_tx.v \\
        --src gcd/gcd.v \\
        --pin clk:CLK \\
        --pin uart_rx:GPIO15_IN \\
        --pin uart_tx:GPIO13_OUT0 \\
        --pin uart_tx_oe:GPIO13_OUT1 \\
        --pin clk_en:LEFT_P25_OUT0 \\
        --out fpga/shrike/shrike_project

    # Generate the i2c_gcd project (SCL=PIN6/GPIO15, SDA=PIN4/GPIO13, result_ready=PIN5/GPIO14):
    python fpga/shrike/gen_ffpga.py i2c_gcd \\
        --src fpga/shrike/i2c_gcd/i2c_gcd_top.v \\
        --src fpga/shrike/i2c_gcd/i2c_target.v \\
        --src gcd/gcd.v \\
        --pin clk:CLK \\
        --pin clk_en:LEFT_P25_OUT0 \\
        --pin i2c_scl:GPIO15_IN \\
        --pin i2c_sda_in:GPIO13_IN \\
        --pin i2c_sda_out:GPIO13_OUT0 \\
        --pin i2c_sda_oe:GPIO13_OUT1 \\
        --pin result_ready:GPIO14_OUT0 \\
        --out fpga/shrike/i2c_gcd/shrike_project

    # Generate the spi_gcd project (SCK=PIN6, MOSI=PIN4, MISO=PIN5, SS_N=PIN3; jumpers needed for PIN3/5):
    python fpga/shrike/gen_ffpga.py spi_gcd \\
        --src fpga/shrike/spi_gcd/spi_gcd_top.v \\
        --src fpga/shrike/spi_gcd/spi_target.v \\
        --src gcd/gcd.v \\
        --pin clk:CLK \\
        --pin clk_en:LEFT_P25_OUT0 \\
        --pin spi_sck:GPIO15_IN \\
        --pin spi_mosi:GPIO13_IN \\
        --pin spi_miso:GPIO14_OUT0 \\
        --pin spi_miso_oe:GPIO14_OUT1 \\
        --pin spi_ss_n:GPIO12_IN \\
        --pin result_ready:GPIO16_OUT0 \\
        --out fpga/shrike/spi_gcd/shrike_project
"""

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent

# Template: blank .ffpga project (no modules, no pins) used as the base for generation
TEMPLATE_PATH = HERE / "uart_gcd" / "shrike_project" / "template" / "blank.ffpga"

# Symbolic pin name → raw IOB coordinate ID
# Verified from pins.csv export in Go Configure Software Hub
KNOWN_PINS: dict[str, str] = {
    "CLK": "CLK_t[0:0]_W_in0",
    # GPIO0 — PIN 13 (FPGA_IO0)
    "GPIO0_OUT0": "IOB_t[0:0]_xy[0:6]_out0",
    "GPIO0_OUT1": "IOB_t[0:0]_xy[0:6]_out1",
    "GPIO0_IN": "IOB_t[0:0]_xy[0:6]_in0",
    # GPIO1 — PIN 14 (FPGA_IO1)
    "GPIO1_OUT0": "IOB_t[0:0]_xy[0:7]_out0",
    "GPIO1_OUT1": "IOB_t[0:0]_xy[0:7]_out1",
    "GPIO1_IN": "IOB_t[0:0]_xy[0:7]_in0",
    # GPIO2 — PIN 15
    "GPIO2_OUT0": "IOB_t[0:0]_xy[0:8]_out0",
    "GPIO2_OUT1": "IOB_t[0:0]_xy[0:8]_out1",
    "GPIO2_IN": "IOB_t[0:0]_xy[0:8]_in0",
    # GPIO3 — PIN 16
    "GPIO3_OUT0": "IOB_t[0:0]_xy[0:9]_out0",
    "GPIO3_OUT1": "IOB_t[0:0]_xy[0:9]_out1",
    "GPIO3_IN": "IOB_t[0:0]_xy[0:9]_in0",
    # GPIO4 — PIN 17
    "GPIO4_OUT0": "IOB_t[0:0]_xy[0:10]_out0",
    "GPIO4_OUT1": "IOB_t[0:0]_xy[0:10]_out1",
    "GPIO4_IN": "IOB_t[0:0]_xy[0:10]_in0",
    # GPIO5 — PIN 18
    "GPIO5_OUT0": "IOB_t[0:0]_xy[0:22]_out0",
    "GPIO5_OUT1": "IOB_t[0:0]_xy[0:22]_out1",
    "GPIO5_IN": "IOB_t[0:0]_xy[0:22]_in0",
    # GPIO6 — PIN 19
    "GPIO6_OUT0": "IOB_t[0:0]_xy[0:23]_out0",
    "GPIO6_OUT1": "IOB_t[0:0]_xy[0:23]_out1",
    "GPIO6_IN": "IOB_t[0:0]_xy[0:23]_in0",
    # GPIO7 — PIN 20
    "GPIO7_OUT0": "IOB_t[0:0]_xy[0:24]_out0",
    "GPIO7_OUT1": "IOB_t[0:0]_xy[0:24]_out1",
    "GPIO7_IN": "IOB_t[0:0]_xy[0:24]_in0",
    # GPIO8 — PIN 23
    "GPIO8_OUT0": "IOB_t[0:0]_xy[31:27]_out0",
    "GPIO8_OUT1": "IOB_t[0:0]_xy[31:27]_out1",
    "GPIO8_IN": "IOB_t[0:0]_xy[31:27]_in0",
    # GPIO9 — PIN 24
    "GPIO9_OUT0": "IOB_t[0:0]_xy[31:26]_out0",
    "GPIO9_OUT1": "IOB_t[0:0]_xy[31:26]_out1",
    "GPIO9_IN": "IOB_t[0:0]_xy[31:26]_in0",
    # GPIO10 — PIN 1
    "GPIO10_OUT0": "IOB_t[0:0]_xy[31:25]_out0",
    "GPIO10_OUT1": "IOB_t[0:0]_xy[31:25]_out1",
    "GPIO10_IN": "IOB_t[0:0]_xy[31:25]_in0",
    # GPIO11 — PIN 2
    "GPIO11_OUT0": "IOB_t[0:0]_xy[31:24]_out0",
    "GPIO11_OUT1": "IOB_t[0:0]_xy[31:24]_out1",
    "GPIO11_IN": "IOB_t[0:0]_xy[31:24]_in0",
    # GPIO12 — PIN 3
    "GPIO12_OUT0": "IOB_t[0:0]_xy[31:23]_out0",
    "GPIO12_OUT1": "IOB_t[0:0]_xy[31:23]_out1",
    "GPIO12_IN": "IOB_t[0:0]_xy[31:23]_in0",
    # GPIO13 — PIN 4 (RP2040 GPIO1)
    "GPIO13_OUT0": "IOB_t[0:0]_xy[31:22]_out0",
    "GPIO13_OUT1": "IOB_t[0:0]_xy[31:22]_out1",
    "GPIO13_IN": "IOB_t[0:0]_xy[31:22]_in0",
    # GPIO14 — PIN 5
    "GPIO14_OUT0": "IOB_t[0:0]_xy[31:9]_out0",
    "GPIO14_OUT1": "IOB_t[0:0]_xy[31:9]_out1",
    "GPIO14_IN": "IOB_t[0:0]_xy[31:9]_in0",
    # GPIO15 — PIN 6 (RP2040 GPIO0)
    "GPIO15_OUT0": "IOB_t[0:0]_xy[31:8]_out0",
    "GPIO15_OUT1": "IOB_t[0:0]_xy[31:8]_out1",
    "GPIO15_IN": "IOB_t[0:0]_xy[31:8]_in0",
    # GPIO16 — PIN 7
    "GPIO16_OUT0": "IOB_t[0:0]_xy[31:6]_out0",
    "GPIO16_OUT1": "IOB_t[0:0]_xy[31:6]_out1",
    "GPIO16_IN": "IOB_t[0:0]_xy[31:6]_in0",
    # GPIO17 — PIN 8
    "GPIO17_OUT0": "IOB_t[0:0]_xy[31:5]_out0",
    "GPIO17_OUT1": "IOB_t[0:0]_xy[31:5]_out1",
    "GPIO17_IN": "IOB_t[0:0]_xy[31:5]_in0",
    # GPIO18 — PIN 9
    "GPIO18_OUT0": "IOB_t[0:0]_xy[31:4]_out0",
    "GPIO18_OUT1": "IOB_t[0:0]_xy[31:4]_out1",
    "GPIO18_IN": "IOB_t[0:0]_xy[31:4]_in0",
    # Oscillator enable
    "OSC_EN": "IOB_t[0:0]_xy[0:25]_out0",
    # Legacy aliases for backward compatibility with existing gen_ffpga invocations
    "LEFT_P25_OUT0": "IOB_t[0:0]_xy[0:25]_out0",
}


def resolve_pin(name: str) -> str:
    """Return the raw IOB ID for a symbolic name or pass through a raw ID."""
    return KNOWN_PINS.get(name, name)


def generate_ffpga(
    project_name: str,
    src_files: list[str],
    pin_assignments: dict[str, str],  # port_name → symbolic or raw IOB ID
    output_dir: str | Path,
    template_path: str | Path = TEMPLATE_PATH,
) -> Path:
    """
    Generate a .ffpga project file and copy Verilog sources into place.

    Returns the path to the generated .ffpga file.
    """
    template = Path(template_path).read_text(encoding="utf-8")

    # ── reorder: move file containing (* top *) to the end ────────────────
    # Yosys reads files in order; submodules must be defined before the top.
    ordered = list(src_files)
    for i, f in enumerate(ordered):
        content = Path(f).read_text(encoding="utf-8")
        if re.search(r'\(\*\s*top\s*\*\)', content):
            ordered.append(ordered.pop(i))
            break

    # ── modules XML ────────────────────────────────────────────────────────
    modules_xml = "\n".join(
        f'                <module filename="{Path(f).name}"/>' for f in ordered
    )
    template = re.sub(
        r"<scr>.*?</scr>",
        f"<scr>\n{modules_xml}\n            </scr>",
        template,
        flags=re.DOTALL,
    )

    # ── io-spec-tool records XML ────────────────────────────────────────────
    io_records_xml = "\n".join(
        f'                <record id="{resolve_pin(iob_id)}">\n'
        f"                    <port-name>{port}</port-name>\n"
        f"                </record>"
        for port, iob_id in pin_assignments.items()
    )
    template = re.sub(
        r"<io-spec-tool>.*?</io-spec-tool>",
        (
            "<io-spec-tool>\n"
            '            <records filter="34">\n'
            f"{io_records_xml}\n"
            "            </records>\n"
            "        </io-spec-tool>"
        ),
        template,
        flags=re.DOTALL,
    )

    # ── pipeline state: reset to 0 (not yet synthesized) ───────────────────
    template = re.sub(
        r"<pipelineState>\d+</pipelineState>",
        "<pipelineState>0</pipelineState>",
        template,
    )

    # ── timestamp ──────────────────────────────────────────────────────────
    now = datetime.now().strftime("%-d %b %Y %H:%M:%S")
    template = re.sub(r'lastChange="[^"]*"', f'lastChange="{now}"', template)

    # ── checksum: clear so the GUI recomputes it ───────────────────────────
    template = re.sub(
        r'projectChecksumState="\d+"', 'projectChecksumState="0"', template
    )
    template = re.sub(
        r'projectChecksum="[^"]*"', 'projectChecksum="00000000"', template
    )

    # ── create directory layout ────────────────────────────────────────────
    project_dir = Path(output_dir) / project_name
    src_dir = project_dir / "ffpga" / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    for f in ordered:
        link = src_dir / Path(f).name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(os.path.relpath(Path(f).resolve(), src_dir))

    ffpga_path = project_dir / f"{project_name}.ffpga"
    ffpga_path.write_text(template, encoding="utf-8")

    print(f"Generated : {ffpga_path}")
    print(f"Sources   : {src_dir}")
    print(
        f"Bitstream : {project_dir}/ffpga/build/bitstream/FPGA_bitstream_MCU.bin  (after GUI synthesis)"
    )
    return ffpga_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a ForgeFPGA .ffpga project file for Vicharak Shrike."
    )
    p.add_argument(
        "project_name",
        nargs="?",
        help="Project name (also the output subdirectory name)",
    )
    p.add_argument(
        "--src",
        metavar="FILE",
        action="append",
        default=[],
        help="Verilog source file (repeat for each file; order matters for top-module detection)",
    )
    p.add_argument(
        "--pin",
        metavar="PORT:PIN",
        action="append",
        default=[],
        help="Pin assignment: port_name:symbolic_pin_name  (e.g. uart_rx:GPIO15_IN)",
    )
    p.add_argument(
        "--out",
        metavar="DIR",
        default=".",
        help="Parent directory for the generated project (default: current directory)",
    )
    p.add_argument(
        "--template",
        metavar="FILE",
        default=str(TEMPLATE_PATH),
        help=f"Blank .ffpga template to use (default: {TEMPLATE_PATH})",
    )
    p.add_argument(
        "--list-pins",
        action="store_true",
        help="Print known symbolic pin names and exit",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_pins:
        print("Known symbolic pin names for Shrike (SLG47910V):\n")
        for sym, iob in KNOWN_PINS.items():
            print(f"  {sym:<18} {iob}")
        return

    if not args.project_name:
        raise SystemExit("error: project_name is required")
    if not args.src:
        raise SystemExit("error: at least one --src is required")
    if not args.pin:
        raise SystemExit("error: at least one --pin is required")

    pin_assignments: dict[str, str] = {}
    for spec in args.pin:
        if ":" not in spec:
            raise SystemExit(f"Bad --pin value {spec!r}: expected PORT:PIN")
        port, pin = spec.split(":", 1)
        pin_assignments[port.strip()] = pin.strip()

    generate_ffpga(
        project_name=args.project_name,
        src_files=args.src,
        pin_assignments=pin_assignments,
        output_dir=args.out,
        template_path=args.template,
    )


if __name__ == "__main__":
    main()
