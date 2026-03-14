---
name: kicad-schematic
description: >-
  Generate KiCad schematics from design requirements. Use when the user asks to
  create a KiCad schematic, design a circuit board, generate schematics from
  requirements, or work through the hardware design workflow. Covers the full
  flow: requirements, architecture/MCU selection, block design, component
  selection, BOM, and KiCad schematic generation with ERC validation.
argument-hint: "[design description or phase to resume]"
---

# KiCad SchematicBuilder Skill

Generate production-ready KiCad 9 hierarchical schematics from a design description, following a structured 7-phase workflow.

## Prerequisites

This skill works best with these companion skills installed:

- **kicad-file-format** — KiCad S-expression file format reference (for reading/writing `.kicad_sch`, `.kicad_pcb`)
- **jlcpcb-bom-generate-from-kicad** — BOM export for JLCPCB PCB assembly ordering
- **analyze-power-nets** / **find-high-speed-nets** / **plan-pcb-routing** — PCB layout skills (for post-schematic work)

## Required Tools

- `kicad-cli` — KiCad command-line interface (ERC, SVG/PDF export)
- `easyeda2kicad` — LCSC/EasyEDA component import into KiCad format
- `python3` — Script execution
- `fpdf` Python package — PDF generation for workflow documents (`pip install fpdf`)
- `inkscape` (optional) — SVG-to-PNG conversion for visual verification

## Workflow Overview

The skill follows 7 phases. Each phase produces a document in `workflow/` and requires user review before proceeding.

| Phase | Output | Description |
|-------|--------|-------------|
| 1. Requirements | `workflow/01-requirements.md` | Parse design input, structure requirements |
| 2. Architecture | `workflow/02-architecture.md` | MCU selection, system architecture |
| 3. Block Design | `workflow/03-block-design.md` | Decompose into schematic blocks with interfaces |
| 4. Components | `workflow/04-component-selection.md` | Select components with LCSC part numbers |
| 5. BOM | `workflow/05-bom.md` + `.csv` | Bill of materials, library availability check |
| 6. KiCad Project | `workflow/06-kicad-project.md` | Project setup, component import, hierarchy |
| 7. Schematics | `scripts/gen_*.py` + `.kicad_sch` | Generate all schematic sheets |

### Resuming

If $ARGUMENTS specifies a phase number (e.g., "phase 3" or "resume at block design"), skip to that phase. Otherwise, start from Phase 1.

---

## Phase 1: Requirements

### Steps
1. Read the user's design description (free-form text in $ARGUMENTS or ask for it)
2. Extract: functional purpose, power source, communication interfaces, MCU preferences, constraints
3. Propose a structured breakdown:
   - **Functional Requirements** — what the design must do
   - **Power Input** — source voltage, type (AC/DC), expected range
   - **Interfaces** — external connections (connectors, protocols, wireless)
   - **MCU/CPU Selection Criteria** — based on user preferences and interface needs
   - **Environmental/Mechanical Constraints** — size, temperature, enclosure
   - **Applicable Standards** — safety, EMC, regulatory
   - **Out of Scope** — explicitly state what is NOT part of this design
4. Iterate with user until requirements are agreed
5. Save to `workflow/01-requirements.md`
6. Generate PDF: `python3 ${CLAUDE_SKILL_DIR}/scripts/md_to_pdf.py workflow/01-requirements.md`

---

## Phase 2: Architecture & MCU Selection

### Steps
1. Based on requirements, identify 2-3 candidate MCUs
2. Compare on: core performance, peripherals (ADC, GPIO, UART, SPI, I2C), WiFi/BT, power consumption, package size, cost, toolchain maturity
3. Present tabulated comparison with recommendation and rationale
4. User reviews and selects MCU
5. Document system architecture:
   - Power path (input → regulation → rails)
   - Signal domains (isolation boundaries if applicable)
   - Key design decisions and trade-offs
6. Save to `workflow/02-architecture.md` + generate PDF

---

## Phase 3: Block-Level Design

### Steps
1. Decompose architecture into schematic blocks — each block becomes a KiCad hierarchical sheet
2. For each block, document:
   - **Purpose** — what the block does
   - **Function** — how it works
   - **Interfaces** — inputs, outputs, power pins (these become hierarchical labels)
   - **Domain** — which power/ground domain
   - **Design Notes** — key considerations
