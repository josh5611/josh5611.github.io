#!/usr/bin/env python3
"""
Backfill evidence JSONL logs from ALL local Tesla data sources.
Creates one JSON line per data point, organized by month.
Sources: dashboard.log, tesla_history.json, fleet monitor logs,
         raw API snapshots, imported historical files.

Output: tesla_data/evidence/YYYY-MM.jsonl (append-only evidence files)
"""
import json
import os
import re
from datetime import datetime, timezone
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tesla_data")
EVIDENCE_DIR = os.path.join(DATA_DIR, "evidence")
ODB = "C:/ODB-AI-System"
VIN = "5YJSA1H25EFP67580"

os.makedirs(EVIDENCE_DIR, exist_ok=True)

# Collect all records keyed by timestamp to dedup
all_records = []


def add_record(ts_str, source, data):
    """Add a record with timestamp, source label, and full data."""
    all_records.append({
        "ts": ts_str,
        "source": source,
        "vin": VIN,
        "data": data,
    })


# === SOURCE 1: dashboard.log ===
def parse_dashboard_log():
    path = os.path.join(ODB, "tesla_dashboard.log")
    if not os.path.exists(path):
        print(f"  [SKIP] {path} not found")
        return 0
    count = 0
    with open(path, "r") as f:
        for line in f:
            if "Broadcast: battery=" not in line:
                continue
            ts_str = line[:23]
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
                ts = ts.replace(tzinfo=timezone.utc)
            except:
                continue

            match = re.search(
                r"battery=(\w+)%?\s+charging=(\w+)\s+voltage=(\w+)", line
            )
            if not match:
                continue

            add_record(ts.isoformat(), "dashboard_log", {
                "battery_level": None if match.group(1) == "None" else int(match.group(1)),
                "charging_state": match.group(2),
                "charger_voltage": None if match.group(3) == "None" else int(match.group(3)),
                "raw_line": line.strip(),
            })
            count += 1
    return count


# === SOURCE 2: tesla_history.json ===
def parse_history_json():
    path = os.path.join(ODB, "tesla_history.json")
    if not os.path.exists(path):
        print(f"  [SKIP] {path} not found")
        return 0
    with open(path) as f:
        data = json.load(f)

    by_ts = defaultdict(dict)
    for key in ["battery", "voltage", "current", "energy", "range", "usable"]:
        for entry in data.get(key, []):
            ts = entry["ts"]
            by_ts[ts][key] = entry["value"]

    count = 0
    for ts in sorted(by_ts.keys()):
        d = by_ts[ts]
        add_record(ts, "tesla_history_json", {
            "battery_level": d.get("battery"),
            "usable_battery_level": d.get("usable"),
            "battery_range": d.get("range"),
            "charger_voltage": d.get("voltage"),
            "charger_actual_current": d.get("current"),
            "charge_energy_added": d.get("energy"),
        })
        count += 1

    # Also grab alerts
    alert_count = 0
    for a in data.get("alerts", []):
        add_record(a["ts"], "tesla_history_json_alert", {
            "alert_name": a.get("name"),
            "alert_body": a.get("body", "")[:500],
        })
        alert_count += 1

    return count + alert_count


# === SOURCE 3: Fleet monitor log (march26) ===
def parse_fleet_monitor_log():
    count = 0
    for logfile in [
        os.path.join(ODB, "tesla_fleet_monitor_march26.log"),
        os.path.join(ODB, "tesla_charge_monitor.log"),
        os.path.join(ODB, "tesla_overnight_monitor.log"),
    ]:
        if not os.path.exists(logfile):
            continue
        with open(logfile) as f:
            for line in f:
                match = re.match(
                    r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] "
                    r"level=(\d+)% usable=(\d+)% state=(\w+) "
                    r"V=(\d+)V A=(\d+)A kW=(\d+)kW range=([\d.]+)mi",
                    line,
                )
                if match:
                    ts_str = match.group(1).replace(" ", "T") + "+00:00"
                    add_record(ts_str, f"fleet_monitor:{os.path.basename(logfile)}", {
                        "battery_level": int(match.group(2)),
                        "usable_battery_level": int(match.group(3)),
                        "charging_state": match.group(4),
                        "charger_voltage": int(match.group(5)),
                        "charger_actual_current": int(match.group(6)),
                        "charger_power": int(match.group(7)),
                        "battery_range": float(match.group(8)),
                        "raw_line": line.strip(),
                    })
                    count += 1
                elif "TOKEN EXPIRED" in line:
                    ts_match = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
                    if ts_match:
                        ts_str = ts_match.group(1).replace(" ", "T") + "+00:00"
                        add_record(ts_str, f"fleet_monitor:{os.path.basename(logfile)}", {
                            "event": "TOKEN_EXPIRED",
                            "raw_line": line.strip(),
                        })
                        count += 1
    return count


# === SOURCE 4: Raw API snapshots ===
def parse_raw_snapshots():
    count = 0
    for dirpath in [
        os.path.join(DATA_DIR, "raw"),
        os.path.join(DATA_DIR, "historical", "raw_snapshots"),
    ]:
        if not os.path.isdir(dirpath):
            continue
        for fname in os.listdir(dirpath):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
                ts = data.get("timestamp", fname.replace(".json", ""))
                add_record(ts, f"raw_api_snapshot:{fname}", data)
                count += 1
            except:
                continue
    return count


