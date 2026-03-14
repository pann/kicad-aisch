# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

kicad-aisch — AI-assisted KiCad schematic generation tools. The goal is to create generic scripts, workflow, and settings for a **Claude Code skill** that generates KiCad schematics from design requirements.

## Repository Structure

- `scripts/` — Reusable Python scripts for schematic generation
  - `kicad_sch_gen.py` — Generic KiCad schematic generation library (`SchematicBuilder` class)
  - `gen_*.py` — Per-block schematic generator scripts
  - `gen_top_level.py` — Root schematic with hierarchical sheet frames and global labels
  - `md_to_pdf.py` — Markdown-to-PDF converter
  - `extract_easyeda_libs.py` — LCSC component extraction into project libs
- `workflow/` — Design workflow phase outputs (`01-requirements.md`, `02-architecture.md`, etc.)
- `marklin-wifi-ctrl/` — Reference KiCad project (test design used to develop this skill)

## File Conventions

- KiCad schematics: `.kicad_sch` (S-expression format)
- KiCad PCB layouts: `.kicad_pcb` (S-expression format)
- KiCad symbol libraries: `.kicad_sym` (read-only, never modify)
- KiCad footprint libraries: `.kicad_mod`
- PDF files are output only — always read `.md` files to understand the design

## KiCad Workflow

- Use `kicad-cli` for command-line operations (DRC, ERC, export)
- Use `easyeda2kicad` to convert EasyEDA/LCSC components to KiCad format
- LCSC part lookups via lcsc.com for component sourcing
- Target: KiCad 9 format (version 20250114)

## SchematicBuilder API (`scripts/kicad_sch_gen.py`)

The core library for programmatic schematic generation. Key API:

### Symbol Management
- `sb.add_lib(lib_prefix, lib_path, sym_names)` — Extract and embed symbols from `.kicad_sym` files
- Handles KiCad 6->9 format upgrade automatically (`upgrade_for_embed()`)
- Flattens derived symbols (extends) by copying base graphics

### Component Placement
- `sb.place_sym(lib_id, x, y, angle, ref, value, footprint, pin_nums, unit=1, mirror=None)` — Place a component
- `sb.place_power(net_name, x, y)` — Place power symbol with auto wire stub:
  - GND variants: stub goes DOWN (symbol at y + STUB)
  - VCC/+3V3/etc: stub goes UP (symbol at y - STUB)
  - PWR_FLAG: placed directly, no stub

### Wires, Labels, and Markers
- `sb.add_wire(x1, y1, x2, y2)` — Wire between two points
- `sb.add_junction(x, y)` — Junction marker
- `sb.add_no_connect(x, y)` — No-connect marker
- `sb.add_net_label(name, x, y, angle)` — Local net label with wire stub
- `sb.add_hlabel(name, x, y, angle, shape)` — Hierarchical label with wire stub
- `sb.add_global_label(name, x, y, angle, shape)` — Global label with wire stub
- `sb.write(filepath)` — Assemble and write the .kicad_sch file

### Label/Stub Convention
All label functions place the label at a STUB offset from the pin tip:
- `angle=0`: label at x + STUB (right side), stub wire extends right
- `angle=180`: label at x - STUB (left side), stub wire extends left

## Coordinate Conventions

- **STUB = 7.62mm** — Standard wire stub length for labels and power symbols
- **GRID = 1.27mm** — KiCad 50-mil fine grid; all coordinates snapped via `snap()`
- **Symbol libs use Y-up; schematics use Y-down**: `sch_y = origin_y - sym_y`
- Passive component pin offsets (Device:R, Device:C, Device:L):
  - angle=0: pin1 at (0, +3.81) bottom, pin2 at (0, -3.81) top
  - angle=90: pin1 at (+3.81, 0) right, pin2 at (-3.81, 0) left
- LED pin offsets (Device:LED):
  - angle=0: K (cathode) at (-3.81, 0) left, A (anode) at (+3.81, 0) right
  - angle=180: A at left, K at right (for left-to-right current flow)

## Layout Guidelines

- Place components on 2.54mm grid (multiples of 2.54)
- Pin spacing on hierarchical sheet frames: 5.08mm (2 x 2.54)
- **Inter-column gap must accommodate facing global labels**: minimum 2 x STUB + 2 x label_text (~40mm), use 45mm+ for comfort
- **Vertical spacing**: allow enough room for component value text (especially for rotated components like diodes with long names)
- **Power symbol clearance**: watch for overlapping +VCC and GND stubs when they share the same x-coordinate at close y-positions (STUB = 7.62mm each direction)
- Always verify readability with SVG export: `kicad-cli sch export svg --output /tmp/ <file.kicad_sch>`

