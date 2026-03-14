# Phase 5: Bill of Materials

## Workflow Steps (for skill automation)

### Step 1: Compile BOM from component selection
- List all components with designators, values, packages, and LCSC part numbers

### Step 2: Check KiCad standard library availability
- For each component, verify symbol and footprint exist in KiCad libraries
- Flag missing components for import via easyeda2kicad

### Step 3: Export BOM as CSV
- OUTPUT: `.csv` file suitable for Excel import

---

## Test Project: Bill of Materials

### BOM Statistics

| Metric | Count |
|---|---|
| Unique part numbers | 24 |
| Total component count | 43 |
| Active ICs/modules | 8 |
| Discrete semiconductors | 7 |
| Passives (R/C) | 25 |
| Connectors/switches | 5 |
| Estimated BOM cost (1x) | ~$3.90-4.10 |

### KiCad Library Status

| Status | Count | Components |
|---|---|---|
| Available in KiCad | 19 | MB6S, XL1509, SS34, BAT54S, 1N4148WS, BT136-600, MOC3021M, USBLC6-2SC6, all passives, LED, connectors, switches |
| Substitute symbol available | 1 | SN74LVC00A (use 74HC00 symbol, set value to 74LVC00A) |
| Import needed (easyeda2kicad) | 2 | ESP32-C3-MINI-1-N4, EL357N |
| Footprint check needed | 2 | MOC3021S-TA1 (SMD-6P variant), snubber caps (400V film) |

### Components Requiring Import

These components are **not in the KiCad standard libraries** and must be imported before schematic capture:

#### 1. ESP32-C3-MINI-1-N4 (U1)

- **LCSC:** C2838502
- **Import command:** `easyeda2kicad --full --lcsc_id C2838502`
- **Reason:** KiCad has ESP32-C3-WROOM-02 and DevKitM-1, but not the MINI-1 module
- **Priority:** High — central MCU module

#### 2. EL357N(C)(TA)-G (U5, U6)

- **LCSC:** C29981
- **Import command:** `easyeda2kicad --full --lcsc_id C29981`
- **Reason:** Not in Isolator library. PC817 has same pinout but EL357N is SOP-4 (SMD) with different footprint
- **Priority:** Medium — can alternatively use PC817 symbol with custom footprint
- **Qty:** 2 (zero-crossing detector + voltage sense)

### Substitute Symbols

#### SN74LVC00APWR (U3)

- Use KiCad symbol `74xx:74HC00` — identical logic function and pinout
- Set component Value field to `SN74LVC00A`
- Assign footprint `Package_SO:TSSOP-14_4.4x5mm_P0.65mm`
- No import needed

### BOM CSV

The full BOM is exported to `workflow/05-bom.csv` with the following columns:

- Item, Block, Designator, Description, Manufacturer, MPN, Package, LCSC, Qty, Unit Price, KiCad Symbol, KiCad Footprint, Status

The CSV is suitable for import in Excel or LibreOffice Calc.
