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
    # Pin coordinates:
    # pin2 (AC, top):    (55, 67.38) → AC_L
    # pin1 (AC, bottom): (55, 82.62) → AC_N
    # pin3 (DC+, right): (62.62, 75) → VIN rail
    # pin4 (DC-, left):  (47.38, 75) → GND
    br_dc_plus = (62.62, 75)
    sb.add_hlabel("AC_L", br_cx, br_cy - 7.62, 180, "passive")
    sb.add_hlabel("AC_N", br_cx, br_cy + 7.62, 180, "passive")
    # GND on pin4 (DC-): route LEFT first, then DOWN — straight down would
    # collide with AC_N hlabel stub which also ends at (47.38, 82.62).
    gnd_x = br_cx - 7.62 - 7.62  # = 39.76 — clear of AC_N stub
    sb.add_wire(br_cx - 7.62, br_cy, gnd_x, br_cy)
    sb.place_power("GND", gnd_x, br_cy)

    # ═══════════════════════════════════════════════════════════════════
    # C1: 100uF/50V input bulk cap at (82, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C_Polarized", 82, 75, 0,
        "C300", "100uF/50V",
        "Capacitor_SMD:CP_Elec_8x10.5",
        ["1", "2"],
    )
    c300_plus = (82, 71.19)   # pin1(+) top
    c300_minus = (82, 78.81)  # pin2(-) bottom
    sb.place_power("GND", c300_minus[0], c300_minus[1])

    # ═══════════════════════════════════════════════════════════════════
    # C2: 100nF/50V input ceramic bypass at (97, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C", 97, 75, 0,
        "C301", "100nF/50V",
        "Capacitor_SMD:C_0805_2012Metric",
        ["1", "2"],
    )
    c301_plus = (97, 71.19)   # pin1 top
    c301_minus = (97, 78.81)  # pin2 bottom
    sb.place_power("GND", c301_minus[0], c301_minus[1])

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
    xl_vin = (119.84, 67.46)   # pin1 (VIN)
    xl_en = (119.84, 72.54)    # pin4 (~EN) — tied to VIN (always enabled)
    xl_gnd = (130, 77.62)      # pin5-8 (GND)
    xl_out = (140.16, 67.46)   # pin2 (OUT) — switch node
    xl_fb = (140.16, 72.54)    # pin3 (FB) — +3V3 output (fixed version)
    sb.place_power("GND", xl_gnd[0], xl_gnd[1])

    # ── VIN rail: bridge DC+ → C300 → C301 → XL1509 VIN/~EN ──
    # Horizontal bus at y=71.19 (cap pin1 level), segmented at each pin
    vin_y = 71.19
    # Bridge DC+ up to bus level
    sb.add_wire(br_dc_plus[0], br_dc_plus[1], br_dc_plus[0], vin_y)
    # Segment: bridge → C300 pin1
    sb.add_wire(br_dc_plus[0], vin_y, c300_plus[0], vin_y)
    # Segment: C300 pin1 → C301 pin1
    sb.add_wire(c300_plus[0], vin_y, c301_plus[0], vin_y)
    # Segment: C301 pin1 → XL1509 VIN x
    sb.add_wire(c301_plus[0], vin_y, xl_vin[0], vin_y)
    # VIN pin: up from bus to XL1509 pin1
    sb.add_wire(xl_vin[0], vin_y, xl_vin[0], xl_vin[1])
    # ~EN pin: down from bus to XL1509 pin4 (tie high)
    sb.add_wire(xl_vin[0], vin_y, xl_vin[0], xl_en[1])
    # Junctions at branch points
    sb.add_junction(c300_plus[0], vin_y)
    sb.add_junction(c301_plus[0], vin_y)
    sb.add_junction(xl_vin[0], vin_y)

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
    d301_k = (155, 74.19)   # K (cathode) top
    d301_a = (155, 81.81)   # A (anode) bottom
    sb.place_power("GND", d301_a[0], d301_a[1])

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
    l300_left = (166.19, 67.46)   # pin2 (left) → VSW
    l300_right = (173.81, 67.46)  # pin1 (right) → +3V3 output

    # ── VSW rail: XL1509 OUT → SS34 cathode → L1 input ──
    # Horizontal bus at y=67.46 (XL1509 OUT / L1 level), segmented at D301
    vsw_y = 67.46
    # Segment: XL1509 OUT → D301 cathode x
    sb.add_wire(xl_out[0], vsw_y, d301_k[0], vsw_y)
    # Segment: D301 cathode x → L1 left pin
    sb.add_wire(d301_k[0], vsw_y, l300_left[0], vsw_y)
    # SS34 cathode: vertical drop from bus to diode
    sb.add_wire(d301_k[0], vsw_y, d301_k[0], d301_k[1])
    sb.add_junction(d301_k[0], vsw_y)

    # ═══════════════════════════════════════════════════════════════════
    # C3: 220uF/10V output bulk cap at (192, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C_Polarized", 192, 75, 0,
        "C302", "220uF/10V",
        "Capacitor_SMD:CP_Elec_6.3x7.7",
        ["1", "2"],
    )
    c302_plus = (192, 71.19)
    c302_minus = (192, 78.81)
    sb.place_power("GND", c302_minus[0], c302_minus[1])

    # ═══════════════════════════════════════════════════════════════════
    # C4: 22uF/10V output ceramic cap at (207, 75) angle=0
    # ═══════════════════════════════════════════════════════════════════
    sb.place_sym(
        "Device:C", 207, 75, 0,
        "C303", "22uF/10V",
        "Capacitor_SMD:C_0805_2012Metric",
        ["1", "2"],
    )
    c303_plus = (207, 71.19)
    c303_minus = (207, 78.81)
    sb.place_power("GND", c303_minus[0], c303_minus[1])

    # ── +3V3 rail: L1 output → output caps → XL1509 FB ──
    # Horizontal bus at y=71.19 (cap pin1 level), segmented at each pin
    v33_y = 71.19
    # L1 output down to bus level
    sb.add_wire(l300_right[0], l300_right[1], l300_right[0], v33_y)
    # Segment: L1 output → C302 pin1
    sb.add_wire(l300_right[0], v33_y, c302_plus[0], v33_y)
    # Segment: C302 pin1 → C303 pin1
    sb.add_wire(c302_plus[0], v33_y, c303_plus[0], v33_y)
    # XL1509 FB: wire from FB pin right to L1 output x, then up to bus
    sb.add_wire(xl_fb[0], xl_fb[1], l300_right[0], xl_fb[1])
    sb.add_wire(l300_right[0], xl_fb[1], l300_right[0], v33_y)
    sb.add_junction(l300_right[0], v33_y)

    # ═══════════════════════════════════════════════════════════════════
    # Power symbols and PWR_FLAGs
    # ═══════════════════════════════════════════════════════════════════
    # +3V3 power symbol on output rail — place at C303 top
    sb.place_power("+3V3", c303_plus[0], c303_plus[1])

    # PWR_FLAG on +3V3, VIN, and GND to satisfy ERC
    sb.place_power("PWR_FLAG", c302_plus[0], c302_plus[1])
    sb.place_power("PWR_FLAG", c300_plus[0], c300_plus[1])
    sb.place_power("PWR_FLAG", c300_minus[0], c300_minus[1])

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
