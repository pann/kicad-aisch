# kicad-aisch

AI-assisted KiCad schematic generation — a [Claude Code](https://claude.ai/code) skill that generates production-ready KiCad 9 hierarchical schematics from a design description.

## What It Does

Given a hardware design description (e.g., "WiFi-controlled AC motor driver with ESP32"), the skill walks through a structured 7-phase workflow:

1. **Requirements** — parse and structure the design input
2. **Architecture** — MCU selection, system architecture, power domains
3. **Block Design** — decompose into schematic blocks with defined interfaces
4. **Component Selection** — select parts with LCSC part numbers
5. **BOM** — bill of materials with library availability check
6. **KiCad Project** — project setup, component import, hierarchy
7. **Schematics** — generate all schematic sheets with built-in validation

Each phase produces a reviewable document before proceeding to the next.

## How It Works

The core is `SchematicBuilder`, a Python library that programmatically generates KiCad `.kicad_sch` files. For each schematic block, a generator script places components, routes wires, adds labels and power symbols, and runs geometric validation — all on a snapped grid matching KiCad conventions.

Components are sourced from KiCad's standard libraries and LCSC/EasyEDA imports via `easyeda2kicad`.

## Repository Structure

- `skill/` — The Claude Code skill (install this)
  - `SKILL.md` — Skill definition: workflow, API reference, design rules, wiring recipes
  - `scripts/` — Scripts shipped with the skill
  - `examples/` — Working example generators from the test project
- `scripts/` — Development copies (used during skill development)
- `workflow/` — Workflow phase outputs from the test project
- `marklin-wifi-ctrl/` — Test KiCad project (Marklin WiFi AC train controller)

## Prerequisites

- KiCad 9 with `kicad-cli`
- Python 3 with `fpdf`
- `easyeda2kicad` for LCSC component imports
- [Claude Code](https://claude.ai/code)

## Getting Started

Install the skill in Claude Code, then describe your hardware design:

```
/kicad-schematic WiFi-controlled LED matrix with ESP32-S3, 5V input, 64x32 RGB panel
```

The skill will guide you through each phase interactively.

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — Repository structure and development workflow
- [`skill/SKILL.md`](skill/SKILL.md) — Full skill reference: SchematicBuilder API, coordinate conventions, wiring rules, validation, ERC configuration

## License

MIT