3. Create signal and power bus summary table (all inter-block connections)
4. Create block interconnect diagram showing block-to-block wiring
5. If applicable, document isolation boundary crossings
6. Include a design verification checklist
7. Save to `workflow/03-block-design.md` + generate PDF

---

## Phase 4: Component Selection

### Steps
1. For each block, propose components:
   - 2-3 alternatives for critical/active components
   - Consider: price, LCSC availability, package (SMT preferred), datasheet specs
   - Include LCSC part numbers for all components
2. Present options with rationale; user reviews and selects
3. Document rejected alternatives with reasons
4. List common passives shared across blocks
5. Include preliminary BOM summary with cost estimate
6. Save to `workflow/04-component-selection.md` + generate PDF

---

## Phase 5: Bill of Materials

### Steps
1. Compile complete BOM from Phase 4 with columns:
   - Item, Block, Designator, Description, Manufacturer, MPN, Package, LCSC, Qty, Unit Price, KiCad Symbol, KiCad Footprint, Status
2. Check KiCad standard library availability for each component:
   - **Available** — symbol and footprint in standard KiCad libs
   - **Substitute** — map to equivalent standard library symbol
   - **Import** — needs easyeda2kicad import (flag these)
3. Export BOM as CSV: `workflow/05-bom.csv`
4. Save to `workflow/05-bom.md` + generate PDF

---

## Phase 6: KiCad Project Structure

### Steps
1. **Import missing components** (flagged in Phase 5):
   ```bash
   cd <project_dir>
   easyeda2kicad --full --lcsc_id <LCSC_ID> --output ./<project>.kicad_sym --project-relative
   # Fix footprint library references:
   sed -i 's|easyeda2kicad:|<project>:|g' <project>.pretty/*.kicad_mod
   ```
   Create `sym-lib-table` and `fp-lib-table` in project dir.

2. **Create KiCad project** — ask user for: project name, author, company
   - Create `.kicad_pro` with ERC configuration (see ERC section below)
   - Create root schematic with title block

3. **Create hierarchical sheet structure**:
   - Generate root schematic with `gen_top_level.py` pattern
   - Create empty child sheets for each block
   - Verify with `kicad-cli sch export svg`

4. Save to `workflow/06-kicad-project.md` + generate PDF

---

## Phase 7: Schematic Generation

### Steps
1. **Copy `kicad_sch_gen.py`** from `${CLAUDE_SKILL_DIR}/scripts/` into the project's `scripts/` folder
2. **Copy `md_to_pdf.py`** from `${CLAUDE_SKILL_DIR}/scripts/` into the project's `scripts/` folder
3. For each block, write a generator script (`scripts/gen_<block>.py`) that:
   - Uses `SchematicBuilder` from `kicad_sch_gen.py`
   - Loads required symbols with `sb.add_lib()`
   - Places components with `sb.place_sym()`
   - Routes wires with `sb.add_wire()`
   - Adds hierarchical labels matching the block interfaces from Phase 3
   - Adds power symbols with `sb.place_power()`
   - Writes the `.kicad_sch` file with `sb.write()`
4. Write `gen_top_level.py` for the root schematic (sheet frames + global labels)
5. Run all generators
6. Run ERC: `kicad-cli sch erc --output /tmp/erc.rpt --exit-code-violations <root.kicad_sch>`
7. Fix any ERC errors, re-run until clean
8. Export SVG for visual verification: `kicad-cli sch export svg --output /tmp/ <root.kicad_sch>`
9. Optionally convert to PNG for review: `inkscape --export-type=png /tmp/<sheet>.svg`

### Generator Script Pattern

See `${CLAUDE_SKILL_DIR}/examples/` for complete working examples. The basic pattern:

```python
#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from kicad_sch_gen import SchematicBuilder, snap, STUB

# UUIDs (generate once, keep stable)
ROOT_UUID       = "..."  # from root schematic
SHEET_INST_UUID = "..."  # from root schematic's sheet entry
SHEET_UUID      = "..."  # this sheet's own UUID

# KiCad symbol library paths
DEVICE_LIB = "/usr/share/kicad/symbols/Device.kicad_sym"
POWER_LIB  = "/usr/share/kicad/symbols/power.kicad_sym"

def main():
    sb = SchematicBuilder(
        project_name="my-project",
        root_uuid=ROOT_UUID,
        sheet_inst_uuid=SHEET_INST_UUID,
        sheet_uuid=SHEET_UUID,
        title="Block Name",
        date="2026-01-01",
        rev="0.1",
        company="Company",
        author="Author",
        comment2="Block description",
        page="2",
    )

    # Load symbols
    sb.add_lib("Device", DEVICE_LIB, ["R", "C", "LED"])
    sb.add_lib("power", POWER_LIB, ["+3V3", "GND"])

    # Place components
    sb.place_sym("Device:R", 80, 60, 0, "R1", "1k",
                 "Resistor_SMD:R_0603_1608Metric", ["1", "2"])

    # Connect power
    sb.place_power("+3V3", 80, 56.19)  # pin2 top
    sb.place_power("GND", 80, 63.81)   # pin1 bottom

    # Add hierarchical labels (interfaces to other blocks)
    sb.add_hlabel("SIGNAL_IN", 72.38, 60, 180, "input")

    # Write output
    sb.write(os.path.join("..", "my-project", "block_name.kicad_sch"))

if __name__ == "__main__":
    main()
```

---

## SchematicBuilder API Reference

### Constructor
```python
SchematicBuilder(project_name, root_uuid, sheet_inst_uuid, sheet_uuid,
                 title="", date="", rev="", company="", author="",
                 comment2="", paper="A4", page="1")
```

### Symbol Management
- `sb.add_lib(lib_prefix, lib_path, sym_names)` — Extract symbols from `.kicad_sym` and embed in schematic
  - Handles KiCad 6->9 format upgrade automatically
  - Flattens derived symbols (`extends`)
  - `lib_prefix`: e.g., `"Device"`, `"power"`, `"Connector"`, or project name for custom libs

### Component Placement
- `sb.place_sym(lib_id, x, y, angle, ref, value, footprint, pin_nums, unit=1, mirror=None)`
  - `lib_id`: Fully-qualified name, e.g., `"Device:R"`
  - `angle`: 0, 90, 180, or 270
  - `pin_nums`: List of pin number strings, e.g., `["1", "2"]`
  - `unit`: For multi-unit ICs (e.g., quad NAND gates)
  - `mirror`: `"x"` or `"y"` axis, or `None`

- `sb.place_power(net_name, x, y)` — Place power symbol with auto wire stub
  - GND variants: symbol placed at `y + 7.62` (below), stub wire down
  - VCC/+3V3/etc: symbol placed at `y - 7.62` (above), stub wire up
  - PWR_FLAG: placed directly at (x, y), no stub

### Wiring and Labels
- `sb.add_wire(x1, y1, x2, y2)` — Wire between two points
- `sb.add_junction(x, y)` — Junction at multi-wire crossing
- `sb.add_no_connect(x, y)` — No-connect marker for unused pins
- `sb.add_net_label(name, x, y, angle=0)` — Local net label with STUB wire
- `sb.add_hlabel(name, x, y, angle, shape)` — Hierarchical label with STUB wire
  - `shape`: `"input"`, `"output"`, `"bidirectional"`, `"passive"`
- `sb.add_global_label(name, x, y, angle, shape)` — Global label with STUB wire

### Output
- `sb.assemble()` — Return complete schematic as string
- `sb.write(filepath)` — Write `.kicad_sch` file

---

## Coordinate Conventions

- **All coordinates in mm**, snapped to 1.27mm grid via `snap()`
- **STUB = 7.62mm** — wire stub length for all labels and power symbols
- **Symbol libraries use Y-up; schematics use Y-down**
  - Schematic pin position: `(origin_x + sym_x, origin_y - sym_y)` for angle=0
  - For angle=90: offset (x,y) becomes (+y, -x) in schematic
  - For angle=180: offset (x,y) becomes (-x, +y)
  - For angle=270: offset (x,y) becomes (-y, +x)
- **Passive components** (R, C, L) at angle=0: pin1 at (0, +3.81) bottom, pin2 at (0, -3.81) top
- **LED** at angle=0: cathode at (-3.81, 0) left, anode at (+3.81, 0) right

