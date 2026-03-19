#!/usr/bin/env python3
"""Generic KiCad schematic generation library.

Provides reusable functions for programmatically creating KiCad 9 schematics:
  - Symbol extraction from .kicad_sym libraries
  - KiCad 6→9 format conversion (safe no-op on KiCad 9 files)
  - Component placement with proper instance paths
  - Power symbols, wires, labels, junctions, no-connects
  - Complete schematic assembly

Coordinate conventions (all in mm):
  - KiCad symbol libraries use Y-up; schematics use Y-down.
  - Schematic pin = (origin_x + sym_x, origin_y - sym_y) for angle=0
  - For angle=90:  pin offset (x,y) → schematic (+y, -x)
  - For angle=180: pin offset (x,y) → schematic (-x, +y) [both axes flip]
  - For angle=270: pin offset (x,y) → schematic (-y, +x)

Passive component pin offsets (Device:R, Device:C, Device:L):
  angle=0:   pin1 at (0, +3.81) [bottom], pin2 at (0, -3.81) [top]
  angle=90:  pin1 at (+3.81, 0) [right],  pin2 at (-3.81, 0) [left]
  angle=180: pin1 at (0, -3.81) [top],    pin2 at (0, +3.81) [bottom]
  angle=270: pin1 at (-3.81, 0) [left],   pin2 at (+3.81, 0) [right]

LED pin offsets (Device:LED):
  angle=0: K (cathode) at (-3.81, 0) [left], A (anode) at (+3.81, 0) [right]
    Note: current flows A→K, so with angle=0 current flows right-to-left.
    For left-to-right current flow, use angle=180:
  angle=180: A at (-3.81, 0) [left], K at (+3.81, 0) [right]

Usage:
    from kicad_sch_gen import SchematicBuilder

    sb = SchematicBuilder(
        project_name="my-project",
        root_uuid="...",
        sheet_inst_uuid="...",
        sheet_uuid="...",
    )
    sb.add_lib("Device", "/usr/share/kicad/symbols/Device.kicad_sym", ["R", "LED"])
    sb.add_lib("power", "/usr/share/kicad/symbols/power.kicad_sym", ["+3V3", "GND"])

    sb.place_sym("Device:R", 80, 60, 0, "R1", "1k",
                 "Resistor_SMD:R_0603_1608Metric", ["1", "2"])
    sb.place_power("+3V3", 80, 56.19)
    sb.place_power("GND", 80, 63.81)
    sb.add_hlabel("LED_CTRL", 80, 60, 180, "input")

    sb.write("output.kicad_sch")
"""

import re
import uuid as _uuid
from collections import defaultdict


STUB = 7.62  # Wire stub length (mm) — standard KiCad grid spacing
GRID = 1.27  # KiCad 50-mil fine grid (mm)

# Component fence half-sizes (keep-out zone covering body + pins + 1.27mm clearance).
# Any wire inside this zone that does NOT connect to a registered pin is flagged.
# Format: (half_width, half_height) — centered on symbol origin, before rotation.
BODY_R   = (2.54, 5.08)    # Device:R — body(1.016)+clearance, pins(3.81)+clearance
BODY_C   = (3.81, 5.08)    # Device:C — plates(2.032)+clearance, pins(3.81)+clearance
BODY_L   = (2.54, 5.08)    # Device:L — same fence as R
BODY_LED = (5.08, 2.54)    # Device:LED — horiz pins(3.81)+clearance, body(1.27)+clearance
BODY_D   = (5.08, 2.54)    # Device:D — same fence as LED

# Schematic pin offsets for auto-registration (angle=0, Y-down coords).
# Rotation is applied automatically in place_sym().
_PASSIVE_PINS = {
    "Device:R":   [(0, 3.81), (0, -3.81)],     # pin1 bottom, pin2 top
    "Device:C":   [(0, 3.81), (0, -3.81)],
    "Device:L":   [(0, 3.81), (0, -3.81)],
    "Device:LED": [(-3.81, 0), (3.81, 0)],      # K left, A right
    "Device:D":   [(-3.81, 0), (3.81, 0)],
}


def snap(v, grid=GRID):
    """Snap a coordinate value to the nearest grid point (1.27mm = 50 mil)."""
    return round(round(v / grid) * grid, 4)


def u():
    """Generate a random UUID string."""
    return str(_uuid.uuid4())


# ---------------------------------------------------------------------------
# Symbol extraction helpers
# ---------------------------------------------------------------------------

def extract_sym(lib_path, sym_name):
    """Extract a top-level symbol block from a .kicad_sym library file.

    Returns the raw text of the symbol including all sub-symbols.
    Raises ValueError if the symbol is not found.
    """
    with open(lib_path) as f:
        content = f.read()
    target = f'(symbol "{sym_name}"'
    start = content.find(target)
    if start == -1:
        raise ValueError(f"Symbol '{sym_name}' not found in {lib_path}")
    depth, i = 0, start
    while i < len(content):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                break
        i += 1
    return content[start:i + 1]


