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
   - Places components with `sb.place_sym()` + `sb.register_pin()` for each pin
   - Routes wires with `sb.add_wire()` following the Wiring Recipes
   - Adds hierarchical labels matching the block interfaces from Phase 3
   - Adds power symbols with `sb.place_power()`
   - Writes the `.kicad_sch` file with `sb.write()` — **must print `[CLEAN]`**
4. Write `gen_top_level.py` for the root schematic (sheet frames + global labels)
5. Run all generators — **fix all validation warnings before proceeding**
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
  - GND variants: symbol placed at `y + 7.62` (below), stub wire down, arrow points down
  - Negative rails (`-5V`, `-5VA`, `-6V`, etc.): same as GND — stub DOWN, arrow points down
  - Positive rails (`+3V3`, `+5V`, `+5VA`, etc.): symbol at `y - 7.62` (above), stub wire up, arrow points up
  - PWR_FLAG: placed directly at (x, y), no stub

### Wiring, Buses, and Labels
- `sb.add_wire(x1, y1, x2, y2)` — Wire between two points
- `sb.add_bus_alias(name, members)` — Define a bus alias (e.g., `"SPI"` → `["SPI_MOSI",...]`). Use `{SPI}` in labels.
- `sb.add_bus(x1, y1, x2, y2)` — Bus wire (thick line for signal groups)
- `sb.add_bus_entry(x, y, dx, dy)` — Diagonal bus entry connecting wire to bus
- `sb.add_bus_tap(name, bus_x, tap_y, side, shape)` — Complete bus tap: entry + wire + label
- `sb.add_junction(x, y)` — Junction at multi-wire crossing
- `sb.add_no_connect(x, y)` — No-connect marker for unused pins
- `sb.add_net_label(name, x, y, angle=0)` — Local net label with STUB wire
- `sb.add_hlabel(name, x, y, angle, shape)` — Hierarchical label with STUB wire
  - `shape`: `"input"`, `"output"`, `"bidirectional"`, `"passive"`
- `sb.add_global_label(name, x, y, angle, shape)` — Global label with STUB wire

### Pin & Body Registration (for validation)
- `sb.register_pin(x, y, ref="", pin="")` — Register a pin tip position for mid-wire checks
- `sb.register_body(cx, cy, half_w, half_h, angle=0, ref="")` — Register component body rectangle for wire-through-body checks

**Fence constants** for common passives — keep-out zone covering body + pins + 1.27mm clearance:
- `BODY_R = (2.54, 5.08)` — Device:R fence (body + pins + clearance)
- `BODY_C = (3.81, 5.08)` — Device:C fence (wider plates + pins + clearance)
- `BODY_L = (2.54, 5.08)` — Device:L fence (same as R)
- `BODY_LED = (5.08, 2.54)` — Device:LED fence (horizontal pins + clearance)
- `BODY_D = (5.08, 2.54)` — Device:D fence (same as LED)

**Auto-registration**: ALL `place_sym()` calls automatically register both the fence AND the pin positions:
- **Known passives** (R, C, L, LED, D): use predefined fence constants
- **All other components** (ICs, connectors, relays, etc.): fence is computed from the symbol's actual pin positions plus 2.54mm clearance on each side. Pin positions are parsed from the embedded lib_symbols.

No manual `register_body()` or `register_pin()` calls needed — all components are fenced automatically.

**Power symbols** are also fenced: `place_power()` registers a 3.81mm fence around each GND/VCC symbol graphic. The stub wire is exempted via pin registration. This prevents other wires from crossing through power symbol graphics.

**Pin exemption**: Wires connecting to a registered pin of the component are allowed inside the fence. Only non-connecting wires are flagged.

Manual `register_body()` can still be used to override or add custom fences if needed.

### Net Declaration (post-generation validation)
- `sb.declare_net(name, pins)` — Declare intended connectivity: all listed `(ref, pin)` tuples must be on the same net
- `sb.check_nets(root_sch_path)` — Export netlist via kicad-cli and compare against declarations

