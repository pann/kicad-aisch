#!/usr/bin/env python3
"""Generator for Block 8: USB Programming (usb_prog.kicad_sch).

Circuit: USB-C receptacle with ESD protection and CC pull-downs for ESP32-C3
native USB (CDC/JTAG). No USB-UART bridge needed.

Schematic layout (left to right):

  J1 (USB-C 14P)          U4 (USBLC6-2SC6)
  ┌──────────┐              ┌────┐
  │ VBUS ────┼──────────────┤VBUS│
  │          │              │    │
  │ D-  ─────┼──pin1──I/O1──┤    ├──I/O1──pin6──> USB_D- (hlabel)
  │ D-  ─────┘              │    │
  │ D+  ─────┼──pin3──I/O2──┤    ├──I/O2──pin4──> USB_D+ (hlabel)
  │ D+  ─────┘              │    │
  │ CC1 ─────┼── R17(5.1K) ── GND    │ GND│
  │ CC2 ─────┼── R18(5.1K) ── GND    └────┘
  │          │
  │ GND ─────┼── GND
  │ SHIELD ──┼── GND
  └──────────┘

Components:
  J1      USB-C receptacle 14-pin (USB 2.0)  Connector_USB:USB_C_Receptacle
  U4      USBLC6-2SC6    SOT-23-6   C2827693  (ESD protection)
  R17     5.1K           0603       C23186    (CC1 pull-down)
  R18     5.1K           0603       C23186    (CC2 pull-down)

Pin positions (symbol coordinates, angle=0):
  USB_C_Receptacle_USB2.0_14P (all signal pins exit right at x=+15.24):
    SHIELD(S1): (-7.62, -22.86, angle=90)  → bottom-left
    GND(A1):    (0, -22.86, angle=90)      → bottom (+ hidden A12, B1, B12)
    VBUS(A4):   (15.24, 15.24, angle=180)  → right-top (+ hidden A9, B4, B9)
    CC1(A5):    (15.24, 10.16, angle=180)  → right
    CC2(B5):    (15.24, 7.62, angle=180)   → right
    D-(A7):     (15.24, 2.54, angle=180)   → right (+ hidden B7)
    D+(A6):     (15.24, -2.54, angle=180)  → right (+ hidden B6)

  USBLC6-2SC6 (extends USBLC6-2P6):
    Pin1 I/O1:  (-5.08, 0, angle=0)     → left
    Pin3 I/O2:  (-5.08, -2.54, angle=0)  → left
    Pin5 VBUS:  (0, 5.08, angle=270)     → top
    Pin2 GND:   (0, -7.62, angle=90)     → bottom
    Pin6 I/O1:  (5.08, 0, angle=180)     → right
    Pin4 I/O2:  (5.08, -2.54, angle=180) → right

Coordinate plan:
  J1 at (50, 80), angle=0:
    Schematic pin positions (at cx+px, cy-py for angle=0):
      SHIELD: (50 + (-7.62), 80 - (-22.86)) = (42.38, 102.86)
      GND:    (50 + 0, 80 - (-22.86))       = (50, 102.86)
      VBUS:   (50 + 15.24, 80 - 15.24)      = (65.24, 64.76)
      CC1:    (50 + 15.24, 80 - 10.16)      = (65.24, 69.84)
      CC2:    (50 + 15.24, 80 - 7.62)       = (65.24, 72.38)
      D-:     (50 + 15.24, 80 - 2.54)       = (65.24, 77.46)
      D+:     (50 + 15.24, 80 - (-2.54))    = (65.24, 82.54)

  U4 at (110, 80), angle=0:
    Pin1 I/O1(D-): (110 + (-5.08), 80 - 0)      = (104.92, 80)
    Pin3 I/O2(D+): (110 + (-5.08), 80 - (-2.54)) = (104.92, 82.54)
    Pin5 VBUS:     (110 + 0, 80 - 5.08)          = (110, 74.92)
    Pin2 GND:      (110 + 0, 80 - (-7.62))       = (110, 87.62)
    Pin6 I/O1(D-): (110 + 5.08, 80 - 0)          = (115.08, 80)
    Pin4 I/O2(D+): (110 + 5.08, 80 - (-2.54))    = (115.08, 82.54)

  R17 at (85, 69.84), angle=90 (horizontal):
    pin2: (85 - 3.81, 69.84) = (81.19, 69.84) [left, connects to CC1]
    pin1: (85 + 3.81, 69.84) = (88.81, 69.84) [right, connects to GND]

  R18 at (85, 72.38), angle=90 (horizontal):
    pin2: (81.19, 72.38) [left, connects to CC2]
    pin1: (88.81, 72.38) [right, connects to GND]

Usage:
  python3 scripts/gen_usb_prog.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "c8642268-bd1f-47bb-9d74-30221e4beffb"
SHEET_UUID = "efc4923a-0435-448d-95f7-f869b5841635"

# Library paths
CONNECTOR_LIB = "/usr/share/kicad/symbols/Connector.kicad_sym"
POWER_PROT_LIB = "/usr/share/kicad/symbols/Power_Protection.kicad_sym"
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTFILE = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl", "usb_prog.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="USB Programming",
        date="2026-03-05",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 8: USB-C for ESP32-C3 native USB",
        page="10",
        pwr_start=1000,
    )

    # ── Library symbols ──
    sb.add_lib("Connector", CONNECTOR_LIB, ["USB_C_Receptacle_USB2.0_14P"])
    sb.add_lib("Power_Protection", POWER_PROT_LIB, ["USBLC6-2SC6"])
    sb.add_lib("Device", DEVICE_LIB, ["R"])
    sb.add_lib("power", POWER_LIB, ["GND", "+5V"])

    # ═══════════════════════════════════════════════════════════════════
    # Component placement
    # ═══════════════════════════════════════════════════════════════════

    # ── J1: USB-C receptacle at (50, 80) ──
    j1_cx, j1_cy = 50, 80
    j1_pins = ["S1", "A1", "A12", "B1", "B12",
               "A4", "A9", "B4", "B9",
               "A5", "B5", "A7", "B7", "A6", "B6"]
    sb.place_sym(
        "Connector:USB_C_Receptacle_USB2.0_14P", j1_cx, j1_cy, 0,
        "J1000", "USB_C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        j1_pins,
    )

    # J1 pin positions (schematic coords)
    j1_shield = (42.38, 102.86)
    j1_gnd = (50, 102.86)
    j1_vbus = (65.24, 64.76)
    j1_cc1 = (65.24, 69.84)
    j1_cc2 = (65.24, 72.38)
    j1_dm = (65.24, 77.46)   # D-
    j1_dp = (65.24, 82.54)   # D+

    # ── U4: USBLC6-2SC6 at (110, 80) ──
    u4_cx, u4_cy = 110, 80
    sb.place_sym(
        "Power_Protection:USBLC6-2SC6", u4_cx, u4_cy, 0,
        "U1000", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
        ["1", "2", "3", "4", "5", "6"],
    )

    u4_io1_in = (104.92, 80)      # Pin 1 I/O1 left (D-)
    u4_io2_in = (104.92, 82.54)   # Pin 3 I/O2 left (D+)
    u4_vbus = (110, 74.92)        # Pin 5 VBUS top
    u4_gnd = (110, 87.62)         # Pin 2 GND bottom
    u4_io1_out = (115.08, 80)     # Pin 6 I/O1 right (D-)
    u4_io2_out = (115.08, 82.54)  # Pin 4 I/O2 right (D+)

    # ── R17: CC1 pull-down 5.1K at (85, 69.84), angle=90 ──
    sb.place_sym(
        "Device:R", 85, 69.84, 90,
        "R1000", "5.1K", "Resistor_SMD:R_0603_1608Metric", ["1", "2"],
    )
    # R17 pin2 (left) at (81.19, 69.84), pin1 (right) at (88.81, 69.84)

    # ── R18: CC2 pull-down 5.1K at (85, 72.38), angle=90 ──
    sb.place_sym(
        "Device:R", 85, 72.38, 90,
        "R1001", "5.1K", "Resistor_SMD:R_0603_1608Metric", ["1", "2"],
    )
    # R18 pin2 (left) at (81.19, 72.38), pin1 (right) at (88.81, 72.38)

    # ═══════════════════════════════════════════════════════════════════
    # Wiring
    # ═══════════════════════════════════════════════════════════════════

    # ── VBUS: J1 VBUS → wire up to U4 VBUS ──
    # J1 VBUS at (65.24, 64.76), U4 VBUS at (110, 74.92)
    # Route: right from J1 to x=110, then down to U4
    sb.add_wire(j1_vbus[0], j1_vbus[1], 110, 64.76)
    sb.add_wire(110, 64.76, 110, 74.92)

    # ── D- path: J1 D- → U4 I/O1 in → U4 I/O1 out → USB_D- hlabel ──
    # J1 D- at (65.24, 77.46), U4 pin1 at (104.92, 80)
    # Route: right from J1 to x=95, then down to y=80, then right to U4
    sb.add_wire(j1_dm[0], j1_dm[1], 95, 77.46)
    sb.add_wire(95, 77.46, 95, 80)
    sb.add_wire(95, 80, u4_io1_in[0], u4_io1_in[1])

    # U4 pin6 I/O1 out → USB_D- hlabel
    sb.add_hlabel("USB_D-", 115.08 + 7.62, 80, 0, "bidirectional")
    sb.add_wire(u4_io1_out[0], u4_io1_out[1], 115.08 + 7.62, 80)

    # ── D+ path: J1 D+ → U4 I/O2 in → U4 I/O2 out → USB_D+ hlabel ──
    # J1 D+ at (65.24, 82.54), U4 pin3 at (104.92, 82.54) — same y!
    sb.add_wire(j1_dp[0], j1_dp[1], u4_io2_in[0], u4_io2_in[1])

    # U4 pin4 I/O2 out → USB_D+ hlabel
    sb.add_hlabel("USB_D+", 115.08 + 7.62, 82.54, 0, "bidirectional")
    sb.add_wire(u4_io2_out[0], u4_io2_out[1], 115.08 + 7.62, 82.54)

    # ── B-side data pins: connect B7→A7 (D-) and B6→A6 (D+) ──
    # B7 (D-) at (j1_cx+15.24, j1_cy) connects vertically to A7 (D-) at (j1_cx+15.24, j1_cy-2.54)
    b7_x, b7_y = j1_cx + 15.24, j1_cy
    b6_x, b6_y = j1_cx + 15.24, j1_cy + 5.08
    sb.add_wire(b7_x, b7_y, j1_dm[0], j1_dm[1])
    sb.add_junction(j1_dm[0], j1_dm[1])
    sb.add_wire(b6_x, b6_y, j1_dp[0], j1_dp[1])
    sb.add_junction(j1_dp[0], j1_dp[1])

    # ── CC1: J1 CC1 → R17 pin2 ──
    sb.add_wire(j1_cc1[0], j1_cc1[1], 81.19, 69.84)

    # ── CC2: J1 CC2 → R18 pin2 ──
    sb.add_wire(j1_cc2[0], j1_cc2[1], 81.19, 72.38)

    # ── GND connections ──
    # R17 pin1 (right) → GND: share a common GND point
    # R18 pin1 (right) → GND: wire down to same GND
    # Route both to (92, y) then down to common GND
    sb.add_wire(88.81, 69.84, 92, 69.84)
    sb.add_wire(92, 69.84, 92, 72.38)
    sb.add_wire(88.81, 72.38, 92, 72.38)
    sb.add_junction(92, 72.38)
    sb.add_wire(92, 72.38, 92, 72.38 + 7.62)
    sb.place_power("GND", 92, 72.38 + 7.62)

    # J1 GND (50, 102.86) → GND power symbol
    sb.add_wire(j1_gnd[0], j1_gnd[1], j1_gnd[0], j1_gnd[1] + 7.62)
    sb.place_power("GND", j1_gnd[0], j1_gnd[1] + 7.62)

    # J1 SHIELD (42.38, 102.86) → wire to J1 GND
    sb.add_wire(j1_shield[0], j1_shield[1], j1_gnd[0], j1_gnd[1])

    # U4 GND (110, 87.62) → GND
    sb.add_wire(u4_gnd[0], u4_gnd[1], u4_gnd[0], u4_gnd[1] + 7.62)
    sb.place_power("GND", u4_gnd[0], u4_gnd[1] + 7.62)

    # ── +5V on VBUS (for USB detection, not used for power) ──
    # Add a +5V power flag at the VBUS wire for ERC
    # Actually, VBUS is just for ESD clamp reference — no +5V power symbol needed
    # The board is track-powered, VBUS is only connected to U4 for ESD clamping

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 8 (USB Programming) schematic generated.")

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
