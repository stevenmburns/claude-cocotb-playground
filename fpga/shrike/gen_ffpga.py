#!/usr/bin/env python3
"""
gen_ffpga.py — Generate a ForgeFPGA (.ffpga) project file for Vicharak Shrike (SLG47910V).

The generated file is ready to open in the Renesas Go Configure Software Hub GUI.
Press Synthesize, then Generate Bitstream. The bitstream lands at:
    <project_dir>/ffpga/build/bitstream/FPGA_bitstream_MCU.bin

Flash with shrike-ctl:
    python shrike-ctl.py /dev/ttyACM0 <project_dir>/ffpga/build/bitstream/FPGA_bitstream_MCU.bin

Known IOB pin coordinates for Shrike (verified from uart_gcd, spi_gcd, i2c_gcd synthesis):

    Symbolic name     IOB coordinate ID                   Board connection
    ─────────────────────────────────────────────────────────────────────
    CLK               CLK_t[0:0]_W_in0                   50 MHz on-chip OSC
    GPIO15_IN         IOB_t[0:0]_xy[31:8]_in0            PIN 6 ← RP2040 GPIO0 (UART TX / SPI SCK / I2C SCL)
    GPIO15_OUT0       IOB_t[0:0]_xy[31:8]_out0           PIN 6 → RP2040 GPIO0
    GPIO16_OUT0       IOB_t[0:0]_xy[31:1]_out0           PIN 7 output
    GPIO14_OUT0       IOB_t[0:0]_xy[31:15]_out0          PIN 5 output — SPI MISO / I2C result_ready
    GPIO14_OUT1       IOB_t[0:0]_xy[31:15]_out1          PIN 5 output enable
    GPIO14_IN         IOB_t[0:0]_xy[31:15]_in0           PIN 5 input
    GPIO13_OUT0       IOB_t[0:0]_xy[31:22]_out0          PIN 4 → RP2040 GPIO1 (UART RX / I2C SDA out)
    GPIO13_OUT1       IOB_t[0:0]_xy[31:22]_out1          PIN 4 → RP2040 GPIO1 (OE)
    GPIO13_IN         IOB_t[0:0]_xy[31:22]_in0           PIN 4 ← RP2040 GPIO1 (I2C SDA in / SPI MOSI)
    GPIO12_IN         IOB_t[0:0]_xy[31:29]_in0           PIN 3 input — SPI SS_N
    LEFT_P25_OUT0     IOB_t[0:0]_xy[0:25]_out0           Left-side pos 25 (used for clk_en)

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
# Verified from uart_gcd project (uart_gcd.ffpga-pin-mapping)
KNOWN_PINS: dict[str, str] = {
    "CLK": "CLK_t[0:0]_W_in0",
    "GPIO15_IN": "IOB_t[0:0]_xy[31:8]_in0",  # PIN 6 ← RP2040 GPIO0 (UART TX)
    "GPIO15_OUT0": "IOB_t[0:0]_xy[31:8]_out0",  # PIN 6 → RP2040 GPIO0
    "GPIO13_OUT0": "IOB_t[0:0]_xy[31:22]_out0",  # PIN 4 → RP2040 GPIO1 (UART RX)
    "GPIO13_OUT1": "IOB_t[0:0]_xy[31:22]_out1",  # PIN 4 → RP2040 GPIO1 (output enable)
    "GPIO13_IN": "IOB_t[0:0]_xy[31:22]_in0",  # PIN 4 ← RP2040 GPIO1 (inferred from xy[31:22] base)
    "GPIO14_OUT0": "IOB_t[0:0]_xy[31:15]_out0",  # PIN 5 output (inferred: y = 22 - 7*(N-13))
    "GPIO14_OUT1": "IOB_t[0:0]_xy[31:15]_out1",  # PIN 5 output enable (inferred)
    "GPIO14_IN": "IOB_t[0:0]_xy[31:15]_in0",  # PIN 5 input (inferred)
    "GPIO12_IN": "IOB_t[0:0]_xy[31:29]_in0",  # PIN 3 input (inferred: y = 22 + 7*(13-N))
    "GPIO16_OUT0": "IOB_t[0:0]_xy[31:1]_out0",  # PIN 7 output (inferred)
    "LEFT_P25_OUT0": "IOB_t[0:0]_xy[0:25]_out0",  # left-side pos 25 (clk_en in uart_gcd)
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

    # ── modules XML ────────────────────────────────────────────────────────
    modules_xml = "\n".join(
        f'                <module filename="{Path(f).name}"/>' for f in src_files
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

    for f in src_files:
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
