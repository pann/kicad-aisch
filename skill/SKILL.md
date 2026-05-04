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

Generate production-ready KiCad 9 hierarchical schematics from a design description, following a structured 8-phase workflow.

## Prerequisites

This skill works best with these companion skills installed:

- **kicad-file-format** — KiCad S-expression file format reference (for reading/writing `.kicad_sch`, `.kicad_pcb`)
- **jlcpcb-bom-generate-from-kicad** — Converts KiCad-exported BOM and `.pos` files into the JLCPCB PCBA upload format. Handles the column-name conversion (Designation→Comment, etc.) and CPL Y-coordinate negation. Used in Phase 7 (BOM CSV export) and Phase 8 (fab outputs).
- **analyze-power-nets** / **find-high-speed-nets** / **plan-pcb-routing** — PCB layout skills (for post-schematic work)

## Required Tools

- `kicad-cli` — KiCad command-line interface (ERC, SVG/PDF export, BOM CSV export, gerber/drill/CPL export)
- `easyeda2kicad` — LCSC/EasyEDA component import into KiCad format
- `python3` — Script execution
- `fpdf2` Python package — PDF generation for workflow documents (`pip install fpdf2`)
- `inkscape` (optional) — SVG-to-PNG conversion for visual verification

### Recommended companion skills

- **jlcpcb-bom-generate-from-kicad** — Sibling skill. Handles JLCPCB column-name conversion (KiCad `Reference`/`Value` → JLCPCB `Designator`/`Comment`) and CPL Y-coordinate negation (KiCad Y-down → JLCPCB Y-up). Used in Phase 7 (BOM CSV) and Phase 8 (fab outputs).

## Workflow Overview

The skill follows 8 phases. Each phase produces a document in `workflow/` and requires user review before proceeding.

| Phase | Output | Description |
|-------|--------|-------------|
| 1. Requirements | `workflow/01-requirements.md` | Parse design input, structure requirements |
| 2. Architecture | `workflow/02-architecture.md` | MCU selection, system architecture |
| 3. Block Design | `workflow/03-block-design.md` | Decompose into schematic blocks with interfaces |
| 4. Components | `workflow/04-component-selection.md` | Select components with LCSC part numbers |
| 5. BOM Notes | `workflow/05-bom-notes.md` | Engineering rationale for part choices (the *why*); not an assembly file |
| 6. KiCad Project | `workflow/06-kicad-project.md` | Project setup, component import, hierarchy |
| 7. Schematics | `scripts/gen_*.py` + `.kicad_sch` + `<project>_schematics.pdf` + `BOM_jlcpcb.csv` | Generate all schematic sheets, populate LCSC/MPN fields, export PDF + assembly BOM |
| 8. Fab Outputs | `<project>/fab/` (gerbers, drill, BOM CSV, CPL CSV, upload zip) | JLCPCB PCBA upload package |

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

## Phase 5: BOM Notes & Component Selection

The deliverable here is **engineering rationale**, not an assembly spreadsheet. The assembly source of truth (the JLCPCB BOM CSV) is generated mechanically from the schematic in Phase 7 — it is not hand-maintained, and it is **not** produced in this phase. There is no `05-bom.csv` anymore.

`workflow/05-bom-notes.md` captures the *why* behind each part choice so a reviewer (or future-you) can understand the decisions without re-running the comparison.

### Steps
1. For each block / functional group, document component selection rationale:
   - Which parts were selected, with LCSC and MPN
   - Alternatives considered and rejected (with reasons: cost, availability, performance, package, footprint reuse)
   - Why this part won — call out the deciding factor (cheapest in stock, only one with required spec, footprint already used elsewhere, JLCPCB Basic vs Extended status, etc.)
2. Flag DNP candidates with explicit DNP justification — e.g. "calibration branch disabled in production", "debug-only header", "factory programming jumper".
3. Call out **special components** that need narrative beyond a generic LCSC family pick:
   - Precision passives (e.g. 0.1 % thin-film with explicit TCR spec)
   - Polypropylene film capacitors (low-loss audio/signal)
   - Foil resistors, current-sense resistors with Kelvin sense
   - 4-terminal Kelvin sense networks
   - Anything where "any 0603 1k" would be wrong
