# SafeRoute India — AI-Powered Safe Route Planner

## Setup & Run

```bash
# 1. Unzip and enter folder
unzip smart_safe_route.zip && cd smart_safe_route

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install Flask (only dependency)
pip install flask

# 4. Run
python app.py

# 5. Open browser
# http://localhost:5000
```

## Usage
- Type any Indian city/locality in the "From" field → autocomplete appears
- Type destination in "To" field
- Select Daytime or Night
- Click "Find Safe Route"
- See the safest Dijkstra-computed path, ESS score, and crime heatmap

## Data
90 real Indian locations across 20 cities (Delhi, Mumbai, Bengaluru, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad, Jaipur, Lucknow, Patna, Bhopal, Nagpur, Indore, Chandigarh, Surat, Kochi, Visakhapatnam, Coimbatore).
Crime data normalised from NCRB 2022-23 IPC cognisable crime reports.

## ML Stack
- K-Means Clustering (k=6) — detects crime hotspots shown as heatmap
- Logistic Regression (pure Python, no sklearn) — classifies safe/unsafe
- Dijkstra's Algorithm — finds lowest-danger-weight path through location graph
