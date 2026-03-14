# Phase 2: Architecture & MCU Selection

## Workflow Steps (for skill automation)

### Step 1: Evaluate MCU candidates
- Based on requirements, compare 2-3 candidate MCUs on: core performance, peripherals, WiFi/BT, power consumption, package size, cost, toolchain maturity

### Step 2: Present comparison and recommendation for review
- Tabulated comparison with rationale for recommendation

### Step 3: User reviews and selects MCU
- Iterate until MCU choice is agreed

### Step 4: Document architecture decisions
- Output: `workflow/02-architecture.md` — MCU selection and system architecture
- Generate PDF: `python3 scripts/md_to_pdf.py workflow/02-architecture.md`

---

## [Project Name]: Architecture & MCU Selection

### Candidate Comparison

| Feature | [MCU 1] | [MCU 2] | [MCU 3] |
|---------|---------|---------|---------|
| **CPU** | | | |
| **WiFi** | | | |
| **GPIO** | | | |
| **ADC** | | | |
| **Flash** | | | |
| **Package** | | | |
| **Price (LCSC)** | | | |
| **Toolchain** | | | |

### Assessment Against Requirements

[For each requirement, assess how each MCU meets it]

### Recommendation: [MCU Name]

[Rationale for selection — 2-3 paragraphs]

### System Architecture Overview

[Text diagram or description showing:]
- Power path (input -> regulation -> rails)
- Signal domains and isolation boundaries (if applicable)
- Major functional blocks and data flow
- Key design decisions and trade-offs

### Power Domains

| Domain | Ground Reference | Voltage Rails | Components |
|--------|-----------------|---------------|------------|
| [e.g., AC domain] | [track ground] | [24VAC] | [list] |
| [e.g., DC domain] | [MCU GND] | [3.3V, 5V] | [list] |
