#!/usr/bin/env python3
"""Generator for top-level marklin-wifi-ctrl.kicad_sch.

Regenerates the root schematic with hierarchical sheet frames including
sheet pins matching each sub-sheet's hierarchical labels, plus global
labels routing inter-sheet signals.

All coordinates are on the 2.54mm (100-mil) KiCad grid.

Based on the pattern from the traincontrol-shield reference scripts.

Usage:
  python3 scripts/gen_top_level.py
"""

import os
import uuid as _uuid

# ── Project constants ──
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
STUB = 7.62

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl")
OUTFILE = os.path.join(PROJECT_DIR, "marklin-wifi-ctrl.kicad_sch")


def u():
    return str(_uuid.uuid4())


def wire(x1, y1, x2, y2):
    return (f'\t(wire\n\t\t(pts (xy {x1} {y1}) (xy {x2} {y2}))\n'
            f'\t\t(stroke (width 0) (type solid))\n\t\t(uuid "{u()}")\n\t)')


def glabel(name, x, y, angle, shape="bidirectional"):
    """Global label with a wire stub (STUB mm)."""
    just = "right" if angle == 180 else "left"
    dx = STUB if angle == 180 else -STUB
    lx = x + dx
    label = (f'\t(global_label "{name}"\n\t\t(shape {shape})\n'
             f'\t\t(at {x} {y} {angle})\n\t\t(fields_autoplaced yes)\n'
             f'\t\t(effects (font (size 1.27 1.27)) (justify {just} bottom))\n'
             f'\t\t(uuid "{u()}")\n\t)')
    return wire(min(x, lx), y, max(x, lx), y) + '\n' + label


def sheet_frame(sinst_uuid, filename, sheetname, page, x, y, w, h, pins=None):
    """Generate a hierarchical sheet frame with optional pins."""
    pins_str = ""
    if pins:
        for (pname, pshape, bx, by, pangle) in pins:
            just = "right" if pangle == 0 else "left"
            pins_str += (
                f'\t\t(pin "{pname}" {pshape}\n'
                f'\t\t\t(at {bx} {by} {pangle})\n'
                f'\t\t\t(effects (font (size 1.27 1.27)) (justify {just}))\n'
                f'\t\t\t(uuid "{u()}")\n'
                f'\t\t)\n'
            )
    return (f'\t(sheet\n'
            f'\t\t(at {x} {y})\n'
            f'\t\t(size {w} {h})\n'
            f'\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom yes)\n'
            f'\t\t(on_board yes)\n'
            f'\t\t(dnp no)\n'
            f'\t\t(fields_autoplaced yes)\n'
            f'\t\t(stroke (width 0.1524) (type solid))\n'
            f'\t\t(fill (color 0 0 0 0.0000))\n'
            f'\t\t(uuid "{sinst_uuid}")\n'
            f'\t\t(property "Sheetname" "{sheetname}"\n'
            f'\t\t\t(at {x} {y - 1.27} 0)\n'
            f'\t\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'\t\t)\n'
            f'\t\t(property "Sheetfile" "{filename}"\n'
            f'\t\t\t(at {x} {y + h + 1.27} 0)\n'
            f'\t\t\t(effects (font (size 1.27 1.27)) (justify left top) hide)\n'
            f'\t\t)\n'
            f'{pins_str}'
            f'\t\t(instances\n'
            f'\t\t\t(project "{PROJECT_NAME}"\n'
            f'\t\t\t\t(path "/{ROOT_UUID}"\n'
            f'\t\t\t\t\t(page "{page}")\n'
            f'\t\t\t\t)\n'
            f'\t\t\t)\n'
            f'\t\t)\n'
            f'\t)')


