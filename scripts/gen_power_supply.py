#!/usr/bin/env python3
"""Generator for Block 1: Power Supply schematic (power_supply.kicad_sch).

Converts 24 VAC track voltage to 3.3 VDC for MCU and digital circuitry.

Signal flow (left → right):
  AC_L, AC_N → MB6S bridge → input caps → XL1509-3.3 buck → inductor → output caps → +3V3
                                                  ↑ SS34 catch diode

Components:
  D1  - MB6S bridge rectifier, SOP-4 (LCSC C2978785)
  U1  - XL1509-3.3E1 buck converter, SOP-8 (LCSC C74193)
  D2  - SS34 Schottky catch diode, SMA (LCSC C8678)
  L1  - 68uH/2A inductor, 8x8mm (LCSC C408345)
  C1  - 100uF/50V electrolytic input cap (LCSC C2993926)
  C2  - 100nF/50V ceramic input bypass (LCSC C49678)
  C3  - 220uF/10V electrolytic output cap (LCSC C2891399)
  C4  - 22uF/10V ceramic output cap (LCSC C5662523)

Pin positions in schematic (angle=0):
  MB6S:      pin2(AC) top (cx,cy-7.62), pin1(AC) bottom (cx,cy+7.62),
             pin3(DC+) right (cx+7.62,cy), pin4(DC-) left (cx-7.62,cy)
  XL1509:    pin1(VIN) (cx-10.16,cy-2.54), pin4(~EN) (cx-10.16,cy+2.54),
             pin5-8(GND) (cx,cy+7.62), pin2(OUT) (cx+10.16,cy-2.54),
             pin3(FB) (cx+10.16,cy+2.54)
  SS34/Schottky angle=270: K top (cx,cy-3.81), A bottom (cx,cy+3.81)
  L angle=90: pin1 right (cx+3.81,cy), pin2 left (cx-3.81,cy)
  C/C_Polarized angle=0: pin1(+) top (cx,cy-3.81), pin2(-) bottom (cx,cy+3.81)

Usage:
  python3 scripts/gen_power_supply.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "69aebb0f-a53c-4668-9eb1-5471b8889188"
SHEET_UUID = "cb2d87ca-656d-4d00-8315-c5972f3b17fd"

# KiCad standard library paths
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"
DIODE_BRIDGE_LIB = "/usr/share/kicad/symbols/Diode_Bridge.kicad_sym"
REGULATOR_LIB = "/usr/share/kicad/symbols/Regulator_Switching.kicad_sym"
DIODE_LIB = "/usr/share/kicad/symbols/Diode.kicad_sym"

# Output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl")
OUTFILE = os.path.join(PROJECT_DIR, "power_supply.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="Power Supply",
        date="2026-03-11",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 1: 24VAC to 3.3VDC buck converter",
        page="3",
        pwr_start=300,
    )

    # ── Library symbols ──
    sb.add_lib("Diode_Bridge", DIODE_BRIDGE_LIB, ["MB6S"])
    sb.add_lib("Regulator_Switching", REGULATOR_LIB, ["XL1509-3.3"])
    sb.add_lib("Diode", DIODE_LIB, ["SS34"])
    sb.add_lib("Device", DEVICE_LIB, ["C", "C_Polarized", "L"])
    sb.add_lib("power", POWER_LIB, ["+3V3", "GND", "PWR_FLAG"])

    # ═══════════════════════════════════════════════════════════════════
    # D1: MB6S Bridge Rectifier at (55, 75)
    # ═══════════════════════════════════════════════════════════════════
    br_cx, br_cy = 55, 75
    sb.place_sym(
        "Diode_Bridge:MB6S", br_cx, br_cy, 0,
        "D300", "MB6S",
        "Diode_SMD:Diode_Bridge_Diotec_SO-DIL-Slim",
        ["4", "2", "1", "3"],
    )
    # pin2 (AC, top): (55, 67.38) → AC_L
    # pin1 (AC, bottom): (55, 82.62) → AC_N
    # pin3 (DC+, right): (62.62, 75) → VIN rail
    # pin4 (DC-, left): (47.38, 75) → GND
    sb.add_hlabel("AC_L", br_cx, br_cy - 7.62, 180, "passive")
    sb.add_hlabel("AC_N", br_cx, br_cy + 7.62, 180, "passive")
    # GND on pin4 (DC-): route LEFT first, then DOWN — straight down would
    # short with AC_N hlabel stub which also ends at (47.38, 82.62).
    gnd_x = br_cx - 7.62 - 7.62  # = 39.76 — clear of AC_N stub
    sb.add_wire(br_cx - 7.62, br_cy, gnd_x, br_cy)
    sb.place_power("GND", gnd_x, br_cy)
    sb.add_net_label("VIN", br_cx + 7.62, br_cy, 0)

    # ═══════════════════════════════════════════════════════════════════
    # C1: 100uF/50V input bulk cap at (82, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C_Polarized", 82, 75, 0,
        "C300", "100uF/50V",
        "Capacitor_SMD:CP_Elec_8x10.5",
        ["1", "2"],
    )
    # pin1(+) top: (82, 71.19) → VIN
    # pin2(-) bottom: (82, 78.81) → GND
    sb.add_net_label("VIN", 82, 71.19, 180)
    sb.place_power("GND", 82, 78.81)

    # ═══════════════════════════════════════════════════════════════════
    # C2: 100nF/50V input ceramic bypass at (97, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C", 97, 75, 0,
        "C301", "100nF/50V",
        "Capacitor_SMD:C_0805_2012Metric",
        ["1", "2"],
    )
    sb.add_net_label("VIN", 97, 71.19, 180)
    sb.place_power("GND", 97, 78.81)

    # ═══════════════════════════════════════════════════════════════════
    # U1: XL1509-3.3 Buck Converter at (130, 70)
    # ═══════════════════════════════════════════════════════════════════
    xl_cx, xl_cy = 130, 70
    sb.place_sym(
        "Regulator_Switching:XL1509-3.3", xl_cx, xl_cy, 0,
        "U300", "XL1509-3.3E1",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        ["1", "4", "5", "6", "7", "8", "2", "3"],
    )
    # pin1 (VIN): (119.84, 67.46) → VIN
    # pin4 (~EN): (119.84, 72.54) → VIN (tied high = always enabled)
    # pin5-8 (GND): (130, 77.62) → GND
    # pin2 (OUT): (140.16, 67.46) → VSW (switch node)
    # pin3 (FB): (140.16, 72.54) → +3V3 output (fixed version feedback)
    sb.add_net_label("VIN", xl_cx - 10.16, xl_cy - 2.54, 180)
    sb.add_net_label("VIN", xl_cx - 10.16, xl_cy + 2.54, 180)
    sb.place_power("GND", xl_cx, xl_cy + 7.62)
    sb.add_net_label("VSW", xl_cx + 10.16, xl_cy - 2.54, 0)
    sb.add_net_label("+3V3", xl_cx + 10.16, xl_cy + 2.54, 0)

    # ═══════════════════════════════════════════════════════════════════
    # D2: SS34 Schottky catch diode at (155, 78) angle=270
    # angle=270: K at top (cx, cy-3.81), A at bottom (cx, cy+3.81)
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Diode:SS34", 155, 78, 270,
        "D301", "SS34",
        "Diode_SMD:D_SMA",
        ["1", "2"],
    )
    # K (cathode) top: (155, 74.19) → VSW net
    # A (anode) bottom: (155, 81.81) → GND
    sb.add_net_label("VSW", 155, 74.19, 180)
    sb.place_power("GND", 155, 81.81)

    # ═══════════════════════════════════════════════════════════════════
    # L1: 68uH inductor at (170, 67.46) angle=90 (horizontal)
    # angle=90: pin1 at right (cx+3.81, cy), pin2 at left (cx-3.81, cy)
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:L", 170, 67.46, 90,
        "L300", "68uH",
        "Inductor_SMD:L_Bourns_SRN8040TA",
        ["1", "2"],
    )
    # pin2 (left): (166.19, 67.46) → VSW
    # pin1 (right): (173.81, 67.46) → V3V3 output
    sb.add_net_label("VSW", 166.19, 67.46, 180)
    sb.add_net_label("+3V3", 173.81, 67.46, 0)

    # ═══════════════════════════════════════════════════════════════════
    # C3: 220uF/10V output bulk cap at (192, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C_Polarized", 192, 75, 0,
        "C302", "220uF/10V",
        "Capacitor_SMD:CP_Elec_6.3x7.7",
        ["1", "2"],
    )
    sb.add_net_label("+3V3", 192, 71.19, 180)
    sb.place_power("GND", 192, 78.81)

    # ═══════════════════════════════════════════════════════════════════
    # C4: 22uF/10V output ceramic cap at (207, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C", 207, 75, 0,
        "C303", "22uF/10V",
        "Capacitor_SMD:C_0805_2012Metric",
        ["1", "2"],
    )
    sb.add_net_label("+3V3", 207, 71.19, 180)
    sb.place_power("GND", 207, 78.81)

    # ═══════════════════════════════════════════════════════════════════
    # Power symbols: +3V3 on the V3V3 net, PWR_FLAG
    # ═══════════════════════════════════════════════════════════════════
    # +3V3 power symbol on output rail — place at C4 top
    sb.place_power("+3V3", 207, 71.19)

    # PWR_FLAG on +3V3, VIN, and GND to satisfy ERC
    sb.place_power("PWR_FLAG", 192, 71.19)
    sb.place_power("PWR_FLAG", 82, 71.19)
    sb.place_power("PWR_FLAG", 82, 78.81)  # GND at C1 bottom

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 1 (Power Supply) schematic generated.")

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
