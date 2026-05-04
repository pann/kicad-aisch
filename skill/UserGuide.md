# KiCad SchematicBuilder Skill — User Guide

## What This Skill Does

The `kicad-schematic` skill guides you through designing and generating production-ready KiCad 9 hierarchical schematics from a plain-text design description. It follows a structured 8-phase workflow:

1. **Requirements** — parse your design description into structured requirements
2. **Architecture** — select MCU, define system architecture and power domains
3. **Block Design** — decompose into schematic blocks with defined interfaces
4. **Component Selection** — choose components with LCSC part numbers for each block
5. **BOM Notes** — engineering rationale for part choices (the *why*, not an assembly file)
6. **KiCad Project** — set up project, import components, create hierarchy
7. **Schematic Generation** — generate `.kicad_sch` files, populate LCSC/MPN custom fields, export the assembly BOM CSV
8. **Fab Outputs** — gerbers, drill, BOM CSV, CPL CSV — everything JLCPCB needs for a PCBA order

Each phase produces a reviewable document. You approve each phase before moving to the next.

## Installation

### Prerequisites

Install these tools on your system:

```bash
# KiCad 9 CLI (comes with KiCad installation)
kicad-cli --version

# easyeda2kicad (for LCSC component import)
pip install easyeda2kicad

# fpdf (for PDF document generation)
pip install fpdf

# Optional: inkscape (for SVG-to-PNG visual verification)
sudo apt install inkscape   # or equivalent for your OS
```

### Install the Skill

Copy the `skill/` folder to your Claude Code skills directory:

```bash
# For personal use (all projects)
mkdir -p ~/.claude/skills/kicad-schematic
cp -r skill/* ~/.claude/skills/kicad-schematic/

# OR for a specific project only
mkdir -p .claude/skills/kicad-schematic
cp -r skill/* .claude/skills/kicad-schematic/
```

### Recommended Companion Skills

These skills complement the schematic workflow (install separately if available):

- **kicad-file-format** — KiCad S-expression file format reference
- **jlcpcb-bom-generate-from-kicad** — Export BOM for JLCPCB PCB assembly
- **analyze-power-nets** — Identify power nets for PCB routing
- **find-high-speed-nets** — Classify nets by speed for signal integrity
- **plan-pcb-routing** — Generate PCB routing plans

## Usage

### Starting a New Design

Invoke the skill with a design description:

```
/kicad-schematic A WiFi-enabled temperature logger with 4 thermocouple inputs,
SD card storage, and a 2.4" TFT display. Powered by USB-C, battery backup optional.
```

Or simply invoke it and provide the description when prompted:

```
/kicad-schematic
```

Claude will also suggest the skill automatically when you describe a hardware design task in natural language.

### Resuming at a Specific Phase

If you've already completed some phases (e.g., you have requirements and architecture documents), resume at a later phase:

```
/kicad-schematic resume at phase 3
/kicad-schematic phase=5
/kicad-schematic continue from block design
```

### Working Through the Phases

Each phase follows the same pattern:

1. Claude analyzes inputs from previous phases
2. Claude proposes output (requirements, architecture, component choices, etc.)
3. You review, request changes, or approve
4. Claude saves the document to `workflow/` and generates a PDF
5. Move to the next phase

**You are always in control.** Claude will not proceed to the next phase without your approval.

### Phase-by-Phase Guide

#### Phase 1: Requirements
- **Input:** Your design description (free text)
- **Output:** `workflow/01-requirements.md` — structured requirements document
- **What to review:** Are all functional requirements captured? Power specs correct? Interfaces complete?

#### Phase 2: Architecture & MCU Selection
- **Input:** Approved requirements
- **Output:** `workflow/02-architecture.md` — MCU comparison and system architecture
- **What to review:** Is the MCU choice appropriate? Are power domains defined? Isolation boundaries correct?

#### Phase 3: Block Design
- **Input:** Approved architecture
- **Output:** `workflow/03-block-design.md` — block decomposition with interfaces
- **What to review:** Are blocks well-scoped (one page each)? Interface signals complete? No missing connections?

#### Phase 4: Component Selection
- **Input:** Approved block design
- **Output:** `workflow/04-component-selection.md` — selected components with LCSC numbers
- **What to review:** Component choices reasonable? Availability OK? Price acceptable? Alternatives documented?

#### Phase 5: BOM Notes
- **Input:** Approved components
- **Output:** `workflow/05-bom-notes.md` — engineering rationale for each part choice (the *why*)
- **What to review:** Is each part choice justified? Are alternatives documented? DNP candidates flagged? Special components (precision passives, film caps, Kelvin-sense networks) called out? Single-source / consignment parts identified?
- **Note:** No CSV is produced here. The assembly BOM CSV is generated mechanically in Phase 7 from the schematic itself, after `LCSC` and `MPN` custom fields are populated on every symbol.

