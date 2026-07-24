import json
import os
import pandas as pd

# 1. SETTINGS & PATH
path = r'C:\Users\admin\OneDrive\Desktop\Documents\ipl\ipl_male_json'

def load_all_ipl_stats(folder_path):
    data_list = []
    files = [f for f in os.listdir(folder_path) if f.endswith('.json') and f != 'README.txt']
    
    print(f"Reading {len(files)} files... please wait.")

    for file in files:
        with open(os.path.join(folder_path, file), 'r') as f:
            data = json.load(f)
            info = data.get('info', {})
            season = str(info.get('season'))[:4]
            
            # Focus on Impact Era (2023-2026)
            if season in ['2023', '2024', '2025', '2026']:
                toss_winner = info.get('toss', {}).get('winner')
                match_winner = info.get('outcome', {}).get('winner')
                venue = info.get('venue')
                
                # Calculate Runs
                total_runs = 0
                for innings in data.get('innings', []):
                    for over in innings.get('overs', []):
                        for delivery in over.get('deliveries', []):
                            total_runs += delivery.get('runs', {}).get('total', 0)
                
                data_list.append({
                    'season': season,
                    'venue': venue,
                    'toss_winner': toss_winner,
                    'winner': match_winner,
                    'total_runs': total_runs
                })
    return pd.DataFrame(data_list)

# --- EXECUTION (This part is NOT indented) ---
df = load_all_ipl_stats(path)

if not df.empty:
    print("\n" + "="*40)
    print("      COMPLETE IPL ANALYSIS (2023-2026)")
    print("="*40)

    # 1. TOSS ANALYSIS
    # Filters out 'No Result' matches for a clean toss calculation
    clean_df = df[df['winner'] != 'No Result'].copy()
    toss_win_pct = (clean_df['toss_winner'] == clean_df['winner']).mean() * 100
    
    print(f"Match Win % after winning Toss: {toss_win_pct:.2f}%")
    print(f"Match Win % after losing Toss: {100 - toss_win_pct:.2f}%")
    print("-" * 40)

    # 2. STADIUM ANALYSIS
    stadium_stats = df.groupby('venue')['total_runs'].mean().sort_values()
    print("TOP 3 LOWEST SCORING STADIUMS:")
    print(stadium_stats.head(3))
    print("="*40)
else:
    print("No data found. Check your folder path.")