#!/usr/bin/env python3
"""Generator for Block 2: ESP32-C3 MCU schematic (esp32_c3.kicad_sch).

Central controller with WiFi, GPIOs for motor control, zero-crossing input,
voltage sense ADC, USB programming interface, and status LED output.

Components:
  U1   - ESP32-C3-MINI-1-N4 module (LCSC C2838502)
  C1   - 10uF/10V bulk decoupling (LCSC C15850)
  C2   - 10uF/10V bulk decoupling (LCSC C15850)
  C3   - 100nF/25V HF decoupling (LCSC C14663)
  C4   - 100nF/25V HF decoupling (LCSC C14663)
  C5   - 100nF/25V HF decoupling (LCSC C14663)
  C6   - 100nF/25V HF decoupling (LCSC C14663)
  C7   - 100nF EN pin RC delay (LCSC C14663)
  R1   - 10K EN pull-up (LCSC C25804)
  R2   - 10K GPIO9 boot pull-up (LCSC C25804)
  SW1  - Reset button (EN pin, active-low) (LCSC C2886620)
  SW2  - Boot button (GPIO9, active-low) (LCSC C2886620)

ESP32-C3-MINI-1-N4 pin positions in schematic (angle=0):
  All left-side pins at (cx - 11.43, cy - lib_y), angle=0
  All right-side pins at (cx + 11.43, cy - lib_y), angle=180
  Module spans 66.04mm vertically (lib_y from -33.02 to +33.02)

GPIO assignments:
  IO0  (pin 12) - ZC_PULSE input (interrupt)
  IO1  (pin 13) - V_SENSE ADC input
  IO2  (pin  5) - FWD_CMD output
  IO3  (pin  6) - REV_CMD output
  IO4  (pin 18) - LED_CTRL output
  IO18 (pin 26) - USB_DN
  IO19 (pin 27) - USB_DP
  EN   (pin  8) - Reset (pull-up + button + cap)
  IO9  (pin 23) - Boot select (pull-up + button)

Usage:
  python3 scripts/gen_esp32_c3.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sch_gen import SchematicBuilder

# Project constants
PROJECT_NAME = "marklin-wifi-ctrl"
ROOT_UUID = "5dc91ac1-0911-4dbb-9ad6-5d1b9efb7191"
SHEET_INST_UUID = "0246fff8-dcb8-478e-b397-3f68718ca88d"
SHEET_UUID = "e7fe1344-e18c-40fc-bdbc-6cdaafe84f2c"

# KiCad library paths
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
POWER_LIB = "/usr/share/kicad/symbols/power.kicad_sym"
SWITCH_LIB = "/usr/share/kicad/symbols/Switch.kicad_sym"
PROJECT_LIB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "marklin-wifi-ctrl", "marklin-wifi-ctrl.kicad_sym",
)

# Output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "marklin-wifi-ctrl")
OUTFILE = os.path.join(PROJECT_DIR, "esp32_c3.kicad_sch")


def main():
    sb = SchematicBuilder(
        project_name=PROJECT_NAME,
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="ESP32-C3 MCU",
        date="2026-03-11",
        rev="0.1",
        company="ZID AB",
        author="PA Nilsson",
        comment2="Block 2: ESP32-C3-MINI-1 central controller",
        page="4",
        pwr_start=400,
    )

    # ── Library symbols ──
    sb.add_lib("marklin-wifi-ctrl", PROJECT_LIB, ["ESP32-C3-MINI-1-N4"])
    sb.add_lib("Device", DEVICE_LIB, ["R", "C"])
    sb.add_lib("Switch", SWITCH_LIB, ["SW_Push"])
    sb.add_lib("power", POWER_LIB, ["+3V3", "GND"])

    # ═══════════════════════════════════════════════════════════════════
    # U1: ESP32-C3-MINI-1-N4 at (130, 90)
    # ═══════════════════════════════════════════════════════════════════
    cx, cy = 130, 90
    lx = cx - 11.43   # 118.57 — left pin x
    rx = cx + 11.43   # 141.43 — right pin x

    sb.place_sym(
        "marklin-wifi-ctrl:ESP32-C3-MINI-1-N4", cx, cy, 0,
        "U400", "ESP32-C3-MINI-1-N4",
        "marklin-wifi-ctrl:WIFIM-SMD_ESP32-C3-MINI-1",
        [str(i) for i in range(1, 54)],
    )

    # ── Pin position helper ──
    # Left pins (lib angle=0): sch = (lx, cy - lib_y)
    # Right pins (lib angle=180): sch = (rx, cy - lib_y)
    # lib_y values from symbol extraction:
    left_pins = {
        1:  ("GND",  30.48),  2:  ("GND",  27.94),  3:  ("3V3",  25.40),
        4:  ("NC",   22.86),  5:  ("IO2",  20.32),  6:  ("IO3",  17.78),
        7:  ("NC",   15.24),  8:  ("EN",   12.70),  9:  ("NC",   10.16),
        10: ("NC",    7.62), 11:  ("GND",   5.08), 12:  ("IO0",   2.54),
        13: ("IO1",   0.00), 14:  ("GND",  -2.54), 15:  ("NC",   -5.08),
        16: ("IO10", -7.62), 17:  ("NC",  -10.16), 18:  ("IO4", -12.70),
        19: ("IO5", -15.24), 20:  ("IO6", -17.78), 21:  ("IO7", -20.32),
        22: ("IO8", -22.86), 23:  ("IO9", -25.40), 24:  ("NC",  -27.94),
        25: ("NC",  -30.48), 26:  ("IO18",-33.02),
    }
    right_pins = {
        27: ("IO19",-33.02), 28: ("NC",  -30.48), 29: ("NC",  -27.94),
        30: ("RXD0",-25.40), 31: ("TXD0",-22.86), 32: ("NC",  -20.32),
        33: ("NC",  -17.78), 34: ("NC",  -15.24), 35: ("NC",  -12.70),
        36: ("GND", -10.16), 37: ("GND",  -7.62), 38: ("GND",  -5.08),
        39: ("GND",  -2.54), 40: ("GND",   0.00), 41: ("GND",   2.54),
        42: ("GND",   5.08), 43: ("GND",   7.62), 44: ("GND",  10.16),
        45: ("GND",  12.70), 46: ("GND",  15.24), 47: ("GND",  17.78),
        48: ("GND",  20.32), 49: ("GND",  22.86), 50: ("GND",  25.40),
        51: ("GND",  27.94), 52: ("GND",  30.48), 53: ("GND",  33.02),
    }

    def lpin(num):
        """Return schematic (x, y) for a left-side pin."""
        _, lib_y = left_pins[num]
        return (lx, cy - lib_y)

    def rpin(num):
        """Return schematic (x, y) for a right-side pin."""
        _, lib_y = right_pins[num]
        return (rx, cy - lib_y)

    # ── Left-side GND pins (1, 2, 11, 14) ──
    # Wire each horizontally LEFT to clear the IC, then place GND symbol.
    # IMPORTANT: Adjacent GND pins share a vertical bus to avoid overlapping
    # collinear wire stubs (KiCad GUI merges overlapping wires, losing
    # intermediate pin endpoints).
    STUB = 7.62
    gnd_col = lx - 2 * STUB  # x column for GND stubs (left of hlabels)

    # Group 1: pins 1, 2 (adjacent — stubs would overlap)
    for p in [1, 2]:
        px, py = lpin(p)
        sb.add_wire(px, py, gnd_col, py)
    p1_y = lpin(1)[1]
    p2_y = lpin(2)[1]
    sb.add_wire(gnd_col, p1_y, gnd_col, p2_y)  # vertical bus
    sb.place_power("GND", gnd_col, p2_y)        # single GND below pin 2
    sb.add_junction(gnd_col, p2_y)               # T-junction for pin 2 wire

    # Group 2: pins 11, 14 (adjacent — share endpoint, use bus for safety)
    for p in [11, 14]:
        px, py = lpin(p)
        sb.add_wire(px, py, gnd_col, py)
    p11_y = lpin(11)[1]
    p14_y = lpin(14)[1]
    sb.add_wire(gnd_col, p11_y, gnd_col, p14_y)  # vertical bus
    sb.place_power("GND", gnd_col, p14_y)         # single GND below pin 14
    sb.add_junction(gnd_col, p14_y)                # T-junction for pin 14 wire

    # ── +3V3 on pin 3 ──
    # Wire LEFT first — stub going UP would cross GND pins 1,2 above
    v33_col = lx - 2 * STUB - 2.54  # x column for +3V3 (clear of cap row at x≈95)
    p3x, p3y = lpin(3)
    sb.add_wire(p3x, p3y, v33_col, p3y)
    sb.place_power("+3V3", v33_col, p3y)

    # ── Right-side GND bus (pins 36–53) ──
    # Individual wire segments between each pair of adjacent GND pins
    # (a single long wire doesn't reliably connect mid-point pins)
    gnd_pins_r = list(range(53, 35, -1))  # 53, 52, ..., 36
    for i in range(len(gnd_pins_r) - 1):
        p1 = rpin(gnd_pins_r[i])
        p2 = rpin(gnd_pins_r[i + 1])
        sb.add_wire(p1[0], p1[1], p2[0], p2[1])
    # Extend RIGHT so GND stub doesn't cross signal pins below
    gnd_bottom = rpin(36)
    gnd_ext_x = rx + 2 * STUB
    sb.add_wire(gnd_bottom[0], gnd_bottom[1], gnd_ext_x, gnd_bottom[1])
    sb.place_power("GND", gnd_ext_x, gnd_bottom[1])

    # ── NC pins (no-connect markers) ──
    nc_left = [4, 7, 9, 10, 15, 17, 24, 25]
    nc_right = [28, 29, 32, 33, 34, 35]
    for p in nc_left:
        sb.add_no_connect(*lpin(p))
    for p in nc_right:
        sb.add_no_connect(*rpin(p))

    # ── Unused GPIO pins (no-connect) ──
    unused_left = [16, 19, 20, 21, 22]   # IO10, IO5, IO6, IO7, IO8
    unused_right = [30, 31]               # RXD0, TXD0
    for p in unused_left:
        sb.add_no_connect(*lpin(p))
    for p in unused_right:
        sb.add_no_connect(*rpin(p))

    # ═══════════════════════════════════════════════════════════════════
    # Signal hierarchical labels
    # ═══════════════════════════════════════════════════════════════════
    # IO0 (pin 12) → ZC_PULSE input
    sb.add_hlabel("ZC_PULSE", *lpin(12), 180, "input")

    # IO1 (pin 13) → V_SENSE input (ADC)
    sb.add_hlabel("V_SENSE", *lpin(13), 180, "input")

    # IO2 (pin 5) → FWD_CMD output
    sb.add_hlabel("FWD_CMD", *lpin(5), 180, "output")

    # IO3 (pin 6) → REV_CMD output
    sb.add_hlabel("REV_CMD", *lpin(6), 180, "output")

    # IO4 (pin 18) → LED_CTRL output
    sb.add_hlabel("LED_CTRL", *lpin(18), 180, "output")

    # IO18 (pin 26) → USB_D- (matches usb_prog sheet)
    sb.add_hlabel("USB_D-", *lpin(26), 180, "bidirectional")

    # IO19 (pin 27) → USB_D+ (matches usb_prog sheet)
    sb.add_hlabel("USB_D+", *rpin(27), 0, "bidirectional")

    # ═══════════════════════════════════════════════════════════════════
    # EN pin reset circuit: R1 pull-up + C7 cap + SW1 button
    # ═══════════════════════════════════════════════════════════════════
    en_x, en_y = lpin(8)  # (118.57, 77.30)

    # Wire from EN pin to junction area
    en_jx = 100  # junction x for pull-up
    sb.add_wire(en_x, en_y, en_jx, en_y)

    # R1: 10K pull-up at (100, 70) vertical
    # pin2 (top) at (100, 66.19) → +3V3
    # pin1 (bottom) at (100, 73.81) → wire to EN net
    r1_cx, r1_cy = en_jx, 70
    sb.place_sym(
        "Device:R", r1_cx, r1_cy, 0,
        "R400", "10K",
        "Resistor_SMD:R_0603_1608Metric",
        ["1", "2"],
    )
    sb.add_wire(r1_cx, r1_cy + 3.81, r1_cx, en_y)
    sb.place_power("+3V3", r1_cx, r1_cy - 3.81)
    sb.add_junction(en_jx, en_y)

    # C7: 100nF EN delay cap at (107, 84) vertical
    # pin2 (top) at (107, 80.19) → wire to EN net
    # pin1 (bottom) at (107, 87.81) → GND
    c7_cx = 107
    c7_cy = 84
    sb.place_sym(
        "Device:C", c7_cx, c7_cy, 0,
        "C406", "100nF",
        "Capacitor_SMD:C_0603_1608Metric",
        ["1", "2"],
    )
    sb.add_wire(c7_cx, c7_cy - 3.81, c7_cx, en_y)
    sb.place_power("GND", c7_cx, c7_cy + 3.81)
    sb.add_junction(c7_cx, en_y)

    # SW1: Reset button at (90, 77.30) horizontal
    # SW_Push at angle=0: pin1 at (cx-5.08, cy), pin2 at (cx+5.08, cy)
    sw1_cx = 90
    sb.place_sym(
        "Switch:SW_Push", sw1_cx, en_y, 0,
        "SW400", "RESET",
        "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
        ["1", "2"],
    )
    # pin2 (right) at (95.08, en_y) → wire to EN junction
    sb.add_wire(sw1_cx + 5.08, en_y, en_jx, en_y)
    # pin1 (left) at (84.92, en_y) → GND
    sb.place_power("GND", sw1_cx - 5.08, en_y)

    # ═══════════════════════════════════════════════════════════════════
    # IO9 boot circuit: R2 pull-up + SW2 button
    # ═══════════════════════════════════════════════════════════════════
    io9_x, io9_y = lpin(23)  # (118.57, 115.40)

    # Wire from IO9 pin to junction area
    boot_jx = 100
    sb.add_wire(io9_x, io9_y, boot_jx, io9_y)

    # R2: 10K pull-up at (100, 108) vertical
    r2_cx, r2_cy = boot_jx, 108
    sb.place_sym(
        "Device:R", r2_cx, r2_cy, 0,
        "R401", "10K",
        "Resistor_SMD:R_0603_1608Metric",
        ["1", "2"],
    )
    sb.add_wire(r2_cx, r2_cy + 3.81, r2_cx, io9_y)
    sb.place_power("+3V3", r2_cx, r2_cy - 3.81)
    sb.add_junction(boot_jx, io9_y)

    # SW2: Boot button at (90, 115.40) horizontal
    sw2_cx = 90
    sb.place_sym(
        "Switch:SW_Push", sw2_cx, io9_y, 0,
        "SW401", "BOOT",
        "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
        ["1", "2"],
    )
    sb.add_wire(sw2_cx + 5.08, io9_y, boot_jx, io9_y)
    sb.place_power("GND", sw2_cx - 5.08, io9_y)

    # ═══════════════════════════════════════════════════════════════════
    # Decoupling capacitors: 2x 10uF bulk + 4x 100nF bypass
    # Placed in a row above the module
    # ═══════════════════════════════════════════════════════════════════
    cap_y = 38  # center of caps — raised for clearance from module
    cap_configs = [
        ("C400", "10uF",  50, "Capacitor_SMD:C_0805_2012Metric"),
        ("C401", "10uF",  62, "Capacitor_SMD:C_0805_2012Metric"),
        ("C402", "100nF", 74, "Capacitor_SMD:C_0603_1608Metric"),
        ("C403", "100nF", 86, "Capacitor_SMD:C_0603_1608Metric"),
        ("C404", "100nF", 98, "Capacitor_SMD:C_0603_1608Metric"),
        ("C405", "100nF", 110, "Capacitor_SMD:C_0603_1608Metric"),
    ]
    for ref, val, cap_x, fp in cap_configs:
        sb.place_sym(
            "Device:C", cap_x, cap_y, 0,
            ref, val, fp, ["1", "2"],
        )
        sb.place_power("+3V3", cap_x, cap_y - 3.81)
        sb.place_power("GND", cap_x, cap_y + 3.81)

    # ── Write output ──
    sb.write(OUTFILE)
    print("Block 2 (ESP32-C3 MCU) schematic generated.")

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