def upgrade_for_embed(block):
    """Convert KiCad 6 symbol format to KiCad 9 for embedding in a schematic.

    Handles:
    - Removal of (id N) from properties
    - Removal of (color R G B A) from strokes
    - Conversion of bare 'hide' to (hide yes)

    Safe to call on KiCad 9 format blocks (all transformations are no-ops).
    """
    # 1. Remove (id N) from multi-line KiCad 6 properties
    output, i = [], 0
    while i < len(block):
        if block[i:].startswith('(property\n'):
            depth, j = 0, i
            while j < len(block):
                if block[j] == '(':
                    depth += 1
                elif block[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            prop = block[i:j + 1]
            inner = prop[len('(property'):prop.rfind(')')].strip()
            inner = re.sub(r'\(id \d+\)\s*', '', inner)
            qm = re.match(
                r'"((?:[^"\\]|\\.)*)"\s+"((?:[^"\\]|\\.)*)"(.*)',
                inner, re.DOTALL)
            if qm:
                name, val, attrs = qm.group(1), qm.group(2), qm.group(3).strip()
                output.append(f'(property "{name}" "{val}"\n      {attrs}\n    )')
            else:
                output.append(re.sub(r'\s*\(id \d+\)', '', prop))
            i = j + 1
        else:
            output.append(block[i])
            i += 1
    block = ''.join(output)
    # 2. Remove (color R G B A) from strokes
    block = re.sub(
        r'\(stroke\s+\(width\s+([^)]+)\)\s+\(type\s+([^)]+)\)\s+\(color\s+[\d.\s]+\)\s*\)',
        r'(stroke (width \1) (type \2))', block)
    # 3. Fix effects: bare 'hide' → (hide yes)
    block = re.sub(
        r'\(effects\s+\(font\s+\(size\s+([\d.]+\s+[\d.]+)\)\s*\)\s+hide\)',
        r'(effects (font (size \1)) (hide yes))', block)
    block = re.sub(
        r'\(effects\s+\(font\s+\(size\s+([\d.]+\s+[\d.]+)\)\s*\)\s*\)',
        r'(effects (font (size \1)))', block)
    return block


def extract_subsymbols(block, sym_name):
    """Extract _N_M sub-symbol blocks from a symbol block."""
    subsyms, i = [], 0
    target_prefix = f'(symbol "{sym_name}_'
    while i < len(block):
        if block[i:].startswith(target_prefix):
            depth, j = 0, i
            while j < len(block):
                if block[j] == '(':
                    depth += 1
                elif block[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            subsyms.append(block[i:j + 1])
            i = j + 1
        else:
            i += 1
    return subsyms


def lib_sym_entry(lib_path, sym_name, lib_prefix):
    """Get a lib_symbols entry with fully-qualified name (lib_prefix:sym_name).

    Sub-symbol unit names stay bare (without prefix), as required by KiCad 9's
    schematic parser. Derived symbols (extends) are flattened by copying
    graphics from the base symbol.
    """
    block = extract_sym(lib_path, sym_name)
    fqn = f"{lib_prefix}:{sym_name}"
    # Flatten derived symbols: copy graphics from base, remove (extends ...)
    extends_match = re.search(r'\(extends "([^"]+)"\)', block)
    if extends_match:
        base_name = extends_match.group(1)
        base_block = extract_sym(lib_path, base_name)
        base_subsyms = extract_subsymbols(base_block, base_name)
        renamed = [ss.replace(f'(symbol "{base_name}_', f'(symbol "{sym_name}_', 1)
                   for ss in base_subsyms]
        block = re.sub(r'\s*\(extends "[^"]+"\)', '', block)
        block = block.rstrip()
        block = block[:-1].rstrip() + '\n' + '\n'.join(renamed) + '\n)'
    # Rename outer symbol only; sub-symbol names stay bare
    block = block.replace(f'(symbol "{sym_name}"', f'(symbol "{fqn}"', 1)
    # Convert KiCad 6 → KiCad 9 format
    block = upgrade_for_embed(block)
    # Ensure required KiCad 9 fields
    if '(exclude_from_sim' not in block:
        block = block.replace('(in_bom yes)', '(exclude_from_sim no)\n  (in_bom yes)', 1)
    if '(embedded_fonts no)' not in block:
        block = block.rstrip()
        block = block[:-1].rstrip() + '\n  (embedded_fonts no)\n)'
    return block


# ---------------------------------------------------------------------------
# Schematic element generators
# ---------------------------------------------------------------------------

def wire(x1, y1, x2, y2):
    """Create a wire element between two points."""
    x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)
    return (f'\t(wire\n'
            f'\t\t(pts (xy {x1} {y1}) (xy {x2} {y2}))\n'
            f'\t\t(stroke (width 0) (type solid))\n'
            f'\t\t(uuid "{u()}")\n'
            f'\t)')


def bus_wire(x1, y1, x2, y2):
    """Create a bus wire element between two points (thick line)."""
    x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)
    return (f'\t(bus\n'
            f'\t\t(pts (xy {x1} {y1}) (xy {x2} {y2}))\n'
            f'\t\t(stroke (width 0) (type solid))\n'
            f'\t\t(uuid "{u()}")\n'
            f'\t)')


def bus_entry(x, y, dx=2.54, dy=2.54):
    """Create a bus entry (diagonal stub connecting a wire to a bus).

    The entry is a small diagonal line from (x, y) to (x+dx, y+dy).
    Default direction: top-left to bottom-right (signal on left, bus on right).
    Use dx=-2.54 for signal on right, bus on left.
    """
    x, y = snap(x), snap(y)
    return (f'\t(bus_entry\n'
            f'\t\t(at {x} {y})\n'
            f'\t\t(size {dx} {dy})\n'
            f'\t\t(stroke (width 0) (type solid))\n'
            f'\t\t(uuid "{u()}")\n'
            f'\t)')


def junction(x, y):
    """Create a junction at the given position."""
    x, y = snap(x), snap(y)
    return (f'\t(junction\n'
            f'\t\t(at {x} {y})\n'
            f'\t\t(diameter 0)\n'
            f'\t\t(color 0 0 0 0)\n'
            f'\t\t(uuid "{u()}")\n'
            f'\t)')


def no_connect(x, y):
    """Create a no-connect marker at the given position."""
    x, y = snap(x), snap(y)
    return (f'\t(no_connect\n'
            f'\t\t(at {x} {y})\n'
            f'\t\t(uuid "{u()}")\n'
            f'\t)')


def net_label(name, x, y, angle=0):
    """Create a net label with a wire stub.

    x = component pin tip (inner wire end).
    angle=0   → label at x+STUB (right-side), stub extends right.
    angle=180 → label at x-STUB (left-side), stub extends left.
    """
    x, y = snap(x), snap(y)
    just = "right" if angle == 180 else "left"
    dx = -STUB if angle == 180 else STUB
    lx = snap(x + dx)
    label = (f'\t(label "{name}"\n'
             f'\t\t(at {lx} {y} {angle})\n'
             f'\t\t(fields_autoplaced yes)\n'
             f'\t\t(effects (font (size 1.27 1.27)) (justify {just} bottom))\n'
             f'\t\t(uuid "{u()}")\n'
             f'\t)')
    return wire(min(x, lx), y, max(x, lx), y) + '\n' + label


def global_label(name, x, y, angle, shape="input"):
    """Create a global label with a wire stub.

    x = component pin tip (inner wire end).
    Wire stub direction follows same convention as net_label/hlabel.
    """
    x, y = snap(x), snap(y)
    just = "right" if angle == 180 else "left"
    dx = STUB if angle == 180 else -STUB
    lx = snap(x + dx)
    label = (f'\t(global_label "{name}"\n'
             f'\t\t(shape {shape})\n'
             f'\t\t(at {lx} {y} {angle})\n'
             f'\t\t(fields_autoplaced yes)\n'
             f'\t\t(effects (font (size 1.27 1.27)) (justify {just} bottom))\n'
             f'\t\t(uuid "{u()}")\n'
             f'\t)')
    return wire(min(x, lx), y, max(x, lx), y) + '\n' + label


