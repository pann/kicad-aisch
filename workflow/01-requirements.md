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
  6. **Out of Scope** — explicitly state what is NOT part of this design

### Step 3: User reviews and refines requirements
- Iterate until requirements are agreed upon

### Step 4: Save agreed requirements as a structured document
- Output: `<project>/requirements.md` — the frozen requirements baseline

---

## Test Project: Requirements Analysis

### Design Input (raw)
A WiFi-enabled controller for classic Marklin AC model trains. The module sits inside
(or replaces) the locomotive's existing electronics, is powered directly from the
24 VAC rail voltage, and exposes motor control via Modbus TCP over WiFi.
A simple and readily available microcontroller should be used, that is well supported
and have good SW and IDE available.
Software development is not a part of this project, but the SW support for the chosen
CPU/MCU must be considered.

### Proposed Structured Requirements

#### 1. Functional Requirements
- Control a Marklin AC motor with two field windings (one for forward, one for reverse)
- Direction control by selecting which winding is energized
- AC output signal must be controlled on both positive and negative half-cycles of the sine wave (full phase-angle control requires zero-crossing detection on every half-cycle)
- The two field windings must never be energized simultaneously. Hardware interlock (gate logic or equivalent) is required to enforce mutual exclusion independent of firmware
- WiFi connectivity for remote control
- Modbus TCP server for motor speed/direction commands
- Status feedback (at minimum: connected/running indication)

#### 2. Power Input
- Source: 24 VAC nominal from Marklin track (range ~16–25 VAC depending on transformer)
- Must rectify and regulate to logic-level DC (3.3V for MCU, potentially intermediate rail ~12–15V)
- No external DC supply — all power from track

#### 3. Interfaces
- **Track input**: 2-wire AC from rail (power + signal), via solder pads
- **Motor output**: Connections to two field windings (forward and reverse) plus common, via solder pads
- **WiFi**: 802.11 b/g/n for Modbus TCP
- **Status LED**: At least one visible indicator
- **Programming/Debug**: USB or UART header for firmware upload (if MCU supports it natively)

#### 4. MCU Selection Criteria
- WiFi built-in (reduces BOM, simplifies design)
- Well-supported toolchain and IDE (Arduino, ESP-IDF, PlatformIO)
- Sufficient GPIO for: motor drive signals, ADC for voltage sensing, LED, UART
- Low cost, readily available
- Small package suitable for locomotive interior
- **Strong candidates**: ESP32-S3, ESP32-C3, ESP32-C6

#### 5. Environmental/Mechanical Constraints
- Must fit inside a Marklin locomotive body (compact PCB)
- Operating temperature: ambient (indoor model railway)
- No specific IP rating needed
- Components shall as far as possible be SMT; passives in 0603 packages
- In/Out signals from the board shall be solder points (pads), not connectors — connectors are too large for the locomotive interior

#### 6. Applicable Standards
- **IEC 62368-1:2023 (Ed. 4.0)** — *Audio/video, information and communication technology equipment — Part 1: Safety requirements*
  - Hazard-based product safety standard that classifies energy sources, prescribes safeguards, and aims to reduce the likelihood of pain, injury, and property damage from fire.
  - Applies to electrical/electronic equipment in the audio, video, ICT, and office machine fields with rated voltage not exceeding 600 V.
  - Replaces the former IEC 60065 (AV safety) and IEC 60950-1 (IT equipment safety).
  - Reference: https://webstore.iec.ch/en/publication/69308

#### 7. Out of Scope
- Firmware/software development
- Mechanical enclosure design
- DCC protocol support (this is for classic AC Marklin only)
