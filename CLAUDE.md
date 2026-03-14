# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

kicad-aisch — AI-assisted KiCad schematic tools.

## KiCad Workflow

- Use `kicad-cli` for command-line operations (DRC, ERC, export)
- Use `easyeda2kicad` to convert EasyEDA/LCSC components to KiCad format
- LCSC part lookups via lcsc.com for component sourcing

## File Conventions

- KiCad schematics: `.kicad_sch` (S-expression format)
- KiCad PCB layouts: `.kicad_pcb` (S-expression format)
- KiCad symbol libraries: `.kicad_sym`
- KiCad footprint libraries: `.kicad_mod`