Catches shorts and open circuits that geometric validation cannot detect:
```python
sb.declare_net("VREF", [("U202", "5"), ("R205", "2")])
sb.declare_net("FB",   [("U202", "6"), ("R205", "1"), ("R204", "1")])
sb.declare_net("VOUT", [("R204", "2"), ("L202", "2")])

sb.write("output.kicad_sch")
errors = sb.check_nets("/path/to/root.kicad_sch")
# Reports: SHORT if VREF and FB end up on the same net
#          OPEN if R205:1 and R204:1 are on different nets
```

### Validation
- `sb.validate()` — Run geometric wiring checks, return list of issue strings (empty = clean)

### Output
- `sb.assemble()` — Return complete schematic as string
- `sb.write(filepath, validate=True)` — Write `.kicad_sch` file (runs validation by default)

---

## Coordinate Conventions

- **All coordinates in mm**, snapped to 1.27mm grid via `snap()`
- **Hierarchical sheet boxes are fenced** — register each sheet box as a body so wires cannot route through it. Use `sb.register_body(cx, cy, w/2, h/2, ref="SheetName")` after placing a sheet box.
- **Reduce sheet box size** — sheet boxes should be as compact as possible (just enough for pin labels). Large boxes waste space and make routing harder.
- **Sheet pin justify** — left-side pins use `(justify left)`, right-side pins use `(justify right)` to keep labels inside the box.
- **Hierarchical sheet boxes and their pins must also be snapped** — SchematicBuilder auto-snaps wires/labels, but raw s-expression sheet entries (position, size, pin coordinates) must be manually snapped with `snap()`. If sheet pin positions are off-grid, wires from SchematicBuilder won't connect to them and KiCad ERC will report `hier_label_mismatch` and `unconnected_wire_endpoint` errors.
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

### Wiring Rules

These rules are enforced by `sb.validate()` which runs automatically on `sb.write()`. Fix all ERRORs and WARNINGs before declaring a sheet complete.

1. **Wire segments must terminate at pin locations** — KiCad does NOT connect a pin that falls in the middle of a wire segment. Break long bus wires into segments that end at each component pin.
2. **Prefer direct wires over net labels** — Use net labels only when wires would cross or span long distances (>50mm). For nearby connections, use a wire.
3. **Add junctions at T-intersections** — Where three or more wire endpoints meet, add `sb.add_junction()`.
4. **Wires must extend OUT from component pins** — Never route a wire back into or through a component body. Route around components so wires approach pins from outside.
5. **Output hlabels on rightmost symbols** — Place input hlabels on the left side and output hlabels on the rightmost symbols for left-to-right signal flow.
6. **No overlapping collinear wires** — KiCad merges overlapping wires at the same x or y, losing intermediate endpoints. This includes label stubs and power stubs.
7. **All wires must be horizontal or vertical** — No diagonal wires. Use L-shaped bends.
8. **One hlabel per net per sheet** — Use `add_net_label()` for additional connections to the same net.
9. **Register pins for validation** — After `place_sym()`, call `sb.register_pin(x, y, ref, pin)` for each pin. The validator checks registered pins don't fall mid-wire.

---

## Wiring Recipes

Concrete patterns that prevent the most common wiring violations. Each recipe shows the WRONG way (what causes errors) and the RIGHT way.

### Recipe 1: Connecting an IC pin to a horizontal bus above

**Problem**: IC has VIN at (82, 62). Bus is at y=40. Other pins (SW, GND) are on the same x-column between VIN and the bus.

**WRONG** — straight vertical wire through other pins:
```python
sb.add_wire(82, 62, 82, 40)  # passes through SW at (82,60) and GND at (82,57)
```

