# Phase 6: KiCad Project Structure

## Workflow Steps (for skill automation)

### Step 1: Import missing components
- For components not in KiCad standard libraries, use `easyeda2kicad` with `--output` and `--project-relative` to download directly into a project-named library:
  ```
  cd <project_dir>
  easyeda2kicad --full --lcsc_id <id> --output ./<project_name>.kicad_sym --project-relative
  ```
  Repeat for each component. Each call appends to the same library files.
- `--output ./<name>.kicad_sym` creates `<name>.kicad_sym`, `<name>.pretty/`, and `<name>.3dshapes/`
- `--project-relative` sets 3D model paths to `${KIPRJMOD}/<name>.3dshapes/` (correct for KiCad)
- **Fix footprint module names** after import — easyeda2kicad hardcodes `easyeda2kicad:` as the library name inside `.kicad_mod` files:
  ```
  sed -i 's|easyeda2kicad:|<project_name>:|g' <project_name>.pretty/*.kicad_mod
  ```
- **Create `sym-lib-table` and `fp-lib-table`** in the project directory to register the libraries with KiCad (without these, KiCad reports "Library not found")
- Verify imported symbols and footprints load correctly in KiCad

### Step 2: Create KiCad project
- Ask for: Project name, Author name, Company name
- Create `.kicad_pro` project file
- Create root schematic with title block

### Step 3: Create hierarchical sheet structure
- Create empty child schematics for each block
- Add hierarchical sheet entries to root schematic
- Verify project loads with `kicad-cli sch export svg`

---

## Test Project: KiCad Project Structure

### Project Details

| Field | Value |
|---|---|
| Project name | marklin-wifi-ctrl |
| Author | PA Nilsson |
| Company | ZID AB |
| Revision | 0.1 |
| KiCad version | 9.0.7 |
| File format version | 20250114 |

### Component Import

Three components were imported via `easyeda2kicad --full`. Each import downloads a symbol, footprint, and 3D model:

| Component | LCSC | Symbol | Footprint | 3D Model |
|---|---|---|---|---|
| ESP32-C3-MINI-1-N4 | C2838502 | ESP32-C3-MINI-1-N4 | WIFIM-SMD_ESP32-C3-MINI-1 | WIFIM-SMD_ESP32-C3-MINI-1 (.wrl/.step) |
| EL357N(C)(TA)-G | C29981 | EL357N(C)(TA)-G | OPTO-SMD-4_L4.4-W4.1-P2.54-LS7.0-TL | OPTO-SMD-4P_L4.1-W4.4-H2.0-LS7.0-P2.54 (.wrl/.step) |
| MOC3021S-TA1 | C115465 | MOC3021S-TA1 | SMD-6_L7.3-W6.5-P2.54-LS10.2-BL | SMD-6_L7.3-W6.5-H3.6-LS10.16-P2.54 (.wrl/.step) |

After import, the libraries were cleaned to contain only these 3 components (the shared easyeda2kicad output directory contained 27 symbols and 11 footprints from prior imports).

Project-specific libraries named after the project:
- `marklin-wifi-ctrl.kicad_sym` — 3 symbols
- `marklin-wifi-ctrl.pretty/` — 3 footprints
- `marklin-wifi-ctrl.3dshapes/` — 3 models (6 files: .wrl + .step each)

All internal references updated: symbols reference `marklin-wifi-ctrl:<footprint>`, footprints reference `${KIPRJMOD}/marklin-wifi-ctrl.3dshapes/<model>.wrl`.

### Project File Structure

```
marklin-wifi-ctrl/
  marklin-wifi-ctrl.kicad_pro     # Project file
  marklin-wifi-ctrl.kicad_sch     # Root schematic (hierarchy overview)
  connectors.kicad_sch            # Block 9: Track input + motor output
  power_supply.kicad_sch          # Block 1: 24VAC to 3.3VDC
  esp32_c3.kicad_sch              # Block 2: ESP32-C3-MINI-1 module
  zero_crossing.kicad_sch         # Block 3: Zero-cross detector
  voltage_sense.kicad_sch         # Block 6: AC voltage measurement
  hw_interlock.kicad_sch          # Block 4: NAND interlock
  triac_drive.kicad_sch           # Block 5: MOC3021S + BT136 (x2)
  status_led.kicad_sch            # Block 7: Status LED
  usb_prog.kicad_sch              # Block 8: USB-C programming
  sym-lib-table                   # Symbol library table (registers project libs)
  fp-lib-table                    # Footprint library table (registers project libs)
  marklin-wifi-ctrl.kicad_sym     # Imported symbol library (3 symbols)
  marklin-wifi-ctrl.pretty/       # Imported footprint library (3 footprints)
  marklin-wifi-ctrl.3dshapes/     # Imported 3D models (3 models)
```

### Root Schematic Layout

The root schematic (A3 paper) arranges the 9 hierarchical sheet symbols in a 3x3 grid:

| Row | Left | Center | Right |
|---|---|---|---|
| Row 1 (top) | Connectors | Power Supply | ESP32-C3 MCU |
| Row 2 (mid) | Zero-Crossing | Voltage Sensing | Hardware Interlock |
| Row 3 (bot) | TRIAC Drive | Status LED | USB Programming |

Signal flow is left-to-right (AC domain to DC domain) and top-to-bottom (power to output).

### Verification

- Project loads successfully in KiCad 9.0.7
- All 10 sheets (1 root + 9 children) export to SVG without errors
- Title blocks show correct project name, author, company, and revision