4. Identify **single-source / consignment parts** and flag stock-margin concerns. If JLCPCB doesn't stock the part (consignment), say so explicitly so it gets the `Source = Consignment` field in Phase 7.
5. Document **deferred decisions** and known stock risks (e.g. "main MCU is sole-sourced from ST; alternative footprint-compatible part TBD if lead time slips").
6. Save to `workflow/05-bom-notes.md` + generate PDF: `python3 ${CLAUDE_SKILL_DIR}/scripts/md_to_pdf.py workflow/05-bom-notes.md`

### Why no CSV here

The CSV that JLCPCB ingests is generated by `kicad-cli sch export bom` from the schematic itself, after Phase 7 populates `LCSC` and `MPN` custom fields on every symbol. Hand-maintaining a parallel CSV in Phase 5 used to drift out of sync the moment a part was swapped in the schematic. The schematic is now the single source of truth; the BOM Notes document is supporting commentary.

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
10. **Add `LCSC` + `MPN` custom fields to every schematic symbol** (see "LCSC/MPN field population" below). This binds the BOM Notes to the actual symbols.
11. **Export the assembly BOM CSV**:
    ```bash
    kicad-cli sch export bom --output BOM_jlcpcb.csv \
        --fields "Reference,Value,Footprint,LCSC,MPN" <root.kicad_sch>
    ```
    This CSV is the **assembly source of truth**. The `05-bom-notes.md` document is rationale, not the bill that gets uploaded.
12. **Export final PDF**: `kicad-cli sch export pdf --output <project-name>_schematics.pdf <root.kicad_sch>`
    - One of the deliverable outputs of Phase 7 — a single PDF containing all schematic pages.

### LCSC/MPN field population

After all sheets are clean and ERC passes, before declaring Phase 7 done, every symbol instance in every `*.kicad_sch` must carry:

- `LCSC` — the JLCPCB part number (e.g. `C150716`)
- `MPN` — the manufacturer part number (e.g. `AP2114H-3.3TRG1`)
- Optional: `Source` set to `Consignment` for parts JLCPCB doesn't stock (per Phase 5 BOM Notes)

Rules:

- For every `(symbol ...)` block in every `.kicad_sch` file, add the `LCSC` and `MPN` properties as KiCad custom fields.
- Set `(hide yes)` on these fields so they don't visually clutter the schematic — they exist only as metadata for BOM export.
- The operation must be **idempotent**: re-running should update existing `LCSC`/`MPN` fields, not duplicate them. If the field already exists, overwrite the value; do not append a second copy.
- Source the values from Phase 5 BOM Notes (`05-bom-notes.md`), keyed by the component reference designator. If a symbol's reference does not have an LCSC/MPN entry in Phase 5, that's a gap — flag it and add it to BOM Notes before proceeding.

After the fields are populated, run `kicad-cli sch export bom` (step 11 above) to generate the assembly CSV. Verify:

- Row count matches the populated symbol count
- No empty `LCSC` cells (except deliberately blank ones for jumpers, mounting holes, fiducials — these should also be marked DNP if not assembled)
- `Footprint` column matches what's actually placed on the PCB (Phase 8)

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

## Phase 8: Fab Outputs (JLCPCB upload)

Generate everything JLCPCB needs for a PCBA order. All outputs go to `<project>/fab/`, which is **`.gitignore`d** — these files are regenerated per release rather than committed. Tag the source commit (e.g. `<project>-hw-1`) instead.

### Steps

1. **Gerbers + drill**
   ```bash
   kicad-cli pcb export gerbers --output <project>/fab/ <project>/<project>.kicad_pcb
   kicad-cli pcb export drill   --output <project>/fab/ <project>/<project>.kicad_pcb
   ```

