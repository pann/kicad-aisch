# Phase 3: Block-Level Design

## Workflow Steps (for skill automation)

### Step 1: Decompose architecture into schematic blocks
- Each block becomes a KiCad hierarchical sheet
- Blocks should be small enough for a single schematic page

### Step 2: Document each block
- Purpose, interfaces (inputs/outputs/power), domain, key design notes

### Step 3: Create block interconnect diagram
- Show block-to-block wiring with isolation boundary

### Step 4: Write document and generate PDF

---

## Test Project: Block-Level Design

### Block Decomposition

The architecture (Phase 2) defines two galvanically isolated domains — AC (track-referenced) and DC (MCU GND-referenced) — bridged by optocouplers. The design decomposes into 9 schematic blocks, each suitable for a single KiCad hierarchical sheet.

| # | Block | Domain | Sheet |
|---|---|---|---|
| 1 | Power Supply | Crosses boundary (AC in, DC out) | power_supply.kicad_sch |
| 2 | ESP32-C3 MCU | DC | esp32_c3.kicad_sch |
| 3 | Zero-Crossing Detector | Crosses boundary (AC sense, DC output) | zero_crossing.kicad_sch |
| 4 | Hardware Interlock | DC | hw_interlock.kicad_sch |
| 5 | TRIAC Drive (x2) | Crosses boundary (DC control, AC switch) | triac_drive.kicad_sch |
| 6 | Voltage Sensing | Crosses boundary (AC sense, DC ADC) | voltage_sense.kicad_sch |
| 7 | Status LED | DC | status_led.kicad_sch |
| 8 | USB Programming | DC | usb_prog.kicad_sch |
| 9 | Connectors | AC | connectors.kicad_sch |

### Block Descriptions

#### Block 1: Power Supply

**Purpose:** Convert 24 VAC track voltage to 3.3 VDC for the MCU and digital circuitry.

**Function:**
- Bridge rectifier converts 24 VAC to ~30-34 VDC peak (unregulated)
- Input filter capacitor smooths rectified DC
- Buck converter steps down to 3.3 VDC regulated output
- Output decoupling capacitors

**Interfaces:**
- **Inputs:** AC_L, AC_N (24 VAC from track, via connectors block)
- **Outputs:** +3V3 (regulated), DC_GND
- **Power rails provided:** +3V3, DC_GND

**Domain:** Crosses isolation boundary — AC input side is track-referenced, DC output side establishes the MCU ground domain.

**Design notes:**
- The bridge rectifier output is the origin of DC_GND — this is the reference point for the entire DC domain
- Buck converter must handle Vin up to ~35 VDC (from 25 VAC peak) with margin
- Output current budget: ESP32-C3 WiFi active ~240 mA + peripherals ~60 mA = ~300 mA typical, design for 500 mA
- EMI filter on input recommended for conducted emissions

#### Block 2: ESP32-C3 MCU

**Purpose:** Central controller — runs Modbus TCP server, WiFi stack, motor control logic, and phase-angle timing.

**Function:**
- ESP32-C3 RISC-V MCU (QFN32 or module)
- Decoupling capacitors on all VDD pins
- RF matching network and PCB antenna (or module with integrated antenna)
- Boot/reset pushbuttons with RC debounce
- 40 MHz crystal (if bare chip, not needed for module)

**Interfaces:**
- **Power:** +3V3, DC_GND
- **Inputs:** ZC_PULSE (zero-crossing interrupt, from block 3), V_SENSE (analog voltage, from block 6), USB_D+/USB_D- (from block 8)
- **Outputs:** FWD_CMD, REV_CMD (GPIO to hardware interlock, block 4), LED_CTRL (GPIO to status LED, block 7)
- **Bidirectional:** WiFi (antenna, on-chip)

**Domain:** DC only.

**Design notes:**
- If using bare ESP32-C3 chip: need 40 MHz crystal, RF matching, and flash IC
- If using ESP32-C3 module (e.g., ESP32-C3-MINI-1): crystal, flash, and antenna are integrated — simpler BOM, recommended for first revision
- GPIO allocation (preliminary):
  - GPIO0: ZC_PULSE (input, interrupt-capable)
  - GPIO1: V_SENSE (ADC input)
  - GPIO2: FWD_CMD (output)
  - GPIO3: REV_CMD (output)
  - GPIO4: LED_CTRL (output)
  - GPIO18: USB_D- (fixed)
  - GPIO19: USB_D+ (fixed)
  - GPIO8: Boot mode (active low for download, active high for run)
  - GPIO9: Boot button (directly usable as GPIO after boot)