**RIGHT** — route out sideways first, then up, avoiding the pin column:
```python
escape_x = 82 - 5.08  # step left, away from pin column
sb.add_wire(82, 62, escape_x, 62)        # horizontal escape
sb.add_wire(escape_x, 62, escape_x, 40)  # vertical to bus
sb.add_wire(escape_x, 40, 82, 40)        # horizontal to bus tap point
sb.add_junction(82, 40)                   # if bus wire passes through
```

**General rule**: For any IC pin, first route OUTWARD (left-side pins go left, right-side pins go right), then route vertically to the destination.

### Recipe 2: Multi-tap horizontal bus wire

**Problem**: A horizontal bus at y=40 needs to connect to components at x=55, x=82, x=108. Components connect via vertical drop wires.

**WRONG** — single long wire with T-junctions:
```python
sb.add_wire(40, 40, 260, 40)  # one long segment
sb.add_wire(55, 40, 55, 52)   # drop to component
sb.add_wire(82, 40, 82, 62)   # drop to component
# Problem: (55,40) and (82,40) fall mid-wire on the bus segment
```

**RIGHT** — break bus into segments ending at each tap:
```python
sb.add_wire(40, 40, 55, 40)    # segment 1
sb.add_wire(55, 40, 82, 40)    # segment 2
sb.add_wire(82, 40, 108, 40)   # segment 3
sb.add_wire(108, 40, 260, 40)  # segment 4
# Now drops connect at segment endpoints:
sb.add_wire(55, 40, 55, 52)
sb.add_junction(55, 40)
sb.add_wire(82, 40, 82, 62)
sb.add_junction(82, 40)
```

**General rule**: Every point where another wire meets a bus must be a segment endpoint, not a midpoint.

### Recipe 3: Power symbol stubs — avoiding overlaps

**Problem**: Two GND symbols on the same IC at the same x-coordinate create overlapping vertical stubs.

`place_power("GND", x, y)` creates a wire from (x, y) down to (x, y+7.62). If two GND stubs share the same x and their y-ranges overlap, KiCad merges them.

**WRONG** — two GND stubs at same x:
```python
sb.place_power("GND", 100, 80)   # stub: (100, 80) to (100, 87.62)
sb.place_power("GND", 100, 75)   # stub: (100, 75) to (100, 82.62)
# Overlap at y=80 to y=82.62!
```

**RIGHT** — offset x for the second GND, connect with a wire:
```python
sb.place_power("GND", 100, 80)   # first pin gets direct GND
gnd_x = 100 + 5.08               # offset second GND sideways
sb.add_wire(100, 75, gnd_x, 75)  # horizontal escape
sb.place_power("GND", gnd_x, 75) # GND at offset position
```

**Alternative** — use a shared GND bus wire:
```python
gnd_bus_y = 90  # below both pins
sb.add_wire(100, 80, 100, gnd_bus_y)
sb.add_wire(100, 75, 100, 80)     # connect second pin to first wire
sb.add_junction(100, 80)
sb.place_power("GND", 100, gnd_bus_y)
```

The same applies to VCC stubs going upward. Check y-ranges: VCC stubs go from y to y-7.62.

### Recipe 4: Net label stubs — hidden wire awareness

Every `add_net_label()` and `add_hlabel()` creates a 7.62mm wire stub. This stub is a real wire that can overlap with other wires.

**WRONG** — explicit wire overlaps label stub:
```python
sb.add_wire(50, 60, 60, 60)         # explicit wire
sb.add_net_label("SIG", 60, 60, 0)  # stub from (60,60) to (67.62,60)
sb.add_wire(60, 60, 70, 60)         # overlaps the stub!
```

**RIGHT** — let the stub BE the wire, or start the explicit wire where the stub ends:
```python
sb.add_wire(50, 60, 60, 60)         # wire to pin
sb.add_net_label("SIG", 60, 60, 0)  # stub from (60,60) to (67.62,60) — this IS the connection
# No additional wire needed — the label stub connects at (60,60)
```

