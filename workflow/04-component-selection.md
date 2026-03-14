# Phase 4: Component Selection

## Workflow Steps (for skill automation)

### Step 1: For each block, propose components
- Consider price, availability, and LCSC part numbers
- Propose 2-3 alternatives for critical components

### Step 2: Review and select with user
- Present options with rationale
- Document rejected alternatives with reasons

### Step 3: Write document and generate PDF

---

## Test Project: Component Selection

### Design Constraints

- First revision uses an **ESP32-C3-MINI-1 module** (not bare chip). This simplifies BOM — no crystal, flash IC, or RF matching network needed.
- **Components shall be SMT as far as possible; passives in 0603 packages.**

---

### Block 1: Power Supply

#### Bridge Rectifier

| Parameter | Selected | Alternative | Rejected |
|---|---|---|---|
| **Part** | MB6S | DB107S | KBP206 |
| **Manufacturer** | ST (Semtech) | Hottech | -- |
| **LCSC** | C2978785 | -- | Too large (through-hole) |
| **Package** | SOP-4 (MBS) | SOP-4 | Through-hole |
| **Rating** | 600V, 0.5A | 1000V, 1A | -- |
| **Price** | ~$0.024 | ~$0.03 | -- |

**Selected: MB6S** — SMD package, 600V rating adequate for 24 VAC (peak ~34V), 0.5A sufficient (MCU domain only, motor current does not pass through PSU).

#### Buck Converter

| Parameter | Selected | Alternative 1 | Alternative 2 |
|---|---|---|---|
| **Part** | XL1509-3.3E1 | LM2596S-3.3 | RT7272BGSP |
| **Manufacturer** | XLSEMI | UMW (TI clone) | Richtek |
| **LCSC** | C74193 | C347420 | C127866 |
| **Package** | SOP-8 | TO-263-5 | SOIC-8-EP |
| **Vin range** | 4.5-40V | 4.5-40V | 4.5-36V |
| **Iout max** | 2A | 3A | 3A |
| **Frequency** | 150 kHz | 150 kHz | 500 kHz |
| **Efficiency** | ~85% | ~85% | ~95% |
| **Price** | $0.14 | $0.24 | $0.26 |
| **Stock** | 42,500+ | 5,200+ | 117,000+ |

**Selected: XL1509-3.3E1** — Lowest cost, smallest package, 40V max input covers 24 VAC rectified (34V peak) with margin. 2A output is 4x the 500 mA requirement. Simple application circuit. Well-proven in hobbyist designs.

**Why not RT7272BGSP?** Better efficiency (95% vs 85%) and synchronous rectification, but overkill for 300 mA typical load. Adjustable output adds complexity. Worth considering if thermal issues arise in enclosed locomotive body.

**Why not LM2596S-3.3?** Excellent documentation but TO-263-5 package is physically large. Better suited for bench supplies than compact train controllers.

#### Buck Converter Support Components

| Component | Value | Package | LCSC | Notes |
|---|---|---|---|---|
| Input cap | 100uF/50V electrolytic | 8x10mm | C2993926 | Smoothing after bridge rectifier |
| Input ceramic cap | 100nF/50V | 0805 | C49678 | High-frequency bypass |
| Output cap | 220uF/10V electrolytic | 6.3x7.7mm | C2891399 | Output ripple reduction |
| Output ceramic cap | 22uF/10V | 0805 | C5662523 | Low-ESR output filtering |
| Schottky diode | SS34 (3A/40V) | SMA | C8678 | Catch diode for XL1509 |
| Inductor | 68uH/2A | 8x8mm | C408345 | Per XL1509 datasheet for 3.3V output |
| Feedback divider | Per datasheet | 0805 | -- | Fixed output version, internal divider |

#### Input EMI Filter (optional, recommended)

| Component | Value | Package | LCSC | Notes |
|---|---|---|---|---|
| Common mode choke | 10mH/0.5A | Through-hole | -- | To be selected in detailed design |
| X-cap | 100nF/275VAC | -- | -- | Across AC input |

---

### Block 2: ESP32-C3 MCU

#### MCU Module

| Parameter | Selected | Alternative |
|---|---|---|
| **Part** | ESP32-C3-MINI-1-N4 | ESP32-C3-MINI-1U-N4 |
| **Manufacturer** | Espressif | Espressif |
| **LCSC** | C2838502 | C2911374 |
| **Antenna** | PCB (integrated) | IPEX (external) |
| **Flash** | 4 MB | 4 MB |
| **Price** | $2.01 | $2.14 |
| **Stock** | 9,700+ | 2,300+ |

