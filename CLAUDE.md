# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

kicad-aisch — AI-assisted KiCad schematic generation tools. The goal is to create generic scripts, workflow, and settings for a **Claude Code skill** that generates KiCad schematics from design requirements.

The skill definition lives in `skill/SKILL.md` — that is the authoritative reference for the SchematicBuilder API, coordinate conventions, wiring rules, design rules, ERC configuration, and the 7-phase workflow. Do not duplicate that content here.

## Repository Structure

- `skill/` — Claude Code skill definition
  - `SKILL.md` — Skill prompt with full API reference, workflow, and design rules
  - `scripts/` — Scripts shipped with the skill (copied into user projects at Phase 7)
  - `examples/` — Working example generator scripts from the test project
- `scripts/` — Development copies of the schematic generation scripts
  - `kicad_sch_gen.py` — Generic KiCad schematic generation library (`SchematicBuilder` class)
  - `gen_*.py` — Per-block schematic generator scripts
  - `gen_top_level.py` — Root schematic with hierarchical sheet frames and global labels
  - `md_to_pdf.py` — Markdown-to-PDF converter
  - `extract_easyeda_libs.py` — LCSC component extraction into project libs
- `workflow/` — Design workflow phase outputs (`01-requirements.md` through `07-schematics.md`)
- `marklin-wifi-ctrl/` — Reference KiCad project (test design used to develop this skill)

## File Conventions

- KiCad schematics: `.kicad_sch` (S-expression format)
- KiCad PCB layouts: `.kicad_pcb` (S-expression format)
- KiCad symbol libraries: `.kicad_sym` (read-only, never modify)
- KiCad footprint libraries: `.kicad_mod`
- PDF files are output only — always read `.md` files to understand the design

## Development Workflow

- Target: KiCad 9 format (version 20250114)
- Run generator scripts from `scripts/`: `python3 scripts/gen_<block>.py`
- Verify with ERC: `kicad-cli sch erc --exit-code-violations <root.kicad_sch>`
- Visual check: `kicad-cli sch export svg --output /tmp/ <root.kicad_sch>`
- Generator scripts must print `[CLEAN]` (no validation warnings) before a sheet is considered done

## Keeping skill/ and scripts/ in Sync

The `scripts/` directory contains development copies used by the test project. The `skill/` directory contains the distributable skill. When modifying scripts:
- Develop and test in `scripts/` against the `marklin-wifi-ctrl/` test project
- Copy finalized changes to `skill/scripts/` and update `skill/examples/` as needed
- Update `skill/SKILL.md` if API or conventions change

## Reference Scripts

The scripts were originally developed using proven KiCad schematic generators from `/home/pa/work/traincontrol/hw/traincontrol-shield/tmp/` as templates.

## Tools Available

- `kicad-cli` — KiCad command-line interface (ERC, DRC, export SVG/PDF)
- `easyeda2kicad` — LCSC/EasyEDA component import into KiCad format
- `python3` — Script execution
- `fpdf2` Python package — PDF generation (uses DejaVu TTF fonts for full Unicode support)
- `inkscape` — SVG-to-PNG conversion (visual verification)