def main():
    # ── Sheet instance UUIDs (from existing root schematic) ──
    SINST = {
        "connectors":    "de86a9ab-4197-4432-a4b5-3b4e90ab8bdd",
        "power_supply":  "69aebb0f-a53c-4668-9eb1-5471b8889188",
        "esp32_c3":      "0246fff8-dcb8-478e-b397-3f68718ca88d",
        "zero_crossing": "12425cfa-6061-40dc-bca8-eb9456dd8125",
        "voltage_sense": "3a9adae2-2f5f-4e75-8e72-e9b71c8f8c82",
        "hw_interlock":  "e9e4a7a2-5959-4eb0-b41e-b72f8a58cddc",
        "triac_drive":   "f8d2bd66-e175-4605-8831-92b6c419f451",
        "status_led":    "0eb1c17e-9b3c-4b80-9a2a-c332b3f136dd",
        "usb_prog":      "c8642268-bd1f-47bb-9d74-30221e4beffb",
    }

    # ── Layout: 3-column grid on A3 ──
    # ALL coordinates on 2.54mm grid (multiples of 2.54)
    # Inter-column gap must accommodate: 2×STUB + global label text (~12mm each)
    # Minimum: 2×7.62 + 2×12 ≈ 40mm. Use 45.72mm for comfortable spacing.
    W = 45.72       # box width (18 × 2.54)
    GAP = 45.72     # inter-column gap (18 × 2.54) — room for labels
    X1 = 25.4       # col 1 left (10 × 2.54)
    R1 = X1 + W     # 71.12
    X2 = R1 + GAP   # 116.84
    R2 = X2 + W     # 162.56
    X3 = R2 + GAP   # 208.28
    R3 = X3 + W     # 254.00

    Y1 = 25.4       # row 1 top (10 × 2.54)
    Y2 = 96.52      # row 2 top (38 × 2.54) — more vertical space
    Y3 = 157.48     # row 3 top (62 × 2.54)

    # Box heights (multiples of 2.54, sized for pin count)
    H_conn  = 30.48  # 12 × 2.54 — 4 pins
    H_psu   = 20.32  #  8 × 2.54 — 2 pins
    H_esp   = 50.8   # 20 × 2.54 — 7 pins
    H_zc    = 25.4   # 10 × 2.54 — 3 pins
    H_vs    = 25.4   # 10 × 2.54 — 3 pins
    H_il    = 30.48  # 12 × 2.54 — 4 pins
    H_triac = 40.64  # 16 × 2.54 — 5 pins
    H_led   = 15.24  #  6 × 2.54 — 1 pin
    H_usb   = 20.32  #  8 × 2.54 — 2 pins

    # Pin spacing: 5.08mm (2 × 2.54) between pins, first at y + 5.08

    PINS_CONN = [
        ("AC_L",      "passive", R1, Y1 + 5.08,  0),
        ("AC_N",      "passive", R1, Y1 + 10.16, 0),
        ("MOTOR_FWD", "passive", R1, Y1 + 20.32, 0),
        ("MOTOR_REV", "passive", R1, Y1 + 25.4,  0),
    ]
    PINS_PSU = [
        ("AC_L", "passive", X2, Y1 + 5.08,  180),
        ("AC_N", "passive", X2, Y1 + 10.16, 180),
    ]
    PINS_ESP = [
        ("FWD_CMD",  "output",        X3,  Y1 + 5.08,  180),
        ("REV_CMD",  "output",        X3,  Y1 + 10.16, 180),
        ("ZC_PULSE", "input",         X3,  Y1 + 15.24, 180),
        ("V_SENSE",  "input",         X3,  Y1 + 20.32, 180),
        ("LED_CTRL", "output",        R3,  Y1 + 5.08,  0),
        ("USB_D-",   "bidirectional", R3,  Y1 + 10.16, 0),
        ("USB_D+",   "bidirectional", R3,  Y1 + 15.24, 0),
    ]
    PINS_ZC = [
        ("AC_L",     "input",  X1, Y2 + 5.08,  180),
        ("AC_N",     "input",  X1, Y2 + 10.16, 180),
        ("ZC_PULSE", "output", R1, Y2 + 5.08,  0),
    ]
    PINS_VS = [
        ("AC_L",    "input",  X2, Y2 + 5.08,  180),
        ("AC_N",    "input",  X2, Y2 + 10.16, 180),
        ("V_SENSE", "output", R2, Y2 + 5.08,  0),
    ]
    PINS_IL = [
        ("FWD_CMD",  "input",  X3,  Y2 + 5.08,  180),
        ("REV_CMD",  "input",  X3,  Y2 + 10.16, 180),
        ("FWD_GATE", "output", R3,  Y2 + 5.08,  0),
        ("REV_GATE", "output", R3,  Y2 + 10.16, 0),
    ]
    PINS_TRIAC = [
        ("FWD_GATE",  "input",   X1, Y3 + 5.08,  180),
        ("REV_GATE",  "input",   X1, Y3 + 10.16, 180),
        ("AC_L",      "passive", X1, Y3 + 15.24, 180),
        ("MOTOR_FWD", "passive", R1, Y3 + 25.4,  0),
        ("MOTOR_REV", "passive", R1, Y3 + 30.48, 0),
    ]
    PINS_LED = [
        ("LED_CTRL", "input", X2, Y3 + 5.08, 180),
    ]
    PINS_USB = [
        ("USB_D-", "bidirectional", X3,  Y3 + 5.08,  180),
        ("USB_D+", "bidirectional", X3,  Y3 + 10.16, 180),
    ]

    # ── Build sheet frames ──
    E = []
    frames = [
        (SINST["connectors"],    "connectors.kicad_sch",    "Connectors",             "2",  X1, Y1, W, H_conn,  PINS_CONN),
        (SINST["power_supply"],  "power_supply.kicad_sch",  "Power Supply",           "3",  X2, Y1, W, H_psu,   PINS_PSU),
        (SINST["esp32_c3"],      "esp32_c3.kicad_sch",      "ESP32-C3 MCU",           "4",  X3, Y1, W, H_esp,   PINS_ESP),
        (SINST["zero_crossing"], "zero_crossing.kicad_sch", "Zero-Crossing Detector", "5",  X1, Y2, W, H_zc,    PINS_ZC),
        (SINST["voltage_sense"], "voltage_sense.kicad_sch", "Voltage Sensing",        "6",  X2, Y2, W, H_vs,    PINS_VS),
        (SINST["hw_interlock"],  "hw_interlock.kicad_sch",  "Hardware Interlock",      "7",  X3, Y2, W, H_il,    PINS_IL),
        (SINST["triac_drive"],   "triac_drive.kicad_sch",   "TRIAC Drive",            "8",  X1, Y3, W, H_triac, PINS_TRIAC),
        (SINST["status_led"],    "status_led.kicad_sch",    "Status LED",             "9",  X2, Y3, W, H_led,   PINS_LED),
        (SINST["usb_prog"],      "usb_prog.kicad_sch",      "USB Programming",        "10", X3, Y3, W, H_usb,   PINS_USB),
    ]
    for sinst, fn, name, pg, x, y, w, h, pins in frames:
        E.append(sheet_frame(sinst, fn, name, pg, x, y, w, h, pins))

    # ── Global labels connecting sheet pins ──
    # For each sheet pin, place a global label with wire stub at the border.
    # Pin exits RIGHT (angle=0): glabel at (bx + STUB, by) facing right (angle=0)
    # Pin exits LEFT (angle=180): glabel at (bx - STUB, by) facing left (angle=180)

    all_pin_lists = [
        PINS_CONN, PINS_PSU, PINS_ESP, PINS_ZC, PINS_VS,
        PINS_IL, PINS_TRIAC, PINS_LED, PINS_USB,
    ]
    for pin_list in all_pin_lists:
        for (pname, pshape, bx, by, pangle) in pin_list:
            if pangle == 0:
                E.append(glabel(pname, bx + STUB, by, 0, "bidirectional"))
            else:
                E.append(glabel(pname, bx - STUB, by, 180, "bidirectional"))

    # ── Assemble root schematic ──
    body = "\n".join(E)
    sinst = ('\t(sheet_instances\n'
             '\t\t(path "/"\n'
             '\t\t\t(page "1")\n'
             '\t\t)\n'
             '\t)')

    content = (f'(kicad_sch\n'
               f'\t(version 20250114)\n'
               f'\t(generator "eeschema")\n'
               f'\t(generator_version "9.0")\n'
               f'\t(uuid "{ROOT_UUID}")\n'
               f'\t(paper "A3")\n'
               f'\t(title_block\n'
               f'\t\t(title "Marklin WiFi AC Train Controller")\n'
               f'\t\t(date "2026-03-11")\n'
               f'\t\t(rev "0.1")\n'
               f'\t\t(company "ZID AB")\n'
               f'\t\t(comment 1 "Author: PA Nilsson")\n'
               f'\t\t(comment 2 "Top-level hierarchy sheet")\n'
               f'\t)\n'
               f'\t(lib_symbols)\n'
               f'{body}\n'
               f'{sinst}\n'
               f'\t(embedded_fonts no)\n'
               f')')

    with open(OUTFILE, "w") as f:
        f.write(content)
    print(f"Written {len(content):6d} bytes -> {OUTFILE}")
    print("Top-level schematic generated.")

    # Verify
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