### Recipe 5: IC pin routing — never through the body

**Problem**: Need to wire an op-amp's output back to -IN for feedback. Both pins are on the same IC.

**WRONG** — wire through the IC body:
```python
# OPA output at (111.43, 72.38), -IN at (111.43, 74.92)
sb.add_wire(111.43, 72.38, 111.43, 74.92)  # vertical through IC body
```

**RIGHT** — route outside the body:
```python
out_pin = (111.43, 72.38)
nin_pin = (111.43, 74.92)
fb_x = 111.43 + 15  # route right, outside the body
sb.add_wire(out_pin[0], out_pin[1], fb_x, out_pin[1])  # horizontal out
sb.add_wire(fb_x, out_pin[1], fb_x, nin_pin[1])        # vertical
sb.add_wire(fb_x, nin_pin[1], nin_pin[0], nin_pin[1])   # horizontal back
```

**General rule**: Left-side IC pins → route LEFT then around. Right-side pins → route RIGHT then around. Top pins → route UP. Bottom → DOWN. Never cross through the component rectangle.

### Recipe 6: Computing connector pin positions

Connector pins are NOT at the component center. They have specific offsets that vary by symbol.

**Common mistake**: Assuming pins are at `(cx + 3.81, cy + offset)` when they're actually at `(cx - 5.08, cy + offset)`.

**Process**: Before wiring to any non-trivial symbol:
1. Open the `.kicad_sym` file or use KiCad's symbol editor
2. Find each pin's library coordinates: `(pin ... (at X Y angle))`
3. Apply the rotation transform to get schematic coordinates
4. Register pins for validation:

```python
# Example: Conn_01x04 at (100, 45), angle=0
# Library pins are at (-5.08, 2.54), (-5.08, 0), (-5.08, -2.54), (-5.08, -5.08)
# Schematic (y-flip): pin_x = 100 + (-5.08) = 94.92
#                      pin1_y = 45 - 2.54 = 42.46, pin2_y = 45 - 0 = 45, etc.
conn_pins = [(94.92, 42.46), (94.92, 45.0), (94.92, 47.54), (94.92, 50.08)]
for i, (px, py) in enumerate(conn_pins):
    sb.register_pin(px, py, "J1", str(i + 1))
```

### Recipe 7: LED polarity for left-to-right current flow

**WRONG** — LED at angle=0 has current flowing right-to-left (A→K):
```python
# angle=0: K(cathode) at left (-3.81, 0), A(anode) at right (+3.81, 0)
# Current flows: right(A) → left(K) — BACKWARDS for left-to-right signal flow
sb.place_sym("Device:LED", lx+15, ly, 0, "D1", "GREEN", fp, ["1", "2"])
sb.add_wire(lx+3.81, ly, lx+15-3.81, ly)   # R → cathode (wrong!)
sb.place_power("GND", lx+15+3.81, ly)       # GND at anode (wrong!)
```

**RIGHT** — use angle=180 for left-to-right current flow:
```python
# angle=180: A(anode) at left (-3.81, 0), K(cathode) at right (+3.81, 0)
# Current flows: left(A) → right(K) — correct for left-to-right signal flow
# Circuit: GPIO → R → A(left) → K(right) → GND
sb.place_sym("Device:LED", lx+15, ly, 180, "D1", "GREEN", fp, ["1", "2"])
sb.add_wire(lx+3.81, ly, lx+15-3.81, ly)   # R pin1 → anode
sb.place_power("GND", lx+15+3.81, ly)       # GND at cathode
```

### Recipe 8: Facing hierarchical sheet pins — direct wires vs labels

**Problem**: Two sheet boxes face each other with a 45mm gap. Their pins carry the same signals.

