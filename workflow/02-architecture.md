# Phase 2: Architecture & MCU Selection

## Workflow Steps (for skill automation)

### Step 1: Evaluate MCU candidates
- Based on requirements, compare candidate MCUs on: core performance, peripherals, WiFi, power, package size, cost, toolchain maturity

### Step 2: Present comparison and recommendation for review
- Tabulated comparison with rationale for recommendation

### Step 3: User reviews and selects MCU
- Iterate until MCU choice is agreed

### Step 4: Document architecture decisions
- Output: `<project>/02-architecture.md` — MCU selection and system architecture rationale

---

## Test Project: Architecture & MCU Selection

### Candidate Comparison

| Feature | ESP32-C3 | ESP32-C6 | ESP32-S3 |
|---|---|---|---|
| **CPU** | RISC-V single-core, 160 MHz | RISC-V single-core, 160 MHz + LP core 20 MHz | Xtensa LX7 dual-core, 240 MHz |
| **RAM** | 400 KB SRAM | 512 KB + 16 KB (LP) | 512 KB SRAM |
| **Flash** | 4 MB (typical) | 4-16 MB | External (module-dependent, 4 MB+) |
| **WiFi** | 802.11 b/g/n | 802.11 ax (WiFi 6) + b/g/n | 802.11 b/g/n |
| **Bluetooth** | BLE 5.0 | BLE 5.3 | BLE 5.0 |
| **Zigbee/Thread** | No | Yes (802.15.4) | No |
| **GPIO** | 22 (11 usable) | 22-30 (package dependent) | Up to 45 |
| **ADC** | 2x 12-bit, 6 channels | 12-bit, 8 channels | 2x 12-bit, 20 channels |
| **PWM** | 6 LED PWM channels | 6 LED PWM channels | 8 LED PWM channels |
| **Native USB** | Yes (CDC/JTAG) | Yes (CDC) | Yes (CDC/JTAG) |
| **Package (smallest)** | QFN32, 5x5 mm | QFN32, 5x5 mm | QFN56, 7x7 mm |
| **Active WiFi** | 95-240 mA | ~60 mA typical | 78-240 mA |
| **Deep sleep** | ~5 uA | ~7 uA | ~9 uA |
| **Temp range** | -40 to +85C (105C ext.) | -40 to +85C (105C ext.) | -40 to +85C (105C ext.) |
| **LCSC chip price** | ~$1.15 | ~$2.18 | ~$2.14 |
| **LCSC module price** | ~$2.17-2.43 | ~$2.83-3.24 | ~$3.46-3.80 |
| **PlatformIO** | Full support | Partial (needs community fork) | Full support |

### Assessment Against Requirements

#### Real-time requirements
- Motor PWM control: All three candidates have sufficient PWM channels (need 2 for motor windings)
- Modbus TCP server: Single-core at 160 MHz is sufficient; dual-core is not needed
- No hard real-time constraints identified

#### Memory requirements
- Modbus TCP + WiFi stack: ~200-300 KB RAM typical
- All three have sufficient RAM (400-512 KB)
- 4 MB flash is adequate for firmware

#### Power requirements
- All power from 24 VAC track. After rectification: ~30-34 VDC peak
- Need buck converter to 3.3V for MCU
- WiFi active current 60-240 mA at 3.3V = 0.2-0.8W — negligible vs motor power
- ESP32-C6 has lowest active WiFi consumption (~60 mA typical) due to WiFi 6

#### Package size
- Must fit inside locomotive body. Compact PCB is critical
- ESP32-C3 and C6: 5x5 mm QFN — smallest
- ESP32-S3: 7x7 mm QFN — larger, but still feasible
- Module size matters more than bare chip (antenna integration)

#### Cost
- ESP32-C3 is cheapest ($1.15 chip, $2.17 module)
- ESP32-S3 and C6 are comparable ($2.14-2.18 chip)
- For a hobby/low-volume project, module price difference is negligible

#### Toolchain maturity
- ESP32-C3: Mature, full support across ESP-IDF, Arduino, PlatformIO
- ESP32-S3: Mature, full support
- ESP32-C6: ESP-IDF and Arduino supported, but PlatformIO requires community fork — less mature

### Recommendation: ESP32-C3

**Rationale:**

1. **Sufficient performance** — 160 MHz RISC-V core handles Modbus TCP + PWM motor control with margin. Dual-core (S3) is overkill for this application.

2. **Smallest and cheapest** — 5x5 mm QFN package, $1.15 chip / $2.17 module. Important for fitting inside a locomotive.

3. **Most mature toolchain** — Full ESP-IDF, Arduino, and PlatformIO support. No workarounds needed (unlike C6 PlatformIO issues).

4. **Native USB** — Built-in CDC/JTAG eliminates need for an external USB-UART bridge (e.g., CP2102), simplifying BOM and PCB.

5. **Adequate peripherals** — GPIO for TRIAC gate triggers, zero-crossing detection input, ADC for voltage sensing, UART for debug, GPIO for LED.

6. **WiFi 6 not needed** — The C6's WiFi 6 and Thread/Zigbee support offer no benefit for a Modbus TCP application on a home network.

**Candidates not selected:**

- **ESP32-S3**: Dual-core 240 MHz is more CPU than needed. Larger package (7x7 mm). Higher module cost. The extra GPIO and ADC channels are not required.
- **ESP32-C6**: WiFi 6 and Zigbee/Thread are not needed. PlatformIO support is immature (requires community fork). Slightly more expensive than C3 with no practical benefit for this application.

