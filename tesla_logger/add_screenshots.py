#!/usr/bin/env python3
"""Add screenshot data points and iCloud photo metadata to historical data."""
import json, os, re
from datetime import datetime, timezone
from collections import defaultdict

HIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tesla_data", "historical")

# Known data points extracted from reading actual screenshots
known_data = [
    {"ts": "2026-03-04T23:16:00-07:00", "src": "IMG_0874", "bat": 39, "rng": None, "chg": "Charging", "v": 239, "a": "21/40A", "note": "8h 45m remaining, charge limit 90%"},
    {"ts": "2026-03-05T00:12:00-07:00", "src": "IMG_0881", "bat": None, "rng": 111, "chg": "Charging", "v": 244, "a": "21/40A", "note": "7h 30m remaining, +36mi added"},
    {"ts": "2026-03-10T11:25:00-07:00", "src": "IMG_1209", "bat": 100, "rng": 201, "chg": "Complete", "v": None, "a": None, "note": "charge limit 100%"},
    {"ts": "2026-03-10T11:25:00-07:00", "src": "IMG_1210", "bat": 83, "rng": None, "chg": None, "v": None, "a": None, "note": "charge limit 100%"},
    {"ts": "2026-03-10T11:28:00-07:00", "src": "IMG_1211", "bat": 83, "rng": 200, "chg": None, "v": None, "a": None, "note": "climate 72F"},
    {"ts": "2026-03-11T11:44:00-07:00", "src": "IMG_1268", "bat": None, "rng": 211, "chg": "Charging", "v": 243, "a": "14/40A", "note": "5min remaining"},
    {"ts": "2026-03-11T12:07:00-07:00", "src": "IMG_1269", "bat": None, "rng": 216, "chg": "Charging", "v": 242, "a": "12/40A", "note": "calculating"},
    {"ts": "2026-03-11T12:07:00-07:00", "src": "IMG_1270", "bat": 94, "rng": None, "chg": "Charging", "v": 242, "a": "11/40A", "note": "calculating"},
    {"ts": "2026-03-11T13:27:00-07:00", "src": "IMG_1271", "bat": 100, "rng": None, "chg": "Complete", "v": None, "a": None, "note": "+1mi added"},
    {"ts": "2026-03-11T13:27:00-07:00", "src": "IMG_1272", "bat": None, "rng": 212, "chg": "Complete", "v": None, "a": None, "note": "+1mi added"},
    {"ts": "2026-03-11T14:31:00-07:00", "src": "IMG_1273", "bat": 94, "rng": None, "chg": "Complete", "v": None, "a": None, "note": "+9mi added"},
    {"ts": "2026-03-11T14:31:00-07:00", "src": "IMG_1274", "bat": None, "rng": 219, "chg": "Complete", "v": None, "a": None, "note": "+9mi added"},
    {"ts": "2026-03-12T14:22:00-07:00", "src": "IMG_1290", "bat": None, "rng": 222, "chg": "Complete", "v": None, "a": None, "note": "+4mi added"},
    {"ts": "2026-03-12T14:22:00-07:00", "src": "IMG_1291", "bat": 93, "rng": None, "chg": "Complete", "v": None, "a": None, "note": "+4mi added"},
]

def save_entry(date_str, entry):
    daily_file = os.path.join(HIST_DIR, f"{date_str}.json")
    if os.path.exists(daily_file):
        with open(daily_file) as f:
            daily = json.load(f)
    else:
        daily = {"date": date_str, "summary": {}, "entries": []}

    daily["entries"].append(entry)
    daily["entries"].sort(key=lambda x: x["timestamp"])
    actual = [e for e in daily["entries"] if e.get("battery", {}).get("level") is not None]
    daily["summary"]["actual_readings"] = len(actual)
    daily["summary"]["total_readings"] = len(daily["entries"])

    with open(daily_file, "w") as f:
        json.dump(daily, f, indent=2, default=str)