**WRONG** — global labels for every facing pair:
```python
# Sheet A right-side pin at (76.20, 106.68)
glabel("SPI_MOSI", 76.20 + STUB, 106.68, 0)
# Sheet B left-side pin at (121.92, 106.68) — same y!
glabel("SPI_MOSI", 121.92 - STUB, 106.68, 180)
# Creates two redundant global labels when a wire would work
```

**RIGHT** — direct wire for facing pins at same y:
```python
sb.add_wire(76.20, 106.68, 121.92, 106.68)  # direct horizontal connection
```

**RIGHT** — L-bend wire for facing pins at different y:
```python
# Sheet A pin at (76.20, 106.68), Sheet B pin at (121.92, 111.76)
mid_x = (76.20 + 121.92) / 2  # or snap to grid
sb.add_wire(76.20, 106.68, mid_x, 106.68)
sb.add_wire(mid_x, 106.68, mid_x, 111.76)
sb.add_wire(mid_x, 111.76, 121.92, 111.76)
```

**Use global labels only when**: pins are on different rows/columns with many intervening sheets, or wires would need to cross other sheet boxes.

---

## Validation

`SchematicBuilder.validate()` runs automatically when you call `sb.write()`. It checks:

| Check | Type | What it catches |
|-------|------|-----------------|
| Diagonal wires | ERROR | Non-orthogonal wire segments |
| Duplicate hlabels | ERROR | Same hlabel name used twice on one sheet |
| Overlapping collinear wires | WARNING | Wire segments on same line with overlapping ranges |
| Mid-wire points | WARNING | Wire endpoints or registered pins falling inside another segment |
| Missing junctions | WARNING | 3+ wire endpoints meeting without a junction marker |
| Wire through fence | WARNING | Wire inside component keep-out zone without connecting to a pin |
| Power stub isolation | ERROR | Power symbol's far endpoint touches another wire — accidental short |
| Symbol inside fence | WARNING | A symbol (component or power) placed inside another component's fence |

### Using `register_pin()` for pin validation

After placing a component, register its pin positions so the validator can check they don't fall mid-wire:

```python
sb.place_sym("Device:R", 80, 60, 0, "R1", "1k", fp, ["1", "2"])
sb.register_pin(80, 63.81, "R1", "1")  # pin1 bottom
sb.register_pin(80, 56.19, "R1", "2")  # pin2 top
```

For ICs with many pins, create a helper:
```python
def register_ic_pins(sb, cx, cy, pin_offsets, ref):
    """Register IC pins from library offsets (y-up) to schematic coords (y-down)."""
    for pin_num, (lib_x, lib_y) in pin_offsets.items():
        sb.register_pin(cx + lib_x, cy - lib_y, ref, pin_num)
```

### Workflow gate

A sheet is **not ready** until `sb.write()` prints `[CLEAN]`. The workflow is:
1. Write the generator script
2. Run it — check validation output
3. Fix all ERRORs and WARNINGs
4. Re-run until `[CLEAN]`
5. Run ERC: `kicad-cli sch erc --exit-code-violations`
6. Export SVG for visual check

### All Validation Must Pass — Blocking Gate
- **All validators must pass before proceeding to the next workflow phase.**
- This includes:
  1. **SchematicBuilder `sb.write()` → `[CLEAN]`** for every generator script
  2. **Net validation `sb.check_nets()` → PASS** for sheets with declared nets
  3. **KiCad ERC → 0 errors** across the full project
- ERC warnings that are understood and documented (e.g., cosmetic bus entry geometry, easyeda2kicad footprint paths) may be accepted but must be listed in `07-schematics.md`.
- ERC errors (shorts, unconnected pins, hierarchy mismatches) are **blockers** — they must be fixed before any further work.
- If an error cannot be fixed, escalate to the user. **Never suppress errors** to proceed.
- **Final validation pass**: As the last step before generating phase reports and moving to the next phase, re-run ALL generators and full-project ERC to catch any regressions. Document the results in `07-schematics.md`.

### Keeping the report file current

