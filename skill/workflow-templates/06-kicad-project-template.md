# Phase 6: KiCad Project Structure

## Workflow Steps (for skill automation)

### Step 1: Import missing components
- For components not in KiCad standard libraries, use `easyeda2kicad`:
  ```
  cd <project_dir>
  easyeda2kicad --full --lcsc_id <id> --output ./<project_name>.kicad_sym --project-relative
  ```
  Repeat for each component. Each call appends to the same library files.
- Fix footprint module names after import:
  ```
  sed -i 's|easyeda2kicad:|<project_name>:|g' <project_name>.pretty/*.kicad_mod
  ```
- Create `sym-lib-table` and `fp-lib-table` in project directory
- Verify imported symbols and footprints load correctly

### Step 2: Create KiCad project
- Ask for: Project name, Author name, Company name
- Create `.kicad_pro` project file with ERC configuration
- Create root schematic with title block

### Step 3: Create hierarchical sheet structure
- Create child schematics for each block (empty or generated)
- Add hierarchical sheet entries to root schematic
- Verify project loads with `kicad-cli sch export svg`

---

## [Project Name]: KiCad Project Structure

### Project Details

| Field | Value |
|-------|-------|
| Project name | [name] |
| Author | [name] |
| Company | [name] |
| KiCad version | 9.0 (format v20250114) |
| Paper size | A4 (sub-sheets), A3 (root) |

### Component Import

| Component | LCSC | Symbol | Footprint | 3D Model |
|-----------|------|--------|-----------|----------|
| [name] | [C...] | [ok] | [ok] | [ok] |

### Project File Structure

```
<project>/
  <project>.kicad_pro          # Project file with ERC settings
  <project>.kicad_sch           # Root schematic (hierarchy)
  block_1.kicad_sch             # Sub-sheet per block
  block_2.kicad_sch
  ...
  <project>.kicad_sym           # Project symbol library (imports)
  <project>.pretty/             # Project footprint library (imports)
  <project>.3dshapes/           # 3D models (imports)
  sym-lib-table                 # Symbol library registration
  fp-lib-table                  # Footprint library registration
```

### Root Schematic Layout

[Describe the grid arrangement of hierarchical sheet frames]
[Document column/row positions for each block]

### Verification

- [ ] Project loads in KiCad without errors
- [ ] All sub-sheets are accessible from root
- [ ] SVG export succeeds for all pages
- [ ] ERC runs with 0 errors (warnings acceptable per ERC config)