## Schematic Design Rules

### Hierarchical Labels
- **One hlabel per net name per sheet** — if the same net connects at multiple points, place the hlabel once and use `add_net_label()` for additional connections
- This avoids duplicate hlabel errors

### PCB Pads
- PCB solder pads still need schematic symbols — use 2mm test points (`Connector:TestPoint` / `TestPoint:TestPoint_Pad_2.0x2.0mm`) as default

### Symbol Libraries
- `.kicad_sym` files are **read-only** — never modify them programmatically
- easyeda2kicad imports symbols with "unspecified" pin types (known limitation)
- `pin_to_pin` ERC warnings from easyeda2kicad imports are acceptable — suppress in project settings

## easyeda2kicad Import Procedure

1. Run from project dir:
   ```
   easyeda2kicad --full --lcsc_id <LCSC_ID> --output ./<project>.kicad_sym --project-relative
   ```
2. **Always run sed after import** to fix footprint library references:
   ```
   sed -i 's|easyeda2kicad:|<project>:|g' <project>.pretty/*.kicad_mod
   ```
   (easyeda2kicad hardcodes `easyeda2kicad:` as library name in footprint 3D model paths)
3. Create `sym-lib-table` and `fp-lib-table` in project dir to register libraries with KiCad

## ERC Configuration

The `erc` section must be at the **JSON root level** of `.kicad_pro` (NOT inside `"schematic"`) — `kicad-cli` ignores it otherwise.

Required `rule_severities` when using easyeda2kicad-imported components:
```json
"erc": {
  "meta": { "version": 0 },
  "pin_map": [
    [0,0,0,0,0,0,0,0,0,0,0,2],
    [0,2,1,0,0,0,0,0,2,1,1,2],
    [0,1,0,0,0,0,0,0,1,1,1,2],
    [0,0,0,0,0,0,0,0,0,0,0,2],
    [0,0,0,0,0,0,0,0,0,0,0,2],
    [0,0,0,0,0,0,0,0,0,0,0,2],
    [0,0,0,0,0,0,0,0,0,0,0,2],
    [0,0,0,0,0,0,0,0,0,0,0,2],
    [0,2,1,0,0,0,0,0,2,1,1,2],
    [0,1,1,0,0,0,0,0,1,1,1,2],
    [0,1,1,0,0,0,0,0,1,1,1,2],
    [2,2,2,2,2,2,2,2,2,2,2,2]
  ],
  "rule_severities": {
    "pin_to_pin": "ignore",
    "same_local_global_label": "ignore",
    "pin_not_driven": "warning"
  }
}
```

**Why each suppression:**
- `pin_to_pin: ignore` — easyeda2kicad "unspecified" pins trigger false positives
- `same_local_global_label: ignore` — deliberate pattern from one-hlabel-per-net rule (local net labels share names with global labels)
- `pin_not_driven: warning` — easyeda2kicad GPIO pins are "unspecified" type, which KiCad doesn't count as driving "input" pins
- `pin_map` row/column 6 (unspecified) set to all 0s (allowed) to prevent false conflicts

## Expected ERC Warnings (Acceptable)

- `lib_symbol_mismatch` — embedded symbols differ from installed KiCad library versions (cosmetic only)
- `pin_not_driven` — input pins driven by easyeda2kicad "unspecified" GPIOs (not a real issue)

## USB-C Connector Note

USB-C 14P connectors (e.g., from easyeda2kicad) have separate A-side and B-side data pins at different symbol positions. Both sides must be wired — connect B7->A7 (D-) and B6->A6 (D+) with vertical wires and junctions.

## Reference Scripts

The scripts in this project were developed using proven KiCad schematic generators from `/home/pa/work/traincontrol/hw/traincontrol-shield/tmp/` as templates. Key patterns carried forward:
- `extract_sym()` / `lib_sym_entry()` — extract and embed symbols from KiCad libs
- `upgrade_for_embed()` — KiCad 6->9 format conversion
- `placed_sym()` / `power_sym()` — component placement with instance paths
- `wire()`, `junction()`, `no_connect()` — basic schematic elements
- `net_label()`, `hlabel()`, `glabel()` — labels with STUB wire stubs
- `assemble()` — complete sheet assembly
- `sheet_frame()` — hierarchical sheet frame entries for top-level schematic

## Tools Available

- `kicad-cli` for KiCad operations (ERC, DRC, export SVG/PDF)
- `easyeda2kicad` for LCSC component conversion
- `fpdf` Python library (latin-1 only — must sanitize Unicode)
- `inkscape` for SVG-to-PNG conversion (visual verification)
