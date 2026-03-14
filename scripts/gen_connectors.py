#!/usr/bin/env python3
"""Generator for Block 9: Connectors schematic (connectors.kicad_sch).

Physical interface to the track and motor windings. All connections are
solder pads (2mm test points) — connectors are too large for the locomotive.

Components:
  TP1 - AC_L track input pad
  TP2 - AC_N track input pad
  TP3 - MOTOR_COM motor common pad (tied to AC_N)
  TP4 - MOTOR_FWD motor forward winding pad
  TP5 - MOTOR_REV motor reverse winding pad

Interfaces (hierarchical labels):
  AC_L      - output (passive) to blocks 1, 3, 5, 6
  AC_N      - output (passive) to blocks 1, 3, 5, 6
  MOTOR_FWD - input (passive) from TRIAC drive (block 5)
  MOTOR_REV - input (passive) from TRIAC drive (block 5)

Note: MOTOR_COM (TP3) is tied to AC_N via a local net label.

Connector:TestPoint pin position: (at 0 0 90) — pin is at symbol centre,
so connection point = placement point regardless of rotation.

Layout:
  Track Input (left):                Motor Output (right):
    TP1 at (70, 70) → AC_L            TP4 at (160, 70) → MOTOR_FWD
    TP2 at (70, 85) → AC_N            TP5 at (160, 85) → MOTOR_REV
                                       TP3 at (160, 100) → AC_N (MOTOR_COM)

Usage:
  python3 scripts/gen_connectors.py
"""

import os
import sys

# Add scripts directory to path for import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "de86a9ab-4197-4432-a4b5-3b4e90ab8bdd"
SHEET_UUID = "e7d4416b-523d-41c2-a3ba-90336c47cd47"

# KiCad standard library paths
CONN_LIB = "/usr/share/kicad/symbols/Connector.kicad_sym"

# Output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl")
OUTFILE = os.path.join(PROJECT_DIR, "connectors.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="Connectors",
        date="2026-03-10",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 9: Track input and motor output connectors",
        page="2",
        pwr_start=200,
    )

    # ── Library symbols ──
    sb.add_lib("Connector", CONN_LIB, ["TestPoint"])

    # ── Track Input Section (left side) ──
    # TP1: AC_L track input
    # TestPoint pin at (cx, cy) — connection point is symbol centre
    sb.place_sym(
        "Connector:TestPoint", 70, 70, 0,
        "TP200", "AC_L",
        "TestPoint:TestPoint_Pad_2.0x2.0mm",
        ["1"],
    )
    # Hierarchical label at pin (70, 70), extending left (angle=180)
    sb.add_hlabel("AC_L", 70, 70, 180, "passive")

    # TP2: AC_N track input
    sb.place_sym(
        "Connector:TestPoint", 70, 85, 0,
        "TP201", "AC_N",
        "TestPoint:TestPoint_Pad_2.0x2.0mm",
        ["1"],
    )
    sb.add_hlabel("AC_N", 70, 85, 180, "passive")

    # ── Motor Output Section (right side) ──
    # TP4: MOTOR_FWD
    sb.place_sym(
        "Connector:TestPoint", 160, 70, 0,
        "TP203", "MOTOR_FWD",
        "TestPoint:TestPoint_Pad_2.0x2.0mm",
        ["1"],
    )
    sb.add_hlabel("MOTOR_FWD", 160, 70, 0, "passive")

    # TP5: MOTOR_REV
    sb.place_sym(
        "Connector:TestPoint", 160, 85, 0,
        "TP204", "MOTOR_REV",
        "TestPoint:TestPoint_Pad_2.0x2.0mm",
        ["1"],
    )
    sb.add_hlabel("MOTOR_REV", 160, 85, 0, "passive")

    # TP3: MOTOR_COM (tied to AC_N)
    sb.place_sym(
        "Connector:TestPoint", 160, 100, 0,
        "TP202", "MOTOR_COM",
        "TestPoint:TestPoint_Pad_2.0x2.0mm",
        ["1"],
    )
    # Connect MOTOR_COM to AC_N net using a net label
    # (only one hlabel per net per sheet — AC_N hlabel already at TP201)
    sb.add_net_label("AC_N", 160, 100, 0)

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 9 (Connectors) schematic generated.")

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