2. **BOM CSV** (assembly bill of materials, the same one Phase 7 generated)
   ```bash
   kicad-cli sch export bom \
       --output <project>/fab/BOM_kicad.csv \
       --fields "Reference,Value,Footprint,LCSC,MPN" \
       <project>/<project>.kicad_sch
   ```
   JLCPCB expects columns: **Comment** (= Value), **Designator** (= Reference), **Footprint**, **LCSC Part #**. Use the `jlcpcb-bom-generate-from-kicad` companion skill to convert column names — it also handles the JLCPCB-specific quirks (designator sorting, comment formatting).

3. **CPL (Component Placement List)**
   ```bash
   kicad-cli pcb export pos \
       --output <project>/fab/CPL_kicad.csv \
       --format csv --units mm --side both \
       <project>/<project>.kicad_pcb
   ```
   The `jlcpcb-bom-generate-from-kicad` skill negates Y-coordinates (KiCad uses Y-down, JLCPCB CPL expects Y-up), normalises rotation, and emits the JLCPCB-format CPL.

4. **Output package** — produce a single `.zip` with the gerbers + drill + JLCPCB-format BOM + JLCPCB-format CPL:
   ```
   <project>/fab/<project>-<rev>.zip
   ```
   Or three separate files (gerber zip, BOM CSV, CPL CSV) if the JLCPCB UI prefers per-file upload — check the current JLCPCB workflow.

5. **`<project>/fab/` is `.gitignore`d**. Do not commit the generated artefacts. Tag the source commit so the fab outputs can be regenerated deterministically: `git tag -a <project>-hw-1 -m "..."`.

### Verification

Before uploading:
- Open the gerber zip in a viewer (gerbv, KiCad gerber viewer) — confirm all layers present and aligned
- Spot-check the BOM CSV: row count matches Phase 7 export, no empty LCSC cells, no stale parts
- Spot-check the CPL: designator count matches BOM, rotation values are sane (0/90/180/270), Y has been negated relative to KiCad's pos export

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

**Net/hierarchical/global labels** are also fenced: `add_net_label()`, `add_hlabel()`, `add_global_label()`, `add_bus_hlabel()`, and `add_bus_net_label()` automatically register a tight bounding box around the label TEXT. Two checks run on these:
- **Label-vs-label overlap** — flagged when two labels' text bounding boxes intersect (e.g. relay_pair sheet pin labels overlapping bus tap labels, or a `{MUX_CTRL}` bus hlabel landing at the same y as an `FMC_SDNE1` tap label on a nearby bus column)
- **Wire-through-label** — flagged when a wire passes through a label's text region (excluding the label's own stub which legitimately ends at the anchor point)

This catches the readability issues where text becomes unreadable due to overlap. To fix: move the label, route the wire around, or shorten/rename the label.

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
4. **Wires must NEVER pass through component fences** — A "fence" is the bounding box of a symbol (including power symbols and their stubs). No wire segment may cross through any fence unless one of its endpoints is a pin OF that component. Route wires around components. This includes power symbol stub regions — a `place_power()` call creates a fence around the symbol AND its stub wire; other wires must not cross through that area. The validator flags these as "passes through fence of" warnings. **These must be fixed before declaring a sheet complete** — they indicate visual clutter and potential accidental connections.
4b. **Wires must extend OUT from component pins** — Never route a wire back into or through a component body. Route around components so wires approach pins from outside.
5. **Output hlabels on rightmost symbols** — Place input hlabels on the left side and output hlabels on the rightmost symbols for left-to-right signal flow.
5b. **Sheet symbol pin side follows signal direction** — On hierarchical sheet boxes (parent sheet), place input pins (`input` shape, signals coming INTO the sub-sheet from this parent) on the **LEFT** edge with `angle=180`. Place output pins (`output` shape, signals leaving the sub-sheet) and bidirectional pins that act as outputs from the sub-sheet on the **RIGHT** edge with `angle=0`. This makes signal flow visually obvious: external sources arrive on the left, sub-sheet results exit on the right. Mixed-direction sheet pins on the same edge are confusing — split them by side based on direction.
6. **No overlapping collinear wires** — KiCad merges overlapping wires at the same x or y, losing intermediate endpoints. This includes label stubs and power stubs.
6b. **Wires must not pass through label text regions** — Net labels and bus hlabels have a text bounding box that extends from the label point in the text direction. Wires that cross through this region make the schematic unreadable. Use short net names when space is tight, and orient labels (angle 0 vs 180) so text extends into empty space. The validator flags these as "passes through text region of label" warnings — fix before declaring the sheet complete.
7. **All wires must be horizontal or vertical** — No diagonal wires. Use L-shaped bends.
7b. **Buses must not cross each other** — Place each bus at a unique x column with enough horizontal spacing so diagonal bus taps from one bus don't reach another bus's vertical line. Minimum gap between bus x positions should be the tap diagonal width (2.54mm) plus label text width plus clearance (~15mm total). If two buses serve adjacent pin groups at the same x, stagger them: place the shorter bus closer to the IC and the longer bus further out.
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

