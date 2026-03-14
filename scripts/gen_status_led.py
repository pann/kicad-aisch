#!/usr/bin/env python3
"""Generator for Block 7: Status LED schematic (status_led.kicad_sch).

Circuit: LED_CTRL (GPIO) ---> R1 (1kΩ) ---> D1 LED (green) ---> GND
Power: +3V3 (not directly on this sheet, comes via LED_CTRL from MCU)

Components:
  D1  - Green LED, 0805 (LCSC C2297)
  R1  - 1kΩ 0603 current-limiting resistor (LCSC C21190)

Interfaces:
  LED_CTRL - hierarchical label, input from ESP32 GPIO (block 2)
  +3V3     - not needed on this sheet (power comes from MCU GPIO)
  GND      - power symbol for LED cathode return

Layout (left to right, signal flow):
  LED_CTRL hlabel -> R1 -> wire -> D1 (LED) -> GND

Coordinate plan:
  R1 at (80.01, 80.01), angle=90 (horizontal):
    pin1 at (+3.81, 0) = (83.82, 80.01) [right] -> wire to D1 anode
    pin2 at (-3.81, 0) = (76.20, 80.01) [left]  -> LED_CTRL hlabel

  D1 at (99.06, 80.01), angle=180 (current flows left-to-right: A left, K right):
    A (anode)   at (-3.81, 0) = (95.25, 80.01) [left]  -> wire from R1
    K (cathode) at (+3.81, 0) = (102.87, 80.01) [right] -> GND

  Wire: R1 pin1 (83.82, 80.01) -> D1 A (95.25, 80.01)
  GND: at D1 K (102.87, 80.01), stub goes right then down

Usage:
  python3 scripts/gen_status_led.py
"""

import os
import sys

# Add scripts directory to path for import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "0eb1c17e-9b3c-4b80-9a2a-c332b3f136dd"
SHEET_UUID = "7182ed34-5401-421d-ae3f-7496b7554d9f"

# KiCad standard library paths
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"

# Output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl")
OUTFILE = os.path.join(PROJECT_DIR, "status_led.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="Status LED",
        date="2026-03-05",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 7: Status indication LED",
        page="9",
        pwr_start=900,
    )

    # ── Library symbols ──
    sb.add_lib("Device", DEVICE_LIB, ["R", "LED"])
    sb.add_lib("power", POWER_LIB, ["GND"])

    # ── Component placement ──
    # R1: 1kΩ current-limiting resistor, horizontal (angle=90)
    # Centre at (80.01, 80.01)
    #   pin1 at (83.82, 80.01) [right] -> wire to LED anode
    #   pin2 at (76.20, 80.01) [left]  -> LED_CTRL input
    sb.place_sym(
        "Device:R", 80.01, 80.01, 90,
        "R900", "1k",
        "Resistor_SMD:R_0603_1608Metric",
        ["1", "2"],
    )

    # D1: Green LED, horizontal (angle=180, current flows left-to-right)
    # Centre at (99.06, 80.01)
    #   A (anode)   at (95.25, 80.01) [left]  -> wire from R1
    #   K (cathode) at (102.87, 80.01) [right] -> GND
    sb.place_sym(
        "Device:LED", 99.06, 80.01, 180,
        "D900", "Green",
        "LED_SMD:LED_0805_2012Metric",
        ["K", "A"],
    )

    # ── Wires ──
    # R1 pin1 (83.82) to D1 anode (95.25)
    sb.add_wire(83.82, 80.01, 95.25, 80.01)

    # ── Power symbols ──
    # GND at D1 cathode (102.87, 80.01)
    sb.place_power("GND", 102.87, 80.01)

    # ── Hierarchical labels ──
    # LED_CTRL input at R1 pin2 (76.20, 80.01), angle=180 (extends left)
    sb.add_hlabel("LED_CTRL", 76.20, 80.01, 180, "input")

    # ── Write output ──
    sb.write(OUTFILE)
    print(f"Block 7 (Status LED) schematic generated.")

    # Verify with kicad-cli if available
    import shutil
    kicad_cli = shutil.which("kicad-cli")
    if kicad_cli:
        import subprocess
        ret = subprocess.run(
            [kicad_cli, "sch", "export", "svg", "--output", "/tmp/", OUTFILE],
            capture_output=True, text=True,
        )
        if ret.returncode == 0:
            print("  SVG export: OK")
        else:
            print(f"  SVG export: FAILED\n{ret.stderr}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