#### Block 3: Zero-Crossing Detector

**Purpose:** Sense AC zero-crossings and provide an isolated logic-level pulse to the MCU for phase-angle timing.

**Function:**
- AC-side resistor divider limits current into optocoupler LED
- 4-diode bridge rectifier steers current through the optocoupler LED on both AC half-cycles (full-wave detection at 100/120 Hz)
- Optocoupler (EL357N) provides galvanic isolation
- DC-side pull-up resistor provides logic-level output

**Interfaces:**
- **Inputs:** AC_L, AC_N (track AC, from connectors block)
- **Outputs:** ZC_PULSE (logic-level signal to ESP32 GPIO, pulses at 100/120 Hz)
- **Power:** +3V3 (DC side pull-up only), DC_GND

**Domain:** Crosses isolation boundary — AC input, DC output.

**Design notes:**
- Full-wave detection required: AC output must be controlled on both positive and negative half-cycles, requiring ZC detection at 2x line frequency
- 4 x 1N4148WS diodes form a full bridge around the optocoupler LED, ensuring correct LED polarity on both AC half-cycles
- Two 3.3K/1W resistors in series (6.6K total) limit LED current to ~5 mA peak at 34V
- DC-side output should be fast enough for accurate zero-crossing timing (<100 us jitter)
- CTR (current transfer ratio) of optocoupler affects output rise time

#### Block 4: Hardware Interlock

**Purpose:** Enforce mutual exclusion of FWD and REV TRIAC gate signals in hardware, independent of firmware.

**Function:**
- Two cross-coupled NAND gates (e.g., 74LVC00 or similar)
- If both FWD_CMD and REV_CMD are asserted simultaneously (firmware fault), both outputs are forced inactive
- Normal operation: only one output active at a time
- Optional: dead-time enforcement (brief all-off period during direction change)

**Interfaces:**
- **Inputs:** FWD_CMD, REV_CMD (from ESP32 GPIOs)
- **Outputs:** FWD_GATE, REV_GATE (to TRIAC drive optocouplers, block 5)
- **Power:** +3V3, DC_GND

**Domain:** DC only (sits between MCU GPIOs and TRIAC optocoupler DC-side inputs).

**Design notes:**
- Truth table:

| FWD_CMD | REV_CMD | FWD_GATE | REV_GATE |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 1 | 0 | 1 | 0 |
| 0 | 1 | 0 | 1 |
| 1 | 1 | 0 | 0 |

- Uses a single 74LVC00 (quad 2-input NAND) — only 2 gates needed for cross-coupling, with 2 spare
- 3.3V compatible logic family required (LVC, AHC, or similar)
- Active-high convention: output HIGH = TRIAC gate enabled
- Decoupling cap on VCC

#### Block 5: TRIAC Drive (x2)

**Purpose:** Isolated gate drive for the two motor winding TRIACs (forward and reverse).

**Function:**
- DC-side: optocoupler LED driven from interlock output (FWD_GATE or REV_GATE) via current-limiting resistor
- Optocoupler (e.g., MOC3021 zero-cross type or MOC3041 with built-in zero-cross) provides isolation
- AC-side: optocoupler TRIAC output triggers the main power TRIAC gate
- Main TRIAC (e.g., BTA16-600B or similar) switches track AC to motor winding
- Snubber network (RC) across TRIAC for dV/dt protection

**Interfaces:**
- **Inputs:** FWD_GATE or REV_GATE (DC side, from interlock block 4), AC_L (track AC, from connectors)
- **Outputs:** MOTOR_FWD or MOTOR_REV (AC to motor winding, via connectors block 9)
- **Power:** +3V3, DC_GND (DC side for optocoupler LED drive only)

**Domain:** Crosses isolation boundary — DC control input, AC power output.

**Design notes:**
- Two identical channels — can be a single sheet instantiated twice or one sheet with both channels
- MOC3021 (random-phase) recommended over MOC3041 (zero-cross) because phase-angle control requires firing at arbitrary points in the AC cycle, not only at zero crossings
- TRIAC rating: 600V, 4A minimum (motor current typically <2A, but provide margin)
- Gate resistor between MOC3021 output and TRIAC gate (~360 ohm typical)
- Snubber: 100 nF + 100 ohm in series across TRIAC (values to be refined in detailed design)
- Heat sinking may be needed depending on motor current and duty cycle

#### Block 6: Voltage Sensing

**Purpose:** Measure track AC voltage magnitude for the MCU (diagnostics, undervoltage detection, speed calibration).

