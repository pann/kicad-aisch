# Phase 5: Bill of Materials

## Workflow Steps (for skill automation)

### Step 1: Compile BOM from component selection
- List all components with designators, values, packages, and LCSC part numbers

### Step 2: Check KiCad standard library availability
- For each component, verify symbol and footprint exist in KiCad libraries
- Flag missing components for import via easyeda2kicad

### Step 3: Export BOM as CSV
- Output: `workflow/05-bom.csv`
- Generate PDF: `python3 scripts/md_to_pdf.py workflow/05-bom.md`

---

## [Project Name]: Bill of Materials

### BOM Statistics

| Metric | Count |
|--------|-------|
| Unique part numbers | [N] |
| Total component count | [N] |
| Estimated total cost | [$X.XX] |

### KiCad Library Status

| Status | Symbol | Footprint | Count |
|--------|--------|-----------|-------|
| Available | Standard lib | Standard lib | [N] |
| Substitute | Map to equivalent | Standard lib | [N] |
| Import | easyeda2kicad | easyeda2kicad | [N] |

### Components Requiring Import

| Component | LCSC | Symbol | Footprint |
|-----------|------|--------|-----------|
| [name] | [C...] | [needs import] | [needs import] |

### Substitute Symbols

| Component | Selected Symbol | KiCad Equivalent | Notes |
|-----------|----------------|-------------------|-------|
| [name] | [original] | [substitute] | [pin compatibility] |

### Full BOM

| Item | Block | Designator | Description | Manufacturer | MPN | Package | LCSC | Qty | Unit Price | KiCad Symbol | KiCad Footprint | Status |
|------|-------|-----------|-------------|-------------|-----|---------|------|-----|-----------|-------------|----------------|--------|
| 1 | | | | | | | | | | | | |

### BOM CSV

Exported to `workflow/05-bom.csv` with the same columns as the table above.
