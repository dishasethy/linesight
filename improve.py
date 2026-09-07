"""
improve.py
----------
DMAIC phases: IMPROVE + CONTROL

IMPROVE: Re-runs the simulation for the bottleneck station with an improvement
applied (representing a Kaizen intervention: e.g., preventive maintenance on
the top root cause, reducing its downtime probability and duration).

CONTROL: Recomputes SPC control limits on the improved process and reports
before/after throughput yield + downtime reduction, so the intervention can be
monitored going forward.

Run: python improve.py   (after simulate.py and analyze.py have been run)
"""

import os
import numpy as np
import pandas as pd
from simulate import simulate_station_shift, STATIONS, DOWNTIME_CAUSES, SHIFTS_TO_SIMULATE
from analyze import compute_oee, spc_control_chart, load_data, detect_bottleneck
from datetime import datetime, timedelta

np.random.seed(7)


def apply_kaizen_improvement(station_name, improvement_factor=0.5):
    """
    Simulates a Kaizen-style intervention: e.g. a buffer/preventive-maintenance
    fix that cuts the downtime PROBABILITY of the bottleneck station roughly in
    half, and trims the average stoppage DURATION (faster recovery via SOP).
    """
    improved_cfg = dict(STATIONS[station_name])
    improved_cfg["downtime_prob"] = improved_cfg["downtime_prob"] * improvement_factor
    lo, hi = improved_cfg["downtime_range_sec"]
    improved_cfg["downtime_range_sec"] = (int(lo * 0.7), int(hi * 0.7))
    return improved_cfg


def simulate_improved(station_name, shifts=SHIFTS_TO_SIMULATE):
    improved_cfg = apply_kaizen_improvement(station_name)
    shift_start = datetime(2026, 1, 1, 6, 0, 0)
    records = []
    for shift_idx in range(shifts):
        this_shift_start = shift_start + timedelta(days=shift_idx)
        records.extend(simulate_station_shift(station_name, improved_cfg, this_shift_start))
    df = pd.DataFrame(records)
    df["shift_date"] = df["timestamp"].dt.date
    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # Load original data + find bottleneck (Control phase needs a known baseline)
    df = load_data()
    oee_before = compute_oee(df)
    bottleneck, avg_throughput_before, _ = detect_bottleneck(oee_before)

    print(f"Bottleneck identified in ANALYZE phase: {bottleneck}")
    print("Applying Kaizen intervention (reduced downtime probability + faster recovery)...\n")

    # Simulate the "after" state for just the bottleneck station
    improved_station_df = simulate_improved(bottleneck)
    improved_station_df["station"] = bottleneck  # ensure label consistency

    oee_after_station = compute_oee(improved_station_df)

    before_throughput = oee_before[oee_before["station"] == bottleneck]["throughput_per_hr"].mean()
    after_throughput = oee_after_station["throughput_per_hr"].mean()
    throughput_gain_pct = ((after_throughput - before_throughput) / before_throughput) * 100

    before_downtime = df[(df["station"] == bottleneck) & (df["event_type"] == "downtime")]["duration_sec"].sum()
    after_downtime = improved_station_df[improved_station_df["event_type"] == "downtime"]["duration_sec"].sum()
    downtime_reduction_pct = ((before_downtime - after_downtime) / before_downtime) * 100

    before_oee = oee_before[oee_before["station"] == bottleneck]["oee"].mean()
    after_oee = oee_after_station["oee"].mean()

    print("=" * 60)
    print("IMPROVE: Before vs After Kaizen Intervention")
    print("=" * 60)
    print(f"Throughput (units/hr):  {before_throughput:.1f}  ->  {after_throughput:.1f}   ({throughput_gain_pct:+.1f}%)")
    print(f"Total downtime (sec):   {before_downtime:,}  ->  {after_downtime:,}   ({downtime_reduction_pct:.1f}% reduction)")
    print(f"Average OEE:            {before_oee:.3f}  ->  {after_oee:.3f}")

    # CONTROL: new SPC limits on the improved process
    spc_after = spc_control_chart(oee_after_station, bottleneck, save_path="outputs/spc_chart_after_improvement.png")
    print("\n" + "=" * 60)
    print("CONTROL: New SPC Limits (Post-Improvement)")
    print("=" * 60)
    print(spc_after)
    print("\nThese become the new control limits to monitor in production --")
    print("any future shift falling outside them should trigger an SOP deviation review.")

    # Save results for the dashboard
    oee_after_station.to_csv("data/oee_after_improvement.csv", index=False)
    summary = pd.DataFrame([{
        "bottleneck_station": bottleneck,
        "throughput_before": round(before_throughput, 1),
        "throughput_after": round(after_throughput, 1),
        "throughput_gain_pct": round(throughput_gain_pct, 1),
        "downtime_before_sec": int(before_downtime),
        "downtime_after_sec": int(after_downtime),
        "downtime_reduction_pct": round(downtime_reduction_pct, 1),
        "oee_before": round(before_oee, 3),
        "oee_after": round(after_oee, 3),
    }])
    summary.to_csv("data/improvement_summary.csv", index=False)
    print("\nSaved: data/oee_after_improvement.csv, data/improvement_summary.csv")