### Recipe 2b: Bus wires must not cross through bus tap regions

**Problem**: Multiple vertical bus columns with taps are connected to sheet box pins via horizontal bus wires. The horizontal buses cross through other columns' tap regions, creating a visual mess of overlapping diagonal entries, labels, and bus wires.

**WRONG** — horizontal bus wires crossing through tap regions of other bus columns:
```python
# Three bus columns at x=240, x=260, x=280, all with taps going left.
# Sheet box pins at x=310, y=65/70/75.
# Horizontal bus from (240, 75) to (310, 75) crosses the tap regions
# of the x=260 and x=280 columns, making labels unreadable.
sb.add_bus(240, 75, 310, 75)  # crosses through other tap zones!
sb.add_bus(260, 70, 310, 70)  # crosses through x=280 tap zone!
```

**RIGHT** — route horizontal buses ABOVE or BELOW all tap regions, then drop vertically to each column:
```python
# Route all horizontal buses above the tap region (e.g., y=55)
# then vertical drops to each column top.
bus_route_y = 55  # above all taps (taps start at y=62+)

# FMC_D column at x=280, pin at (310, 65)
sb.add_bus(310, 65, 280, 65)      # horizontal from pin to column
sb.add_bus(280, 65, 280, 105)     # vertical column with taps

# FMC_A column at x=260, pin at (310, 70)
sb.add_bus(310, 70, 260, 70)      # horizontal from pin
sb.add_bus(260, 70, 260, bus_route_y)  # up to clear route
sb.add_bus(260, bus_route_y, 260, 100) # taps start below bus_route_y
# ...but this still has taps in the crossing zone.
```

**BEST** — space columns far enough apart so their tap regions (entries + labels + stubs) don't overlap, and route horizontal buses only within the clear space above the topmost tap:
```python
# Space bus columns >= 20mm apart (tap region extends ~13mm from bus).
# Route horizontal bus segments to arrive at each column's TOP,
# above all tap entries. Taps extend downward from the column top.
fmc_d_x = 280  # rightmost, closest to sheet box
fmc_a_x = 255  # 25mm gap — tap labels don't overlap
fmc_c_x = 230  # 25mm gap

# Horizontal buses from sheet pins connect at column tops.
# Each column's taps are entirely below the horizontal bus level.
# No horizontal bus wire passes through any tap region.
```

**General rule**: Bus wires must never cross through regions containing bus taps from other bus columns. Each bus column's tap region (bus entries + signal wires + net labels) must be visually clear of crossing bus traffic. Space columns far enough apart (>= 20mm for `label_side="left"` taps) and route horizontal connections above or below all tap zones.

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

**Problem**: Need to wire a component pin to something on the opposite side of the IC. This applies to:
- Same-IC feedback (op-amp output → -IN)
- IC pin → power symbol on the opposite side
- IC pin → external component on the opposite side
- IC pin → net label on the opposite side