def hlabel(name, x, y, angle, shape="input"):
    """Create a hierarchical label with a wire stub.

    x   = component pin tip (inner wire end).
    lx  = label connection point (outer stub end), offset by +/-STUB from x.
    angle=180 → lx is LEFT of x (left-side inputs); label extends left.
    angle=0   → lx is RIGHT of x (right-side outputs); label extends right.
    Wire runs from x (pin) to lx (label).
    """
    x, y = snap(x), snap(y)
    just = "right" if angle == 180 else "left"
    dx = -STUB if angle == 180 else STUB
    lx = snap(x + dx)
    label = (f'\t(hierarchical_label "{name}"\n'
             f'\t\t(shape {shape})\n'
             f'\t\t(at {lx} {y} {angle})\n'
             f'\t\t(fields_autoplaced yes)\n'
             f'\t\t(effects (font (size 1.27 1.27)) (justify {just} bottom))\n'
             f'\t\t(uuid "{u()}")\n'
             f'\t)')
    return wire(min(x, lx), y, max(x, lx), y) + '\n' + label


# ---------------------------------------------------------------------------
# SchematicBuilder — high-level API
# ---------------------------------------------------------------------------

class SchematicBuilder:
    """Builder for a KiCad 9 hierarchical sub-sheet schematic.

    Manages lib_symbols, placed elements, power references, and assembly.

    Args:
        project_name:    KiCad project name (e.g. "marklin-wifi-ctrl")
        root_uuid:       UUID of the root schematic file
        sheet_inst_uuid: UUID of this sheet's entry in the root schematic
        sheet_uuid:      UUID of this sheet's own .kicad_sch file
        title:           Title block title
        date:            Title block date
        rev:             Title block revision
        company:         Title block company
        author:          Title block author (comment 1)
        comment2:        Title block comment 2
        paper:           Paper size (default "A4")
        page:            Page number string
    """

    def __init__(self, project_name, root_uuid, sheet_inst_uuid, sheet_uuid,
                 title="", date="", rev="", company="", author="",
                 comment2="", paper="A4", page="1", pwr_start=1):
        self.project_name = project_name
        self.root_uuid = root_uuid
        self.sheet_inst_uuid = sheet_inst_uuid
        self.sheet_uuid = sheet_uuid
        self.title = title
        self.date = date
        self.rev = rev
        self.company = company
        self.author = author
        self.comment2 = comment2
        self.paper = paper
        self.page = page

        self._lib_entries = []
        self._elements = []
        self._pwr_counter = pwr_start

        # Validation tracking
        self._wires = []            # [(x1, y1, x2, y2), ...] all wire segments
        self._junctions = set()     # {(x, y), ...}
        self._hlabel_names = defaultdict(list)  # name -> [(x, y), ...]
        self._pins = []             # [(x, y, ref, pin_num), ...] registered pins
        self._bodies = []           # [(x1, y1, x2, y2, ref), ...] component body rects
        self._power_stubs = []      # [(cx, cy, sx, sy, net), ...] power stub endpoints
        self._sym_positions = []    # [(x, y, ref), ...] all placed symbol centers
        self._bus_aliases = {}      # {alias_name: [member1, member2, ...]}
        self._declared_nets = {}    # {net_name: [(ref, pin), ...]} for net validation

    @property
    def inst_path(self):
        """Instance path for this sheet: /<root_uuid>/<sheet_inst_uuid>."""
        return f"/{self.root_uuid}/{self.sheet_inst_uuid}"

    def add_lib(self, lib_prefix, lib_path, sym_names):
        """Add symbols from a library to the embedded lib_symbols section.

        Args:
            lib_prefix: Library prefix for fully-qualified names (e.g. "Device")
            lib_path:   Path to the .kicad_sym file
            sym_names:  List of symbol names to extract
        """
        for name in sym_names:
            self._lib_entries.append(lib_sym_entry(lib_path, name, lib_prefix))

    def place_sym(self, lib_id, x, y, angle, ref, value, footprint, pin_nums,
                  unit=1, in_bom="yes", exclude_sim="no", mirror=None):
        """Place a component symbol instance.

        Args:
            lib_id:    Fully-qualified symbol name (e.g. "Device:R")
            x, y:      Centre position in mm (snapped to 1.27mm grid)
            angle:     Rotation in degrees (0, 90, 180, 270)
            ref:       Reference designator (e.g. "R1")
            value:     Component value (e.g. "1k")
            footprint: Fully-qualified footprint name
            pin_nums:  List of pin number strings (e.g. ["1", "2"])
            unit:      Unit number for multi-unit symbols (default 1)
            mirror:    Mirror axis ("x" or "y") or None
        """
        x, y = snap(x), snap(y)
        path = self.inst_path
        p_ref = (f'\t\t(property "Reference" "{ref}"\n'
                 f'\t\t\t(at {x} {y - 4} 0)\n'
                 f'\t\t\t(effects (font (size 1.27 1.27)))\n'
                 f'\t\t)')
        p_val = (f'\t\t(property "Value" "{value}"\n'
                 f'\t\t\t(at {x} {y + 4} 0)\n'
                 f'\t\t\t(effects (font (size 1.27 1.27)))\n'
                 f'\t\t)')
        p_fp = (f'\t\t(property "Footprint" "{footprint}"\n'
                f'\t\t\t(at {x} {y} 0)\n'
                f'\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n'
                f'\t\t)')
        p_ds = (f'\t\t(property "Datasheet" "~"\n'
                f'\t\t\t(at {x} {y} 0)\n'
                f'\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n'
                f'\t\t)')
        pins_s = "\n".join(f'\t\t(pin "{p}" (uuid "{u()}"))' for p in pin_nums)
        inst = (f'\t\t(instances\n'
                f'\t\t\t(project "{self.project_name}"\n'
                f'\t\t\t\t(path "{path}"\n'
                f'\t\t\t\t\t(reference "{ref}")\n'
                f'\t\t\t\t\t(unit {unit})\n'
                f'\t\t\t\t)\n'
                f'\t\t\t)\n'
                f'\t\t)')
        mirror_s = f'\t\t(mirror {mirror})\n' if mirror else ''
        sym = (f'\t(symbol\n'
               f'\t\t(lib_id "{lib_id}")\n'
               f'\t\t(at {x} {y} {angle})\n'
               f'{mirror_s}'
               f'\t\t(unit {unit})\n'
               f'\t\t(exclude_from_sim {exclude_sim})\n'
               f'\t\t(in_bom {in_bom})\n'
               f'\t\t(on_board yes)\n'
               f'\t\t(dnp no)\n'
               f'\t\t(uuid "{u()}")\n'
               f'{p_ref}\n{p_val}\n{p_fp}\n{p_ds}\n'
               f'{pins_s}\n{inst}\n'
               f'\t)')
        self._elements.append(sym)
        self._sym_positions.append((x, y, ref))

        # Auto-register fence and pins.
        # For known passives, use predefined BODY_* constants and pin offsets.
        # For ALL other components (ICs, connectors, etc.), estimate the fence
        # from the embedded symbol's actual pin positions.
        _auto_body = {
            "Device:R": BODY_R, "Device:C": BODY_C, "Device:L": BODY_L,
            "Device:LED": BODY_LED, "Device:D": BODY_D,
        }
        body = _auto_body.get(lib_id)
        pin_offsets = _PASSIVE_PINS.get(lib_id)

        if body:
            # Known passive: use predefined fence and pin offsets
            self.register_body(x, y, body[0], body[1], angle, ref)
            if pin_offsets:
                for i, (dx, dy) in enumerate(pin_offsets):
                    if angle == 90:    dx, dy = dy, -dx
                    elif angle == 180: dx, dy = -dx, -dy
                    elif angle == 270: dx, dy = -dy, dx
                    pnum = pin_nums[i] if i < len(pin_nums) else ""
                    self.register_pin(x + dx, y + dy, ref, pnum)
        else:
            # Unknown component: parse embedded lib_symbol to find pin positions
            # and auto-compute a generous fence from them.
            self._auto_register_from_lib(lib_id, x, y, angle, ref, pin_nums)

    def _auto_register_from_lib(self, lib_id, x, y, angle, ref, pin_nums):
        """Parse embedded lib_symbols to find pin positions, register fence and pins.

        The fence is computed generously: from pin-tip to pin-tip plus 2.54mm
        clearance on each side. This keeps wires and other symbols well away
        from the component body for readability.
        """
        # Find the lib_symbol entry for this lib_id
        target = f'(symbol "{lib_id}"'
        sym_block = None
        for entry in self._lib_entries:
            if target in entry:
                sym_block = entry
                break
        if not sym_block:
            return  # symbol not found in embedded libs

        # Extract all pin positions from the symbol
        pin_data = []  # [(pin_num, lib_x, lib_y), ...]
        for m in re.finditer(
                r'\(pin\s+\w+\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+\d+\)',
                sym_block):
            px, py = float(m.group(1)), float(m.group(2))
            rest = sym_block[m.end():]
            nm = re.search(r'\(number\s+"([^"]+)"', rest[:200])
            pnum = nm.group(1) if nm else ""
            pin_data.append((pnum, px, py))

        if not pin_data:
            return

        # Compute fence from pin extents + generous clearance (2.54mm each side)
        CLEARANCE = 2.54
        lib_xs = [px for _, px, _ in pin_data]
        lib_ys = [py for _, _, py in pin_data]
        # Half-dimensions in library coordinates (before rotation)
        half_w = max(abs(min(lib_xs)), abs(max(lib_xs))) + CLEARANCE
        half_h = max(abs(min(lib_ys)), abs(max(lib_ys))) + CLEARANCE

        self.register_body(x, y, half_w, half_h, angle, ref)

        # Register pin positions (transform from lib to schematic coords)
        for pnum, lib_x, lib_y in pin_data:
            # Schematic offset: (lib_x, -lib_y) for angle=0, then rotate
            dx, dy = lib_x, -lib_y
            if angle == 90:    dx, dy = dy, -dx
            elif angle == 180: dx, dy = -dx, -dy
            elif angle == 270: dx, dy = -dy, dx
            self.register_pin(x + dx, y + dy, ref, pnum)

    def place_power(self, net_name, x, y, angle=0):
        """Place a power symbol with a wire stub from (x,y) to the symbol pin.

        (x,y) is the component pin tip. The stub direction depends on the net:
        - GND variants: stub goes DOWN (+y direction), symbol below
        - Negative rails (-5V, -5VA, -6V, etc.): stub goes DOWN, arrow points down
        - Positive rails (+3V3, +5V, +5VA, etc.): stub goes UP, symbol above
        - PWR_FLAG: placed directly at (x,y), no stub
        """
        x, y = snap(x), snap(y)
        path = self.inst_path
        pwr_ref = f"#PWR{self._pwr_counter:04d}"
        self._pwr_counter += 1

        lib_id = f"power:{net_name}"
        if net_name == "PWR_FLAG":
            sx, sy = x, y
            sym_angle = angle
        elif "GND" in net_name:
            sx, sy = x, snap(y + STUB)
            sym_angle = angle
        elif net_name.startswith("-"):
            # Negative rails: stub DOWN (like GND), symbol rotated 180° so arrow points down
            sx, sy = x, snap(y + STUB)
            sym_angle = 180
        else:
            sx, sy = x, snap(y - STUB)
            sym_angle = angle

        sym = (f'\t(symbol\n'
               f'\t\t(lib_id "{lib_id}")\n'
               f'\t\t(at {sx} {sy} {sym_angle})\n'
               f'\t\t(unit 1)\n'
               f'\t\t(exclude_from_sim no)\n'
               f'\t\t(in_bom no)\n'
               f'\t\t(on_board yes)\n'
               f'\t\t(dnp no)\n'
               f'\t\t(uuid "{u()}")\n'
               f'\t\t(property "Reference" "{pwr_ref}"\n'
               f'\t\t\t(at {sx} {sy - 2} 0)\n'
               f'\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n'
               f'\t\t)\n'
               f'\t\t(property "Value" "{net_name}"\n'
               f'\t\t\t(at {sx} {sy + 2} 0)\n'
               f'\t\t\t(effects (font (size 1.27 1.27)))\n'
               f'\t\t)\n'
               f'\t\t(property "Footprint" ""\n'
               f'\t\t\t(at {sx} {sy} 0)\n'
               f'\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n'
               f'\t\t)\n'
               f'\t\t(property "Datasheet" ""\n'
               f'\t\t\t(at {sx} {sy} 0)\n'
               f'\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n'
               f'\t\t)\n'
               f'\t\t(pin "1" (uuid "{u()}"))\n'
               f'\t\t(instances\n'
               f'\t\t\t(project "{self.project_name}"\n'
               f'\t\t\t\t(path "{path}"\n'
               f'\t\t\t\t\t(reference "{pwr_ref}")\n'
               f'\t\t\t\t\t(unit 1)\n'
               f'\t\t\t\t)\n'
               f'\t\t\t)\n'
               f'\t\t)\n'
               f'\t)')

        if net_name == "PWR_FLAG":
            self._elements.append(sym)
            self._sym_positions.append((x, y, pwr_ref))
            # PWR_FLAG: small fence around the symbol
            self.register_body(x, y, 2.54, 2.54, 0, pwr_ref)
            # Register pin so co-located power symbol stubs get exemption
            self.register_pin(x, y, pwr_ref, "1")
        else:
            self._wires.append((x, y, sx, sy))
            self._power_stubs.append((x, y, sx, sy, net_name))
            self._elements.append(wire(x, y, sx, sy))
            self._elements.append(sym)
            self._sym_positions.append((sx, sy, pwr_ref))
            # Power symbol fence: covers the symbol graphic at (sx, sy).
            # The stub wire connects at (x, y) — the pin exemption allows
            # the stub wire through. Other wires should not cross the symbol.
            # Fence: 3.81mm wide × 3.81mm tall centered on symbol position.
            self.register_body(sx, sy, 3.81, 3.81, 0, pwr_ref)
            # Register the connection point as a pin (allows stub wire exemption)
            self.register_pin(x, y, pwr_ref, "1")

    def add_wire(self, x1, y1, x2, y2):
        """Add a wire between two points."""
        x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)
        self._wires.append((x1, y1, x2, y2))
        self._elements.append(wire(x1, y1, x2, y2))

    def add_bus_alias(self, alias_name, members):
        """Define a bus alias for named bus groups.

        Instead of writing `{SPI_MOSI,SPI_MISO,SPI_CLK,SPI_CS_ADC}` on every
        hlabel, define an alias once and use `{SPI}` everywhere.

        The alias definition is emitted in the schematic header. It must be
        defined in every sheet that references it.

        Args:
            alias_name: Short name (e.g., "SPI", "I2C", "MUX_CTRL")
            members:    List of member net names
        """
        self._bus_aliases[alias_name] = list(members)

    def add_bus_hlabel(self, name, x, y, angle, shape="bidirectional"):
        """Add a hierarchical label with a bus wire stub (for bus signals).

        Same as add_hlabel but uses a bus wire instead of a regular wire
        for the stub. Used for bus-type signals like {SPI} or ELEC_[1..16].
        """
        x, y = snap(x), snap(y)
        dx = -STUB if angle == 180 else STUB
        lx = snap(x + dx)
        self._wires.append((min(x, lx), y, max(x, lx), y))
        self._hlabel_names[name].append((x, y))
        # Bus wire stub instead of regular wire
        just = "right" if angle == 180 else "left"
        label = (f'\t(hierarchical_label "{name}"\n'
                 f'\t\t(shape {shape})\n'
                 f'\t\t(at {lx} {y} {angle})\n'
                 f'\t\t(fields_autoplaced yes)\n'
                 f'\t\t(effects (font (size 1.27 1.27)) (justify {just} bottom))\n'
                 f'\t\t(uuid "{u()}")\n'
                 f'\t)')
        self._elements.append(bus_wire(min(x, lx), y, max(x, lx), y))
        self._elements.append(label)

    def add_bus_net_label(self, name, x, y, angle=0):
        """Add a net label with a bus wire stub (for labeling bus wires)."""
        x, y = snap(x), snap(y)
        just = "right" if angle == 180 else "left"
        dx = -STUB if angle == 180 else STUB
        lx = snap(x + dx)
        self._wires.append((min(x, lx), y, max(x, lx), y))
        label = (f'\t(label "{name}"\n'
                 f'\t\t(at {lx} {y} {angle})\n'
                 f'\t\t(fields_autoplaced yes)\n'
                 f'\t\t(effects (font (size 1.27 1.27)) (justify {just} bottom))\n'
                 f'\t\t(uuid "{u()}")\n'
                 f'\t)')
        self._elements.append(bus_wire(min(x, lx), y, max(x, lx), y))
        self._elements.append(label)

    def add_bus(self, x1, y1, x2, y2):
        """Add a bus wire between two points (thick line for signal groups)."""
        self._elements.append(bus_wire(x1, y1, x2, y2))

    def add_bus_entry(self, x, y, dx=2.54, dy=2.54):
        """Add a bus entry (diagonal stub connecting a signal wire to a bus).

        Args:
            x, y:  Starting point of the diagonal (signal wire side)
            dx, dy: Direction of the diagonal. Default (2.54, 2.54) goes
                    from top-left (signal) to bottom-right (bus).
                    Use (-2.54, 2.54) for signal on right, bus on left.
        """
        self._elements.append(bus_entry(x, y, dx, dy))

    def add_bus_tap(self, label_name, bus_x, tap_y, label_side="left",
                    label_shape="bidirectional"):
        """Add a complete bus tap: bus entry + net label.

        The bus entry diagonal connects the bus wire to the net label's
        stub wire. The net label stub IS the signal wire — no extra wire
        needed between entry and label.

        KiCad bus_entry format: (at X Y) is the signal-wire end,
        (at+size) is the bus-wire end. The signal-wire end must touch
        a wire or label stub. The bus-wire end must touch a bus wire.

        Args:
            label_name:  Net label name (e.g., "ELEC_1")
            bus_x:       X position of the vertical bus wire
            tap_y:       Y position where this tap meets the bus
            label_side:  "left" or "right"
        """
        bus_x = snap(bus_x)
        tap_y = snap(tap_y)

        if label_side == "left":
            # Bus entry: (at) on the bus, (size) pointing to signal wire
            # Bus point: (bus_x, tap_y)
            # Signal point: (bus_x - 2.54, tap_y - 2.54)
            sig_x = snap(bus_x - 2.54)
            sig_y = snap(tap_y - 2.54)
            self.add_bus_entry(bus_x, tap_y, -2.54, -2.54)
            # Wire from signal point going left to label
            wire_end_x = snap(sig_x - 2.54)
            self.add_wire(wire_end_x, sig_y, sig_x, sig_y)
            self.add_net_label(label_name, wire_end_x, sig_y, 180)
        else:
            # Bus entry: (at) on the bus, (size) pointing to signal wire
            # Bus point: (bus_x, tap_y)
            # Signal point: (bus_x + 2.54, tap_y - 2.54)
            sig_x = snap(bus_x + 2.54)
            sig_y = snap(tap_y - 2.54)
            self.add_bus_entry(bus_x, tap_y, 2.54, -2.54)
            # Wire from signal point going right to label
            wire_end_x = snap(sig_x + 2.54)
            self.add_wire(sig_x, sig_y, wire_end_x, sig_y)
            self.add_net_label(label_name, wire_end_x, sig_y, 0)

    def add_junction(self, x, y):
        """Add a junction at the given position."""
        x, y = snap(x), snap(y)
        self._junctions.add((x, y))
        self._elements.append(junction(x, y))

    def add_no_connect(self, x, y):
        """Add a no-connect marker."""
        self._elements.append(no_connect(x, y))

    def add_net_label(self, name, x, y, angle=0):
        """Add a net label with wire stub."""
        x, y = snap(x), snap(y)
        dx = -STUB if angle == 180 else STUB
        lx = snap(x + dx)
        self._wires.append((min(x, lx), y, max(x, lx), y))
        self._elements.append(net_label(name, x, y, angle))

    def add_global_label(self, name, x, y, angle, shape="input"):
        """Add a global label with wire stub."""
        x, y = snap(x), snap(y)
        dx = STUB if angle == 180 else -STUB
        lx = snap(x + dx)
        self._wires.append((min(x, lx), y, max(x, lx), y))
        self._elements.append(global_label(name, x, y, angle, shape))

    def add_hlabel(self, name, x, y, angle, shape="input"):
        """Add a hierarchical label with wire stub."""
        x, y = snap(x), snap(y)
        dx = -STUB if angle == 180 else STUB
        lx = snap(x + dx)
        self._wires.append((min(x, lx), y, max(x, lx), y))
        self._hlabel_names[name].append((x, y))
        self._elements.append(hlabel(name, x, y, angle, shape))

    def register_pin(self, x, y, ref="", pin=""):
        """Register a component pin tip position for validation.

        Call after place_sym() for each pin whose position you know.
        The validator will check that registered pins land on wire endpoints,
        not in the middle of wire segments.

        Args:
            x, y:  Pin tip position in schematic coordinates (mm)
            ref:   Reference designator (e.g. "U1") for error messages
            pin:   Pin number/name (e.g. "3") for error messages
        """
        self._pins.append((snap(x), snap(y), ref, pin))

    def register_body(self, cx, cy, half_w, half_h, angle=0, ref=""):
        """Register a component body rectangle for wire-through-body detection.

        The body is defined by its center and half-dimensions in library
        coordinates. The angle parameter rotates the rectangle (swaps w/h
        for 90/270).

        Use the BODY_* constants for common components:
            sb.register_body(80, 60, *BODY_R, angle=0, ref="R1")

        For ICs, estimate body as the area between pin columns, shrunk
        inward by 2.54mm from pin tips:
            sb.register_body(cx, cy, pin_x_max - 2.54, pin_y_max + 1.27,
                             angle=0, ref="U1")

        Args:
            cx, cy:    Component center position (schematic coordinates)
            half_w:    Half-width of body in library coords (x-axis)
            half_h:    Half-height of body in library coords (y-axis)
            angle:     Component rotation (0, 90, 180, 270)
            ref:       Reference designator for error messages
        """
        cx, cy = snap(cx), snap(cy)
        # Swap w/h for 90/270 rotation (body is axis-aligned in schematic)
        if angle in (90, 270):
            half_w, half_h = half_h, half_w
        self._bodies.append((cx - half_w, cy - half_h,
                             cx + half_w, cy + half_h, ref))

    # -------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------

    def validate(self):
        """Check for common wiring rule violations.

        Returns a list of warning/error strings. Empty list = all checks pass.
        Checks performed:
          1. Diagonal wires (must be horizontal or vertical)
          2. Overlapping collinear wires (KiCad merges them, losing endpoints)
          3. Wire endpoints or registered pins that fall mid-segment
          4. Duplicate hierarchical labels (same name used more than once)
          5. Missing junctions (3+ wire endpoints meet without a junction)
          6. Wires passing through registered component bodies
          7. Power stub isolation (symbol end touching other wires)
          8. Symbols placed inside other component fences
        """
        issues = []

        # --- 1. Diagonal wires -------------------------------------------
        for x1, y1, x2, y2 in self._wires:
            if x1 != x2 and y1 != y2:
                issues.append(
                    f"ERROR: Diagonal wire from ({x1},{y1}) to ({x2},{y2}) "
                    f"— all wires must be horizontal or vertical")

        # --- 2. Overlapping collinear wires ------------------------------
        # Group by axis: horizontal wires by y, vertical wires by x
        h_by_y = defaultdict(list)  # y -> [(x_min, x_max)]
        v_by_x = defaultdict(list)  # x -> [(y_min, y_max)]
        for x1, y1, x2, y2 in self._wires:
            if y1 == y2 and x1 != x2:  # horizontal
                h_by_y[y1].append((min(x1, x2), max(x1, x2)))
            elif x1 == x2 and y1 != y2:  # vertical
                v_by_x[x1].append((min(y1, y2), max(y1, y2)))

        for y, segs in h_by_y.items():
            for i in range(len(segs)):
                for j in range(i + 1, len(segs)):
                    a1, a2 = segs[i]
                    b1, b2 = segs[j]
                    # overlap if ranges intersect (not just touch)
                    if a1 < b2 and b1 < a2:
                        overlap_start = max(a1, b1)
                        overlap_end = min(a2, b2)
                        if overlap_start < overlap_end:
                            issues.append(
                                f"WARNING: Overlapping horizontal wires at y={y}: "
                                f"({a1},{y})-({a2},{y}) and ({b1},{y})-({b2},{y}) "
                                f"overlap in x=[{overlap_start},{overlap_end}]")

        for x, segs in v_by_x.items():
            for i in range(len(segs)):
                for j in range(i + 1, len(segs)):
                    a1, a2 = segs[i]
                    b1, b2 = segs[j]
                    if a1 < b2 and b1 < a2:
                        overlap_start = max(a1, b1)
                        overlap_end = min(a2, b2)
                        if overlap_start < overlap_end:
                            issues.append(
                                f"WARNING: Overlapping vertical wires at x={x}: "
                                f"({x},{a1})-({x},{a2}) and ({x},{b1})-({x},{b2}) "
                                f"overlap in y=[{overlap_start},{overlap_end}]")

        # --- 3. Mid-wire points ------------------------------------------
        # Collect all points that should land on wire ENDPOINTS, not mid-segment
        check_points = []
        # All wire endpoints are potential mid-wire victims of OTHER segments
        for x1, y1, x2, y2 in self._wires:
            check_points.append((x1, y1, "wire endpoint"))
            check_points.append((x2, y2, "wire endpoint"))
        # Registered component pins
        for px, py, ref, pin in self._pins:
            label = f"pin {ref}:{pin}" if ref else "registered pin"
            check_points.append((px, py, label))

        seen_midwire = set()
        for px, py, label in check_points:
            # Check against horizontal wires at same y
            for a1, a2 in h_by_y.get(py, []):
                if a1 < px < a2:  # strictly between endpoints
                    key = (px, py, a1, py, a2, py)
                    if key not in seen_midwire:
                        seen_midwire.add(key)
                        issues.append(
                            f"WARNING: {label} at ({px},{py}) falls mid-wire "
                            f"on horizontal segment ({a1},{py})-({a2},{py}) "
                            f"— KiCad won't connect it; break wire into segments")
            # Check against vertical wires at same x
            for a1, a2 in v_by_x.get(px, []):
                if a1 < py < a2:
                    key = (px, py, px, a1, px, a2)
                    if key not in seen_midwire:
                        seen_midwire.add(key)
                        issues.append(
                            f"WARNING: {label} at ({px},{py}) falls mid-wire "
                            f"on vertical segment ({px},{a1})-({px},{a2}) "
                            f"— KiCad won't connect it; break wire into segments")

        # --- 4. Duplicate hierarchical labels ----------------------------
        for name, positions in self._hlabel_names.items():
            if len(positions) > 1:
                locs = ", ".join(f"({x},{y})" for x, y in positions)
                issues.append(
                    f"ERROR: Hierarchical label '{name}' used {len(positions)} "
                    f"times on same sheet at {locs} "
                    f"— use add_net_label() for additional connections")

        # --- 5. Missing junctions ----------------------------------------
        # Count wire endpoints at each point
        endpoint_count = defaultdict(int)
        for x1, y1, x2, y2 in self._wires:
            endpoint_count[(x1, y1)] += 1
            endpoint_count[(x2, y2)] += 1

        for point, count in endpoint_count.items():
            if count >= 3 and point not in self._junctions:
                issues.append(
                    f"WARNING: {count} wire endpoints meet at "
                    f"({point[0]},{point[1]}) without a junction "
                    f"— add sb.add_junction({point[0]}, {point[1]})")

        # --- 6. Wires through component fence (body + pins + clearance) ---
        # The fence is a keep-out zone around each component. Any wire
        # inside the fence is OK only if it connects to a registered pin
        # of that component.
        pins_by_ref = defaultdict(set)
        for px, py, ref, pin in self._pins:
            pins_by_ref[ref].add((px, py))

        seen_body_hits = set()
        for x1, y1, x2, y2 in self._wires:
            for bx1, by1, bx2, by2, ref in self._bodies:
                hit = False
                if y1 == y2:  # horizontal wire
                    wy = y1
                    wx1, wx2 = min(x1, x2), max(x1, x2)
                    if by1 < wy < by2 and max(wx1, bx1) < min(wx2, bx2):
                        hit = True
                elif x1 == x2:  # vertical wire
                    wx = x1
                    wy1, wy2 = min(y1, y2), max(y1, y2)
                    if bx1 < wx < bx2 and max(wy1, by1) < min(wy2, by2):
                        hit = True
                if hit:
                    # Exempt wires that connect to a pin of this component
                    comp_pins = pins_by_ref.get(ref, set())
                    if (x1, y1) in comp_pins or (x2, y2) in comp_pins:
                        continue
                    key = (x1, y1, x2, y2, ref)
                    if key not in seen_body_hits:
                        seen_body_hits.add(key)
                        issues.append(
                            f"WARNING: Wire ({x1},{y1})-({x2},{y2}) passes "
                            f"through fence of {ref} — route around the "
                            f"component, not through it")

        # --- 7. Power stub isolation ----------------------------------------
        # The far end of a power stub (where the symbol sits) must not
        # touch any OTHER wire. If it does, it creates an accidental short
        # between the power net and whatever signal that wire carries.
        # Collect all wire endpoints EXCEPT the power stub's own endpoints.
        all_endpoints = set()
        for x1, y1, x2, y2 in self._wires:
            all_endpoints.add((x1, y1))
            all_endpoints.add((x2, y2))

        for cx, cy, sx, sy, net in self._power_stubs:
            # sx, sy is the symbol end (far from circuit).
            # Check if any OTHER wire endpoint lands at (sx, sy).
            # The stub itself has endpoints (cx,cy) and (sx,sy) — exclude those.
            # Also check if (sx, sy) falls mid-wire on any segment.
            # First: check for mid-wire hits
            for a1, a2 in h_by_y.get(sy, []):
                if a1 < sx < a2:
                    issues.append(
                        f"ERROR: {net} power stub end at ({sx},{sy}) falls "
                        f"mid-wire on ({a1},{sy})-({a2},{sy}) — accidental "
                        f"short! Move power symbol to a different position")
            for a1, a2 in v_by_x.get(sx, []):
                if a1 < sy < a2:
                    # Exclude the stub's own segment
                    stub_min_y = min(cy, sy)
                    stub_max_y = max(cy, sy)
                    if (a1, a2) != (stub_min_y, stub_max_y):
                        issues.append(
                            f"ERROR: {net} power stub end at ({sx},{sy}) falls "
                            f"mid-wire on ({sx},{a1})-({sx},{a2}) — accidental "
                            f"short! Move power symbol to a different position")

            # Second: check if another wire endpoint (not from this stub) is at (sx, sy)
            # Count how many wire endpoints are at the symbol point
            ep_count = endpoint_count.get((sx, sy), 0)
            # The stub itself contributes 1 endpoint at (sx, sy).
            # If there are more, another wire touches the symbol end.
            if ep_count > 1 and (sx, sy) not in self._junctions:
                issues.append(
                    f"WARNING: {net} power stub end at ({sx},{sy}) touches "
                    f"another wire — possible accidental short. Add a "
                    f"junction if intentional, or move the power symbol")

        # --- 8. Symbols placed inside other component fences --------------
        # No symbol (component or power) should be placed inside another
        # component's fence zone. This catches power symbols placed inside
        # IC bodies and components placed too close to each other.
        for sx, sy, sref in self._sym_positions:
            for bx1, by1, bx2, by2, bref in self._bodies:
                if sref == bref:
                    continue  # skip self (component inside its own fence)
                if bx1 < sx < bx2 and by1 < sy < by2:
                    issues.append(
                        f"WARNING: Symbol {sref} at ({sx},{sy}) is placed "
                        f"inside fence of {bref} — move it outside the "
                        f"component area")

        return issues

    # -------------------------------------------------------------------
    # Net declaration and validation
    # -------------------------------------------------------------------

    def declare_net(self, net_name, pins):
        """Declare intended net connectivity for post-generation validation.

        After writing the schematic, call check_nets() with the root
        schematic path to verify actual connectivity matches declarations.

        Args:
            net_name: Human-readable net name (e.g. "VREF", "FB", "VOUT")
            pins:     List of (ref, pin_number) tuples that should all be
                      on the same net. e.g. [("U202", "5"), ("R205", "2")]
        """
        self._declared_nets[net_name] = [(ref, str(pin)) for ref, pin in pins]

    def check_nets(self, root_sch_path):
        """Validate declared nets against actual KiCad netlist.

        Exports a netlist from the root schematic using kicad-cli, parses
        it, and checks that declared pin groups are on the same net and
        that no two declared nets are shorted together.

        Args:
            root_sch_path: Path to the root .kicad_sch file

        Returns:
            List of error strings (empty = all nets match declarations)
        """
        import subprocess, shutil, tempfile

        if not self._declared_nets:
            return []

        kicad_cli = shutil.which("kicad-cli")
        if not kicad_cli:
            return ["SKIP: kicad-cli not found, cannot validate nets"]

        # Export netlist
        with tempfile.NamedTemporaryFile(suffix=".net", delete=False) as f:
            netlist_path = f.name

        ret = subprocess.run(
            [kicad_cli, "sch", "export", "netlist",
             "--output", netlist_path, root_sch_path],
            capture_output=True, text=True)
        if ret.returncode != 0:
            return [f"SKIP: netlist export failed: {ret.stderr[:200]}"]

        # Parse netlist: build (ref, pin) → actual_net_name mapping
        with open(netlist_path) as f:
            content = f.read()
        import os
        os.unlink(netlist_path)

        pin_to_net = {}  # (ref, pin) → net_name
        # Parse (net (code "N") (name "X") (node (ref "R") (pin "P")) ...)
        i = 0
        while True:
            i = content.find("(net ", i)
            if i == -1:
                break
            # Find net name
            name_start = content.find('(name "', i)
            if name_start == -1:
                break
            name_start += 7
            name_end = content.find('"', name_start)
            net_name = content[name_start:name_end]

            # Find closing paren for this net block
            depth, j = 0, i
            while j < len(content):
                if content[j] == '(':
                    depth += 1
                elif content[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            net_block = content[i:j + 1]

            # Extract all nodes in this net
            for node_match in re.finditer(
                    r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', net_block):
                ref = node_match.group(1)
                pin = node_match.group(2)
                pin_to_net[(ref, pin)] = net_name

            i = j + 1

        # Validate declared nets
        errors = []
        for decl_name, decl_pins in self._declared_nets.items():
            # Find what actual nets these pins are on
            actual_nets = {}
            for ref, pin in decl_pins:
                actual = pin_to_net.get((ref, pin))
                if actual is None:
                    errors.append(
                        f"NET ERROR: {decl_name}: pin {ref}:{pin} not found "
                        f"in netlist (component missing or pin unconnected)")
                else:
                    actual_nets.setdefault(actual, []).append((ref, pin))

            # All pins should be on the same actual net
            if len(actual_nets) > 1:
                details = "; ".join(
                    f"net '{an}' has {', '.join(f'{r}:{p}' for r, p in pins)}"
                    for an, pins in actual_nets.items())
                errors.append(
                    f"NET ERROR: {decl_name}: pins are on DIFFERENT nets — "
                    f"open circuit! {details}")

        # Check for shorts: two declared nets that map to the same actual net
        decl_to_actual = {}
        for decl_name, decl_pins in self._declared_nets.items():
            for ref, pin in decl_pins:
                actual = pin_to_net.get((ref, pin))
                if actual:
                    decl_to_actual.setdefault(decl_name, set()).add(actual)

        # Find declared nets that share an actual net
        actual_to_decls = {}
        for decl_name, actual_set in decl_to_actual.items():
            for actual in actual_set:
                actual_to_decls.setdefault(actual, set()).add(decl_name)

        for actual, decl_set in actual_to_decls.items():
            if len(decl_set) > 1:
                errors.append(
                    f"NET ERROR: SHORT — declared nets "
                    f"{', '.join(sorted(decl_set))} are all on actual net "
                    f"'{actual}' — they should be separate!")

        return errors

    def assemble(self):
        """Assemble the complete schematic as a string."""
        # lib_symbols section
        lib_body = "\n".join(
            "\n".join("\t\t" + line for line in entry.split("\n"))
            for entry in self._lib_entries
        )
        lib_section = f"\t(lib_symbols\n{lib_body}\n\t)"

        # Title block
        title_block = (
            f'\t(title_block\n'
            f'\t\t(title "{self.title}")\n'
            f'\t\t(date "{self.date}")\n'
            f'\t\t(rev "{self.rev}")\n'
            f'\t\t(company "{self.company}")\n'
        )
        if self.author:
            title_block += f'\t\t(comment 1 "Author: {self.author}")\n'
        if self.comment2:
            title_block += f'\t\t(comment 2 "{self.comment2}")\n'
        title_block += '\t)'

        # Sheet instance
        sheet_inst = (
            f'\t(sheet_instances\n'
            f'\t\t(path "{self.inst_path}"\n'
            f'\t\t\t(page "{self.page}")\n'
            f'\t\t)\n'
            f'\t)'
        )

        # Bus aliases
        bus_alias_section = ""
        for alias_name, members in self._bus_aliases.items():
            member_str = " ".join(f'"{m}"' for m in members)
            bus_alias_section += (
                f'\t(bus_alias "{alias_name}" (members {member_str}))\n')

        # Elements
        body = "\n".join(self._elements)

        return (
            f'(kicad_sch\n'
            f'\t(version 20250114)\n'
            f'\t(generator "eeschema")\n'
            f'\t(generator_version "9.0")\n'
            f'\t(uuid "{self.sheet_uuid}")\n'
            f'\t(paper "{self.paper}")\n'
            f'{title_block}\n'
            f'{bus_alias_section}'
            f'{lib_section}\n'
            f'{body}\n'
            f'{sheet_inst}\n'
            f'\t(embedded_fonts no)\n'
            f')'
        )

    def write(self, filepath, validate=True):
        """Write the assembled schematic to a file.

        Args:
            filepath:  Output .kicad_sch path
            validate:  Run wiring validation before writing (default True).
                       Issues are printed but do not block writing.
        """
        content = self.assemble()
        issues = self.validate() if validate else []
        if issues:
            errors = [i for i in issues if i.startswith("ERROR")]
            warnings = [i for i in issues if i.startswith("WARNING")]
            print(f"\n{'=' * 64}")
            print(f"  VALIDATION: {len(errors)} error(s), {len(warnings)} warning(s)")
            print(f"{'=' * 64}")
            for issue in issues:
                print(f"  {issue}")
            print(f"{'=' * 64}\n")
        with open(filepath, "w") as f:
            f.write(content)
        status = "CLEAN" if not issues else f"{len(issues)} issue(s)"
        print(f"Written {len(content):6d} bytes -> {filepath}  [{status}]")
        return content
