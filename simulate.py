"""
simulate.py
-----------
Generates synthetic time-series data for a 4-stage bottling/packaging line:
Filling -> Capping -> Labeling -> Packaging

Each station has its own cycle time, random micro-stoppages (downtime events),
and defect rate. This mimics real OEE (Overall Equipment Effectiveness) logging
data you'd pull from a brewery's MES (Manufacturing Execution System).

Run: python simulate.py
Output: data/production_log.csv
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)  # reproducible results

# ---- Station configuration ----
# ideal_cycle_time_sec: time to process ONE unit under perfect conditions
# downtime_prob: probability of a stoppage event per minute
# downtime_range_sec: (min, max) duration of a stoppage when it occurs
# defect_rate: probability a unit produced at this station is defective
STATIONS = {
    "Filling":   {"ideal_cycle_time_sec": 2.0, "downtime_prob": 0.015, "downtime_range_sec": (30, 180), "defect_rate": 0.008},
    "Capping":   {"ideal_cycle_time_sec": 1.5, "downtime_prob": 0.030, "downtime_range_sec": (20, 300), "defect_rate": 0.015},
    "Labeling":  {"ideal_cycle_time_sec": 1.8, "downtime_prob": 0.010, "downtime_range_sec": (15, 90),  "defect_rate": 0.006},
    "Packaging": {"ideal_cycle_time_sec": 2.5, "downtime_prob": 0.008, "downtime_range_sec": (60, 240), "defect_rate": 0.004},
}

DOWNTIME_CAUSES = {
    "Filling":   ["Nozzle clog", "Level sensor fault", "CIP cleaning cycle", "Bottle misfeed"],
    "Capping":   ["Cap jam", "Torque motor fault", "Cap hopper empty", "Alignment drift"],
    "Labeling":  ["Label roll change", "Sensor misread", "Adhesive fault"],
    "Packaging": ["Carton jam", "Case erector fault", "Palletizer stop"],
}

SHIFT_HOURS = 8
SECONDS_PER_SHIFT = SHIFT_HOURS * 3600
SHIFTS_TO_SIMULATE = 30  # ~1 month of single-shift data


def simulate_station_shift(station_name, cfg, shift_start_time):
    """Simulate one 8-hour shift for a single station, minute by minute."""
    records = []
    elapsed_sec = 0
    current_time = shift_start_time

    while elapsed_sec < SECONDS_PER_SHIFT:
        # Check for a downtime event this minute
        if np.random.random() < cfg["downtime_prob"]:
            duration = np.random.randint(*cfg["downtime_range_sec"])
            cause = np.random.choice(DOWNTIME_CAUSES[station_name])
            records.append({
                "timestamp": current_time,
                "station": station_name,
                "event_type": "downtime",
                "duration_sec": duration,
                "units_produced": 0,
                "units_defective": 0,
                "cause": cause,
            })
            elapsed_sec += duration
            current_time += timedelta(seconds=duration)
            continue

        # Otherwise, simulate 60 seconds of production
        # Real cycle time has slight random variation (machine isn't perfectly consistent)
        actual_cycle_time = cfg["ideal_cycle_time_sec"] * np.random.normal(1.0, 0.08)
        actual_cycle_time = max(actual_cycle_time, 0.5)
        units_this_minute = int(60 / actual_cycle_time)
        defects = np.random.binomial(units_this_minute, cfg["defect_rate"])

        records.append({
            "timestamp": current_time,
            "station": station_name,
            "event_type": "production",
            "duration_sec": 60,
            "units_produced": units_this_minute,
            "units_defective": defects,
            "cause": None,
        })
        elapsed_sec += 60
        current_time += timedelta(seconds=60)

    return records


def simulate_all(shifts=SHIFTS_TO_SIMULATE):
    all_records = []
    shift_start = datetime(2026, 1, 1, 6, 0, 0)  # 6 AM shift start

    for shift_idx in range(shifts):
        this_shift_start = shift_start + timedelta(days=shift_idx)
        for station_name, cfg in STATIONS.items():
            all_records.extend(simulate_station_shift(station_name, cfg, this_shift_start))

    df = pd.DataFrame(all_records)
    df["shift_date"] = df["timestamp"].dt.date
    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = simulate_all()
    df.to_csv("data/production_log.csv", index=False)
    print(f"Generated {len(df):,} log records across {SHIFTS_TO_SIMULATE} shifts.")
    print(f"Saved to data/production_log.csv")
    print("\nQuick preview:")
    print(df.head(10))
