"""
analyze.py
----------
DMAIC phases: MEASURE + ANALYZE

1. MEASURE: Computes OEE (Availability x Performance x Quality) per station per shift.
2. ANALYZE:
   a. Bottleneck detection using Theory of Constraints -> the station with the
      LOWEST effective throughput (units/hour actually achieved) constrains the
      whole line, regardless of which station "looks" busiest.
   b. Statistical Process Control (SPC) control charts (X-bar chart logic) on
      shift-level throughput to flag out-of-control shifts (beyond 3-sigma).
   c. Pareto analysis on downtime causes to find the vital few root causes.

Run: python analyze.py   (after simulate.py has produced data/production_log.csv)
Outputs: prints summary tables + saves outputs/*.png charts
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

IDEAL_CYCLE_TIME = {
    "Filling": 2.0, "Capping": 1.5, "Labeling": 1.8, "Packaging": 2.5
}
SHIFT_SECONDS = 8 * 3600


def load_data(path="data/production_log.csv"):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df


# ---------- MEASURE: OEE per station per shift ----------
def compute_oee(df):
    rows = []
    for (station, shift_date), grp in df.groupby(["station", "shift_date"]):
        total_time = grp["duration_sec"].sum()
        downtime = grp.loc[grp["event_type"] == "downtime", "duration_sec"].sum()
        run_time = total_time - downtime

        units_produced = grp["units_produced"].sum()
        units_defective = grp["units_defective"].sum()
        good_units = units_produced - units_defective

        availability = run_time / total_time if total_time > 0 else 0
        ideal_ct = IDEAL_CYCLE_TIME[station]
        # Performance = (ideal cycle time x units produced) / run time
        performance = (ideal_ct * units_produced) / run_time if run_time > 0 else 0
        performance = min(performance, 1.0)
        quality = good_units / units_produced if units_produced > 0 else 0

        oee = availability * performance * quality
        throughput_per_hr = units_produced / (total_time / 3600) if total_time > 0 else 0

        rows.append({
            "station": station, "shift_date": shift_date,
            "availability": round(availability, 4),
            "performance": round(performance, 4),
            "quality": round(quality, 4),
            "oee": round(oee, 4),
            "units_produced": units_produced,
            "units_defective": units_defective,
            "downtime_sec": downtime,
            "throughput_per_hr": round(throughput_per_hr, 1),
        })
    return pd.DataFrame(rows)


# ---------- ANALYZE (a): Bottleneck detection ----------
def detect_bottleneck(oee_df):
    """
    Theory of Constraints: the bottleneck is the station with the lowest
    AVERAGE effective throughput across shifts -- it caps what the whole
    line can produce, even if other stations show more total downtime.
    """
    avg_throughput = oee_df.groupby("station")["throughput_per_hr"].mean().sort_values()
    avg_oee = oee_df.groupby("station")["oee"].mean().sort_values()
    bottleneck_station = avg_throughput.index[0]
    return bottleneck_station, avg_throughput, avg_oee


# ---------- ANALYZE (b): SPC control chart on throughput ----------
def spc_control_chart(oee_df, station, save_path="outputs/spc_chart.png"):
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    station_data = oee_df[oee_df["station"] == station].sort_values("shift_date").reset_index(drop=True)
    x = station_data["throughput_per_hr"].values
    center_line = x.mean()
    std = x.std()
    ucl = center_line + 3 * std   # Upper Control Limit
    lcl = center_line - 3 * std   # Lower Control Limit

    out_of_control = station_data[(x > ucl) | (x < lcl)]

    plt.figure(figsize=(10, 5))
    plt.plot(range(len(x)), x, marker="o", markersize=4, linewidth=1, label="Throughput/hr")
    plt.axhline(center_line, color="green", linestyle="-", label="Center Line (mean)")
    plt.axhline(ucl, color="red", linestyle="--", label="UCL (+3σ)")
    plt.axhline(lcl, color="red", linestyle="--", label="LCL (-3σ)")
    if len(out_of_control) > 0:
        plt.scatter(out_of_control.index, out_of_control["throughput_per_hr"], color="red", zorder=5, s=60, label="Out of control")
    plt.title(f"SPC Chart: {station} Throughput per Shift")
    plt.xlabel("Shift #")
    plt.ylabel("Units/hour")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=120)
    plt.close()

    return {
        "center_line": round(center_line, 2),
        "ucl": round(ucl, 2),
        "lcl": round(lcl, 2),
        "out_of_control_shifts": len(out_of_control),
    }


# ---------- ANALYZE (c): Pareto analysis on downtime causes ----------
def pareto_analysis(df, station, save_path="outputs/pareto_chart.png"):
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    downtime_df = df[(df["station"] == station) & (df["event_type"] == "downtime")]
    cause_totals = downtime_df.groupby("cause")["duration_sec"].sum().sort_values(ascending=False)
    cause_pct = (cause_totals / cause_totals.sum() * 100)
    cumulative_pct = cause_pct.cumsum()

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(cause_totals.index, cause_totals.values / 60, color="steelblue")
    ax1.set_ylabel("Total downtime (minutes)")
    ax1.set_xticks(range(len(cause_totals)))
    ax1.set_xticklabels(cause_totals.index, rotation=25, ha="right")

    ax2 = ax1.twinx()
    ax2.plot(range(len(cause_totals)), cumulative_pct.values, color="darkorange", marker="o")
    ax2.axhline(80, color="red", linestyle="--", linewidth=1)
    ax2.set_ylabel("Cumulative %")
    ax2.set_ylim(0, 110)

    plt.title(f"Pareto Analysis: {station} Downtime Root Causes")
    plt.tight_layout()
    plt.savefig(save_path, dpi=120)
    plt.close()

    # vital few = causes needed to reach 80% cumulative downtime
    vital_few = cumulative_pct[cumulative_pct <= 80].index.tolist()
    if not vital_few:
        vital_few = [cumulative_pct.index[0]]

    return cause_totals, cumulative_pct, vital_few


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    df = load_data()
    oee_df = compute_oee(df)
    oee_df.to_csv("data/oee_by_station_shift.csv", index=False)

    bottleneck, avg_throughput, avg_oee = detect_bottleneck(oee_df)

    print("=" * 60)
    print("MEASURE: Average Throughput per Station (units/hr)")
    print("=" * 60)
    print(avg_throughput.round(1))
    print("\nAverage OEE per Station")
    print(avg_oee.round(3))

    print("\n" + "=" * 60)
    print(f"ANALYZE: BOTTLENECK STATION = {bottleneck}")
    print("=" * 60)

    spc_result = spc_control_chart(oee_df, bottleneck)
    print(f"\nSPC Control Chart for {bottleneck}:")
    print(spc_result)

    cause_totals, cumulative_pct, vital_few = pareto_analysis(df, bottleneck)
    print(f"\nPareto Root Causes for {bottleneck} downtime:")
    print(cause_totals)
    print(f"\nVital few (drive ~80% of downtime): {vital_few}")

    total_downtime_pct = (cause_totals.loc[vital_few].sum() / cause_totals.sum()) * 100
    print(f"These {len(vital_few)} causes account for {total_downtime_pct:.1f}% of {bottleneck} downtime.")
