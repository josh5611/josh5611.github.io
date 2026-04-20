# Tesla P85D BMS Swing Analysis — April 3-19, 2026

**VIN:** 5YJSA1H25EFP67580  
**Firmware:** 2025.38.12 37d8ecb0f7ed  
**Odometer:** 97,726 miles  
**Rated Range (new):** 242 miles  
**Demonstrated Max (when BMS is working correctly):** ~241 miles (83% = 200 mi on Mar 10 = 241 mi full equivalent — matches rated spec)  
**Demonstrated Min (when BMS is malfunctioning):** ~21 miles (97% = 20.8 mi on Mar 28 = 21 mi full equivalent — 91% suppressed)  

---

## PERIOD 1: April 3-10 — Car plugged in at home, owner in Palm Springs, CA

The car was parked at the owner's residence (S Ivory St, Spokane WA), plugged into a home charger the entire time. Nobody drove it, nobody touched it. Owner was in Palm Springs, California.

### April 3 — 64% battery swing while plugged in
| Time | Battery | Usable | Range | Event |
|------|---------|--------|-------|-------|
| 00:00 | 23% | 19% | 26 mi | Plugged in |
| 00:43 | 20% | — | — | Battery DROPPED 3% while charging |
| 00:46 | 27% | 24% | 40 mi | Jumped UP 7% in 3 minutes |
| 03:55 | 27% | 24% | 39 mi | Stable for 3 hours |
| 03:55 | 33% | 31% | 54 mi | Jumped UP 6% |
| 05:40 | 33% | 31% | 54 mi | Disconnected briefly |
| 08:45 | 33% | 30% | 53 mi | Still 33% - not charging |
| 18:19 | 84% | 83% | 165 mi | Jumped to 84% by evening |

### April 5 — 100% battery, range collapses to 30 mi
**This is the single most damning day of data.**

| Time | Battery | Usable | Range | mi/% | Event |
|------|---------|--------|-------|------|-------|
| 02:58 | 100% | 98% | 121 mi | 1.21 | Plugged in, Charging Complete |
| 03:20 | 100% | 97% | 79 mi | 0.79 | **Lost 42 mi in 20 min — parked, plugged in** |
| 03:30 | 100% | 75% | 30 mi | 0.30 | **Lost another 49 mi in 10 min. 100% = 30 mi.** |
| 09:02 | 100% | 79% | 33 mi | 0.33 | Still suppressed 6 hours later |
| 19:09 | 100% | 98% | 108 mi | 1.08 | Magically recovered — no human intervention |