`workflow/07-schematics.md` must be updated after every significant schematic change:
- Update the generator table, file sizes, hierarchy structure
- Update ERC status (current violation count and breakdown)
- Add notes about symbol pin remapping candidates
- Add notes about pending readability improvements
- Do NOT regenerate the PDF until moving to the next workflow phase — the markdown is the working document

### Readability requirements

1. **Descriptive text annotations** — add `(text "..." ...)` near each functional block explaining its purpose (e.g., "Buck converter: 12V → 5V digital")
2. **Frame boxes** — use dashed rectangles around functional groups on complex sheets (power supply sections, relay blocks, etc.)
3. **Signal name labels on key wires** — for critical internal signals (feedback nodes, sense outputs), add a net label even if the wire connects directly. This documents intent, not connectivity.
4. **Symbol pin remap notes** — when a component symbol would benefit from pin rearrangement (like TPS562201 was remapped), note it in `07-schematics.md` under "Symbol Improvement Candidates". Do NOT edit symbols unless told to.

---

## Schematic Design Rules

### Power Rails Are Global — Use Power Symbols, Never Hlabels
- All power rails and GND nets shall use **KiCad power symbols** (`sb.place_power()`), not hierarchical labels or global labels.
- Power symbols create global nets automatically — they connect across ALL sheets without wiring through the hierarchy.
- **Never** use `add_hlabel()` for power/GND. **Never** add power pins to hierarchical sheet boxes.
- Use only power net names that exist in the KiCad standard power library. Common names:
  `GND`, `+3V3`, `+5V`, `+5VA`, `-5VA`, `+5VD` (digital), `+12V`, `-5V`, `-6V`
- **Never** invent custom power net names (e.g. `+5V_DIG`, `+6V5`). Use the closest standard name, or keep custom names as local `add_net_label()` within a single sheet.
- The power supply sheet places `place_power("+5VA", x, y)` at its output; all other sheets place the same `place_power("+5VA", x, y)` at their consumption points. KiCad connects them globally.
- **One PWR_FLAG per net** — place it on the power supply sheet where the rail is created. Do not add duplicate PWR_FLAGs on the same net in other sheets.
- This eliminates power wiring on parent pages and keeps the hierarchy clean — only signal pins appear on sheet boxes.

### One Hierarchical Label Per Net Per Sheet
- Each `add_hlabel()` name may appear only ONCE per sheet
- For additional connections to the same net, use `add_net_label()` with the same name
- This causes `same_local_global_label` ERC warnings — suppress in project settings (see below)

### Use Buses for Signal Groups (3+ signals, or common interfaces)
- When a sheet has a group of related signals, use a KiCad bus to collect them
- Apply to: numbered groups (ELEC_1..16), protocol buses (SPI, I2C), control groups (MUX address)
- Bus naming: `ELEC_[1..16]`, `SPI[0..3]`, `I2C[0..1]` — matches KiCad bus syntax
- Individual signals connect to the bus via bus entries (diagonal stubs)
- Signals must be ordered: lowest number on top, cascading down
- Apply to both hierarchical sheet pins (parent page) and hlabels inside sub-sheets
- Common interface buses even with only 2 signals (e.g., I2C) should use bus notation — it's standard practice and improves readability
- Internal signal groups within a single sheet (e.g., FMC data/address) should also use bus routing for readability
- **Bus aliases for named groups**: When bus members don't follow a numbered pattern (e.g., SPI_MOSI/MISO/CLK/CS), define a bus alias with `sb.add_bus_alias("SPI", ["SPI_MOSI", "SPI_MISO", "SPI_CLK", "SPI_CS_ADC"])` and use `{SPI}` as the bus name instead of the verbose `{SPI_MOSI,SPI_MISO,SPI_CLK,SPI_CS_ADC}`. **Never** put long comma-separated member lists in hlabels — always use aliases for named buses.

