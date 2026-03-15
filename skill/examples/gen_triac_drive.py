#!/usr/bin/env python3
"""Generator for Block 5: TRIAC Drive schematic (triac_drive.kicad_sch).

Two identical channels: FWD and REV motor winding drive.
Each channel: MCU gate signal → optocoupler → gate resistor → TRIAC → motor
Plus RC snubber across each TRIAC.

Circuit per channel (left-to-right signal flow):
  DC side:
    +3V3 → MOC3021 pin1 (AN, anode)
    MOC3021 pin2 (CAT, cathode) → R_led (470Ω) → FWD_GATE/REV_GATE (active low)

  AC side:
    MOC3021 pin6 (MT) → R_gate (360Ω) → TRIAC Gate
    MOC3021 pin4 (MT) → TRIAC A1 → MOTOR_FWD/MOTOR_REV (hlabel)
    TRIAC A2 → AC_L (hlabel)
    Snubber: R_sn (100Ω) + C_sn (100nF) in series across A1-A2

Components per channel:
  Ux  - MOC3021S-TA1 (marklin-wifi-ctrl:MOC3021S-TA1), SMD-6P
  Qx  - BT136-600E (Device:Q_Triac), TO-252
  Rx  - 470Ω LED current-limit resistor, 0603
  Rx  - 360Ω gate resistor, 1206
  Rx  - 100Ω snubber resistor, 1206
  Cx  - 100nF/400V snubber cap

MOC3021S-TA1 pin positions in schematic (angle=0):
  pin1 (AN):  (cx-12.70, cy-5.08) [upper-left]
  pin2 (CAT): (cx-12.70, cy)      [mid-left]
  pin3 (NC):  (cx-12.70, cy+5.08) [lower-left]
  pin4 (MT):  (cx+12.70, cy+5.08) [lower-right]
  pin5 (SUB): (cx+12.70, cy)      [mid-right]
  pin6 (MT):  (cx+12.70, cy-5.08) [upper-right]

Device:Q_Triac pin positions in schematic (angle=0):
  G:  (cx-3.81, cy+2.54)  [lower-left]
  A2: (cx, cy-3.81)       [top]
  A1: (cx, cy+3.81)       [bottom]

Usage:
  python3 scripts/gen_triac_drive.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "f8d2bd66-e175-4605-8831-92b6c419f451"
SHEET_UUID = "8b0f51a7-1851-4853-b5c5-2621f7f57929"

# KiCad library paths
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"
PROJECT_LIB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "marklin-wifi-ctrl", "marklin-wifi-ctrl.kicad_sym",
)

# Output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl")
OUTFILE = os.path.join(PROJECT_DIR, "triac_drive.kicad_sch")


def add_channel(sb, cy, ch_name, gate_label, motor_label,
                u_ref, q_ref, r_led_ref, r_gate_ref, r_sn_ref, c_sn_ref,
                place_ac_l_hlabel=False):
    """Add one TRIAC drive channel centered at vertical position cy.

    Args:
        sb: SchematicBuilder instance
        cy: Vertical center of the channel
        ch_name: Channel name for net labels (e.g. "FWD", "REV")
        gate_label: Hierarchical label for gate input (e.g. "FWD_GATE")
        motor_label: Hierarchical label for motor output (e.g. "MOTOR_FWD")
        u_ref: MOC3021 reference designator
        q_ref: TRIAC reference designator
        r_led_ref, r_gate_ref, r_sn_ref: Resistor references
        c_sn_ref: Snubber cap reference
    """
    # ── MOC3021S-TA1 optocoupler ──
    moc_cx = 80
    sb.place_sym(
        "marklin-wifi-ctrl:MOC3021S-TA1", moc_cx, cy, 0,
        u_ref, "MOC3021S-TA1",
        "marklin-wifi-ctrl:SMD-6_L7.3-W6.5-P2.54-LS10.2-BL",
        ["1", "2", "3", "4", "5", "6"],
    )
    # MOC pin positions:
    moc_an  = (moc_cx - 12.70, cy - 5.08)  # pin1 AN (upper-left)
    moc_cat = (moc_cx - 12.70, cy)          # pin2 CAT (mid-left)
    moc_nc  = (moc_cx - 12.70, cy + 5.08)  # pin3 NC (lower-left)
    moc_mt4 = (moc_cx + 12.70, cy + 5.08)  # pin4 MT (lower-right)
    moc_sub = (moc_cx + 12.70, cy)          # pin5 SUB (mid-right)
    moc_mt6 = (moc_cx + 12.70, cy - 5.08)  # pin6 MT (upper-right)

    # +3V3 to MOC anode (pin1)
    sb.place_power("+3V3", *moc_an)

    # R_led: 470Ω, horizontal (angle=90) — cathode side
    # Centre at (moc_cat[0] - 15.24 - 3.81, moc_cat[1])
    # = (67.30 - 15.24 - 3.81, cy) = (48.25, cy)
    rled_cx = 48
    sb.place_sym(
        "Device:R", rled_cx, cy, 90,
        r_led_ref, "470R",
        "Resistor_SMD:R_0603_1608Metric",
        ["1", "2"],
    )
    # R_led pin1 at (rled_cx+3.81, cy) = (51.81, cy) → wire to MOC CAT
    # R_led pin2 at (rled_cx-3.81, cy) = (44.19, cy) → gate hlabel
    sb.add_wire(rled_cx + 3.81, cy, moc_cat[0], moc_cat[1])
    sb.add_hlabel(gate_label, rled_cx - 3.81, cy, 180, "input")

    # No-connects
    sb.add_no_connect(*moc_nc)   # pin3 NC
    sb.add_no_connect(*moc_sub)  # pin5 SUB

    # ── TRIAC (Device:Q_Triac) ──
    triac_cx = 145
    triac_cy = cy
    sb.place_sym(
        "Device:Q_Triac", triac_cx, triac_cy, 0,
        q_ref, "BT136-600E",
        "Package_TO_SOT_SMD:TO-252-2",
        ["G", "A2", "A1"],
    )
    # TRIAC pin positions:
    triac_g  = (triac_cx - 3.81, triac_cy + 2.54)   # Gate (lower-left)
    triac_a2 = (triac_cx, triac_cy - 3.81)           # A2 (top)
    triac_a1 = (triac_cx, triac_cy + 3.81)           # A1 (bottom)

    # ── Motor net: MOC pin4 → TRIAC A1, with hlabel ──
    # Horizontal bus at y = MOC pin4 level (cy+5.08)
    motor_bus_y = moc_mt4[1]
    sb.add_hlabel(motor_label, moc_mt4[0], moc_mt4[1], 0, "passive")
    # Wire from MOC pin4 to TRIAC A1 x, then up to A1
    sb.add_wire(moc_mt4[0], motor_bus_y, triac_a1[0], motor_bus_y)
    sb.add_wire(triac_a1[0], motor_bus_y, triac_a1[0], triac_a1[1])
    sb.add_junction(moc_mt4[0], motor_bus_y)  # hlabel + wire branch

    # ── AC_L net: TRIAC A2 (hlabel on first channel, net label otherwise) ──
    if place_ac_l_hlabel:
        sb.add_hlabel("AC_L", triac_a2[0], triac_a2[1], 0, "passive")
    else:
        sb.add_net_label("AC_L", triac_a2[0], triac_a2[1], 0)

    # ── R_gate: 360Ω, horizontal (angle=90) ──
    # Between MOC pin6 (upper-right) and TRIAC gate
    # MOC pin6 at (92.70, cy-5.08), TRIAC G at (141.19, cy+2.54)
    # Place R_gate between them, at y = cy-5.08 (same as MOC pin6)
    rgate_cx = 108
    rgate_y = cy - 5.08
    sb.place_sym(
        "Device:R", rgate_cx, rgate_y, 90,
        r_gate_ref, "360R",
        "Resistor_SMD:R_1206_3216Metric",
        ["1", "2"],
    )
    # R_gate pin2 at (104.19, rgate_y) ← wire from MOC pin6
    # R_gate pin1 at (111.81, rgate_y) → wire down to TRIAC gate
    sb.add_wire(moc_mt6[0], moc_mt6[1], rgate_cx - 3.81, rgate_y)
    # Wire from R_gate pin1 down to TRIAC gate: (111.81, rgate_y) → bend → (triac_g)
    rgate_out_x = rgate_cx + 3.81
    sb.add_wire(rgate_out_x, rgate_y, rgate_out_x, triac_g[1])
    sb.add_wire(rgate_out_x, triac_g[1], triac_g[0], triac_g[1])

    # ── Snubber: R_sn + C_sn in series across TRIAC ──
    # Place to the right of TRIAC, vertically between A2 (top) and A1 (bottom)
    sn_x = triac_cx + 20  # = 165
    sn_mid_y = cy  # midpoint between A2 and A1

    # R_sn vertical at (sn_x, cy-3): pin2 at top, pin1 at bottom
    rsn_cy = cy - 3
    sb.place_sym(
        "Device:R", sn_x, rsn_cy, 0,
        r_sn_ref, "100R",
        "Resistor_SMD:R_1206_3216Metric",
        ["1", "2"],
    )
    # R_sn pin2 (top) at (sn_x, rsn_cy-3.81) → wire to AC_L net (TRIAC A2)
    # R_sn pin1 (bottom) at (sn_x, rsn_cy+3.81) → wire to C_sn

    # C_sn vertical at (sn_x, cy+3): pin2 at top, pin1 at bottom
    csn_cy = cy + 3
    sb.place_sym(
        "Device:C", sn_x, csn_cy, 0,
        c_sn_ref, "100nF/400V",
        "Capacitor_SMD:C_1206_3216Metric",
        ["1", "2"],
    )
    # C_sn pin2 (top) at (sn_x, csn_cy-3.81) → wire from R_sn pin1
    # C_sn pin1 (bottom) at (sn_x, csn_cy+3.81) → wire to motor net
    sb.add_wire(sn_x, rsn_cy + 3.81, sn_x, csn_cy - 3.81)  # R_sn → C_sn

    # Snubber top (R_sn pin2) → TRIAC A2 (AC_L side) via wire
    rsn_top = (sn_x, rsn_cy - 3.81)
    sb.add_wire(triac_a2[0], triac_a2[1], sn_x, triac_a2[1])   # A2 right to snubber x
    sb.add_wire(sn_x, triac_a2[1], rsn_top[0], rsn_top[1])      # down to R_sn pin2
    sb.add_junction(triac_a2[0], triac_a2[1])  # hlabel/net_label also at A2

    # Snubber bottom (C_sn pin1) → motor bus via wire
    csn_bot = (sn_x, csn_cy + 3.81)
    sb.add_wire(triac_a1[0], motor_bus_y, sn_x, motor_bus_y)    # A1 bus right to snubber x
    sb.add_wire(sn_x, motor_bus_y, csn_bot[0], csn_bot[1])      # up to C_sn pin1
    sb.add_junction(triac_a1[0], motor_bus_y)  # MOC wire also at this point
    sb.add_junction(sn_x, motor_bus_y)         # snubber branch


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="TRIAC Drive",
        date="2026-03-10",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 5: MOC3021S + BT136 motor winding drive (x2)",
        page="8",
        pwr_start=800,
    )

    # ── Library symbols ──
    sb.add_lib("marklin-wifi-ctrl", PROJECT_LIB, ["MOC3021S-TA1"])
    sb.add_lib("Device", DEVICE_LIB, ["R", "C", "Q_Triac"])
    sb.add_lib("power", POWER_LIB, ["+3V3"])

    # ── Channel 1: Forward ── (upper half, cy=55)
    add_channel(
        sb, cy=55, ch_name="FWD",
        gate_label="FWD_GATE", motor_label="MOTOR_FWD",
        u_ref="U800", q_ref="Q800",
        r_led_ref="R800", r_gate_ref="R801",
        r_sn_ref="R802", c_sn_ref="C800",
        place_ac_l_hlabel=True,
    )

    # ── Channel 2: Reverse ── (lower half, cy=110)
    add_channel(
        sb, cy=110, ch_name="REV",
        gate_label="REV_GATE", motor_label="MOTOR_REV",
        u_ref="U801", q_ref="Q801",
        r_led_ref="R803", r_gate_ref="R804",
        r_sn_ref="R805", c_sn_ref="C801",
    )

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 5 (TRIAC Drive) schematic generated.")

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