**Selected: ESP32-C3-MINI-1-N4** — PCB antenna version. Lowest cost, highest stock. External antenna (1U variant) only needed if WiFi range is insufficient inside the locomotive body — unlikely for home layout distances.

#### Decoupling Capacitors

| Component | Value | Qty | Package | LCSC | Notes |
|---|---|---|---|---|---|
| Bulk decoupling | 10uF/10V ceramic | 2 | 0805 | C15850 | VDD3P3 and VDD3P3_RTC |
| HF decoupling | 100nF/25V ceramic | 4 | 0603 | C14663 | Each VDD pin |

#### Boot/Reset

| Component | Value | Package | LCSC | Notes |
|---|---|---|---|---|
| Reset button | 3x4mm tactile SMD | SMD | C2886620 | Active-low reset (EN pin) |
| Boot button | 3x4mm tactile SMD | SMD | C2886620 | GPIO9 low = download mode |
| Pull-up resistor (EN) | 10K | 0603 | C25804 | EN pin pull-up |
| Pull-up resistor (GPIO9) | 10K | 0603 | C25804 | Boot pin pull-up (run mode) |
| Reset cap | 100nF | 0603 | C14663 | EN pin RC delay |

---

### Block 3: Zero-Crossing Detector

#### Optocoupler

| Parameter | Selected | Alternative | Rejected |
|---|---|---|---|
| **Part** | EL357N(C)(TA)-G | PC817C | 6N137 |
| **Manufacturer** | Everlight | Sharp | -- |
| **LCSC** | C29981 | C66340 | Overkill speed |
| **Package** | SOP-4 | DIP-4 | -- |
| **CTR** | 130-260% (C rank) | 200-400% (C rank) | -- |
| **Speed** | ~4us rise | ~4us rise | -- |
| **Isolation** | 3.75kV | 5kV | -- |
| **Price** | ~$0.03 | ~$0.04 | -- |

**Selected: EL357N(C)(TA)-G** — SMD package, adequate speed for 50/60 Hz zero-crossing detection (~20ms period, <100us timing requirement easily met). High CTR C-rank gives clean output transitions.

**Why not PC817?** DIP package is larger. Both work, but EL357N is SMD and slightly cheaper.

#### Support Components

| Component | Value | Package | Notes |
|---|---|---|---|
| AC series resistor | 3.3K/1W | 1206 or axial | Limits LED current to ~5mA at 34V peak |
| AC series resistor 2 | 3.3K/1W | 1206 or axial | Two in series for voltage sharing (6.6K total) |
| DC pull-up resistor | 10K | 0603 | Pull-up to 3.3V on output (C25804) |
| Bridge diodes | 1N4148WS x4 | SOD-323 | Full-wave bridge for both-half-cycle ZC detection (C2128) |

---

### Block 4: Hardware Interlock

#### Logic IC

| Parameter | Selected | Alternative |
|---|---|---|
| **Part** | 74LVC00AD,118 | SN74LVC00APWR |
| **Manufacturer** | Nexperia | Texas Instruments |
| **LCSC** | C6044 | C7803 |
| **Package** | SOIC-14 | TSSOP-14 |
| **VCC range** | 1.65-5.5V | 1.65-5.5V |
| **Price** | $0.13 | $0.10 |
| **Stock** | Good | Good |

**Selected: SN74LVC00APWR (TI)** — Slightly cheaper, TSSOP-14 saves board space. 3.3V operation, 5ns propagation delay (vastly faster than needed). Quad NAND — uses 2 gates for cross-coupled interlock, 2 gates spare.

#### Support Components

| Component | Value | Package | Notes |
|---|---|---|---|
| Decoupling cap | 100nF/10V | 0603 | VCC bypass (C14663) |

---

### Block 5: TRIAC Drive (x2)

#### TRIAC Gate Drive Optocoupler

| Parameter | Selected | Alternative |
|---|---|---|
| **Part** | MOC3021S-TA1 | MOC3021 (DIP) |
| **Manufacturer** | Lite-On | Lite-On |
| **LCSC** | C115465 | C123202 |
| **Package** | SMD-6P | DIP-6 |
| **Type** | Random-phase (non-zero-cross) | Random-phase |
| **Isolation** | 5.3kV | 5.3kV |
| **Price** | $0.14 | $0.086 |
| **Stock** | Good | 30,000+ |
| **Qty needed** | 2 | -- |

**Selected: MOC3021S-TA1** — SMD version of the MOC3021, per design requirement for SMT components. Random-phase type required for phase-angle motor speed control (must fire at arbitrary points in AC cycle). Zero-cross types (MOC3041) would only allow on/off control, defeating the purpose.

#### Power TRIAC

