import os
import requests
import json
from datetime import datetime

# Indicator IDs
INDICATORS = ['T10Y3M', 'SAHMREALTIME', 'INDPRO', 'UNRATE']

def fetch_fred_data(series_id):
    """Fetch data directly from FRED as CSV (No API key required)"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        if len(lines) < 2:
            return None
        
        for i in range(len(lines) - 1, 0, -1):
            date, value = lines[i].split(',')
            if value != '.':
                return {
                    'date': date,
                    'value': float(value)
                }
        return None
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return None

def calculate_probabilities(latest_data):
    """Weighted World Model based on research"""
    yield_spread = latest_data.get('T10Y3M', {}).get('value', 0.5)
    sahm_val = latest_data.get('SAHMREALTIME', {}).get('value', 0.1)
    
    yield_risk = 95 if yield_spread < 0 else (60 if yield_spread < 0.5 else 20)
    sahm_risk = 95 if sahm_val >= 0.5 else (50 if sahm_val >= 0.3 else 10)

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
    
    accuracy_report = "Initial Run - No historical data to compare yet."
    if len(history) > 4:
        past_pred = history[-4]['1_month']
        current_reality = current_probs['today']
        diff = abs(current_reality - past_pred)
        accuracy_report = f"Prediction vs Reality: 1 month ago we predicted {past_pred}% risk today. Actual risk is {current_reality}%. Variance: {diff}%"

    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)
    
    # Generate FULL_HISTORY.md
    with open('FULL_HISTORY.md', 'w') as f:
        f.write("# 📜 Full Model History\n\n")
        f.write("| Date | Today's Risk | 1 Month Risk | 1 Year Risk |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for entry in reversed(history):
            date_str = entry['timestamp'].split('T')[0]
            f.write(f"| {date_str} | {entry['today']}% | {entry['1_month']}% | {entry['1_year']}% |\n")
        
        # Simple text-based graph
        f.write("\n## 📈 Trend (Today's Risk)\n```\n")
        for entry in history:
            date_str = entry['timestamp'].split('T')[0]
            bar = "█" * (entry['today'] // 5)
            f.write(f"{date_str}: {bar} {entry['today']}%\n")
        f.write("```\n")
    
    return accuracy_report

def main():
    print("Fetching latest economic data...")
    latest_data = {id: fetch_fred_data(id) for id in INDICATORS}
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
### 📚 [View Full History & Trends](./FULL_HISTORY.md)

*Data sourced from FRED. This model is for informational purposes and uses established financial research weightings.*
"""
    with open('README.md', 'w') as f:
        f.write(report)

if __name__ == "__main__":
    main()
