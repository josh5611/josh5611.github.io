#!/usr/bin/env python3
"""
Tesla Fleet API Data Logger for GitHub Actions
Polls Tesla API, saves data to JSON files in the repo.
Runs on GitHub's servers 24/7 via cron schedule.
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timezone

# === CONFIG ===
FLEET_API = "https://fleet-api.prd.na.vn.cloud.tesla.com"
AUTH_URL = "https://auth.tesla.com/oauth2/v3/token"
CLIENT_ID = "b26f2545-b2fa-45b4-8d06-be4a298249fc"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tesla_data")

# === TOKEN MANAGEMENT ===
def refresh_access_token(refresh_token):
    """Get a fresh access token using the refresh token."""
    r = requests.post(AUTH_URL, json={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token
    }, timeout=30)

    if r.status_code != 200:
        print(f"[ERROR] Token refresh failed: {r.status_code} {r.text[:200]}")
        return None, None

    data = r.json()
    return data.get("access_token"), data.get("refresh_token", refresh_token)

def get_vehicles(access_token):
    """Get list of vehicles."""
    r = requests.get(f"{FLEET_API}/api/1/vehicles", headers={
        "Authorization": f"Bearer {access_token}"
    }, timeout=30)

    if r.status_code != 200:
        print(f"[ERROR] Get vehicles failed: {r.status_code}")
        return []

    return r.json().get("response", [])

def get_vehicle_data(access_token, vehicle_id):
    """Get full vehicle data."""
    endpoints = "charge_state,climate_state,drive_state,vehicle_state,vehicle_config"
    r = requests.get(
        f"{FLEET_API}/api/1/vehicles/{vehicle_id}/vehicle_data",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"endpoints": endpoints},
        timeout=30
    )

    if r.status_code == 408:
        return {"status": "asleep", "timestamp": datetime.now(timezone.utc).isoformat()}

    if r.status_code != 200:
        print(f"[ERROR] Vehicle data failed: {r.status_code} {r.text[:200]}")
        return None

    return r.json().get("response", {})

def get_recent_alerts(access_token, vehicle_id):
    """Get recent vehicle alerts (BMS, firmware, etc)."""
    try:
        r = requests.get(
            f"{FLEET_API}/api/1/vehicles/{vehicle_id}/recent_alerts",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30
        )
        if r.status_code == 200:
            return r.json().get("response", {})
    except:
        pass
    return {}

def save_data(vehicle_data, alerts):
    """Save data to daily JSON file. Always produces a unique entry via timestamp."""
    os.makedirs(DATA_DIR, exist_ok=True)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.isoformat()

    # Extract key metrics
    charge = vehicle_data.get("charge_state", {})
    drive = vehicle_data.get("drive_state", {})
    climate = vehicle_data.get("climate_state", {})
    vehicle = vehicle_data.get("vehicle_state", {})

    entry = {
        "timestamp": timestamp,
        "poll_id": now.strftime("%Y%m%d_%H%M%S"),
        "status": vehicle_data.get("status", vehicle_data.get("state", "unknown")),
        "battery": {
            "level": charge.get("battery_level"),
            "usable": charge.get("usable_battery_level"),
            "range_miles": charge.get("battery_range"),
            "est_range": charge.get("est_battery_range"),
            "ideal_range": charge.get("ideal_battery_range"),
        },
        "charging": {
            "state": charge.get("charging_state"),
            "charge_rate": charge.get("charge_rate"),
            "charger_power": charge.get("charger_power"),
            "charger_voltage": charge.get("charger_voltage"),
            "charger_actual_current": charge.get("charger_actual_current"),
            "charge_energy_added": charge.get("charge_energy_added"),
            "charge_miles_added": charge.get("charge_miles_added_rated"),
            "time_to_full": charge.get("time_to_full_charge"),
            "charge_limit": charge.get("charge_limit_soc"),
        },
        "climate": {
            "inside_temp_c": climate.get("inside_temp"),
            "outside_temp_c": climate.get("outside_temp"),
            "is_climate_on": climate.get("is_climate_on"),
        },
        "drive": {
            "speed": drive.get("speed"),
            "power": drive.get("power"),
            "latitude": drive.get("latitude"),
            "longitude": drive.get("longitude"),
            "heading": drive.get("heading"),
        },
        "vehicle": {
            "odometer": vehicle.get("odometer"),
            "locked": vehicle.get("locked"),
            "firmware": vehicle.get("car_version"),
            "sentry_mode": vehicle.get("sentry_mode"),
        },
        "alerts": alerts if alerts else None,
    }

    # Daily file
    daily_file = os.path.join(DATA_DIR, f"{date_str}.json")

    # Load existing or create new
    if os.path.exists(daily_file):
        with open(daily_file, "r") as f:
            daily_data = json.load(f)
    else:
        daily_data = {"date": date_str, "entries": []}

    daily_data["entries"].append(entry)
    daily_data["last_updated"] = timestamp

    with open(daily_file, "w") as f:
        json.dump(daily_data, f, indent=2, default=str)

    # Also save latest snapshot
    latest_file = os.path.join(DATA_DIR, "latest.json")
    with open(latest_file, "w") as f:
        json.dump(entry, f, indent=2, default=str)

    print(f"[OK] Saved: battery={entry['battery']['level']}% "
          f"charging={entry['charging']['state']} "
          f"range={entry['battery']['range_miles']}mi "
          f"firmware={entry['vehicle']['firmware']}")

    return entry

def save_raw(vehicle_data, alerts):
    """Save complete raw API response for evidence."""
    os.makedirs(os.path.join(DATA_DIR, "raw"), exist_ok=True)
    now = datetime.now(timezone.utc)
    raw_file = os.path.join(DATA_DIR, "raw", f"{now.strftime('%Y-%m-%d_%H%M%S')}.json")

    with open(raw_file, "w") as f:
        json.dump({
            "timestamp": now.isoformat(),
            "vehicle_data": vehicle_data,
            "alerts": alerts
        }, f, indent=2, default=str)

def save_evidence_log(entry, vehicle_data, alerts):
    """Append one line per poll to a monthly JSONL evidence log. Never overwritten."""
    os.makedirs(os.path.join(DATA_DIR, "evidence"), exist_ok=True)
    now = datetime.now(timezone.utc)
    month_file = os.path.join(DATA_DIR, "evidence", f"{now.strftime('%Y-%m')}.jsonl")

    record = {
        "ts": now.isoformat(),
        "poll_id": entry.get("poll_id"),
        "status": entry.get("status"),
        "battery_level": entry.get("battery", {}).get("level"),
        "usable_level": entry.get("battery", {}).get("usable"),
        "range_mi": entry.get("battery", {}).get("range_miles"),
        "charging_state": entry.get("charging", {}).get("state"),
        "voltage": entry.get("charging", {}).get("charger_voltage"),
        "current": entry.get("charging", {}).get("charger_actual_current"),
        "power_kw": entry.get("charging", {}).get("charger_power"),
        "inside_temp_c": entry.get("climate", {}).get("inside_temp_c"),
        "outside_temp_c": entry.get("climate", {}).get("outside_temp_c"),
        "odometer": entry.get("vehicle", {}).get("odometer"),
        "firmware": entry.get("vehicle", {}).get("firmware"),
        "alerts": [a.get("name") for a in (alerts.get("recent_alerts") or [])] if alerts else [],
    }

    with open(month_file, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

def main():
    # Get tokens from environment (GitHub Secrets)
    refresh_token = os.environ.get("TESLA_REFRESH_TOKEN")
    if not refresh_token:
        print("[FATAL] TESLA_REFRESH_TOKEN not set")
        sys.exit(1)

    # Refresh access token
    print("[INFO] Refreshing access token...")
    access_token, new_refresh_token = refresh_access_token(refresh_token)
    if not access_token:
        print("[FATAL] Could not get access token")
        sys.exit(1)

    # If refresh token changed, update the secret
    if new_refresh_token and new_refresh_token != refresh_token:
        # Write new refresh token for GitHub Actions to update the secret
        with open(os.path.join(DATA_DIR, ".new_refresh_token"), "w") as f:
            f.write(new_refresh_token)
        print("[INFO] Refresh token rotated - needs secret update")

    # Get vehicles
    vehicles = get_vehicles(access_token)
    if not vehicles:
        print("[WARN] No vehicles found or API error")
        entry = save_data({"status": "no_vehicles", "state": "unknown"}, {})
        save_evidence_log(entry, {}, {})
        return

    vehicle = vehicles[0]
    vehicle_id = vehicle.get("id")
    vin = vehicle.get("vin", "unknown")
    state = vehicle.get("state", "unknown")

    print(f"[INFO] Vehicle: {vin} | State: {state}")

    if state == "asleep":
        entry = save_data({
            "status": "asleep",
            "state": "asleep",
            "charge_state": {},
            "drive_state": {},
            "climate_state": {},
            "vehicle_state": {}
        }, {})
        save_evidence_log(entry, {}, {})
        print("[INFO] Vehicle asleep — logged without waking")
        return

    # Get full data
    print("[INFO] Polling vehicle data...")
    vehicle_data = get_vehicle_data(access_token, vehicle_id)

    if not vehicle_data:
        entry = save_data({"status": "error", "state": "api_error"}, {})
        save_evidence_log(entry, {}, {})
        return

    # Get alerts
    alerts = get_recent_alerts(access_token, vehicle_id)

    # Save processed data
    entry = save_data(vehicle_data, alerts)

    # Save raw data for evidence
    save_raw(vehicle_data, alerts)

    # Append to permanent evidence log (one line per poll, never deleted)
    save_evidence_log(entry, vehicle_data, alerts)

    print("[DONE] Tesla data logged successfully")

if __name__ == "__main__":
    main()
