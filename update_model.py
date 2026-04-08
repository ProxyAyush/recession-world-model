import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# Indicator IDs
# T10Y3M: 10-Year Treasury Minus 3-Month Treasury Spread
# SAHMREALTIME: Sahm Rule Recession Indicator
# INDPRO: Industrial Production Index
# UNRATE: Unemployment Rate
INDICATORS = ['T10Y3M', 'SAHMREALTIME', 'INDPRO', 'UNRATE']

def fetch_fred_data(series_id):
    """Fetch data from DBnomics (No API key required)"""
    url = f"https://api.db.nomics.world/v22/series/FRED/FRED/{series_id}?observations=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        series = data['series']['docs'][0]
        return {
            'date': series['period'][-1],
            'value': float(series['value'][-1])
        }
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return None

def calculate_probabilities(latest_data):
    """Weighted World Model based on research"""
    # Latest values
    yield_spread = latest_data.get('T10Y3M', {}).get('value', 0.5)
    sahm_val = latest_data.get('SAHMREALTIME', {}).get('value', 0.1)
    
    # Probability Logic
    # 1. Yield Spread (Estrella-Mishkin Model)
    yield_risk = 95 if yield_spread < 0 else (60 if yield_spread < 0.5 else 20)
    
    # 2. Sahm Rule (Labor Momentum)
    sahm_risk = 95 if sahm_val >= 0.5 else (50 if sahm_val >= 0.3 else 10)

    # Weights
    today_prob = int((sahm_risk * 0.85) + (yield_risk * 0.15))
    one_month_prob = int((sahm_risk * 0.6) + (yield_risk * 0.4))
    one_year_prob = int((yield_risk * 0.8) + (sahm_risk * 0.2))
    
    return {
        'today': today_prob,
        '1_month': one_month_prob,
        '1_year': one_year_prob,
        'timestamp': datetime.now().isoformat()
    }

def update_history(current_probs):
    history_file = 'history.json'
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
    else:
        history = []
    
    history.append(current_probs)
    
    # Accuracy Tracking (How far off were we?)
    # We compare current 'today' reality vs what we predicted 1 month ago
    accuracy_report = "Initial Run - No historical data to compare yet."
    if len(history) > 4: # Assuming weekly runs, 4 weeks ~ 1 month
        past_pred = history[-4]['1_month']
        current_reality = current_probs['today']
        diff = abs(current_reality - past_pred)
        accuracy_report = f"Prediction vs Reality: 1 month ago we predicted {past_pred}% risk today. Actual risk is {current_reality}%. Variance: {diff}%"

    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)
    
    return accuracy_report

def main():
    print("Fetching latest economic data...")
    latest_data = {id: fetch_fred_data(id) for id in INDICATORS}
    
    # Filter out failed fetches
    latest_data = {k: v for k, v in latest_data.items() if v is not None}
    
    probs = calculate_probabilities(latest_data)
    accuracy = update_history(probs)
    
    # Generate Markdown Report
    report = f"""# 📈 Recession World Model - Weekly Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🔮 Current Projections
| Horizon | Probability | Status |
| :--- | :--- | :--- |
| **Today** | **{probs['today']}%** | {'🟢 Low' if probs['today'] < 30 else ('🟡 Moderate' if probs['today'] < 60 else '🔴 High')} |
| **1 Month** | **{probs['1_month']}%** | {'🟢 Low' if probs['1_month'] < 30 else ('🟡 Moderate' if probs['1_month'] < 60 else '🔴 High')} |
| **1 Year** | **{probs['1_year']}%** | {'🟢 Low' if probs['1_year'] < 30 else ('🟡 Moderate' if probs['1_year'] < 60 else '🔴 High')} |

## 🎯 Model Accuracy Tracker
{accuracy}

## 📊 Raw Indicators Used
- **Yield Spread (10Y-3M):** {latest_data.get('T10Y3M', {}).get('value')}%
- **Sahm Rule Value:** {latest_data.get('SAHMREALTIME', {}).get('value')}
- **Industrial Production Index:** {latest_data.get('INDPRO', {}).get('value')}
- **Unemployment Rate:** {latest_data.get('UNRATE', {}).get('value')}%

---
*Data sourced from FRED via DBnomics. This model is for informational purposes and uses established financial research weightings.*
"""
    with open('README.md', 'w') as f:
        f.write(report)

if __name__ == "__main__":
    main()