**WRONG** — wire through the IC body (same-IC feedback):
```python
# OPA output at (111.43, 72.38), -IN at (111.43, 74.92)
sb.add_wire(111.43, 72.38, 111.43, 74.92)  # vertical through IC body
```

**WRONG** — wire from a right-side pin to a power symbol on the left side:
```python
# ADG1406 GND/VSS pins on the right side at (cx+8.89, cy+25.40)
# -5VA power symbol placed on the LEFT side of the IC
gnd_pin = (cx + 8.89, cy + 25.40)
vss_pin = (cx + 8.89, cy + 27.94)
# These wires drop down then route LEFT, passing UNDER the IC body
sb.add_wire(gnd_pin[0], gnd_pin[1], gnd_pin[0], gnd_pin[1] + 5)
sb.add_wire(gnd_pin[0], gnd_pin[1] + 5, cx - 15, gnd_pin[1] + 5)  # crosses body!
sb.place_power("-5VA", cx - 15, gnd_pin[1] + 5)
```
The fence validator may NOT catch this if both endpoints are at registered pins (the IC pin AND the power symbol pin), so visual inspection is required.

**RIGHT** — power symbol on the SAME side as the pin:
```python
# Right-side IC pins → power symbol routed RIGHT, away from the body
gnd_pin = (cx + 8.89, cy + 25.40)
sb.add_wire(gnd_pin[0], gnd_pin[1], gnd_pin[0] + 7.62, gnd_pin[1])
sb.place_power("GND", gnd_pin[0] + 7.62, gnd_pin[1])
# Or: route DOWN below the IC body, then to a power symbol
sb.add_wire(gnd_pin[0], gnd_pin[1], gnd_pin[0], cy + body_half_h + 5)
sb.place_power("GND", gnd_pin[0], cy + body_half_h + 5)
```

**RIGHT** — for opposite-side power symbols, route AROUND the body:
```python
# If you must use a power symbol on the opposite side, route around the IC:
gnd_pin = (cx + 8.89, cy + 25.40)
detour_y = cy + body_half_h + 7  # below the IC body
sb.add_wire(gnd_pin[0], gnd_pin[1], gnd_pin[0], detour_y)  # down past body
sb.add_wire(gnd_pin[0], detour_y, cx - 15, detour_y)        # left, BELOW body
sb.add_wire(cx - 15, detour_y, cx - 15, target_y)            # up to target
sb.place_power("-5VA", cx - 15, target_y)
```

**General rules**:
1. **Left-side IC pins → route LEFT then around. Right-side pins → route RIGHT then around. Top pins → route UP. Bottom → DOWN.** Never cross through the component rectangle.
2. **Power symbols belong on the SAME SIDE as the pin they connect to.** A right-side pin gets a right-side or below-body power symbol — never a left-side one with a wire crossing the body.
3. **Net labels and external destinations follow the same rule.** If the destination is on the opposite side of an IC, the wire MUST detour around the body (above or below), not through it.
4. **The fence validator has a blind spot**: if both wire endpoints are at registered pins, the wire is exempted from the through-body check. Crossing-body wires between two valid pins (e.g., IC pin and power symbol) will pass validation but are still wrong. Always visually inspect SVG output for body crossings.

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
| Label-vs-label overlap | WARNING | Two labels' text bounding boxes intersect — text becomes unreadable |
| Wire through label | WARNING | Wire passes through a label's text region (excluding the label's own stub) |

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

### Validation Is Mandatory After Every Change
- **BLOCKING REQUIREMENT: Every time a schematic file is created or modified — whether by running a generator script, editing a `.kicad_sch` file directly, or any other means — ALL THREE validation levels below must run and pass before the change is considered complete.** This is not optional. Never skip validation, never defer it, never report a change as done without showing validator output. Even trivial, one-line changes require full validation.

**Level 1: Generator validation (per-sheet)**
After modifying any `gen_*.py` file, immediately run it:
```bash
python3 gen_<block>.py
```
Must print `[CLEAN]`. If it doesn't, fix all issues before proceeding.