**Function:**
- Isolated measurement using either:
  - (a) Resistor divider + optocoupler (simple, low accuracy), or
  - (b) Small isolation transformer + rectifier + divider (better accuracy)
- Output scaled to 0-3.3V range for ESP32 ADC input
- Low-pass filter to smooth rectified signal to a DC level proportional to AC RMS

**Interfaces:**
- **Inputs:** AC_L, AC_N (track AC, from connectors)
- **Outputs:** V_SENSE (analog 0-3.3V to ESP32 ADC, block 2)
- **Power:** +3V3, DC_GND (DC side)

**Domain:** Crosses isolation boundary — AC sense input, DC analog output.

**Design notes:**
- Approach (a) is simpler but nonlinear (optocoupler CTR varies). Suitable for relative measurement / threshold detection
- Approach (b) provides better linearity but adds a transformer. Overkill for this application
- Recommended: approach (a) with software calibration
- ADC input protection: series resistor + clamp diodes to 3.3V and GND
- ESP32-C3 ADC is 12-bit but has limited linearity — adequate for voltage monitoring, not precision measurement

#### Block 7: Status LED

**Purpose:** Visual indication of controller state (power, WiFi connected, motor running, fault).

**Function:**
- Single LED driven from MCU GPIO via current-limiting resistor
- GPIO supports PWM for brightness control or blink patterns

**Interfaces:**
- **Inputs:** LED_CTRL (from ESP32 GPIO, block 2)
- **Power:** +3V3, DC_GND

**Domain:** DC only.

**Design notes:**
- Standard LED + resistor (e.g., green LED, 1K resistor for ~1.5 mA at 3.3V)
- ESP32 GPIO can source ~12 mA — direct drive is fine, no transistor needed
- Consider using an LED with integrated resistor to reduce BOM
- Firmware defines blink patterns (out of scope for hardware design, but GPIO must support PWM)

#### Block 8: USB Programming

**Purpose:** USB-C connector for firmware programming and debug via ESP32-C3 native USB (CDC/JTAG).

**Function:**
- USB-C receptacle with proper CC pull-down resistors (5.1K to GND) for device mode
- ESD protection TVS diode array on D+/D-
- Direct connection to ESP32-C3 USB pins (GPIO18=D-, GPIO19=D+)

**Interfaces:**
- **Outputs:** USB_D+, USB_D- (to ESP32, block 2)
- **Power:** VBUS (5V from USB host) — not used for powering the board (track-powered), but may be connected for USB detection
- **Ground:** USB_GND connected to DC_GND

**Domain:** DC only.

**Design notes:**
- No USB-UART bridge IC needed — ESP32-C3 has native USB CDC/JTAG
- USB-C CC resistors: 5.1K on each CC pin to GND (device mode, signals USB 2.0 default power)
- ESD protection is essential — USB port is an external interface exposed to user handling
- Consider USB_VBUS detection on a GPIO for auto-boot into download mode (optional, firmware-level feature)
- USB ground must be common with MCU ground (DC_GND)

#### Block 9: Connectors

**Purpose:** Physical interface to the track and motor windings.

**Function:**
- Track input: 2 solder pads for 24 VAC (AC_L, AC_N)
- Motor output: 3 solder pads for motor common + two windings (MOTOR_COM, MOTOR_FWD, MOTOR_REV)
- Motor common is connected to AC_N (one side of track)

**Interfaces:**
- **Track input:** AC_L, AC_N (distributed to power supply, zero-crossing detector, voltage sense, TRIAC drive blocks)
- **Motor output:** MOTOR_FWD (from TRIAC 1), MOTOR_REV (from TRIAC 2), MOTOR_COM (AC_N)

**Domain:** AC only.

**Design notes:**
- Solder pads used instead of connectors — connectors are too large for the locomotive interior
- Track connections carry up to 2A motor current + MCU supply — pad size and trace width must match
- Motor common (MOTOR_COM) is tied to AC_N — this means one side of both windings shares a common return to the track
- Polarity marking recommended for track input (silkscreen labels on pads)

### Signal and Power Bus Summary

