#!/usr/bin/env python3
"""Generator for Block 3: Zero-Crossing Detector (zero_crossing.kicad_sch).

Circuit: Full-wave optocoupler-based AC zero-crossing detector.

Requirement: AC output must be controlled on both positive and negative half-cycles,
so zero-crossing detection must operate at 2x line frequency (100/120 Hz).

A 4-diode bridge (D4-D7) steers current through the EL357N LED on BOTH AC half-cycles:

               D4(A→K)                    D5(A→K)
  AC_L──R1──R2──┤├──── U5_AN    U5_CAT ────┤├──── AC_N (node_B)
   (node_A)             │ LED               ↑
               D7(K←A)  ↓        D6(K←A)    │
  AC_N──────────┤├──── U5_CAT   U5_AN ─────┤├──── AC_L (node_A)

Simplified as standard Graetz bridge with LED as load:
               ┌── D4(A→K) ── U5_AN ──┐
  node_A ──────┤                       ├── LED ── (always AN→CAT)
               └── U5_CAT ── D7(A→K) ─┘
                                           │
               ┌── D6(A→K) ── U5_AN ──┐   │
  node_B ──────┤                       ├───┘
               └── U5_CAT ── D5(A→K) ─┘

Positive half (AC_L > AC_N): node_A → D4 → U5_AN → LED → U5_CAT → D5 → node_B ✓
Negative half (AC_N > AC_L): node_B → D6 → U5_AN → LED → U5_CAT → D7 → node_A ✓

DC side:
  +3V3 → R5(10K) → U5 COL (pull-up)
  U5 EM → GND
  ZC_PULSE at COL junction (active-low: LOW near AC peaks, HIGH near zero crossings)

Components:
  U5     EL357N(C)(TA)-G   SOP-4    C29981  (project lib)
  D4-D7  1N4148WS           SOD-323  C2128   (full-wave bridge, 4 diodes)
  R1     3.3K 1W            1206             (AC series 1)
  R2     3.3K 1W            1206             (AC series 2)
  R5     10K                0603     C25804  (DC pull-up)

Pin positions (angle=0, schematic Y-down):
  EL357N: AN@(cx-11.43, cy-2.54), CAT@(cx-11.43, cy+2.54),
          COL@(cx+11.43, cy-2.54), EM@(cx+11.43, cy+2.54)
  1N4148WS (extends 1N4001): K@(cx-3.81, cy), A@(cx+3.81, cy) [angle=0]

Layout:
  Signal flow left-to-right. Diode bridge around U5 LED side (left).
  DC output (COL, R5, ZC_PULSE) on the right.

  Bridge topology (schematic coordinates):
                    ┌─ D4 ─┐
    node_A ─────────┤      ├── U5_AN (77.46)
                    └─ D7 ─┘        │ LED
                    ┌─ D6 ─┐        │
    node_B ─────────┤      ├── U5_CAT (82.54)
                    └─ D5 ─┘

  D4: upper-left,  connects node_A → U5_AN  (positive half, upper path)
  D7: lower-left,  connects U5_CAT → node_A (negative half, lower-left return)
  D6: lower-right(?), connects node_B → U5_AN (negative half, upper path)
  D5: upper-right(?), connects U5_CAT → node_B (positive half, lower return)

  Simplified vertical bridge at x=70..76:
    D4 at (70, 74), angle=180: A@left(66.19) K@right(73.81) → K connects to U5_AN wire
    D7 at (70, 86), angle=0:   K@left(66.19) A@right(73.81) → A connects to U5_CAT wire
      (D7 conducts right→left: CAT → node_A on negative half)
    D6 at (80, 74), angle=180: A@left(76.19) K@right(83.81) → K connects to U5_AN
      Wait, this puts D6 K at same point as D4 K. They share U5_AN connection. ✓
    D5 at (80, 86), angle=0:   K@left(76.19) A@right(83.81) → A connects to U5_CAT
      D5 K connects to node_B. ✓

  Actually, let me use a cleaner layout with the bridge as two vertical columns:

  Left column (x=68): D4 (top, fwd right) and D7 (bottom, fwd left)
    D4 at (68, 74.92), angle=180: A@(64.19) K@(71.81) — current L→R
    D7 at (68, 85.08), angle=0:   K@(64.19) A@(71.81) — current R→L

  Right column: not needed if D4/D7 K/A connect to U5_AN/CAT via wires.

  Hmm, a full bridge needs 4 diodes in a diamond. Let me use a different approach:
  two horizontal pairs.

  Upper pair (y=77.46, same as U5_AN):
    D4: node_A → U5_AN
    D6: node_B → U5_AN

  Lower pair (y=82.54, same as U5_CAT):
    D5: U5_CAT → node_B
    D7: U5_CAT → node_A

Usage:
  python3 scripts/gen_zero_crossing.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "12425cfa-6061-40dc-bca8-eb9456dd8125"
SHEET_UUID = "09ac1fc8-d7b7-450f-806c-6e384a19c1cf"

# Library paths
PROJECT_LIB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "marklin-wifi-ctrl", "marklin-wifi-ctrl.kicad_sym",
)
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
DIODE_LIB = "/usr/share/kicad/symbols/Diode.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTFILE = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl", "zero_crossing.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="Zero-Crossing Detector",
        date="2026-03-05",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 3: Full-wave AC zero-cross via EL357N",
        page="5",
        pwr_start=500,
    )

    # ── Library symbols ──
    sb.add_lib("marklin-wifi-ctrl", PROJECT_LIB, ["EL357N(C)(TA)-G"])
    sb.add_lib("Diode", DIODE_LIB, ["1N4148WS"])
    sb.add_lib("Device", DEVICE_LIB, ["R"])
    sb.add_lib("power", POWER_LIB, ["GND", "+3V3"])

    # ═══════════════════════════════════════════════════════════════════
    # Component placement
    #
    # Full-wave bridge layout:
    #
    #                     ┌── D4(→) ──┐
    #   AC_L ── R1 ── R2 ─┤           ├── U5_AN ─┐
    #          (node_A)   └── D6(←) ──┘           │ LED
    #                     ┌── D5(←) ──┐           │
    #   AC_N ─────────────┤           ├── U5_CAT ─┘   +3V3
    #          (node_B)   └── D7(→) ──┘                 │
    #                                               R5(10K)
    #                                    COL ───────┤── ZC_PULSE
    #                                    EM ── GND
    #
    # D4: node_A → U5_AN  (pos half, upper-left to upper-right)
    # D6: node_B → U5_AN  (neg half, lower-left to upper-right)
    # D5: U5_CAT → node_B (pos half, lower-right to lower-left)
    # D7: U5_CAT → node_A (neg half, lower-right to upper-left)
    #
    # Bridge layout uses vertical diode pairs:
    #   Left vertical pair at x=65:  D4(top), D7(bottom) — both connect to node_A
    #   Right vertical pair at x=77: D6(top), D5(bottom) — both connect to node_B
    #   Top horizontal bus at y=72:  D4_K, D6_K → wire to U5_AN
    #   Bottom horizontal bus at y=88: D5_A, D7_A → wire to U5_CAT
    # ═══════════════════════════════════════════════════════════════════

    # ── U5: EL357N optocoupler at (140, 90) ──
    u5_cx, u5_cy = 140, 90
    sb.place_sym(
        "marklin-wifi-ctrl:EL357N(C)(TA)-G", u5_cx, u5_cy, 0,
        "U500", "EL357N", "marklin-wifi-ctrl:OPTO-SMD-4_L4.4-W4.1-P2.54-LS7.0-TL",
        ["1", "2", "3", "4"],
    )
    u5_an  = (u5_cx - 11.43, u5_cy - 2.54)  # Pin 1, LED anode
    u5_cat = (u5_cx - 11.43, u5_cy + 2.54)  # Pin 2, LED cathode
    u5_col = (u5_cx + 11.43, u5_cy - 2.54)  # Pin 4, collector
    u5_em  = (u5_cx + 11.43, u5_cy + 2.54)  # Pin 3, emitter

    # ── AC side: R1, R2 in series (horizontal, angle=90) ──
    sb.place_sym(
        "Device:R", 30, 75, 90,
        "R500", "3.3K/1W", "Resistor_SMD:R_1206_3216Metric", ["1", "2"],
    )
    sb.place_sym(
        "Device:R", 45, 75, 90,
        "R501", "3.3K/1W", "Resistor_SMD:R_1206_3216Metric", ["1", "2"],
    )
    # R1 pin1(33.81) → R2 pin2(41.19)
    sb.add_wire(33.81, 75, 41.19, 75)
    # AC_L hlabel at R1 pin2 (26.19)
    sb.add_hlabel("AC_L", 26.19, 75, 180, "input")

    # node_A: junction of R2 output, D4, D7
    node_a_x, node_a_y = 55, 75
    sb.add_wire(48.81, 75, node_a_x, 75)

    # node_B: junction of AC_N, D6, D5  (30mm below node_A for diode spacing)
    node_b_x, node_b_y = 55, 105
    sb.add_hlabel("AC_N", node_b_x, node_b_y, 180, "input")

    # ── Bridge diodes (vertical, wide spacing for readability) ──
    # 1N4148WS angle=270: K@top(cy-3.81), A@bottom(cy+3.81), current bottom→top
    # 1N4148WS angle=90:  A@top(cy-3.81), K@bottom(cy+3.81), current top→bottom

    d_left_x = 62     # left diode column (D4/D7, connects to node_A)
    d_right_x = 92    # right diode column (D6/D5, connects to node_B)
    bus_top = 58       # top horizontal bus → U5_AN
    bus_bot = 122      # bottom horizontal bus → U5_CAT

    # D4: node_A → bus_top (current flows up), angle=270 (A at bottom, K at top)
    d4_cy = (bus_top + node_a_y) / 2  # 75
    sb.place_sym(
        "Diode:1N4148WS", d_left_x, d4_cy, 270,
        "D500", "1N4148WS", "Diode_SMD:D_SOD-323", ["1", "2"],
    )
    sb.add_wire(d_left_x, d4_cy - 3.81, d_left_x, bus_top)      # K → bus_top
    sb.add_wire(d_left_x, d4_cy + 3.81, d_left_x, node_a_y)     # A → node_A level
    sb.add_wire(d_left_x, node_a_y, node_a_x, node_a_y)          # to node_A

    # D7: bus_bot → node_A (current flows up), angle=270 (A at bottom, K at top)
    d7_cy = (node_a_y + bus_bot) / 2  # 91
    sb.place_sym(
        "Diode:1N4148WS", d_left_x, d7_cy, 270,
        "D503", "1N4148WS", "Diode_SMD:D_SOD-323", ["1", "2"],
    )
    sb.add_wire(d_left_x, d7_cy - 3.81, d_left_x, d4_cy + 3.81)  # K → up to D4 A
    sb.add_wire(d_left_x, d7_cy + 3.81, d_left_x, bus_bot)        # A → bus_bot
    sb.add_junction(d_left_x, node_a_y)

    # D6: node_B → bus_top (current flows up), angle=270
    d6_cy = (bus_top + node_b_y) / 2  # 81
    sb.place_sym(
        "Diode:1N4148WS", d_right_x, d6_cy, 270,
        "D502", "1N4148WS", "Diode_SMD:D_SOD-323", ["1", "2"],
    )
    sb.add_wire(d_right_x, d6_cy - 3.81, d_right_x, bus_top)     # K → bus_top
    sb.add_wire(d_right_x, d6_cy + 3.81, d_right_x, node_b_y)    # A → node_B level
    sb.add_wire(d_right_x, node_b_y, node_b_x, node_b_y)         # to node_B

    # D5: bus_bot → node_B (current flows up... wait, D5 conducts top→bottom)
    # angle=90: A at top, K at bottom. Conducts top→bottom ✓
    d5_cy = (node_b_y + bus_bot) / 2  # 97
    sb.place_sym(
        "Diode:1N4148WS", d_right_x, d5_cy, 90,
        "D501", "1N4148WS", "Diode_SMD:D_SOD-323", ["1", "2"],
    )
    sb.add_wire(d_right_x, d5_cy - 3.81, d_right_x, node_b_y)    # A → node_B level
    sb.add_wire(d_right_x, d5_cy + 3.81, d_right_x, bus_bot)     # K → bus_bot
    sb.add_junction(d_right_x, node_b_y)

    # ── Bus wires ──
    # Top bus → U5_AN
    sb.add_wire(d_left_x, bus_top, d_right_x, bus_top)
    sb.add_wire(d_right_x, bus_top, u5_an[0], bus_top)
    sb.add_wire(u5_an[0], bus_top, u5_an[0], u5_an[1])
    sb.add_junction(d_right_x, bus_top)

    # Bottom bus → U5_CAT
    sb.add_wire(d_left_x, bus_bot, d_right_x, bus_bot)
    sb.add_wire(d_right_x, bus_bot, u5_cat[0], bus_bot)
    sb.add_wire(u5_cat[0], bus_bot, u5_cat[0], u5_cat[1])
    sb.add_junction(d_right_x, bus_bot)

    # ── DC side ──
    sb.place_power("GND", u5_em[0], u5_em[1])

    # R5 (10K pull-up) at (170, 80), vertical
    r5_x = 170
    sb.place_sym(
        "Device:R", r5_x, 80, 0,
        "R502", "10K", "Resistor_SMD:R_0603_1608Metric", ["1", "2"],
    )
    sb.place_power("+3V3", r5_x, 80 - 3.81)

    # Wire: U5 COL → R5/ZC_PULSE junction
    zc_y = u5_col[1]
    sb.add_wire(u5_col[0], u5_col[1], r5_x, zc_y)
    sb.add_wire(r5_x, 80 + 3.81, r5_x, zc_y)
    sb.add_junction(r5_x, zc_y)

    # ZC_PULSE hlabel
    sb.add_hlabel("ZC_PULSE", r5_x, zc_y, 0, "output")

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 3 (Zero-Crossing Detector) schematic generated — full-wave bridge.")

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
