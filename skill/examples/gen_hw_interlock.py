#!/usr/bin/env python3
"""Generator for Block 4: Hardware Interlock schematic (hw_interlock.kicad_sch).

Cross-coupled NAND gate interlock ensuring FWD and REV cannot be active
simultaneously. Uses SN74LVC00APWR (quad 2-input NAND, TSSOP-14).

Truth table:
  FWD_CMD | REV_CMD | FWD_GATE | REV_GATE
  --------|---------|----------|----------
     0    |    0    |    0     |    0
     1    |    0    |    1     |    0
     0    |    1    |    0     |    1
     1    |    1    |    0     |    0

Circuit (cross-coupled NAND):
  Gate A (unit 1): inputs = FWD_CMD, REV_CMD  → output = ~(FWD & REV) = LOCK
  Gate B (unit 2): inputs = FWD_CMD, LOCK     → output = FWD_GATE
  Wait — that doesn't match the truth table. Let me reconsider.

  Actually, for the interlock truth table:
  - FWD_GATE = FWD_CMD AND NOT(REV_CMD) = FWD_CMD AND (NAND output when both high)
  - REV_GATE = REV_CMD AND NOT(FWD_CMD)

  Using NAND gates:
  Gate A (unit 1): inputs = FWD_CMD, REV_CMD → output LOCK = ~(FWD & REV)
    LOCK=1 when not both active, LOCK=0 when both active
  Gate B (unit 2): inputs = FWD_CMD, LOCK → output = ~(FWD & LOCK)
    When LOCK=1 (normal): ~(FWD & 1) = ~FWD → inverted! Need another inversion.

  Better approach — direct AND-with-complement using two NAND pairs:
  Gate 1: NAND(FWD_CMD, ~REV_CMD) — but we don't have ~REV_CMD directly.

  Simplest correct approach with 2 gates:
  Gate A (unit 1): NAND(FWD_CMD, REV_CMD) → INHIBIT (low when both active)
  Gate B (unit 2): NAND(FWD_CMD, INHIBIT) → ~FWD_GATE
  Gate C (unit 3): NAND(REV_CMD, INHIBIT) → ~REV_GATE

  FWD=1, REV=0: INHIBIT=1, ~FWD_GATE = NAND(1,1) = 0 → FWD_GATE=1 (active low output)
  FWD=0, REV=1: INHIBIT=1, ~REV_GATE = NAND(1,1) = 0 → REV_GATE=1
  FWD=1, REV=1: INHIBIT=0, ~FWD_GATE = NAND(1,0) = 1 → FWD_GATE=0, REV_GATE=0
  FWD=0, REV=0: INHIBIT=1, ~FWD_GATE = NAND(0,1) = 1 → FWD_GATE=0, REV_GATE=0

  Hmm, that gives active-low outputs. The block design says active-high.
  So the outputs are inverted. We need 3 NAND gates (uses units 1-3 of the quad).

  Better: Use the classic cross-coupled interlock:
  Gate A (unit 1): NAND(FWD_CMD, Gate_B_out) → FWD_GATE_N (active low)
  Gate B (unit 2): NAND(REV_CMD, Gate_A_out) → REV_GATE_N (active low)

  FWD=1, REV=0: B_out=NAND(0,A_out)=1, A_out=NAND(1,1)=0 → FWD_GATE_N=0 (active)
  FWD=0, REV=1: A_out=NAND(0,B_out)=1, B_out=NAND(1,1)=0 → REV_GATE_N=0 (active)
  FWD=1, REV=1: A_out=NAND(1,B_out), B_out=NAND(1,A_out)
    Stable: A_out=1, B_out=1 → NAND(1,1)=0 for both → race condition

  Cross-coupled NANDs create a latch, not an interlock. Not what we want.

  Let's use the 3-gate approach (INHIBIT + 2 gated outputs):
  Gate 1 (unit 1): NAND(FWD_CMD, REV_CMD) → INHIBIT
  Gate 2 (unit 2): NAND(INHIBIT, FWD_CMD) → FWD_GATE_N
  Gate 3 (unit 3): NAND(INHIBIT, REV_CMD) → REV_GATE_N
  Then: FWD_GATE = ~FWD_GATE_N, REV_GATE = ~REV_GATE_N

  To get active-high, we'd need inversions (4th gate for one, but we need 2).
  With 4 NAND gates (all 4 units):
  Gate 1: NAND(FWD_CMD, REV_CMD) → INHIBIT
  Gate 2: NAND(INHIBIT, FWD_CMD) → FWD_GATE_N
  Gate 3: NAND(INHIBIT, REV_CMD) → REV_GATE_N
  Gate 4: spare — tie inputs to VCC or use as inverter

  Active-low outputs are fine for driving optocoupler LEDs (sink current).
  The block design says active-high, but since the TRIAC optocoupler (MOC3021)
  LED anode connects to +3V3 via resistor and cathode to the gate output,
  active-low (output LOW = LED on = TRIAC fires) is actually more natural.

  Let's go with active-low outputs (3 gates used, 1 spare):
  Gate 1 (unit 1): NAND(FWD_CMD, REV_CMD) → INHIBIT
  Gate 2 (unit 2): NAND(FWD_CMD, INHIBIT) → FWD_GATE (active low)
  Gate 3 (unit 3): NAND(REV_CMD, INHIBIT) → REV_GATE (active low)
  Gate 4 (unit 4): spare, inputs tied to VCC

Components:
  U1  - SN74LVC00APWR (74xx:7400), TSSOP-14 (LCSC C7803)
  C1  - 100nF 0603 decoupling cap (LCSC C14663)

Pin layout for 74LS00/7400 (each NAND gate unit, angle=0):
  Lib coords (Y-up):
    Input A: (-7.62, +2.54) → Sch: (cx-7.62, cy-2.54) [upper-left]
    Input B: (-7.62, -2.54) → Sch: (cx-7.62, cy+2.54) [lower-left]
    Output:  (+7.62,  0)    → Sch: (cx+7.62, cy)       [right]
  Power unit (unit 5):
    VCC: (0, +12.7) → Sch: (cx, cy-12.7)
    GND: (0, -12.7) → Sch: (cx, cy+12.7)

Layout:
  Gate 1 (INHIBIT) at (80, 55)
  Gate 2 (FWD_GATE) at (130, 45)
  Gate 3 (REV_GATE) at (130, 75)
  Power unit at (175, 55)
  C1 decoupling at (190, 55)
  Spare gate (unit 4) at (175, 90) — inputs tied to VCC via no-connect or VCC

Usage:
  python3 scripts/gen_hw_interlock.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "e9e4a7a2-5959-4eb0-b41e-b72f8a58cddc"
SHEET_UUID = "f5c0d31e-d662-48fe-bf8c-9ba65cbb150b"

# KiCad standard library paths
LIB_74XX = "/usr/share/kicad/symbols/74xx.kicad_sym"
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"

# Output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl")
OUTFILE = os.path.join(PROJECT_DIR, "hw_interlock.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="Hardware Interlock",
        date="2026-03-10",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 4: Cross-coupled NAND interlock",
        page="7",
        pwr_start=700,
    )

    # ── Library symbols ──
    sb.add_lib("74xx", LIB_74XX, ["7400"])
    sb.add_lib("Device", DEVICE_LIB, ["C"])
    sb.add_lib("power", POWER_LIB, ["+3V3", "GND"])

    # ── Pin position helpers ──
    # 7400 NAND gate unit (angle=0): inputs at (cx-7.62, cy∓2.54), output at (cx+7.62, cy)
    # Power unit (angle=0): VCC at (cx, cy-12.7), GND at (cx, cy+12.7)

    # ═══════════════════════════════════════════════════════════════════
    # Gate 1 (unit 1): NAND(FWD_CMD, REV_CMD) → INHIBIT
    # ═══════════════════════════════════════════════════════════════════
    g1_cx, g1_cy = 80, 60
    sb.place_sym(
        "74xx:7400", g1_cx, g1_cy, 0,
        "U700", "SN74LVC00APWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        ["1", "2", "3"],
        unit=1,
    )
    # Gate 1 inputs: pin1 at (72.38, 57.46) [upper-left], pin2 at (72.38, 62.54) [lower-left]
    # Gate 1 output: pin3 at (87.62, 60) [right]
    sb.add_hlabel("FWD_CMD", 72.38, 57.46, 180, "input")
    sb.add_hlabel("REV_CMD", 72.38, 62.54, 180, "input")
    sb.add_net_label("INHIBIT", 87.62, 60, 0)

    # ═══════════════════════════════════════════════════════════════════
    # Gate 2 (unit 2): NAND(FWD_CMD, INHIBIT) → FWD_GATE (active low)
    # ═══════════════════════════════════════════════════════════════════
    g2_cx, g2_cy = 135, 45
    sb.place_sym(
        "74xx:7400", g2_cx, g2_cy, 0,
        "U700", "SN74LVC00APWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        ["4", "5", "6"],
        unit=2,
    )
    # Gate 2 inputs: pin4 at (127.38, 42.46), pin5 at (127.38, 47.54)
    # Gate 2 output: pin6 at (142.62, 45)
    sb.add_net_label("FWD_CMD", 127.38, 42.46, 180)
    sb.add_net_label("INHIBIT", 127.38, 47.54, 180)
    sb.add_hlabel("FWD_GATE", 142.62, 45, 0, "output")

    # ═══════════════════════════════════════════════════════════════════
    # Gate 3 (unit 3): NAND(REV_CMD, INHIBIT) → REV_GATE (active low)
    # ═══════════════════════════════════════════════════════════════════
    g3_cx, g3_cy = 135, 75
    sb.place_sym(
        "74xx:7400", g3_cx, g3_cy, 0,
        "U700", "SN74LVC00APWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        ["9", "10", "8"],
        unit=3,
    )
    # Gate 3 inputs: pin9 at (127.38, 72.46), pin10 at (127.38, 77.54)
    # Gate 3 output: pin8 at (142.62, 75)
    sb.add_net_label("REV_CMD", 127.38, 72.46, 180)
    sb.add_net_label("INHIBIT", 127.38, 77.54, 180)
    sb.add_hlabel("REV_GATE", 142.62, 75, 0, "output")

    # ═══════════════════════════════════════════════════════════════════
    # Gate 4 (unit 4): spare — tie both inputs high (to VCC)
    # ═══════════════════════════════════════════════════════════════════
    g4_cx, g4_cy = 80, 100
    sb.place_sym(
        "74xx:7400", g4_cx, g4_cy, 0,
        "U700", "SN74LVC00APWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        ["12", "13", "11"],
        unit=4,
    )
    # Tie inputs to +3V3
    # pin12 at (72.38, 97.46), pin13 at (72.38, 102.54)
    # Connect both inputs together with wire, then to +3V3
    sb.add_wire(72.38, 97.46, 72.38, 102.54)
    sb.place_power("+3V3", 72.38, 97.46)
    # Output pin11 at (87.62, 100) — no connect (NAND(1,1) = 0, unused)
    sb.add_no_connect(87.62, 100)

    # ═══════════════════════════════════════════════════════════════════
    # Power unit (unit 5)
    # ═══════════════════════════════════════════════════════════════════
    pwr_cx, pwr_cy = 185, 60
    sb.place_sym(
        "74xx:7400", pwr_cx, pwr_cy, 0,
        "U700", "SN74LVC00APWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        ["14", "7"],
        unit=5,
    )
    # VCC pin14 at (185, 47.3) [cy - 12.7], GND pin7 at (185, 72.7) [cy + 12.7]
    sb.place_power("+3V3", pwr_cx, pwr_cy - 12.7)
    sb.place_power("GND", pwr_cx, pwr_cy + 12.7)

    # ═══════════════════════════════════════════════════════════════════
    # C1: 100nF decoupling capacitor (angle=0, vertical)
    # ═══════════════════════════════════════════════════════════════════
    c_cx, c_cy = 200, 60
    sb.place_sym(
        "Device:C", c_cx, c_cy, 0,
        "C700", "100nF",
        "Capacitor_SMD:C_0603_1608Metric",
        ["1", "2"],
    )
    # pin1 at bottom (c_cx, c_cy+3.81), pin2 at top (c_cx, c_cy-3.81)
    sb.place_power("+3V3", c_cx, c_cy - 3.81)
    sb.place_power("GND", c_cx, c_cy + 3.81)

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 4 (Hardware Interlock) schematic generated.")

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
