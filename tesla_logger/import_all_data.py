#!/usr/bin/env python3
"""
import_all_data.py - Parse ALL Tesla data sources into daily JSON files.

Sources:
  1. TESLA_COMPLETE_CHARGE_LOG_March24-26_2026.md (API log)
  2. tesla_dashboard.log (broadcast lines)
  3. tesla_history.json (JSON arrays)
  4. Various ODB log files
  5. Tesla App screenshots (filename metadata)
  6. Desktop screenshots (filename + mtime)
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ODB = "C:/ODB-AI-System"
EVIDENCE = "C:/Users/joshb/My Drive/Tesla_Evidence"
OUT_DIR = "C:/Users/joshb/josh5611.github.io/tesla_data/historical"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_float(v):
    """Convert to float, return None for None/'None'/empty."""
    if v is None:
        return None
    s = str(v).strip()
    if s in ("None", "", "NaN", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def safe_int(v):
    f = safe_float(v)
    return int(f) if f is not None else None


def make_entry(ts, source, **kwargs):
    """Create a normalised data entry dict."""
    entry = {
        "timestamp": ts.isoformat(),
        "source": source,
        "estimated": False,
        "battery": {
            "level": kwargs.get("level"),
            "usable": kwargs.get("usable"),
            "range_miles": kwargs.get("range_miles"),
        },
        "charging": {
            "state": kwargs.get("state"),
            "charger_voltage": kwargs.get("voltage"),
            "charger_actual_current": kwargs.get("current"),
            "charge_energy_added": kwargs.get("energy_added"),
        },
    }
    return entry


def parse_ts(s):
    """Parse various timestamp formats into a datetime."""
    s = s.strip().rstrip("]").lstrip("[")
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            # strip tz for consistency (all data is local or UTC-ish)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# SOURCE 1: Complete charge log markdown
# ---------------------------------------------------------------------------

def parse_complete_charge_log(path):
    entries = []
    if not os.path.isfile(path):
        print(f"  [SKIP] {path} not found")
        return entries

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Each block starts with [timestamp]
    blocks = re.split(r'(?=\[\d{4}-\d{2}-\d{2} )', text)
    for block in blocks:
        # Get timestamp
        ts_m = re.match(r'\[(\d{4}-\d{2}-\d{2} [\d:.]+)\]', block)
        if not ts_m:
            continue
        ts = parse_ts(ts_m.group(1))
        if ts is None:
            continue

        # Skip ERROR lines
        if "ERROR" in block.split("\n")[0]:
            continue

        level = safe_int(re.search(r'level=(\d+)%', block).group(1)) if re.search(r'level=(\d+)%', block) else None
        usable = safe_int(re.search(r'usable=(\d+)%', block).group(1)) if re.search(r'usable=(\d+)%', block) else None
        state_m = re.search(r'state=(\w+)', block)
        state = state_m.group(1) if state_m else None

        volt_m = re.search(r'voltage=(\w+)V', block)
        voltage = safe_float(volt_m.group(1)) if volt_m else None

        cur_m = re.search(r'current=(\w+)A', block)
        current = safe_float(cur_m.group(1)) if cur_m else None

        added_m = re.search(r'added=([\d.]+)kWh', block)
        energy_added = safe_float(added_m.group(1)) if added_m else None

        range_m = re.search(r'rated=([\d.]+)mi', block)
        range_miles = safe_float(range_m.group(1)) if range_m else None

        if level is None and state is None:
            continue

        entries.append(make_entry(ts, "complete_charge_log",
                                  level=level, usable=usable, state=state,
                                  voltage=voltage, current=current,
                                  energy_added=energy_added, range_miles=range_miles))
    return entries


# ---------------------------------------------------------------------------
# SOURCE 2: tesla_dashboard.log
# ---------------------------------------------------------------------------

def parse_dashboard_log(path):
    entries = []
    if not os.path.isfile(path):
        print(f"  [SKIP] {path} not found")
        return entries

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.search(
                r'^(\d{4}-\d{2}-\d{2} [\d:,.]+)\s+\[INFO\]\s+Broadcast:\s+battery=(\S+)%\s+charging=(\S+)\s+voltage=(\S+)',
                line)
            if not m:
                continue
            ts_str = m.group(1).replace(",", ".")
            bat = m.group(2)
            chg = m.group(3)
            vol = m.group(4)

            # Skip None values
            if bat == "None" or vol == "None":
                continue

            ts = parse_ts(ts_str)
            if ts is None:
                continue

            entries.append(make_entry(ts, "dashboard_log",
                                      level=safe_int(bat), state=chg,
                                      voltage=safe_float(vol)))
    return entries


# ---------------------------------------------------------------------------
# SOURCE 3: tesla_history.json
# ---------------------------------------------------------------------------

def parse_history_json(path):
    entries = []
    if not os.path.isfile(path):
        print(f"  [SKIP] {path} not found")
        return entries

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build a lookup by timestamp for each field
    ts_map = {}  # ts_str -> dict of fields

    for field, key in [
        ("battery", "level"),
        ("voltage", "voltage"),
        ("current", "current"),
        ("energy", "energy_added"),
        ("range", "range_miles"),
        ("usable", "usable"),
    ]:
        arr = data.get(field, [])
        for item in arr:
            ts_str = item.get("ts", "")
            val = item.get("value")
            if ts_str not in ts_map:
                ts_map[ts_str] = {}
            ts_map[ts_str][key] = val

    for ts_str, fields in ts_map.items():
        ts = parse_ts(ts_str)
        if ts is None:
            continue
        # Skip if no battery level
        if fields.get("level") is None:
            continue
        entries.append(make_entry(ts, "history_json",
                                  level=safe_int(fields.get("level")),
                                  usable=safe_int(fields.get("usable")),
                                  voltage=safe_float(fields.get("voltage")),
                                  current=safe_float(fields.get("current")),
                                  energy_added=safe_float(fields.get("energy_added")),
                                  range_miles=safe_float(fields.get("range_miles"))))
    return entries


# ---------------------------------------------------------------------------
# SOURCE 4: Various ODB log files
# ---------------------------------------------------------------------------

def parse_charge_log_march25b(path):
    """Format: [timestamp] level=X% usable=X% state=X V=XV A=XA kW=XkW added=XkWh range=Xmi"""
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\[(\d{4}-\d{2}-\d{2} [\d:]+)\]', line)
            if not m:
                continue
            ts = parse_ts(m.group(1))
            if ts is None:
                continue
            level = safe_int(re.search(r'level=(\d+)%', line).group(1)) if re.search(r'level=(\d+)%', line) else None
            usable = safe_int(re.search(r'usable=(\d+)%', line).group(1)) if re.search(r'usable=(\d+)%', line) else None
            state_m = re.search(r'state=(\w+)', line)
            state = state_m.group(1) if state_m else None
            volt = safe_float(re.search(r'V=(\d+)V', line).group(1)) if re.search(r'V=(\d+)V', line) else None
            cur = safe_float(re.search(r'A=(\d+)A', line).group(1)) if re.search(r'A=(\d+)A', line) else None
            added = safe_float(re.search(r'added=([\d.]+)kWh', line).group(1)) if re.search(r'added=([\d.]+)kWh', line) else None
            range_m = safe_float(re.search(r'range=([\d.]+)mi', line).group(1)) if re.search(r'range=([\d.]+)mi', line) else None
            if level is not None:
                entries.append(make_entry(ts, os.path.basename(path),
                                          level=level, usable=usable, state=state,
                                          voltage=volt, current=cur,
                                          energy_added=added, range_miles=range_m))
    return entries


def parse_drive_log(path):
    """Format: [timestamp] SOC=X% range=Xmi state=X V=XV speed=X power=X shift=X"""
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\[(\d{4}-\d{2}-\d{2} [\d:]+)\]', line)
            if not m:
                continue
            ts = parse_ts(m.group(1))
            if ts is None:
                continue
            soc = safe_int(re.search(r'SOC=(\d+)%', line).group(1)) if re.search(r'SOC=(\d+)%', line) else None
            range_m = safe_float(re.search(r'range=([\d.]+)mi', line).group(1)) if re.search(r'range=([\d.]+)mi', line) else None
            state_m = re.search(r'state=(\w+)', line)
            state = state_m.group(1) if state_m else None
            volt = safe_float(re.search(r'V=(\d+)V', line).group(1)) if re.search(r'V=(\d+)V', line) else None
            if soc is not None:
                entries.append(make_entry(ts, os.path.basename(path),
                                          level=soc, state=state, voltage=volt,
                                          range_miles=range_m))
    return entries


def parse_overnight_monitor(path):
    """Format: [timestamp] State | XX% | XX.XXmi | XV | XkW"""
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\[(\d{4}-\d{2}-\d{2} [\d:]+)\]\s+(\w+)\s*\|\s*(\d+)%\s*\|\s*([\d.]+)mi\s*\|\s*(\w+)V\s*\|\s*(\w+)kW', line)
            if not m:
                continue
            ts = parse_ts(m.group(1))
            if ts is None:
                continue
            state = m.group(2)
            level = safe_int(m.group(3))
            range_miles = safe_float(m.group(4))
            voltage = safe_float(m.group(5))
            entries.append(make_entry(ts, os.path.basename(path),
                                      level=level, state=state,
                                      voltage=voltage, range_miles=range_miles))
    return entries


def parse_fleet_monitor(path):
    """Format: [timestamp] level=X% usable=X% state=X V=XV A=XA kW=XkW range=Xmi"""
    return parse_charge_log_march25b(path)  # Same format


def parse_monitor_march26b(path):
    """Format: [timestamp] level=X% usable=X% state=X V=XV A=XA range=Xmi port=X"""
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\[(\d{4}-\d{2}-\d{2} [\d:]+)\]', line)
            if not m:
                continue
            if "ALERTS" in line or "===" in line:
                continue
            ts = parse_ts(m.group(1))
            if ts is None:
                continue
            level = safe_int(re.search(r'level=(\d+)%', line).group(1)) if re.search(r'level=(\d+)%', line) else None
            usable = safe_int(re.search(r'usable=(\d+)%', line).group(1)) if re.search(r'usable=(\d+)%', line) else None
            state_m = re.search(r'state=(\w+)', line)
            state = state_m.group(1) if state_m else None
            volt = safe_float(re.search(r'V=(\d+)V', line).group(1)) if re.search(r'V=(\d+)V', line) else None
            cur = safe_float(re.search(r'A=(\d+)A', line).group(1)) if re.search(r'A=(\d+)A', line) else None
            range_m = safe_float(re.search(r'range=([\d.]+)mi', line).group(1)) if re.search(r'range=([\d.]+)mi', line) else None
            if level is not None:
                entries.append(make_entry(ts, os.path.basename(path),
                                          level=level, usable=usable, state=state,
                                          voltage=volt, current=cur,
                                          range_miles=range_m))
    return entries


def parse_full_monitor_march25c(path):
    """Multi-line blocks starting with [timestamp]\n  CHARGE: ..."""
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    blocks = re.split(r'(?=\[\d{4}-\d{2}-\d{2} )', text)
    for block in blocks:
        ts_m = re.match(r'\[(\d{4}-\d{2}-\d{2} [\d:.]+)\]', block)
        if not ts_m:
            continue
        ts = parse_ts(ts_m.group(1))
        if ts is None:
            continue

        level = safe_int(re.search(r'level=(\d+)%', block).group(1)) if re.search(r'level=(\d+)%', block) else None
        usable = safe_int(re.search(r'usable=(\d+)%', block).group(1)) if re.search(r'usable=(\d+)%', block) else None
        state_m = re.search(r'state=(\w+)', block)
        state = state_m.group(1) if state_m else None
        volt_m = re.search(r'voltage=(\w+)V', block)
        voltage = safe_float(volt_m.group(1)) if volt_m else None
        cur_m = re.search(r'current=(\w+)A', block)
        current = safe_float(cur_m.group(1)) if cur_m else None
        added_m = re.search(r'added=([\d.]+)kWh', block)
        energy_added = safe_float(added_m.group(1)) if added_m else None
        range_m = re.search(r'rated=([\d.]+)mi', block)
        range_miles = safe_float(range_m.group(1)) if range_m else None

        if level is not None:
            entries.append(make_entry(ts, os.path.basename(path),
                                      level=level, usable=usable, state=state,
                                      voltage=voltage, current=current,
                                      energy_added=energy_added, range_miles=range_miles))
    return entries


def parse_charge_monitor(path):
    """CHANGED lines: [timestamp] CHANGED: {"key": "old -> new"}"""
    # This file only has change deltas, not absolute values - skip
    return []


def parse_full_overnight_test(path):
    """Same multi-line block format as full_monitor_march25c."""
    return parse_full_monitor_march25c(path)


# ---------------------------------------------------------------------------
# SOURCE 5: Tesla App screenshots
# ---------------------------------------------------------------------------

def parse_tesla_app_screenshots(directory):
    entries = []
    if not os.path.isdir(directory):
        print(f"  [SKIP] {directory} not found")
        return entries

    for fname in os.listdir(directory):
        if not fname.startswith("Tesla_App_"):
            continue
        fpath = os.path.join(directory, fname)
        if not os.path.isfile(fpath):
            continue

        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))

        level = None
        range_miles = None
        voltage = None
        current = None
        state = None

        # Battery percentage: Tesla_App_83pct_ or Tesla_App_94pct_ or _Charging_94pct_
        pct_m = re.search(r'(\d+)pct', fname)
        if pct_m:
            level = int(pct_m.group(1))

        # Range: Tesla_App_200mi_ or _211mi_
        mi_m = re.search(r'(\d+)mi', fname)
        if mi_m:
            range_miles = float(mi_m.group(1))

        # Voltage: _243V_ or _242V_
        v_m = re.search(r'(\d+)V', fname)
        if v_m:
            voltage = float(v_m.group(1))

        # Current: _14of40A_ or _12of40A_
        a_m = re.search(r'(\d+)of(\d+)A', fname)
        if a_m:
            current = float(a_m.group(1))

        # State
        if "Charging_Complete" in fname or "Charging Complete" in fname:
            state = "Complete"
        elif "Charging" in fname:
            state = "Charging"

        if level is not None or range_miles is not None:
            entries.append(make_entry(mtime, f"screenshot:{fname}",
                                      level=level, state=state,
                                      voltage=voltage, current=current,
                                      range_miles=range_miles))
    return entries


# ---------------------------------------------------------------------------
# SOURCE 6: Desktop screenshots
# ---------------------------------------------------------------------------

def parse_desktop_screenshots(directory):
    entries = []
    if not os.path.isdir(directory):
        print(f"  [SKIP] {directory} not found")
        return entries

    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if not os.path.isfile(fpath):
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
        # These are just reference points - no parseable battery data in filenames
        entries.append(make_entry(mtime, f"desktop_screenshot:{fname}"))
    return entries


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def dedup_entries(entries, window_sec=5):
    """Remove duplicates within a time window. Keep highest-info entry."""
    if not entries:
        return entries

    entries.sort(key=lambda e: e["timestamp"])
    result = [entries[0]]

    for e in entries[1:]:
        prev = result[-1]
        t1 = datetime.fromisoformat(prev["timestamp"])
        t2 = datetime.fromisoformat(e["timestamp"])
        diff = abs((t2 - t1).total_seconds())

        if diff < window_sec:
            # Keep the one with more data
            def score(x):
                s = 0
                for v in x["battery"].values():
                    if v is not None:
                        s += 1
                for v in x["charging"].values():
                    if v is not None:
                        s += 1
                return s
            if score(e) > score(prev):
                result[-1] = e
        else:
            result.append(e)

    return result


# ---------------------------------------------------------------------------
# Gap estimation
# ---------------------------------------------------------------------------

def estimate_gaps(entries, gap_threshold_min=30, interval_min=5, max_per_gap=200):
    """Fill gaps > threshold with linear-interpolated battery level entries."""
    if len(entries) < 2:
        return entries, []

    gap_report = []
    filled = []

    for i in range(len(entries) - 1):
        filled.append(entries[i])

        t1 = datetime.fromisoformat(entries[i]["timestamp"])
        t2 = datetime.fromisoformat(entries[i + 1]["timestamp"])
        gap_sec = (t2 - t1).total_seconds()
        gap_min = gap_sec / 60.0

        if gap_min > gap_threshold_min:
            bat1 = entries[i]["battery"]["level"]
            bat2 = entries[i + 1]["battery"]["level"]

            gap_info = {
                "start": entries[i]["timestamp"],
                "end": entries[i + 1]["timestamp"],
                "gap_minutes": round(gap_min, 1),
                "battery_start": bat1,
                "battery_end": bat2,
                "estimated_count": 0,
            }

            if bat1 is not None and bat2 is not None:
                n_intervals = int(gap_min / interval_min)
                n_intervals = min(n_intervals, max_per_gap)
                step = timedelta(minutes=interval_min)

                for j in range(1, n_intervals + 1):
                    frac = j / (n_intervals + 1)
                    est_bat = round(bat1 + (bat2 - bat1) * frac, 1)
                    est_ts = t1 + step * j

                    if est_ts >= t2:
                        break

                    est_entry = make_entry(est_ts, "estimated",
                                           level=est_bat)
                    est_entry["estimated"] = True
                    est_entry["gap"] = {
                        "start": entries[i]["timestamp"],
                        "end": entries[i + 1]["timestamp"],
                    }
                    filled.append(est_entry)
                    gap_info["estimated_count"] += 1

            gap_report.append(gap_info)

    filled.append(entries[-1])
    return filled, gap_report


# ---------------------------------------------------------------------------
# Save daily files
# ---------------------------------------------------------------------------

def save_daily_files(entries, out_dir):
    by_date = defaultdict(list)
    for e in entries:
        dt = datetime.fromisoformat(e["timestamp"])
        day = dt.strftime("%Y-%m-%d")
        by_date[day].append(e)

    summaries = {}
    for day in sorted(by_date.keys()):
        day_entries = by_date[day]
        actual = [e for e in day_entries if not e["estimated"]]
        estimated = [e for e in day_entries if e["estimated"]]

        bat_levels = [e["battery"]["level"] for e in actual if e["battery"]["level"] is not None]

        summary = {
            "actual": len(actual),
            "estimated": len(estimated),
            "total": len(day_entries),
            "battery_min": min(bat_levels) if bat_levels else None,
            "battery_max": max(bat_levels) if bat_levels else None,
            "battery_start": bat_levels[0] if bat_levels else None,
            "battery_end": bat_levels[-1] if bat_levels else None,
        }

        day_data = {
            "date": day,
            "summary": summary,
            "entries": day_entries,
        }

        fpath = os.path.join(out_dir, f"{day}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(day_data, f, indent=2, default=str)

        summaries[day] = summary

    return summaries


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    all_entries = []

    # SOURCE 1
    print("Parsing SOURCE 1: Complete charge log...")
    src1 = parse_complete_charge_log(
        os.path.join(EVIDENCE, "04_API_Logs", "TESLA_COMPLETE_CHARGE_LOG_March24-26_2026.md"))
    print(f"  -> {len(src1)} entries")
    all_entries.extend(src1)

    # SOURCE 2
    print("Parsing SOURCE 2: Dashboard log...")
    src2 = parse_dashboard_log(os.path.join(ODB, "tesla_dashboard.log"))
    print(f"  -> {len(src2)} entries")
    all_entries.extend(src2)

    # SOURCE 3
    print("Parsing SOURCE 3: History JSON...")
    src3 = parse_history_json(os.path.join(ODB, "tesla_history.json"))
    print(f"  -> {len(src3)} entries")
    all_entries.extend(src3)

    # SOURCE 4: Various log files
    print("Parsing SOURCE 4: ODB log files...")
    log_parsers = [
        ("tesla_charge_log_march25b.log", parse_charge_log_march25b),
        ("tesla_charge_monitor.log", parse_charge_monitor),
        ("tesla_drive_log_march26.log", parse_drive_log),
        ("tesla_fleet_monitor_march26.log", parse_fleet_monitor),
        ("tesla_full_monitor_march25c.log", parse_full_monitor_march25c),
        ("tesla_full_overnight_test.log", parse_full_overnight_test),
        ("tesla_monitor_march26b.log", parse_monitor_march26b),
        ("tesla_overnight_monitor.log", parse_overnight_monitor),
    ]
    for fname, parser in log_parsers:
        path = os.path.join(ODB, fname)
        result = parser(path)
        print(f"  {fname}: {len(result)} entries")
        all_entries.extend(result)

    # SOURCE 5
    print("Parsing SOURCE 5: Tesla App screenshots...")
    src5 = parse_tesla_app_screenshots(
        os.path.join(EVIDENCE, "02_Screenshots_Tesla_App"))
    print(f"  -> {len(src5)} entries")
    all_entries.extend(src5)

    # SOURCE 6
    print("Parsing SOURCE 6: Desktop screenshots...")
    src6 = parse_desktop_screenshots(
        os.path.join(EVIDENCE, "03_Screenshots_Desktop"))
    print(f"  -> {len(src6)} entries")
    all_entries.extend(src6)

    total_raw = len(all_entries)
    print(f"\nTotal raw entries: {total_raw}")

    # Sort + dedup
    print("Deduplicating (5-second window)...")
    all_entries = dedup_entries(all_entries)
    print(f"After dedup: {len(all_entries)} (removed {total_raw - len(all_entries)})")

    # Estimate gaps
    print("Estimating gaps (>30min, 5min intervals, max 200/gap)...")
    all_entries, gap_report = estimate_gaps(all_entries)
    est_count = sum(1 for e in all_entries if e["estimated"])
    print(f"Added {est_count} estimated entries")
    print(f"Gaps found: {len(gap_report)}")

    # Save daily files
    print(f"\nSaving daily JSON files to {OUT_DIR}...")
    summaries = save_daily_files(all_entries, OUT_DIR)

    # Save gap report
    gap_path = os.path.join(OUT_DIR, "gap_report.json")
    with open(gap_path, "w", encoding="utf-8") as f:
        json.dump({"total_gaps": len(gap_report), "gaps": gap_report}, f, indent=2)
    print(f"Gap report saved to {gap_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("DAILY COVERAGE SUMMARY")
    print("=" * 70)
    print(f"{'Date':<14} {'Actual':>8} {'Estimated':>10} {'Total':>8} {'Bat Min':>8} {'Bat Max':>8} {'Start':>6} {'End':>6}")
    print("-" * 70)
    for day in sorted(summaries.keys()):
        s = summaries[day]
        print(f"{day:<14} {s['actual']:>8} {s['estimated']:>10} {s['total']:>8} "
              f"{str(s['battery_min'] or '-'):>8} {str(s['battery_max'] or '-'):>8} "
              f"{str(s['battery_start'] or '-'):>6} {str(s['battery_end'] or '-'):>6}")
    print("-" * 70)

    total_actual = sum(s["actual"] for s in summaries.values())
    total_est = sum(s["estimated"] for s in summaries.values())
    print(f"{'TOTAL':<14} {total_actual:>8} {total_est:>10} {total_actual + total_est:>8}")
    print(f"\nDate range: {min(summaries.keys())} to {max(summaries.keys())}")
    print(f"Daily files: {len(summaries)}")
    print("Done.")


if __name__ == "__main__":
    main()
