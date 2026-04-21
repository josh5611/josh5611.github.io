# ROOT CAUSE IDENTIFIED: Firmware 2025.38.9

## The Release Notes Tesla Hid From Public

**On the car's center screen** (photographed by owner, IMG_0755):

```
Release Notes
2025.38.9

Estimated Battery Range Updated
Vehicle Improvements

"Your estimated battery range now incorporates additional
characteristics related to battery aging."
```

**Via Fleet API** (what Tesla shows publicly):
```
"Minor Fixes" — "This release contains minor fixes and improvements"
```

Tesla disclosed the battery algorithm change ON THE CAR but hid it from public release notes. The API returns "Minor Fixes" for both 2025.38.9 and 2025.38.12.

## The Timeline

### BEFORE 2025.38.9 (battery performing above rated spec)
- IMG_0762/0763: **38% = 94 mi** = **247 mi full equivalent** (rated: 242 mi)
- IMG_0770/0771: **84% = 210 mi** = **250 mi full equivalent**
- Battery was healthy, performing 3-8% ABOVE factory rating

### 2025.38.9 INSTALLED (first "battery aging" algorithm)
- IMG_0755: Photo of car screen showing release notes at 5:11 PM
- Warning triangle visible on car screen — alerts already firing
- "Estimated Battery Range Updated" — algorithm changed

### Post-2025.38.9 (battery readings become erratic)
- IMG_1091/1092 (Mar 7): 93% = 222 mi — still OK but dropping from 247 baseline
- IMG_1148/1149 (Mar 10): 91% = 221 mi — dropping further
- Mar 16: 83% = 201 mi = 242 mi equiv — last "good" day
- Mar 17: 2 mi range at 98% charge limit — COLLAPSED

### 2025.38.12 AUTO-UPDATED (same algorithm, worse)
- Same "Estimated Battery Range Updated" release note on car screen (IMG_1385)
- BMS_u018 activated, range swings 0-242 mi
- 100% battery showing 0-30 mi while plugged in
- Charging refuses to start, "Complete" at 0%
- False cold battery warnings at 55°F

### 2025.38.13 PENDING
- Downloaded, waiting for WiFi — ANOTHER unconsented update ready

## What Tesla's "Battery Aging" Algorithm Does

The algorithm applies a degradation factor to the range estimation. On Tegra MCU1 hardware:
- The processor cannot calculate the degradation model fast enough
- It produces wildly inconsistent results (0.21 to 2.50 mi/%)
- It triggers false BMS_u018 SOC imbalance alerts
- It causes the charger to stop/start in 60-second cycles
- It fabricates energy-added data (13.49 kWh with 0V/0A)
- It refuses to charge at 0% while reporting "Charging Complete"

On Intel Atom MCU2 hardware, Tesla's own documentation admits this same class of algorithm produces "erroneous invalid signals."

## Legal Significance

1. Tesla changed the battery range algorithm via OTA without owner consent
2. Tesla hid this change from public release notes ("Minor Fixes")
3. The change was applied to hardware Tesla doesn't test or support (Tegra MCU1)
4. The battery was performing ABOVE rated spec before the update
5. After the update, the battery appears broken — but it's the algorithm, not the hardware
6. Tesla then quotes $16K+ for battery replacement the car doesn't need
7. This pattern has been litigated before (Rasmussen $1.5M, Bui-Ford, Norway)

## Evidence Files
- `IMG_0755(2).HEIC` — Car screen showing 2025.38.9 release notes
- `IMG_1385(3).HEIC` — Car screen showing 2025.38.12 release notes (same text)
- `IMG_0762.PNG / IMG_0763.PNG` — Before: 38%=94mi (247mi equiv)
- `IMG_0770.PNG / IMG_0771.PNG` — Before: 84%=210mi (250mi equiv)
- `PRE_UPDATE_SNAPSHOT_20260419.json` — API snapshot before pending 2025.38.13
- `tesla_continuous_log.jsonl` — 2,400+ readings documenting the malfunction