# === SOURCE 5: Local API data files ===
def parse_local_api_files():
    count = 0
    for fname in [
        "tesla_live_data.json",
        "tesla_full_dump.json",
        "tesla_full_dump_all.json",
        "tesla_full_evidence.json",
    ]:
        fpath = os.path.join(ODB, fname)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
            ts = data.get("timestamp", datetime.fromtimestamp(
                os.path.getmtime(fpath), tz=timezone.utc
            ).isoformat())
            add_record(ts, f"local_api_file:{fname}", data)
            count += 1
        except:
            continue
    return count


# === SOURCE 6: Alert snapshot files ===
def parse_alert_snapshots():
    count = 0
    for fname in os.listdir(ODB):
        if not fname.startswith("tesla_alerts_snapshot_"):
            continue
        fpath = os.path.join(ODB, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            # Extract timestamp from filename
            ts_match = re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", fname)
            if ts_match:
                ts_str = ts_match.group(1)[:10] + "T" + ts_match.group(1)[11:13] + ":" + ts_match.group(1)[13:15] + ":" + ts_match.group(1)[15:17] + "+00:00"
            else:
                ts_str = datetime.fromtimestamp(
                    os.path.getmtime(fpath), tz=timezone.utc
                ).isoformat()
            add_record(ts_str, f"alert_snapshot:{fname}", data)
            count += 1
        except:
            continue
    return count


# === SOURCE 7: Imported historical daily files ===
def parse_historical_daily():
    hist_dir = os.path.join(DATA_DIR, "historical")
    if not os.path.isdir(hist_dir):
        return 0
    count = 0
    for fname in sorted(os.listdir(hist_dir)):
        if not re.match(r"\d{4}-\d{2}-\d{2}\.json$", fname):
            continue
        fpath = os.path.join(hist_dir, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            for entry in data.get("entries", []):
                if entry.get("estimated"):
                    continue  # Skip estimated/interpolated entries
                ts = entry.get("timestamp", "")
                add_record(ts, f"historical_import:{fname}", entry)
                count += 1
            for alert in data.get("alerts", []):
                ts = alert.get("timestamp", "")
                add_record(ts, f"historical_alert:{fname}", alert)
                count += 1
        except:
            continue
    return count


# === MAIN ===
def main():
    print("=" * 60)
    print("TESLA EVIDENCE LOG BACKFILL")
    print("=" * 60)

    print("\n[1/7] Parsing dashboard.log...")
    c = parse_dashboard_log()
    print(f"  {c} records")

    print("\n[2/7] Parsing tesla_history.json...")
    c = parse_history_json()
    print(f"  {c} records")

    print("\n[3/7] Parsing fleet monitor logs...")
    c = parse_fleet_monitor_log()
    print(f"  {c} records")

    print("\n[4/7] Parsing raw API snapshots...")
    c = parse_raw_snapshots()
    print(f"  {c} records")

    print("\n[5/7] Parsing local API data files...")
    c = parse_local_api_files()
    print(f"  {c} records")

    print("\n[6/7] Parsing alert snapshots...")
    c = parse_alert_snapshots()
    print(f"  {c} records")

    print("\n[7/7] Parsing historical daily files...")
    c = parse_historical_daily()
    print(f"  {c} records")

    # Sort all records by timestamp
    print(f"\nTotal records collected: {len(all_records)}")
    all_records.sort(key=lambda x: x["ts"])

    # Deduplicate within 2-second windows from same source type
    deduped = []
    for rec in all_records:
        if not deduped:
            deduped.append(rec)
            continue
        prev = deduped[-1]
        # Simple dedup: same source base + within 2 seconds
        try:
            t1 = datetime.fromisoformat(prev["ts"])
            t2 = datetime.fromisoformat(rec["ts"])
            same_source = prev["source"].split(":")[0] == rec["source"].split(":")[0]
            if same_source and abs((t2 - t1).total_seconds()) < 2:
                continue
        except:
            pass
        deduped.append(rec)

    print(f"After dedup: {len(deduped)} records")

    # Write to monthly JSONL files
    by_month = defaultdict(list)
    for rec in deduped:
        try:
            month = rec["ts"][:7]  # YYYY-MM
            if len(month) == 7 and month[4] == "-":
                by_month[month].append(rec)
        except:
            by_month["unknown"].append(rec)

    total_written = 0
    for month in sorted(by_month.keys()):
        records = by_month[month]
        outfile = os.path.join(EVIDENCE_DIR, f"{month}.jsonl")
        with open(outfile, "w") as f:
            for rec in records:
                f.write(json.dumps(rec, default=str) + "\n")
        total_written += len(records)
        print(f"  {month}: {len(records)} records -> {outfile}")

    # Write index
    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": total_written,
        "months": {m: len(recs) for m, recs in sorted(by_month.items())},
        "sources": {},
        "date_range": {
            "first": deduped[0]["ts"][:19] if deduped else None,
            "last": deduped[-1]["ts"][:19] if deduped else None,
        },
    }
    # Count by source
    for rec in deduped:
        src = rec["source"].split(":")[0]
        index["sources"][src] = index["sources"].get(src, 0) + 1

    with open(os.path.join(EVIDENCE_DIR, "INDEX.json"), "w") as f:
        json.dump(index, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"EVIDENCE BACKFILL COMPLETE")
    print(f"  Total records: {total_written}")
    print(f"  Date range: {index['date_range']['first']} to {index['date_range']['last']}")
    print(f"  Monthly files: {len(by_month)}")
    print(f"  Sources: {json.dumps(index['sources'], indent=4)}")
    print(f"  Output: {EVIDENCE_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