| Parameter | Selected | Alternative | Rejected |
|---|---|---|---|
| **Part** | BT136-600E | BTA16-600B | BTA08-600C |
| **Manufacturer** | WEIDA | Minos | -- |
| **LCSC** | C2901007 | C5452761 | -- |
| **Package** | TO-252 (SMD) | TO-220 (THT) | -- |
| **Rating** | 600V / 4A | 600V / 16A | -- |
| **Gate trigger** | ~10mA (sensitive) | ~50mA | -- |
| **Price** | $0.11 | $0.35 | -- |
| **Stock** | 1,820 | 370 | -- |
| **Qty needed** | 2 | -- | -- |

**Selected: BT136-600E** — 4A rating provides 2x margin over typical motor current (<2A). Sensitive gate (10mA) is easier to drive from MOC3021 output. SMD package (TO-252) saves space. Significantly cheaper than BTA16-600B.

**Why not BTA16-600B?** 16A is massive overkill for a model train motor. More expensive, lower stock, requires through-hole mounting. The BT136 at 4A is adequate with margin.

#### Support Components (per channel, x2)

| Component | Value | Package | Notes |
|---|---|---|---|
| Optocoupler LED resistor | 470R | 0603 | Drive current from 3.3V: (3.3-1.2)/470 = ~4.5mA (C23179) |
| Gate resistor | 360R/0.5W | 1206 | Between MOC3021 output and TRIAC gate |
| Snubber resistor | 100R/0.5W | 1206 | Across TRIAC, in series with snubber cap |
| Snubber capacitor | 100nF/400V | Film/ceramic | Across TRIAC, dV/dt protection |

---

### Block 6: Voltage Sensing

#### Optocoupler

Same as zero-crossing detector: **EL357N(C)(TA)-G** (C29981). Keeps BOM simple.

#### Support Components

| Component | Value | Package | Notes |
|---|---|---|---|
| AC series resistor 1 | 10K/0.5W | 1206 | Current limiting into optocoupler LED |
| AC series resistor 2 | 10K/0.5W | 1206 | Voltage sharing |
| DC load resistor | 10K | 0603 | Sets DC output level (C25804) |
| Filter cap | 1uF/10V | 0603 | Low-pass filter (~16 Hz with 10K) (C15849) |
| ADC protection resistor | 1K | 0603 | Series with ADC input (C21190) |
| Clamp diode to 3V3 | BAT54S (dual) | SOT-23 | Schottky clamp, overvoltage protection |

---

### Block 7: Status LED

| Component | Value | Package | LCSC | Notes |
|---|---|---|---|---|
| LED (green) | 0805 SMD | 0805 | C2297 | Standard green, 20mcd typ |
| Current limiting resistor | 1K | 0603 | C21190 | ~1.5mA at 3.3V (adequate brightness for indicator) |

---

### Block 8: USB Programming

#### USB-C Connector

| Parameter | Selected | Alternative |
|---|---|---|
| **Part** | TYPE-C 16P (073) | TYPE-C 6P |
| **Manufacturer** | SHOU HAN | SHOU HAN |
| **LCSC** | C2906290 | -- |
| **Pins** | 16 (full) | 6 (simplified) |
| **Price** | $0.044 | $0.020 |

**Selected: 16-pin USB-C** — Full pinout for proper USB 2.0 operation. At $0.044 the cost difference from 6-pin is negligible.

#### ESD Protection

| Parameter | Selected |
|---|---|
| **Part** | USBLC6-2SC6 |
| **Manufacturer** | TECH PUBLIC (or ST) |
| **LCSC** | C2827693 (TP) or C7519 (ST) |
| **Package** | SOT-23-6 |
| **ESD rating** | ±30kV air, ±25kV contact |
| **Capacitance** | 0.4pF (minimal signal impact) |
| **Price** | $0.02 (TP) / $0.07 (ST) |

**Selected: USBLC6-2SC6** — Industry standard for USB ESD protection. TECH PUBLIC clone acceptable for prototype; use ST for production.

#### Support Components

| Component | Value | Package | Notes |
|---|---|---|---|
| CC1 pull-down | 5.1K | 0603 | USB-C CC1 pin to GND (device mode) (C23186) |
| CC2 pull-down | 5.1K | 0603 | USB-C CC2 pin to GND (device mode) (C23186) |

---

### Block 9: Connectors

#### Track Input (2 pads)

| Parameter | Selected |
|---|---|
| **Type** | Solder pads (2mm test points) |
| **Symbol** | Connector:TestPoint |
| **Footprint** | TestPoint:TestPoint_Pad_2.0x2.0mm |
| **Designators** | TP1 (AC_L), TP2 (AC_N) |
| **Price** | $0.00 (PCB feature only) |

