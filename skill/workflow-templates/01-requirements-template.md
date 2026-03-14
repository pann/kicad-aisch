# Phase 1: Requirements

## Workflow Steps (for skill automation)

### Step 1: Parse design input
- Read the user's design description (free-form text)
- Extract: functional purpose, power source, communication interfaces, MCU preferences, constraints

### Step 2: Propose structured requirements for review
- Present a structured breakdown:
  1. **Functional Requirements** — what the design must do
  2. **Power Input** — source voltage, type (AC/DC), expected range
  3. **Interfaces** — external connections (connectors, protocols, wireless)
  4. **MCU/CPU Selection Criteria** — based on user preferences and interface needs
  5. **Environmental/Mechanical Constraints** — size, temperature, enclosure
  6. **Applicable Standards** — safety, EMC, regulatory
  7. **Out of Scope** — explicitly state what is NOT part of this design

### Step 3: User reviews and refines requirements
- Iterate until requirements are agreed upon

### Step 4: Save agreed requirements as a structured document
- Output: `workflow/01-requirements.md` — the frozen requirements baseline
- Generate PDF: `python3 scripts/md_to_pdf.py workflow/01-requirements.md`

---

## [Project Name]: Requirements Analysis

### Design Input (raw)

[Paste or summarize the user's original design description here]

### Proposed Structured Requirements

#### 1. Functional Requirements

[What the design must do — bullet list]

#### 2. Power Input

| Parameter | Value |
|-----------|-------|
| Source | [e.g., 24VAC, 12VDC, USB 5V] |
| Range | [e.g., 18-30VAC] |
| Max current | [e.g., 2A] |

#### 3. Interfaces

| Interface | Type | Direction | Notes |
|-----------|------|-----------|-------|
| [e.g., WiFi] | [802.11b/g/n] | [bidirectional] | [Modbus TCP] |

#### 4. MCU Selection Criteria

[Bullet list of key MCU requirements derived from functional needs]

#### 5. Environmental/Mechanical Constraints

[Size, temperature range, enclosure, mounting, etc.]

#### 6. Applicable Standards

[Safety, EMC, regulatory requirements]

#### 7. Out of Scope

[Explicitly list what is NOT included in this design]
