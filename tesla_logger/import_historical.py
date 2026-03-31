#!/usr/bin/env python3
"""
Import historical Tesla data from local logs into GitHub format.
Parses dashboard.log + tesla_history.json, estimates gaps.
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tesla_data")
HISTORY_DIR = os.path.join(DATA_DIR, "historical")

def parse_dashboard_log():
    """Parse the dashboard.log for broadcast entries."""
    log_path = "C:/ODB-AI-System/tesla_dashboard.log"
    entries = []

    with open(log_path, "r") as f:
        for line in f:
            if "Broadcast: battery=" not in line:
                continue

            ts_str = line[:23]
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
                ts = ts.replace(tzinfo=timezone.utc)
            except:
                continue

            match = re.search(r"battery=(\w+)%?\s+charging=(\w+)\s+voltage=(\w+)", line)
            if not match:
                continue

            battery = match.group(1)
            charging = match.group(2)
            voltage = match.group(3)

            if battery == "None":
                continue

            entries.append({
                "timestamp": ts.isoformat(),
                "source": "dashboard_log",
                "battery": {"level": int(battery)},
                "charging": {"state": charging, "charger_voltage": int(voltage) if voltage != "None" else None},
            })

    return entries

def parse_history_json():
    """Parse tesla_history.json for detailed time series."""
    path = "C:/ODB-AI-System/tesla_history.json"
    with open(path) as f:
        data = json.load(f)

    # Index by timestamp
    by_ts = defaultdict(dict)

    for key in ["battery", "voltage", "current", "energy", "range", "usable"]:
        for entry in data.get(key, []):
            ts = entry["ts"]
            by_ts[ts][key] = entry["value"]

    entries = []
    for ts in sorted(by_ts.keys()):
        d = by_ts[ts]
        entries.append({
            "timestamp": ts,
            "source": "history_json",
            "battery": {
                "level": d.get("battery"),
                "usable": d.get("usable"),
                "range_miles": d.get("range"),
            },
            "charging": {
                "charger_voltage": d.get("voltage"),
                "charger_actual_current": d.get("current"),
                "charge_energy_added": d.get("energy"),
            },
        })

    return entries

def parse_alerts():
    """Parse alert history."""
    path = "C:/ODB-AI-System/tesla_history.json"
    with open(path) as f:
        data = json.load(f)

    alerts = []
    for a in data.get("alerts", []):
        alerts.append({
            "timestamp": a["ts"],
            "name": a.get("name"),
            "body": a.get("body", "")[:200],
        })
    return alerts

def parse_full_data():
    """Parse the full vehicle data snapshot."""
    path = "C:/ODB-AI-System/tesla_fleet_full_data.json"
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def parse_live_data():
    """Parse the live data snapshot."""
    path = "C:/ODB-AI-System/tesla_live_data.json"
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def estimate_gaps(entries):
    """Estimate data for gaps between readings."""
    if len(entries) < 2:
        return []

    estimated = []
    for i in range(len(entries) - 1):
        ts1 = datetime.fromisoformat(entries[i]["timestamp"])
        ts2 = datetime.fromisoformat(entries[i + 1]["timestamp"])
        gap = (ts2 - ts1).total_seconds()

        # If gap is more than 30 minutes, create estimated entries
        if gap > 1800:
            bat1 = entries[i].get("battery", {}).get("level")
            bat2 = entries[i + 1].get("battery", {}).get("level")

            if bat1 is not None and bat2 is not None:
                # Linear interpolation
                num_estimates = int(gap / 300)  # One every 5 minutes
                num_estimates = min(num_estimates, 100)  # Cap at 100

                for j in range(1, num_estimates):
                    ratio = j / num_estimates
                    est_ts = ts1 + timedelta(seconds=gap * ratio)
                    est_bat = round(bat1 + (bat2 - bat1) * ratio)

                    estimated.append({
                        "timestamp": est_ts.isoformat(),
                        "source": "estimated",
                        "estimated": True,
                        "gap_start": entries[i]["timestamp"],
                        "gap_end": entries[i + 1]["timestamp"],
                        "gap_seconds": gap,
                        "battery": {"level": est_bat},
                        "charging": {"state": "estimated"},
                    })

    return estimated

def save_daily_files(all_entries, alerts):
    """Save entries into daily JSON files."""
    os.makedirs(HISTORY_DIR, exist_ok=True)

    by_date = defaultdict(list)
    for entry in all_entries:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            date_str = ts.strftime("%Y-%m-%d")
            by_date[date_str].append(entry)
        except:
            continue

    alerts_by_date = defaultdict(list)
    for alert in alerts:
        try:
            ts = datetime.fromisoformat(alert["timestamp"])
            date_str = ts.strftime("%Y-%m-%d")
            alerts_by_date[date_str].append(alert)
        except:
            continue

    total_entries = 0
    total_estimated = 0

    for date_str in sorted(by_date.keys()):
        entries = sorted(by_date[date_str], key=lambda x: x["timestamp"])
        day_alerts = alerts_by_date.get(date_str, [])

        actual = [e for e in entries if not e.get("estimated")]
        estimated = [e for e in entries if e.get("estimated")]

        daily = {
            "date": date_str,
            "summary": {
                "actual_readings": len(actual),
                "estimated_readings": len(estimated),
                "total_readings": len(entries),
                "alerts_count": len(day_alerts),
                "source": "historical_import",
                "imported_at": datetime.now(timezone.utc).isoformat(),
            },
            "entries": entries,
            "alerts": day_alerts,
        }

        # Calculate battery range for the day
        battery_levels = [e["battery"]["level"] for e in entries
                         if e.get("battery", {}).get("level") is not None]
        if battery_levels:
            daily["summary"]["battery_min"] = min(battery_levels)
            daily["summary"]["battery_max"] = max(battery_levels)
            daily["summary"]["battery_start"] = battery_levels[0]
            daily["summary"]["battery_end"] = battery_levels[-1]

        filepath = os.path.join(HISTORY_DIR, f"{date_str}.json")
        with open(filepath, "w") as f:
            json.dump(daily, f, indent=2, default=str)

        total_entries += len(entries)
        total_estimated += len(estimated)
        print(f"  {date_str}: {len(actual)} actual + {len(estimated)} estimated = {len(entries)} total | {len(day_alerts)} alerts")

    return total_entries, total_estimated

def save_vehicle_info():
    """Save vehicle info snapshot."""
    full_data = parse_full_data()
    live_data = parse_live_data()

    info = {
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "vin": full_data.get("vin") or live_data.get("vin"),
        "vehicle_id": full_data.get("vehicle_id") or live_data.get("vehicle_id"),
        "display_name": live_data.get("display_name"),
        "color": full_data.get("color"),
        "state": full_data.get("state"),
        "full_data_snapshot": full_data,
        "live_data_snapshot": live_data,
    }

    filepath = os.path.join(HISTORY_DIR, "vehicle_info.json")
    with open(filepath, "w") as f:
        json.dump(info, f, indent=2, default=str)
    print(f"  Vehicle info saved: VIN={info['vin']}")

def save_gap_report(entries, estimated):
    """Save a report of all data gaps."""
    gaps = []
    for i in range(len(entries) - 1):
        ts1 = datetime.fromisoformat(entries[i]["timestamp"])
        ts2 = datetime.fromisoformat(entries[i + 1]["timestamp"])
        gap = (ts2 - ts1).total_seconds()

        if gap > 1800:  # 30+ minutes
            gaps.append({
                "start": entries[i]["timestamp"],
                "end": entries[i + 1]["timestamp"],
                "gap_seconds": gap,
                "gap_hours": round(gap / 3600, 1),
                "battery_before": entries[i].get("battery", {}).get("level"),
                "battery_after": entries[i + 1].get("battery", {}).get("level"),
                "estimated_entries_filled": len([e for e in estimated
                    if entries[i]["timestamp"] <= e["timestamp"] <= entries[i + 1]["timestamp"]]),
            })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_gaps_over_30min": len(gaps),
        "total_gap_hours": round(sum(g["gap_hours"] for g in gaps), 1),
        "gaps": gaps,
    }

    filepath = os.path.join(HISTORY_DIR, "gap_report.json")
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"  Gap report: {len(gaps)} gaps totaling {report['total_gap_hours']} hours")
    for g in gaps:
        print(f"    {g['start'][:19]} -> {g['end'][:19]} ({g['gap_hours']}h) "
              f"bat: {g['battery_before']}% -> {g['battery_after']}% "
              f"({g['estimated_entries_filled']} estimated)")

def main():
    print("=" * 60)
    print("TESLA HISTORICAL DATA IMPORT")
    print("=" * 60)

    print("\n[1/6] Parsing dashboard.log...")
    log_entries = parse_dashboard_log()
    print(f"  Found {len(log_entries)} broadcast readings")

    print("\n[2/6] Parsing tesla_history.json...")
    history_entries = parse_history_json()
    print(f"  Found {len(history_entries)} history readings")

    print("\n[3/6] Parsing alerts...")
    alerts = parse_alerts()
    print(f"  Found {len(alerts)} alerts")

    # Merge and deduplicate (prefer history_json as it has more detail)
    print("\n[4/6] Merging and deduplicating...")
    all_entries = history_entries + log_entries
    # Sort by timestamp
    all_entries.sort(key=lambda x: x["timestamp"])
    # Deduplicate within 5-second windows
    deduped = []
    for entry in all_entries:
        if not deduped:
            deduped.append(entry)
            continue
        prev_ts = datetime.fromisoformat(deduped[-1]["timestamp"])
        curr_ts = datetime.fromisoformat(entry["timestamp"])
        if (curr_ts - prev_ts).total_seconds() > 5:
            deduped.append(entry)
        elif entry.get("source") == "history_json" and deduped[-1].get("source") != "history_json":
            deduped[-1] = entry  # Prefer history_json
    print(f"  {len(all_entries)} total -> {len(deduped)} after dedup")

    print("\n[5/6] Estimating gaps...")
    estimated = estimate_gaps(deduped)
    print(f"  Created {len(estimated)} estimated entries for gaps")

    # Merge estimated into main list
    combined = deduped + estimated
    combined.sort(key=lambda x: x["timestamp"])

    print("\n[6/6] Saving daily files...")
    total, total_est = save_daily_files(combined, alerts)

    print("\nSaving vehicle info...")
    save_vehicle_info()

    print("\nGenerating gap report...")
    save_gap_report(deduped, estimated)

    print(f"\n{'=' * 60}")
    print(f"IMPORT COMPLETE")
    print(f"  Total entries: {total} ({total - total_est} actual + {total_est} estimated)")
    print(f"  Alerts: {len(alerts)}")
    print(f"  Files saved to: {HISTORY_DIR}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