| Signal/Rail | Type | From Block | To Block(s) | Domain |
|---|---|---|---|---|
| AC_L | Power | 9 (Connectors) | 1, 3, 5, 6 | AC |
| AC_N | Power | 9 (Connectors) | 1, 3, 5, 6, 9 (MOTOR_COM) | AC |
| +3V3 | Power | 1 (Power Supply) | 2, 3, 4, 5, 6, 7, 8 | DC |
| DC_GND | Power | 1 (Power Supply) | 2, 3, 4, 5, 6, 7, 8 | DC |
| ZC_PULSE | Signal | 3 (Zero-Cross) | 2 (ESP32 GPIO) | DC |
| FWD_CMD | Signal | 2 (ESP32 GPIO) | 4 (Interlock) | DC |
| REV_CMD | Signal | 2 (ESP32 GPIO) | 4 (Interlock) | DC |
| FWD_GATE | Signal | 4 (Interlock) | 5 (TRIAC Drive) | DC |
| REV_GATE | Signal | 4 (Interlock) | 5 (TRIAC Drive) | DC |
| V_SENSE | Analog | 6 (Voltage Sense) | 2 (ESP32 ADC) | DC |
| LED_CTRL | Signal | 2 (ESP32 GPIO) | 7 (Status LED) | DC |
| USB_D+/D- | Signal | 8 (USB Prog) | 2 (ESP32 USB) | DC |
| MOTOR_FWD | Power | 5 (TRIAC 1) | 9 (Connectors) | AC |
| MOTOR_REV | Power | 5 (TRIAC 2) | 9 (Connectors) | AC |

### Block Interconnect Diagram

~~~diagram
# Domain backgrounds
group "AC DOMAIN (track-referenced)" 1 1 34 98 fill=255,240,240
group "DC DOMAIN (MCU GND-referenced)" 42 1 57 98 fill=240,245,255

vline 38 0 100 style=dashed label="ISOLATION BOUNDARY"

# ===== AC-SIDE BLOCKS =====
box conn "9: Connectors" 10 8 18 6
box acbus "AC Bus" 10 20 10 4

# ===== BOUNDARY-CROSSING BLOCKS (drawn straddling the boundary) =====
box psu "1: Power Supply" 38 8 20 6
box zcross "3: Zero-Cross Detect" 38 28 20 6
box triac "5: TRIAC Drive (x2)" 30 68 18 6
box vsense "6: Voltage Sense" 38 48 18 6

# ===== DC-SIDE BLOCKS =====
box esp "2: ESP32-C3 MCU" 66 38 18 8
box interlock "4: HW Interlock" 58 58 16 6
box led "7: Status LED" 86 28 14 5
box usb "8: USB Programming" 86 48 16 5

# ===== MOTOR OUTPUT =====
box motor "Motor Windings" 10 82 18 6

# ========== ARROWS ==========

# --- Power path ---
arrow conn psu right left label="24 VAC"
arrow psu esp right left label="+3V3"

# --- AC bus distribution ---
arrow conn acbus

# --- Zero-crossing ---
arrow acbus zcross right left label="AC sense"
arrow zcross esp right left label="ZC_PULSE"

# --- Voltage sensing ---
arrow acbus vsense right left label="AC sense"
arrow vsense esp right left label="V_SENSE"

# --- Motor control: ESP -> Interlock -> TRIAC -> Motor ---
arrow esp interlock bottom top label="FWD/REV_CMD"
arrow interlock triac left right label="FWD/REV_GATE"
arrow acbus triac right left label="Track AC"
arrow triac motor bottom top label="Switched AC"

# --- Peripherals ---
arrow esp led right left label="LED_CTRL"
arrow usb esp left right label="USB D+/D-"
~~~

### Isolation Boundary Crossings

All signals crossing the AC/DC isolation boundary pass through optocouplers:

| Crossing | Direction | Isolation Device | Block |
|---|---|---|---|
| Zero-crossing sense | AC to DC | Signal optocoupler (EL357N/PC817) | 3 |
| TRIAC FWD gate drive | DC to AC | TRIAC-output optocoupler (MOC3021) | 5 |
| TRIAC REV gate drive | DC to AC | TRIAC-output optocoupler (MOC3021) | 5 |
| Voltage sense | AC to DC | Signal optocoupler or isolation amp | 6 |
| Power supply | AC to DC | Bridge rectifier + buck (transformer isolation if needed) | 1 |

**Total optocouplers: 4** (1x zero-crossing, 2x TRIAC gate drive, 1x voltage sense)

### Design Verification Checklist

- All architecture elements from Phase 2 are covered by at least one block
- Each block fits on a single KiCad schematic sheet
- All inter-block interfaces are explicitly named and typed
- Isolation boundary crossings are identified with specific isolation devices
- Power budget accounted for (500 mA at 3.3V from buck converter)
- Hardware interlock truth table ensures mutual exclusion
- Signal flow is unidirectional at each interface (no ambiguous bidirectional signals except USB)
- Motor common return path is clearly defined (AC_N)
