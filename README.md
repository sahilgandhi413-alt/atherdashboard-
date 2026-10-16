# ⚡ Ather EV Market Intelligence Dashboard

An interactive, real-time analytics dashboard for the Indian electric two-wheeler market, built with **Streamlit** and **Plotly**. It explores sales, models, cities, charging, trends, customer ratings and sustainability using a 100,000-row dataset.

> **Note:** The dataset is synthetic and for educational purposes only.

**Live demo:** https://ather5.streamlit.app

---

## Features

- **7 dashboard pages:** Overview, Models, Cities, Charging, Trends, Customer Insights, Sustainability
- **Sidebar filters:** Model, Year, State, Charging type
- **Interactive Plotly charts** with a dark EV-themed UI
- **Three live data modes:**
  1. **CSV file (auto-sync):** re-reads the CSV whenever the file changes
  2. **Live simulator:** generates new sales records every few seconds for demos
  3. **Remote URL / API:** loads a CSV or JSON from a link on every refresh
- **Built-in vector artwork** (logo, scooters, skyline) that works offline, with optional custom images

---

## Project structure

```
atherdashboard-/
├── README.md
└── PROJECT_FILES/
    ├── ather_dashboard.py                              # main Streamlit app
    ├── ather_ev_market_intelligence_100k_synthetic.csv # dataset (tab-separated)
    ├── requirements.txt                                # Python dependencies
    └── assets/                                         # optional custom images
```

---

## Dataset

The file is **tab-separated** and has 15 columns:

| Column | Description |
|---|---|
| `RecordID` | Unique record ID |
| `Company` | Manufacturer |
| `Model` | Scooter model |
| `ModelYear` | Model year |
| `VehicleType` | Vehicle category |
| `BatteryCapacity_kWh` | Battery size in kWh |
| `CertifiedRange_km` | Certified range in km |
| `ExShowroomPrice_INR` | Ex-showroom price in ₹ |
| `City` | City of sale |
| `State` | State of sale |
| `ChargingType` | Charging type |
| `SalesMonth` | Month of sale (`YYYY-MM`) |
| `UnitsSold` | Units sold |
| `CustomerRating` | Customer rating |
| `WarrantyYears` | Warranty in years |

The app detects the separator (tab, comma or semicolon) automatically.

---

## Run locally

**1. Clone the repository**
```bash
git clone https://github.com/sahilgandhi413-alt/atherdashboard-.git
cd atherdashboard-/PROJECT_FILES
```

**2. (Optional) Create a virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac / Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Start the app**
```bash
streamlit run ather_dashboard.py
```

The app opens at `http://localhost:8501`.

**Recommended:** Python 3.11 or 3.12.

---

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **Create app** and choose:
   - **Repository:** `sahilgandhi413-alt/atherdashboard-`
   - **Branch:** `main`
   - **Main file path:** `PROJECT_FILES/ather_dashboard.py`
4. Click **Deploy**.

**Tips**
- Avoid spaces in folder and file names. They break dependency installation.
- Keep the CSV in the same folder as `ather_dashboard.py`.
- GitHub rejects files over 100 MB.
- Every push to `main` redeploys the app automatically.

---

## Dependencies

```
streamlit
pandas==2.2.3
numpy==1.26.4
plotly
openpyxl
```

---

## Optional custom images

Create an `assets/` folder next to `ather_dashboard.py` and add:

| File | Purpose |
|---|---|
| `hero.jpg` | City or skyline banner |
| `scooter.png` | Scooter cut-out with transparent background |
| `logo.png` | Logo |

If these are missing, the built-in vector artwork is used.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `FileNotFoundError` for the CSV | Make sure the CSV is in the same folder as `ather_dashboard.py` and the name matches exactly (case-sensitive) |
| `'DataFrame' object has no attribute 'Model'` | The CSV was read with the wrong separator. Use the latest `ather_dashboard.py`, which auto-detects it |
| Dependency install fails | Remove spaces from folder and file names, and check `requirements.txt` |
| Library errors on a new Python version | Select Python 3.11 or 3.12 in the app's Streamlit settings |

---

## Tech stack

Python · Streamlit · Pandas · NumPy · Plotly

---

## Author

**Sahil Gandhi** · [GitHub](https://github.com/sahilgandhi413-alt)