# 1. Add known screenshot data
print("Adding known screenshot data points...")
for d in known_data:
    ts = datetime.fromisoformat(d["ts"])
    date_str = ts.strftime("%Y-%m-%d")
    entry = {
        "timestamp": d["ts"],
        "source": f"screenshot:{d['src']}",
        "battery": {"level": d["bat"], "range_miles": d["rng"]},
        "charging": {"state": d["chg"], "charger_voltage": d["v"], "charger_actual_current": d["a"]},
        "note": d["note"],
    }
    save_entry(date_str, entry)
    print(f"  {date_str} {d['src']}: bat={d['bat']}% rng={d['rng']}mi chg={d['chg']}")

# 2. Scan iCloud photos for early March metadata
print("\nScanning iCloud photos for early March (Mar 1-9)...")
photos_dir = "C:/Users/joshb/iCloudPhotos/Photos"
early_count = 0

for f in sorted(os.listdir(photos_dir)):
    if not f.endswith(".PNG"):
        continue
    path = os.path.join(photos_dir, f)
    mtime = os.path.getmtime(path)
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)

    if dt.year != 2026 or dt.month != 3:
        continue

    num_match = re.search(r"IMG_(\d+)", f)
    if not num_match:
        continue
    num = int(num_match.group(1))

    # Photos in the 810-1100 range from March 1-9 are Tesla-era
    if dt.day <= 9 and 810 <= num <= 1150:
        date_str = dt.strftime("%Y-%m-%d")
        size = os.path.getsize(path)

        entry = {
            "timestamp": dt.isoformat(),
            "source": f"icloud_photo:{f}",
            "photo_number": num,
            "file_size_kb": round(size / 1024),
            "battery": {"level": None},
            "charging": {"state": "unknown"},
            "note": "Photo metadata - needs visual review for Tesla data extraction",
        }
        save_entry(date_str, entry)
        early_count += 1

print(f"  Added {early_count} photo metadata entries for Mar 1-9")

# 3. Also add iCloud Tesla app screenshots from Mar 13-31 that might have data
print("\nScanning later iCloud screenshots (Mar 13-31)...")
later_count = 0
# These are in the 1297+ range
for f in sorted(os.listdir(photos_dir)):
    if not f.endswith(".PNG"):
        continue
    path = os.path.join(photos_dir, f)
    mtime = os.path.getmtime(path)
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)

    if dt.year != 2026 or dt.month != 3 or dt.day < 13:
        continue

    num_match = re.search(r"IMG_(\d+)", f)
    if not num_match:
        continue
    num = int(num_match.group(1))
    size = os.path.getsize(path)

    # Tesla app screenshots are typically 300-400KB PNGs
    if 300 < size / 1024 < 500 and num >= 1297:
        date_str = dt.strftime("%Y-%m-%d")
        entry = {
            "timestamp": dt.isoformat(),
            "source": f"icloud_photo:{f}",
            "photo_number": num,
            "file_size_kb": round(size / 1024),
            "battery": {"level": None},
            "charging": {"state": "unknown"},
            "note": "Likely Tesla app screenshot (300-400KB PNG) - needs visual review",
        }
        save_entry(date_str, entry)
        later_count += 1

print(f"  Added {later_count} likely Tesla screenshots for Mar 13-31")

# 4. Summary
print("\n=== FINAL DATA COVERAGE ===")
for f in sorted(os.listdir(HIST_DIR)):
    if not f.endswith(".json") or f in ["gap_report.json", "vehicle_info.json", "all_alert_snapshots.json"]:
        continue
    path = os.path.join(HIST_DIR, f)
    with open(path) as fh:
        d = json.load(fh)
    actual = d.get("summary", {}).get("actual_readings", 0)
    total = d.get("summary", {}).get("total_readings", len(d.get("entries", [])))
    print(f"  {d.get('date', f)}: {total} entries ({actual} with battery data)")

print("\nDone!")
