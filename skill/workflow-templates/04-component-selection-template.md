# Phase 4: Component Selection

## Workflow Steps (for skill automation)

### Step 1: For each block, propose components
- Consider price, availability, and LCSC part numbers
- Propose 2-3 alternatives for critical components

### Step 2: Review and select with user
- Present options with rationale
- Document rejected alternatives with reasons

### Step 3: Write document and generate PDF
- Output: `workflow/04-component-selection.md`
- Generate PDF: `python3 scripts/md_to_pdf.py workflow/04-component-selection.md`

---

## [Project Name]: Component Selection

### Design Constraints

- [e.g., SMT components preferred, 0603 passives]
- [e.g., Module-based MCU (not bare chip)]

### Block 1: [Block Name]

#### [Component Type] Selection

| Parameter | [Option A] | [Option B] | [Option C] |
|-----------|-----------|-----------|-----------|
| Manufacturer | | | |
| MPN | | | |
| LCSC | | | |
| Package | | | |
| Key Spec | | | |
| Price | | | |

**Selected:** [Option] — [rationale]

#### Support Components

| Designator | Description | Value | Package | LCSC | Notes |
|-----------|-------------|-------|---------|------|-------|
| [C1] | [Decoupling cap] | [100nF] | [0603] | [C...] | [purpose] |

[Repeat for each block]

### Common Passives

| Value | Package | LCSC | Used In | Qty |
|-------|---------|------|---------|-----|
| [100nF] | [0603] | [C...] | [Blocks 1,2,4] | [6] |

### BOM Summary

| Metric | Value |
|--------|-------|
| Unique parts | [N] |
| Total components | [N] |
| Estimated cost | [$X.XX] |

### Components Reviewed and Rejected

| Component | Reason Rejected |
|-----------|----------------|
| [name] | [reason] |

### Open Items for Detailed Design

- [Any unresolved questions or trade-offs]
