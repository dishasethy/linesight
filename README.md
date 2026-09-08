# Line Sight — DMAIC-Based Bottleneck Detection & Process Optimization System

A simulated 4-stage bottling/packaging line (Filling → Capping → Labeling → Packaging)
analyzed end-to-end using the Six Sigma **DMAIC** framework: Measure, Analyze, Improve, Control.

## What this project does
- **Simulates** realistic OEE-style production data (cycle times, random downtime events, defect rates) for 30 shifts.
- **Measures** Availability, Performance, Quality, and OEE per station per shift.
- **Analyzes** which station is the true bottleneck using Theory of Constraints (lowest effective throughput — not just lowest OEE), builds an **SPC control chart** (X-bar, ±3σ) to flag abnormal shifts, and runs a **Pareto analysis** to find the vital-few root causes of downtime.
- **Improves** by simulating a Kaizen-style intervention (e.g., preventive maintenance cutting the top failure mode's frequency/duration) and quantifies before/after throughput, downtime, and OEE.
- **Controls** by recalculating SPC limits on the improved process — the ongoing monitoring baseline.
- **Visualizes** everything in a live Streamlit dashboard.

## Project structure
```
line_sight/
│
├── simulate.py                          # generates synthetic production log data
├── analyze.py                           # MEASURE + ANALYZE: OEE, bottleneck, SPC, Pareto
├── improve.py                           # IMPROVE + CONTROL: Kaizen simulation, before/after
├── dashboard.py                         # Streamlit dashboard
├── requirements.txt                     # numpy, pandas, matplotlib, streamlit
├── README.md                            # setup + interview-ready explanation
│
├── data/                                 # ← auto-created, holds generated CSVs
│   ├── production_log.csv                #   raw simulated event log (from simulate.py)
│   ├── oee_by_station_shift.csv          #   OEE per station per shift (from analyze.py)
│   ├── oee_after_improvement.csv         #   post-Kaizen OEE data (from improve.py)
│   └── improvement_summary.csv           #   before/after summary metrics (from improve.py)
│
├── outputs/                              # ← auto-created, holds generated charts
│   ├── spc_chart.png                     #   SPC control chart, bottleneck (before)
│   ├── spc_chart_after_improvement.png   #   SPC control chart (after fix)
│   └── pareto_chart.png                  #   Pareto root-cause chart
│
├── venv/                                 # your virtual environment (create locally, don't commit)
└── __pycache__/                          # auto-generated Python cache (don't commit)
```

## Setup — from scratch

### 1. Prerequisites
- Python 3.9+ installed (`python --version` to check)
- Git (push to GitHub)

### 2. Clone / navigate to the project folder
```bash
git clone https://github.com/dishasethy/linesight.git
cd linesight
```

### 3. Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate it:
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows Command Prompt:
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the DMAIC pipeline, in order
```bash
# Step 1: Generate synthetic production data (MEASURE input)
python simulate.py

# Step 2: Run DMAIC Measure + Analyze (OEE, bottleneck, SPC, Pareto)
python analyze.py

# Step 3: Run DMAIC Improve + Control (simulate fix, compare before/after)
python improve.py
```
Each script prints results to the terminal and automatically saves CSVs to `data/` and charts to `outputs/`.

### 6. Launch the dashboard
```bash
streamlit run dashboard.py
```
This opens a browser tab (usually `http://localhost:8501`) with the live KPI dashboard.

## Pushing to GitHub
```bash
git add .
git commit -m "Complete Line Sight DMAIC process optimization pipeline"
git push origin main
```

## Interpreting the results (for your interview)
- **Why throughput, not OEE, decides the bottleneck**: a station can have a "good-looking" OEE % but still cap the line's real output if its absolute units/hour is lowest. This project deliberately checks both and shows they can disagree — a Theory-of-Constraints insight worth mentioning.
- **SPC control limits (±3σ)**: any shift outside these bounds signals a special-cause variation (not normal day-to-day noise) — worth investigating on the floor.
- **Pareto's 80/20**: the chart identifies the 2–3 causes responsible for the bulk of downtime, so improvement effort isn't spread thin across every possible fault.

## Extending this further
- Swap synthetic data for a real Kaggle manufacturing/predictive-maintenance dataset for stronger credibility.
- Add a capacity-planning module (e.g., using `PuLP`) to recommend optimal shift/resource allocation.
- Deploy the dashboard on Streamlit Community Cloud so you can share a live link on your resume.