#### Motor Output (3 pads)

| Parameter | Selected |
|---|---|
| **Type** | Solder pads (2mm test points) |
| **Symbol** | Connector:TestPoint |
| **Footprint** | TestPoint:TestPoint_Pad_2.0x2.0mm |
| **Designators** | TP3 (MOTOR_COM), TP4 (MOTOR_FWD), TP5 (MOTOR_REV) |
| **Price** | $0.00 (PCB feature only) |

**Note:** Solder pads used instead of connectors per design requirement — connectors are too large for the locomotive interior. Wires are soldered directly to the board. 2mm test point pads used as schematic symbols; pad size may be increased during PCB layout to accommodate wire gauge for 2A motor current.

---

### Common Passives (shared across blocks)

| Component | Value | Package | LCSC | Usage |
|---|---|---|---|---|
| Resistor 10K | 10K 1% | 0603 | C25804 | Pull-ups, dividers |
| Resistor 1K | 1K 1% | 0603 | C21190 | LED, series protection |
| Resistor 5.1K | 5.1K 1% | 0603 | C23186 | USB CC |
| Resistor 470R | 470R 1% | 0603 | C23179 | Optocoupler LED drive |
| Cap 100nF/25V | 100nF X7R | 0603 | C14663 | Decoupling |
| Cap 10uF/10V | 10uF X5R | 0805 | C15850 | Bulk decoupling |
| Cap 1uF/10V | 1uF X7R | 0603 | C15849 | Filtering |
| Diode 1N4148 | 75V/150mA | SOD-323 | C2128 | Signal/protection |

---

### BOM Summary

| Block | Key Active Components | Estimated Active Cost |
|---|---|---|
| 1. Power Supply | MB6S + XL1509 + SS34 + inductor | ~$0.50 |
| 2. ESP32-C3 MCU | ESP32-C3-MINI-1-N4 | ~$2.01 |
| 3. Zero-Crossing | EL357N | ~$0.03 |
| 4. HW Interlock | SN74LVC00APWR | ~$0.10 |
| 5. TRIAC Drive (x2) | MOC3021S x2 + BT136-600E x2 | ~$0.50 |
| 6. Voltage Sense | EL357N + BAT54S | ~$0.06 |
| 7. Status LED | LED + resistor | ~$0.01 |
| 8. USB Programming | USB-C + USBLC6-2SC6 | ~$0.07 |
| 9. Connectors | Solder pads (no components) | $0.00 |
| **Total active components** | | **~$3.43** |

Passives (resistors, caps, diodes) add approximately $0.30-0.50, bringing the **estimated total BOM cost to ~$3.90-4.10** (at LCSC single-unit pricing, excluding PCB).

---

### Components Reviewed and Rejected

| Component | Reason for Rejection |
|---|---|
| ESP32-C3 bare chip | Requires external crystal, flash, RF matching — too complex for Rev 1 |
| ESP32-C3-MINI-1U (IPEX) | External antenna unnecessary for home layout range |
| LM2596S-3.3 (buck) | TO-263 package too large for in-locomotive PCB |
| RT7272BGSP (buck) | Higher efficiency but overkill; adjustable adds complexity |
| BTA16-600B (TRIAC) | 16A massively oversized for <2A motor; more expensive, through-hole |
| MOC3041 (zero-cross opto) | Zero-cross type prevents phase-angle speed control |
| PC817 (optocoupler) | DIP package larger than EL357N SMD; otherwise equivalent |
| 6N137 (optocoupler) | High-speed opto — overkill for 50/60 Hz zero-crossing |
| MOC3021 DIP-6 (through-hole) | Design requires SMT components; replaced by MOC3021S-TA1 (SMD-6P) |
| 0402 passives | Design specifies 0603 package for passives |
| 6-pin USB-C connector | Marginal cost savings ($0.02), incomplete USB-C implementation |

---

### Open Items for Detailed Design

1. **XL1509 application circuit** — verify inductor value and Schottky diode rating against datasheet reference design
2. **Snubber values** — 100nF + 100R are starting values; may need tuning based on TRIAC dV/dt behavior with inductive (motor) load
3. **EMI filter** — common mode choke and X-cap values to be determined during layout/testing
4. **Zero-crossing resistor values** — verify 2x 3.3K (6.6K total) gives adequate LED current across full AC cycle for reliable detection
5. **Thermal analysis** — BT136-600E in TO-252 package at 2A needs ~1.6W dissipation check; may need copper pour for heat sinking
6. **LCSC stock verification** — confirm all parts in stock at time of ordering (stock levels from March 2026 research)