**Level 2: Net validation (per-sheet, if declared)**
If the generator has `declare_net()` calls, verify `check_nets()` prints `PASS`.

**Level 3: Full-project ERC**
After ANY generator change, run full-project ERC:
```bash
kicad-cli sch erc --exit-code-violations <root>.kicad_sch
```
Check for `multiple_net_names` (shorts) and `hier_label_mismatch` (hierarchy errors). These are **blockers**.

**Iterative workflow:**
The schematic phase is iterative — changes trigger re-validation, which may reveal new issues, which require more changes. The cycle is:
1. Make a change to a generator
2. Run the generator → must be `[CLEAN]`
3. Run full ERC → must have 0 errors
4. If ERC fails, fix and repeat from step 1
5. Only report the change as complete when all validators pass

**Never report a change as done if validation hasn't run.** If you modified `gen_power_supply.py`, you must show the `[CLEAN]` output AND the ERC result before moving on.

**Regression detection:**
When fixing an issue on one sheet, changes can break other sheets (shared nets, hierarchy labels, bus names). Always regenerate ALL affected sheets and run full ERC — not just the sheet you modified.

**Final gate before next phase:**
Re-run ALL generators and full-project ERC as the last step before generating reports. Document results in `07-schematics.md`.

**ERC error policy:**
- ERC errors = blockers. Fix before any further work.
- ERC warnings that are understood and documented may be accepted (list in `07-schematics.md`).
- If an error cannot be fixed, escalate to the user. **Never suppress errors** to proceed.
- `multiple_net_names` is configured as **error** severity — shorts are never acceptable.

### Update Earlier Documents When Requirements Change
- When a design decision changes during later phases (e.g., new calibration topology, added components, changed signal chain), **go back and update all affected earlier workflow documents** (requirements, architecture, block design, component selection, BOM).
- The workflow documents are living documents — they must always reflect the current state of the design, not just the initial decisions.
- Examples: adding N-FETs for relay coil drive → update BOM and block design. Changing AFE signal chain order (filter before amp) → update architecture. Adding VREF_BIAS circuit → update component selection.
- If you're unsure which documents are affected, check all of them.

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

### Test Points on Power Nets
- **Every global power net** must have at least one `Connector:TestPoint` symbol connected to it. This includes all positive rails (+3V3, +5V, +5VA, +5VD, etc.), negative rails (-5VA, etc.), and GND.
- **GND must have at least 3 test points**, distributed across different sheets to provide convenient probe access near each major circuit block.
- Use `TestPoint:TestPoint_Pad_D1.0mm` footprint for minimal board area.
- To connect a test point to a power net: place the TestPoint symbol, add a short horizontal wire from the TP pin (at the symbol origin), then `place_power()` at the far end of the wire. Do **not** place the power symbol directly at the TP origin — the power stub's vertical wire will pass through the TestPoint body fence.
- Reference designators: use `TPnnn` where `nnn` matches the sheet's component numbering block (e.g., TP200–TP206 on the power supply sheet, TP400–TP404 on the VCCS sheet).
- Place test points in empty areas of the sheet — typically in a row below or beside the main circuit, using `add_net_label()` for signal nets or `place_power()` via a short wire for power nets.

### Symbols Carry LCSC / MPN — BOM CSV Is Generated, Never Hand-Maintained
- Every schematic symbol carries `LCSC` and `MPN` as KiCad custom fields (set `(hide yes)` so they don't clutter the canvas). Use KiCad's BOM exporter (`kicad-cli sch export bom --fields "Reference,Value,Footprint,LCSC,MPN"`) to produce the assembly CSV that JLCPCB ingests.
- **Never hand-maintain a BOM CSV.** The `workflow/05-bom-notes.md` document is engineering rationale only — it does not get uploaded anywhere. The schematic is the single source of truth for what is on the board. If you need to change a part, change it on the symbol (LCSC/MPN fields), regenerate the CSV, and update BOM Notes with the rationale.

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