#### Phase 6: KiCad Project
- **Input:** Approved BOM
- **Output:** `workflow/06-kicad-project.md` + KiCad project files
- **What to review:** Project loads in KiCad? Components imported correctly? Hierarchy correct?

#### Phase 7: Schematic Generation
- **Input:** All previous phases
- **Output:** `scripts/gen_*.py` generator scripts + `.kicad_sch` schematic files + `BOM_jlcpcb.csv` (assembly BOM, generated via `kicad-cli sch export bom`) + `<project>_schematics.pdf`
- **What to review:** ERC clean (0 errors)? SVG exports readable? Labels don't overlap? Wiring correct? Every symbol has LCSC + MPN custom fields populated? BOM CSV row count matches the symbol count?

#### Phase 8: Fab Outputs
- **Input:** Clean schematic + finished PCB layout
- **Output:** `<project>/fab/` containing gerbers, drill, BOM CSV, CPL CSV, and an upload zip
- **What to review:** Gerbers visually correct in a viewer? BOM CSV has no empty LCSC cells? CPL designators match BOM? `fab/` is `.gitignore`d (artefacts are regenerated, not committed)?

### After Schematic Generation

Once schematics are complete, you can:

1. **Open in KiCad** — the `.kicad_sch` files load directly in KiCad 9
2. **Run ERC** — `kicad-cli sch erc --exit-code-violations <project>.kicad_sch`
3. **Export PDFs** — `kicad-cli sch export pdf --output schematic.pdf <project>.kicad_sch`
4. **Proceed to PCB layout** — use companion skills for power net analysis and routing planning
5. **Order PCBs** — use the JLCPCB BOM skill to generate assembly files

## Output File Structure

After completing all phases, your project will look like:

```
my-project/
  workflow/
    01-requirements.md (+.pdf)
    02-architecture.md (+.pdf)
    03-block-design.md (+.pdf)
    04-component-selection.md (+.pdf)
    05-bom-notes.md (+.pdf)        # Engineering rationale; NOT an assembly file
    06-kicad-project.md (+.pdf)
    07-schematics.md (+.pdf)
  scripts/
    kicad_sch_gen.py            # Core library (copied from skill)
    md_to_pdf.py                # PDF generator (copied from skill)
    gen_top_level.py            # Root schematic generator
    gen_<block1>.py             # Per-block generators
    gen_<block2>.py
    ...
  <project>/
    <project>.kicad_pro         # KiCad project file
    <project>.kicad_sch         # Root schematic
    <block1>.kicad_sch          # Generated sub-sheets
    <block2>.kicad_sch
    ...
    <project>.kicad_sym         # Imported component symbols
    <project>.pretty/           # Imported footprints
    <project>.3dshapes/         # Imported 3D models
    sym-lib-table               # Library registration
    fp-lib-table
    BOM_jlcpcb.csv              # Generated by `kicad-cli sch export bom` (Phase 7)
    fab/                        # .gitignore'd — Phase 8 fab outputs
      gerbers/                  #   gerber files
      <project>-drill.drl       #   drill file
      BOM_kicad.csv             #   raw KiCad BOM export
      CPL_kicad.csv             #   raw KiCad pos export
      <project>-<rev>.zip       #   JLCPCB upload package
```

## Tips

- **Regenerate, don't edit:** If a schematic needs changes, modify the generator script and re-run it. The `.kicad_sch` files are generated output.
- **Stable UUIDs:** Generator scripts use fixed UUIDs for sheet instances. Don't change these or KiCad will lose track of the hierarchy.
- **ERC warnings are normal:** `lib_symbol_mismatch` warnings are cosmetic (embedded vs installed library versions). `pin_not_driven` warnings from easyeda2kicad imports are expected.
- **Visual verification matters:** Always check SVG exports for overlapping text, disconnected wires, or cramped layouts.
- **One hlabel per net per sheet:** If you need the same signal at multiple points on a sheet, use one hierarchical label plus local net labels.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `kicad-cli` not found | Install KiCad 9 or add to PATH |
| `easyeda2kicad` fails | Check LCSC part number is valid; check network connectivity |
| ERC shows `pin_to_pin` errors | Add ERC config to `.kicad_pro` (see SKILL.md ERC section) |
| Footprint "library not found" | Run sed fix and create `fp-lib-table` (see easyeda2kicad procedure) |
| SVG export fails | Check all sub-sheets exist and root schematic references them |
| Labels overlap in SVG | Increase GAP between columns in `gen_top_level.py` (minimum 45mm) |
| Power symbol overlap | Ensure VCC/GND stubs at same x don't overlap (7.62mm each direction) |