### System Architecture Overview

~~~diagram
# Two domain groups
group "AC DOMAIN (track-referenced)" 1 1 34 98 fill=255,240,240
group "DC DOMAIN (MCU GND-referenced)" 42 1 57 98 fill=240,245,255

vline 38 0 100 style=dashed label="ISOLATION BOUNDARY"

# ===== TRACK INPUT (top left) =====
box track "Track 24 VAC" 10 6 14 5

# ===== POWER PATH (top right) =====
box bridge "Bridge Rectifier" 62 6 16 5
box buck "Buck Converter (3.3V)" 62 16 18 5

# ===== ZERO-CROSSING PATH (row 2, well below buck) =====
box zcross "Zero-crossing Optocoupler" 24 26 20 5
box zcross_out "Zero-cross Input (GPIO)" 62 26 18 5

# ===== MCU (center right) =====
box esp "ESP32-C3" 62 39 16 8

# ===== PERIPHERALS (far right, spaced vertically) =====
box wifi "WiFi / Modbus TCP" 86 33 16 5
box led "Status LED" 86 42 12 4
box usb "USB Programming" 86 50 14 4
box vsense "Voltage Sense (ADC, iso)" 86 58 18 4

# ===== HW INTERLOCK (below ESP32) =====
box interlock "HW Interlock (NAND gates)" 58 54 20 5

# ===== OPTOCOUPLERS (on boundary, below interlock) =====
box opto1 "Opto FWD" 44 65 10 4
box opto2 "Opto REV" 44 76 10 4

# ===== TRIACs (AC side, same rows as optos) =====
box triac1 "TRIAC 1 (Fwd)" 20 65 14 4
box triac2 "TRIAC 2 (Rev)" 20 76 14 4

# ===== MOTOR WINDINGS (offset left/right so arrows don't cross TRIACs) =====
box fwd "Fwd Winding" 8 89 12 4
box rev "Rev Winding" 32 89 12 4

# ===== AC BUS TAP (far left, between TRIACs, feeds from left side) =====
box acbus "AC Bus" 5 70 6 4

# ========== ARROWS ==========

# --- Power path ---
arrow track bridge right left label="AC power"
arrow bridge buck
arrow buck esp

# --- WiFi ---
arrow esp wifi right left

# --- Zero-crossing path ---
arrow track zcross right left label="AC sense"
arrow zcross zcross_out right left label="isolated"
arrow zcross_out esp bottom top

# --- Track AC bus down left edge, then right to TRIACs ---
arrow track acbus bottom top
arrow acbus triac1 right left label="Track AC"
arrow acbus triac2 right left

# --- Motor control: ESP32 -> Interlock -> Optos -> TRIACs ---
arrow esp interlock bottom top label="GPIO FWD/REV"
arrow interlock opto1 bottom top
arrow interlock opto2 bottom top
arrow opto1 triac1 left right label="gate"
arrow opto2 triac2 left right label="gate"

# --- TRIACs to motor windings (offset to avoid crossing through other TRIAC) ---
arrow triac1 fwd left top
arrow triac2 rev right top

# --- ESP32 peripherals (right side, no crossing) ---
arrow esp led right left
arrow esp usb right left
arrow vsense esp left right
~~~

**Two separate ground domains:**
- **AC domain**: Track-referenced. TRIACs, motor windings, and zero-crossing sense circuit operate here
- **DC domain**: MCU GND, derived from bridge rectifier output. ESP32, LED, USB operate here
- **Isolation boundary**: Optocouplers bridge the two domains for TRIAC gate drive and zero-crossing detection

**Motor drive approach:**
- The motor is AC-driven — the field windings receive track AC directly, NOT rectified DC
- **Direction control**: Two TRIACs, one per field winding. Only one is active at a time. The ESP32 selects direction by triggering the appropriate TRIAC gate via optocoupler isolation
- **Hardware interlock**: A hardware mutual exclusion circuit (e.g., cross-coupled NAND gates or similar logic) prevents both TRIAC gate signals from being active simultaneously, regardless of firmware state. This protects the motor even in case of MCU software fault or runaway
- **Speed control**: Phase-angle control — the ESP32 detects AC zero-crossings via isolated optocoupler interrupt, then fires the TRIAC gate at a variable delay to control the portion of each AC half-cycle delivered to the motor
- **Zero-crossing detection**: An optocoupler on the track AC provides galvanic isolation and a clean logic-level signal to an ESP32 GPIO input

**Key architectural decisions:**
- AC motor path is galvanically separate from the DC MCU domain — optocouplers provide isolation for all signals crossing the boundary
- Single 3.3V rail for MCU from bridge rectifier + buck converter
- Hardware interlock gate logic between ESP32 GPIOs and TRIAC optocouplers — ensures mutual exclusion of forward/reverse windings independent of software
- Three optocouplers needed: 2x TRIAC gate drive, 1x zero-crossing detection
- Zero-crossing detector needed for phase-angle speed control
- TRIACs chosen over relays: no mechanical wear, fast switching, silent operation, enables phase-angle speed control (relays can only do on/off)
- Voltage sensing of track AC also requires isolation (isolated ADC input or optocoupler-based sensing)
- USB native on ESP32-C3 used for programming — no external UART bridge IC needed