### All Coordinates Must Be Snapped — Including Raw S-Expressions
- Any code that generates raw KiCad s-expressions (not through SchematicBuilder) must snap ALL coordinates with `snap()`.
- This includes `gen_top_level.py` which builds sheet frames, wires, and global labels directly.
- Floating point arithmetic (e.g., `x + 7.62`) can produce values like `111.75999999999999` instead of `111.76`. KiCad treats these as different points — wires won't connect.
- Always: `snap(x + 7.62)` not `x + 7.62`.

### Every Sheet Pin Must Have a Wire
- KiCad requires a physical wire touching each hierarchical sheet pin — name-based connection alone is not enough.
- For every sheet pin: draw a wire from the pin to a net label (or hlabel) with the matching signal name.
- When using buses: the bus taps create net labels on the bus side, AND each sheet pin needs its own wire + net label on the sheet box side. Both labels share the same name, connecting by name.
- Pattern: `bus_tap("ELEC_1") ←name→ net_label("ELEC_1") ←wire→ sheet_pin("ELEC_1")`
- Missing wires cause `pin_not_connected` and `label_dangling` ERC errors.

### Use Hierarchical Sub-Sheets for Repeated Circuits
- When a design has multiple identical sub-circuits (e.g., 8 AFE channels, multiple buck converters with the same topology), implement them as a single sub-sheet file instantiated multiple times.
- Each instance gets unique reference designators via KiCad's multi-instance mechanism (multiple `(path ...)` entries per component).
- Benefits: one circuit to maintain, guaranteed consistency across instances, smaller schematic files, easier review.
- The sub-sheet uses generic signal names (ELEC_1, ELEC_2) and the parent page maps them to instance-specific nets.
- Use `add_multi_instance()` post-processing to add instance paths, or generate separate files from the same template function if multi-instance is too complex.

### No Redundant Labels — Keep Schematics Clean
- If an hlabel connects directly to a component pin (via its stub wire or a short wire), do **not** add a duplicate `add_net_label()` for that same net on the same page unless it is needed elsewhere on the sheet.
- Only add a net label when the signal must fan out to multiple locations on the same page.
- Redundant labels clutter the schematic and make it harder to read.

### Symbol Libraries Are Read-Only
- Never modify `.kicad_sym` files
- easyeda2kicad imports produce "unspecified" pin types — this is a known limitation, not a bug
- Handle via ERC configuration, not by editing symbols

### LED Current Limiting Resistors — Always Calculate
- **Never use a generic resistor value** for LEDs. Always calculate: `R = (Vsupply - Vf) / Iled`
- Typical values: Vf ≈ 2.0V (green/yellow), Vf ≈ 3.0V (blue/white), Iled ≈ 2mA for indicators
- For positive rails: `+Rail → R → LED(A→K) → GND`. Use LED angle=180 for left-to-right current flow.
- For negative rails: `GND → R → LED(A→K) → -Rail`. Current flows from GND (higher potential) through LED to the negative rail. Same LED angle=180.
- **Check polarity**: LED at angle=0 has K(cathode) at left, A(anode) at right — current flows right-to-left. Use angle=180 to flip for left-to-right flow.

### PCB Pads Need Schematic Symbols
- Every PCB solder pad needs a schematic symbol
- Use `Connector:TestPoint` with `TestPoint:TestPoint_Pad_2.0x2.0mm` footprint as default

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
    "pin_not_driven": "warning",
    "multiple_net_names": "error"
  }
}
```

**Why each rule:**
- `pin_to_pin: ignore` — easyeda2kicad "unspecified" pins trigger false positives
- `same_local_global_label: ignore` — deliberate pattern from one-hlabel-per-net rule
- `pin_not_driven: warning` — easyeda2kicad GPIO pins are "unspecified", don't satisfy KiCad's "driven" check for input pins
- `multiple_net_names: error` — catches accidental shorts where two different net names are connected together. This must be treated as an error, not a warning.

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