### Layout Spacing Guidelines
- Place components on 2.54mm grid
- Pin spacing on hierarchical sheet frames: 5.08mm
- Inter-column gap for facing global labels: minimum 45mm (2x STUB + label text)
- Watch for overlapping power stubs at same x-coordinate (GND goes 7.62mm down, VCC goes 7.62mm up)
- Verify readability with SVG export after generation

---

## Schematic Design Rules

### One Hierarchical Label Per Net Per Sheet
- Each `add_hlabel()` name may appear only ONCE per sheet
- For additional connections to the same net, use `add_net_label()` with the same name
- This causes `same_local_global_label` ERC warnings — suppress in project settings (see below)

### Symbol Libraries Are Read-Only
- Never modify `.kicad_sym` files
- easyeda2kicad imports produce "unspecified" pin types — this is a known limitation, not a bug
- Handle via ERC configuration, not by editing symbols

### PCB Pads Need Schematic Symbols
- Every PCB solder pad needs a schematic symbol
- Use `Connector:TestPoint` with `TestPoint:TestPoint_Pad_2.0x2.0mm` footprint as default

### USB-C 14P Connectors
- easyeda2kicad USB-C 14P connectors have separate A-side and B-side data pins at different symbol positions
- Both sides must be wired: connect B7->A7 (D-) and B6->A6 (D+) with wires + junctions

---

## ERC Configuration

Add this `erc` section at the **JSON root level** of `.kicad_pro` (NOT inside `"schematic"`):

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
- `same_local_global_label: ignore` — deliberate pattern from one-hlabel-per-net rule
- `pin_not_driven: warning` — easyeda2kicad GPIO pins are "unspecified", don't satisfy KiCad's "driven" check for input pins

**Expected acceptable warnings after clean ERC:**
- `lib_symbol_mismatch` — embedded symbols differ from installed KiCad library versions (cosmetic)
- `pin_not_driven` — input pins driven by easyeda2kicad "unspecified" GPIOs

---

## easyeda2kicad Import Procedure

```bash
cd <project_dir>

# 1. Download component (appends to existing library files)
easyeda2kicad --full --lcsc_id <LCSC_ID> --output ./<project>.kicad_sym --project-relative

# 2. Fix footprint library references (MUST DO after every import)
sed -i 's|easyeda2kicad:|<project>:|g' <project>.pretty/*.kicad_mod

# 3. Create library registration files (once per project)
cat > sym-lib-table << 'EOF'
(sym_lib_table
  (version 7)
  (lib (name "<project>")(type "KiCad")(uri "${KIPRJMOD}/<project>.kicad_sym")(options "")(descr ""))
)
EOF

cat > fp-lib-table << 'EOF'
(fp_lib_table
  (version 7)
  (lib (name "<project>")(type "KiCad")(uri "${KIPRJMOD}/<project>.pretty")(options "")(descr ""))
)
EOF
```

---

## Examples

Working example scripts from a reference project (Marklin WiFi AC train controller) are in `${CLAUDE_SKILL_DIR}/examples/`. These demonstrate real-world usage of every SchematicBuilder feature:

| Example | Block | Demonstrates |
|---------|-------|-------------|
| `gen_connectors.py` | Test point connectors | Minimal layout, hlabel stubs |
| `gen_status_led.py` | GPIO LED | LED polarity, simple signal path |
| `gen_power_supply.py` | AC-DC buck converter | Complex multi-stage, PWR_FLAG, net labels |
| `gen_esp32_c3.py` | MCU with boot circuit | Large IC, decoupling caps, many pins |
| `gen_hw_interlock.py` | Quad NAND interlock | Multi-unit IC, spare gate tie-off |
| `gen_triac_drive.py` | Dual TRIAC channels | Parameterized multi-instance, snubber |
| `gen_zero_crossing.py` | Optocoupler ZC detect | Diode bridge, isolation boundary |
| `gen_voltage_sense.py` | Isolated ADC input | RC filter, ESD clamp |
| `gen_usb_prog.py` | USB-C interface | Complex connector, ESD protection |
| `gen_top_level.py` | Root hierarchy sheet | Sheet frames, global labels, layout grid |

**These are EXAMPLES from a specific project.** Do not copy them verbatim — adapt the patterns to the current design.
