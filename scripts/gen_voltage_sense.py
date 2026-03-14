#!/usr/bin/env python3
"""Generator for Block 6: Voltage Sensing schematic (voltage_sense.kicad_sch).

Circuit: Optocoupler-based AC voltage measurement with analog output to ESP32 ADC.

AC side (left):
  AC_L → R12(10K/1206) → R13(10K/1206) → U6 AN (LED anode)
  U6 CAT (LED cathode) → AC_N
  Two 10K resistors in series (20K total) limit LED current to ~1.2mA peak at 24Vrms.

DC side (right):
  +3V3 → R14(10K/0603) → node_A → U6 COL (collector)
  U6 EM (emitter) → GND
  node_A → C13(1uF/0603) → GND     (low-pass filter, ~16Hz)
  node_A → R15(1K/0603) → node_B   (ADC series protection)
  node_B → D3 COM (BAT54S)          (ESD clamp)
  D3 A → GND, D3 K → +3V3          (clamps signal to 0..3.3V)
  node_B → V_SENSE hlabel           (output to ESP32 ADC)

Components:
  U6   EL357N(C)(TA)-G   SOP-4    C29981  (project lib)
  D3   BAT54S             SOT-23   C66740  (Diode:BAT54S)
  R12  10K 0.5W           1206             (Device:R)
  R13  10K 0.5W           1206             (Device:R)
  R14  10K                0603     C25804  (Device:R)
  R15  1K                 0603     C21190  (Device:R)
  C13  1uF/10V            0603     C15849  (Device:C)

EL357N pin positions (angle=0, schematic Y-down):
  Pin 1 (AN):  (cx-11.43, cy-2.54)  upper-left   LED anode
  Pin 2 (CAT): (cx-11.43, cy+2.54)  lower-left   LED cathode
  Pin 3 (EM):  (cx+11.43, cy+2.54)  lower-right  emitter
  Pin 4 (COL): (cx+11.43, cy-2.54)  upper-right  collector

BAT54S pin positions (angle=0, schematic Y-down):
  Pin 1 (A):   (cx-7.62, cy)        left    anode → GND
  Pin 2 (K):   (cx+7.62, cy)        right   cathode → +3V3
  Pin 3 (COM): (cx, cy+5.08)        bottom  common → signal

Usage:
  python3 scripts/gen_voltage_sense.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "3a9adae2-2f5f-4e75-8e72-e9b71c8f8c82"
SHEET_UUID = "4d810b3d-3262-4637-84a2-8bf71e40cdc5"

# Library paths
PROJECT_LIB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "marklin-wifi-ctrl", "marklin-wifi-ctrl.kicad_sym",
)
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
DIODE_LIB = "/usr/share/kicad/symbols/Diode.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTFILE = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl", "voltage_sense.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="Voltage Sensing",
        date="2026-03-05",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 6: AC voltage measurement via EL357N",
        page="6",
        pwr_start=600,
    )

    # ── Library symbols ──
    sb.add_lib("marklin-wifi-ctrl", PROJECT_LIB, ["EL357N(C)(TA)-G"])
    sb.add_lib("Diode", DIODE_LIB, ["BAT54S"])
    sb.add_lib("Device", DEVICE_LIB, ["R", "C"])
    sb.add_lib("power", POWER_LIB, ["GND", "+3V3"])

    # ═══════════════════════════════════════════════════════════════════
    # Component placement — coordinates in mm
    # ═══════════════════════════════════════════════════════════════════

    # ── U6: EL357N optocoupler at (95, 80), angle=0 ──
    # Pin 1 (AN):  (83.57, 77.46) upper-left   — LED anode
    # Pin 2 (CAT): (83.57, 82.54) lower-left   — LED cathode
    # Pin 3 (EM):  (106.43, 82.54) lower-right — emitter
    # Pin 4 (COL): (106.43, 77.46) upper-right — collector
    u6_cx, u6_cy = 95, 80
    sb.place_sym(
        "marklin-wifi-ctrl:EL357N(C)(TA)-G", u6_cx, u6_cy, 0,
        "U600", "EL357N", "marklin-wifi-ctrl:OPTO-SMD-4_L4.4-W4.1-P2.54-LS7.0-TL",
        ["1", "2", "3", "4"],
    )

    # U6 pin coordinates
    u6_an = (83.57, 77.46)    # LED anode (upper-left)
    u6_cat = (83.57, 82.54)   # LED cathode (lower-left)
    u6_col = (106.43, 77.46)  # collector (upper-right)
    u6_em = (106.43, 82.54)   # emitter (lower-right)

    # ── AC side: R12, R13 in series (horizontal, angle=90) ──
    # R12 at (52, 77.46): pin2(left)@(48.19)→AC_L, pin1(right)@(55.81)→R13
    sb.place_sym(
        "Device:R", 52, 77.46, 90,
        "R600", "10K/0.5W", "Resistor_SMD:R_1206_3216Metric", ["1", "2"],
    )
    # R13 at (68, 77.46): pin2(left)@(64.19)→R12, pin1(right)@(71.81)→U6 AN
    sb.place_sym(
        "Device:R", 68, 77.46, 90,
        "R601", "10K/0.5W", "Resistor_SMD:R_1206_3216Metric", ["1", "2"],
    )

    # Wires: R12 pin1 → R13 pin2, R13 pin1 → U6 AN
    sb.add_wire(55.81, 77.46, 64.19, 77.46)    # R12→R13
    sb.add_wire(71.81, 77.46, 83.57, 77.46)    # R13→U6 AN

    # AC_L hlabel at R12 pin2 (48.19, 77.46), extends left
    sb.add_hlabel("AC_L", 48.19, 77.46, 180, "input")

    # AC_N hlabel at U6 CAT (83.57, 82.54), extends left
    sb.add_hlabel("AC_N", 83.57, 82.54, 180, "input")

    # ── DC side ──
    # U6 EM → GND
    sb.place_power("GND", u6_em[0], u6_em[1])

    # DC output node at (125, 77.46)
    node_a = (125, 77.46)

    # Wire from U6 COL to node_A
    sb.add_wire(u6_col[0], u6_col[1], node_a[0], node_a[1])

    # R14 (10K DC load) vertical at (125, 67), angle=0
    #   pin1@(125, 70.81) [bottom] → wire to node_A
    #   pin2@(125, 63.19) [top] → +3V3
    sb.place_sym(
        "Device:R", 125, 67, 0,
        "R602", "10K", "Resistor_SMD:R_0603_1608Metric", ["1", "2"],
    )
    sb.add_wire(125, 70.81, 125, 77.46)    # R14 pin1 → node_A
    sb.place_power("+3V3", 125, 63.19)     # R14 pin2 → +3V3

    # C13 (1uF filter) vertical at (125, 87), angle=0
    #   pin2@(125, 83.19) [top] → wire from node_A
    #   pin1@(125, 90.81) [bottom] → GND
    sb.place_sym(
        "Device:C", 125, 87, 0,
        "C600", "1uF", "Capacitor_SMD:C_0603_1608Metric", ["1", "2"],
    )
    sb.add_wire(125, 77.46, 125, 83.19)    # node_A → C13 pin2
    sb.place_power("GND", 125, 90.81)      # C13 pin1 → GND

    # Junction at node_A (R14, C13, wire from COL, wire to R15)
    sb.add_junction(125, 77.46)

    # R15 (1K ADC protection) horizontal at (140, 77.46), angle=90
    #   pin2@(136.19, 77.46) [left] → wire from node_A
    #   pin1@(143.81, 77.46) [right] → to D3/V_SENSE node_B
    sb.place_sym(
        "Device:R", 140, 77.46, 90,
        "R603", "1K", "Resistor_SMD:R_0603_1608Metric", ["1", "2"],
    )
    sb.add_wire(125, 77.46, 136.19, 77.46)  # node_A → R15 pin2

    # ── D3: BAT54S ESD clamp at (158, 68), angle=0 ──
    # Pin 1 (A):   (150.38, 68) [left]   → GND
    # Pin 2 (K):   (165.62, 68) [right]  → +3V3
    # Pin 3 (COM): (158, 73.08) [bottom] → signal (node_B)
    d3_cx, d3_cy = 158, 68
    sb.place_sym(
        "Diode:BAT54S", d3_cx, d3_cy, 0,
        "D600", "BAT54S", "Package_TO_SOT_SMD:SOT-23", ["1", "2", "3"],
    )

    d3_a = (150.38, 68)      # A → GND
    d3_k = (165.62, 68)      # K → +3V3
    d3_com = (158, 73.08)    # COM → signal

    sb.place_power("GND", d3_a[0], d3_a[1])
    sb.place_power("+3V3", d3_k[0], d3_k[1])

    # node_B at (158, 77.46) — junction of R15 output, D3 COM, and V_SENSE
    node_b = (158, 77.46)

    # Wire: R15 pin1 (143.81) → node_B (158)
    sb.add_wire(143.81, 77.46, node_b[0], node_b[1])

    # Wire: node_B (158, 77.46) up to D3 COM (158, 73.08)
    sb.add_wire(node_b[0], node_b[1], d3_com[0], d3_com[1])

    # V_SENSE hlabel at node_B, extends right
    sb.add_hlabel("V_SENSE", node_b[0], node_b[1], 0, "output")

    # Junction at node_B (D3 COM wire, R15 output, V_SENSE label wire)
    sb.add_junction(node_b[0], node_b[1])

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 6 (Voltage Sensing) schematic generated.")

    # Verify with kicad-cli
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