At 100% battery, this car should show ~225 miles (proven by the car's own readings when BMS is functioning). It showed **30 miles** — an **85% range suppression** while plugged in and fully charged. The usable battery dropped from 98% to 75% while the battery stayed at 100%, proving the BMS is artificially restricting available energy.

### April 7 — 100% battery, range: 34-112 mi
| Time | Battery | Usable | Range | mi/% |
|------|---------|--------|-------|------|
| 06:29 | 100% | 90% | 34 mi | 0.34 |
| 10:24 | 100% | 99% | 112 mi | 1.12 |

100% battery swinging between 34 and 112 miles. Car plugged in, not moving.

### April 8 — Range INCREASES as battery DROPS
| Time | Battery | Usable | Range | mi/% | Event |
|------|---------|--------|-------|------|-------|
| 02:56 | 100% | 97% | 63 mi | 0.63 | Plugged in |
| 08:33 | 100% | 99% | 132 mi | 1.32 | Range doubled by itself |
| 20:37 | 77% | 76% | 176 mi | 2.29 | **Battery -23%, range +44 mi** |

The car lost 23% battery but GAINED 44 miles of range. This is thermodynamically impossible and proves the BMS readings are fabricated by software, not derived from actual battery state.

---

## PERIOD 2: April 17-19 — Car at home in Spokane, stranded owner

### April 17 — The smoking gun day
| Time | Battery | Range | mi/% | Event |
|------|---------|-------|------|-------|
| 10:47 | 92% | 207 mi | 2.25 | Charging Complete — NORMAL reading |
| **16:06** | **80%** | **30 mi** | **0.38** | **False "cold battery" warning. 55°F outside, 77°F inside** |
| 17:07 | — | 30 mi | — | Home screen widget confirms 30 mi |
| 18:25 | — | 30 mi | — | Still 30 mi, 2 hours later |
| **22:06** | **87%** | **168 mi** | **1.93** | **NO CHARGING. Battery UP 7%, range UP 460%** |
| 22:12 | 86% | 171 mi | 1.99 | Battery dropping, range rising |

### April 18 — Inverse correlation continues, then another collapse
| Time | Battery | Range | mi/% | Event |
|------|---------|-------|------|-------|
| 00:02 | 82% | 178 mi | 2.17 | Battery down, range up — impossible |
| 00:03 | 81% | 180 mi | 2.22 | Continues |
| 06:50 | 79% | 182 mi | 2.30 | Overnight — bat -2%, range +2 mi |
| 09:47 | 79% | 181 mi | 2.29 | Stable for hours |
| 12:59 | 79% | 181 mi | 2.29 | Still stable |
| **13:13** | **79%** | **140 mi** | **1.77** | **Dropped 41 mi in 14 minutes while parked** |
| 16:46 | 90% | 152 mi | 1.69 | After charging |
| **19:12** | **96%** | **147 mi** | **1.53** | **96% showing only 147 mi (expected 216)** |
| **23:50** | **94%** | **51 mi** | **0.54** | **"Cold battery" again. 94% = 51 mi. 74% suppressed** |

### April 19 — Continues
| Time | Battery | Range | mi/% | Event |
|------|---------|-------|------|-------|
| 10:25 | 78% | 165 mi | 2.12 | Cold cleared, near normal |
| 15:02 | 88% | 148 mi | 1.68 | Dropping again |
| 17:35 | 88% | 144 mi | 1.64 | Lost 4 mi in 2.5 hrs parked |
| **19:32** | **90%** | **132 mi** | **1.47** | **Charging Complete, only 132 mi** |
| **19:46** | **91%** | **102 mi** | **1.12** | **BMS_u018_SOC_Imbalance_Limiting ACTIVE** |

---

## SUMMARY OF FINDINGS

### Miles-per-percent ratio (should be consistent ~2.25 mi/% based on car's own normal readings)
| Ratio | Battery | Range | Date/Time |
|-------|---------|-------|-----------|
| **0.30** | 100% | 30 mi | Apr 5, 3:30 AM |
| **0.34** | 100% | 34 mi | Apr 7, 6:29 AM |
| **0.38** | 80% | 30 mi | Apr 17, 4:06 PM |
| **0.54** | 94% | 51 mi | Apr 18, 11:50 PM |
| 0.63 | 100% | 63 mi | Apr 8, 2:56 AM |
| 1.12 | 91% | 102 mi | Apr 19, 7:46 PM |
| 1.47 | 90% | 132 mi | Apr 19, 7:32 PM |
| 2.12 | 78% | 165 mi | Apr 19, 10:25 AM |
| 2.25 | 92% | 207 mi | Apr 17, 10:47 AM |
| **2.29** | **77%** | **176 mi** | **Apr 8, 8:39 PM** |
| **2.30** | **79%** | **182 mi** | **Apr 18, 6:50 AM** |

**Range: 0.30 to 2.30 mi/% — a 7.7X variance.** A functioning BMS produces consistent ratios (~2.25 mi/% for this car when working correctly).

### Physically impossible events documented
1. Battery percentage INCREASED without charging (Apr 3, Apr 17)
2. Range INCREASED without charging (Apr 5, Apr 7, Apr 8, Apr 17)
3. Battery dropping while range increasing — multiple consecutive readings (Apr 8, Apr 17-18)
4. 100% battery showing 30 miles range (Apr 5)
5. 96% battery showing 147 miles (Apr 18) — should show ~198
6. Range dropping 42 miles in 20 minutes while parked and plugged in (Apr 5)
7. Range dropping 41 miles in 14 minutes while parked (Apr 18)
8. False "cold battery" warnings at 55°F ambient and 77°F interior (Apr 17, Apr 18)

### Tesla's own alert confirms the fault
**BMS_u018_SOC_Imbalance_Limiting** — "Maximum battery charge level reduced / OK to drive - Schedule service"

This alert, generated by Tesla's own vehicle software, confirms that the Battery Management System is malfunctioning. Despite this, Tesla has refused to roll back firmware 2025.38.12 or repair the BMS software.

### Root cause
Firmware update **2025.38.12** changed the BMS algorithm. The battery pack is physically healthy (proven by trickle charger tests and the fact that range periodically returns to normal values). The defect is entirely in the BMS software introduced by this firmware version.

---

*Data sources: Tesla Fleet API live pulls, local dashboard monitoring (60-second intervals), iPhone Tesla App screenshots with iOS timestamps, GitHub Actions automated logging.*

*All evidence preserved in git version control at github.com/josh5611/josh5611.github.io with cryptographic commit hashes for chain of custody.*
