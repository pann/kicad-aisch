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


STUB = 7.62  # Wire stub length (mm) — standard KiCad grid spacing
GRID = 1.27  # KiCad 50-mil fine grid (mm)


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

    def place_power(self, net_name, x, y, angle=0):
        """Place a power symbol with a wire stub from (x,y) to the symbol pin.

        (x,y) is the component pin tip. The stub direction depends on the net:
        - GND variants: stub goes DOWN (+y direction), symbol below
        - VCC/+3V3/etc: stub goes UP (-y direction), symbol above
        - PWR_FLAG: placed directly at (x,y), no stub
        """
        x, y = snap(x), snap(y)
        path = self.inst_path
        pwr_ref = f"#PWR{self._pwr_counter:04d}"
        self._pwr_counter += 1

        lib_id = f"power:{net_name}"
        if net_name == "PWR_FLAG":
            sx, sy = x, y
        elif "GND" in net_name:
            sx, sy = x, snap(y + STUB)
        else:
            sx, sy = x, snap(y - STUB)

        sym = (f'\t(symbol\n'
               f'\t\t(lib_id "{lib_id}")\n'
               f'\t\t(at {sx} {sy} {angle})\n'
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
        else:
            self._elements.append(wire(x, y, sx, sy))
            self._elements.append(sym)

    def add_wire(self, x1, y1, x2, y2):
        """Add a wire between two points."""
        self._elements.append(wire(x1, y1, x2, y2))

    def add_junction(self, x, y):
        """Add a junction at the given position."""
        self._elements.append(junction(x, y))

    def add_no_connect(self, x, y):
        """Add a no-connect marker."""
        self._elements.append(no_connect(x, y))

    def add_net_label(self, name, x, y, angle=0):
        """Add a net label with wire stub."""
        self._elements.append(net_label(name, x, y, angle))

    def add_global_label(self, name, x, y, angle, shape="input"):
        """Add a global label with wire stub."""
        self._elements.append(global_label(name, x, y, angle, shape))

    def add_hlabel(self, name, x, y, angle, shape="input"):
        """Add a hierarchical label with wire stub."""
        self._elements.append(hlabel(name, x, y, angle, shape))

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
            f'{lib_section}\n'
            f'{body}\n'
            f'{sheet_inst}\n'
            f'\t(embedded_fonts no)\n'
            f')'
        )

    def write(self, filepath):
        """Write the assembled schematic to a file."""
        content = self.assemble()
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Written {len(content):6d} bytes -> {filepath}")
        return content
