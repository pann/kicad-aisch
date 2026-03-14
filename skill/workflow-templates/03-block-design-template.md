# Phase 3: Block-Level Design

## Workflow Steps (for skill automation)

### Step 1: Decompose architecture into schematic blocks
- Each block becomes a KiCad hierarchical sheet
- Blocks should be small enough for a single schematic page (A4)

### Step 2: Document each block
- Purpose, interfaces (inputs/outputs/power), domain, key design notes

### Step 3: Create block interconnect diagram
- Show block-to-block wiring with isolation boundary

### Step 4: Write document and generate PDF
- Output: `workflow/03-block-design.md`
- Generate PDF: `python3 scripts/md_to_pdf.py workflow/03-block-design.md`

---

## [Project Name]: Block-Level Design

### Block Decomposition

| # | Block | Domain | Sheet | Purpose |
|---|-------|--------|-------|---------|
| 1 | [name] | [domain] | [filename.kicad_sch] | [one-line purpose] |

### Block Descriptions

#### Block 1: [Name]

**Purpose:** [What this block does]

**Function:** [How it works — 2-3 sentences]

**Interfaces:**

| Signal | Direction | Type | Connected To |
|--------|-----------|------|-------------|
| [name] | [in/out/bidir] | [passive/input/output] | [block.signal] |

**Domain:** [Power/ground domain]

**Design Notes:**
- [Key considerations, component choices, constraints]

[Repeat for each block]

### Signal and Power Bus Summary

| Signal | Type | Source Block | Destination Block(s) | Notes |
|--------|------|-------------|----------------------|-------|
| [name] | [power/signal/control] | [block] | [block(s)] | [description] |

### Block Interconnect Diagram

```
[Text diagram showing blocks as boxes with signal connections between them]
[Mark isolation boundaries with dashed lines]
```

### Isolation Boundary Crossings

| Signal | Isolation Device | AC-Side Block | DC-Side Block |
|--------|-----------------|---------------|---------------|
| [name] | [optocoupler type] | [block] | [block] |

### Design Verification Checklist

- [ ] Every block interface signal appears in exactly two blocks
- [ ] All power rails are sourced by exactly one block
- [ ] Isolation boundary crossings use appropriate devices
- [ ] Each block fits on a single A4 schematic page
- [ ] No circular dependencies between blocks
