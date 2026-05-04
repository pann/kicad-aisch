# Phase 5: BOM Notes & Component Selection

## Workflow Steps (for skill automation)

### Step 1: Per-block selection rationale
- For each block / functional group, document which parts were selected (with LCSC + MPN), what alternatives were considered, and why this part won.

### Step 2: Flag DNP candidates
- List parts marked Do-Not-Place with explicit justification (calibration branch disabled, debug-only header, factory-programming jumper, etc.).

### Step 3: Special-component callouts
- Precision passives (TCR, tolerance), film caps, foil resistors, Kelvin sense — anything where a generic LCSC family won't do.

### Step 4: Single-source / consignment parts
- Identify parts JLCPCB doesn't stock; flag for `Source = Consignment` field in Phase 7.

### Step 5: Save deliverable
- Output: `workflow/05-bom-notes.md`
- Generate PDF: `python3 scripts/md_to_pdf.py workflow/05-bom-notes.md`
- **No CSV is produced here.** The assembly BOM CSV is generated mechanically in Phase 7 from the schematic via `kicad-cli sch export bom`, after `LCSC` and `MPN` custom fields are populated on every symbol.

---

## [Project Name]: BOM Notes

### Selection Rationale by Block

#### [Block Name 1]

| Designator(s) | Selected (MPN / LCSC) | Alternatives considered | Why this won |
|---------------|----------------------|-------------------------|--------------|
| [refs] | [MPN] / [C...] | [list] | [cost / availability / spec / footprint reuse / JLCPCB Basic vs Extended] |

#### [Block Name 2]

[…]

### DNP Candidates

| Designator | Part | DNP Justification |
|-----------|------|-------------------|
| [ref] | [MPN] | [why not assembled in production] |

### Special Components

Components that need narrative beyond a generic LCSC family pick.

| Designator(s) | Part | Why special |
|---------------|------|-------------|
| [ref] | [MPN] | [precision / tolerance / TCR / film / Kelvin / etc.] |

### Single-Source / Consignment Parts

Parts JLCPCB does not stock or where supply is constrained.

| Designator(s) | Part | Source / risk | Mitigation |
|---------------|------|---------------|-----------|
| [ref] | [MPN] | [Consignment / sole-source / lead-time] | [alt footprint / second source / stock margin] |

### Deferred Decisions & Stock Risks

- [TBD: e.g. "main MCU sole-sourced from ST; identify footprint-compatible fallback before tape-out"]
- [TBD: e.g. "0.1 % thin-film 1k 0603 has 6-week lead time; consider 0805 alternate"]
