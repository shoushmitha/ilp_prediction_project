import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
matches = pd.read_csv(os.path.join(DATA_DIR, "matches.csv"))
deliveries = pd.read_csv(os.path.join(DATA_DIR, "deliveries.csv"))

TEAM_MAPPING = {
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bengaluru": "Royal Challengers Bangalore",
    "Royal Challengers Bangalore": "Royal Challengers Bangalore",
    "Delhi Daredevils": "Delhi Capitals",
    "Delhi Capitals": "Delhi Capitals",
    "Rising Pune Supergiants": "Rising Pune Supergiants",
    "Rising Pune Supergiant": "Rising Pune Supergiants",
    "Deccan Chargers": "Sunrisers Hyderabad",
}

def standardise_team_name(name):
    if not isinstance(name, str):
        return name
    name = name.strip()
    return TEAM_MAPPING.get(name, name)

def standardise_venue_name(venue):
    if not isinstance(venue, str):
        return venue
    venue = venue.strip().lower()
    if "wankhede" in venue:
        return "Wankhede Stadium"
    if "chinnaswamy" in venue:
        return "M Chinnaswamy Stadium"
    if "chidambaram" in venue or "chepauk" in venue:
        return "MA Chidambaram Stadium"
    if "eden gardens" in venue:
        return "Eden Gardens"
    if "feroz shah kotla" in venue or "arun jaitley" in venue:
        return "Arun Jaitley Stadium"
    if "rajiv gandhi" in venue or "uppal" in venue:
        return "Rajiv Gandhi International Stadium"
    if "sawai mansingh" in venue:
        return "Sawai Mansingh Stadium"
    if "narendra modi" in venue or "motera" in venue or "ahmedabad" in venue:
        return "Narendra Modi Stadium"
    if "dy patil" in venue:
        return "Dr DY Patil Sports Academy"
    if "ekana" in venue or "lucknow" in venue:
        return "Ekana Cricket Stadium"
    if "brabourne" in venue:
        return "Brabourne Stadium"
    if "punjab cricket association" in venue or "mohali" in venue or "indrajit singh" in venue:
        return "PCA Stadium Mohali"
    if "maharashtra cricket association" in venue or "gahunje" in venue:
        return "MCA Stadium Pune"
    if "dubai" in venue:
        return "Dubai International Cricket Stadium"
    if "sharjah" in venue:
        return "Sharjah Cricket Stadium"
    if "sheikh zayed" in venue or "abu dhabi" in venue:
        return "Sheikh Zayed Stadium"
    return venue.title()

matches["team1"] = matches["team1"].apply(standardise_team_name)
matches["team2"] = matches["team2"].apply(standardise_team_name)
matches["winner"] = matches["winner"].apply(standardise_team_name)
matches["toss_winner"] = matches["toss_winner"].apply(standardise_team_name)
matches["venue"] = matches["venue"].apply(standardise_venue_name)

matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
matches = matches.sort_values("date").reset_index(drop=True)

# Feature functions
def get_form_before_match(team, match_index, n=5):
    past = matches.iloc[:match_index]
    team_matches = past[(past["team1"] == team) | (past["team2"] == team)].tail(n)
    if len(team_matches) == 0:
        return 0.5
    wins = (team_matches["winner"] == team).sum()
    return wins / len(team_matches)

def get_h2h_ratio(team1, team2, match_index):
    past = matches.iloc[:match_index]
    h2h = past[
        ((past["team1"] == team1) & (past["team2"] == team2)) |
        ((past["team1"] == team2) & (past["team2"] == team1))
    ]
    if len(h2h) == 0:
        return 0.5
    t1_wins = (h2h["winner"] == team1).sum()
    return t1_wins / len(h2h)

def get_venue_win_rate(team, venue, match_index):
    past = matches.iloc[:match_index]
    venue_matches = past[
        ((past["team1"] == team) | (past["team2"] == team)) &
        (past["venue"] == venue)
    ]
    if len(venue_matches) == 0:
        return 0.5
    wins = (venue_matches["winner"] == team).sum()
    return wins / len(venue_matches)

# Precompute runs
deliveries["match_id"] = deliveries["match_id"].astype(str)
matches["match_id"] = matches["match_id"].astype(str)
match_runs = deliveries.groupby("match_id")["total_runs"].sum().reset_index()
match_runs.columns = ["match_id", "total_match_runs"]
matches = matches.merge(match_runs, on="match_id", how="left")

def get_venue_avg_score(venue, match_index):
    past = matches.iloc[:match_index]
    venue_past = past[past["venue"] == venue]["total_match_runs"].dropna()
    if len(venue_past) == 0:
        return matches["total_match_runs"].mean()
    return venue_past.mean()

print("Building features...")
final_data = []
for idx, row in matches.iterrows():
    team1 = row["team1"]
    team2 = row["team2"]
    venue = row["venue"]
    winner = row["winner"]
    if pd.isna(winner) or winner in ("No Result", ""):
        continue
    target = 1 if winner == team1 else 0
    toss_winner = str(row.get("toss_winner", "")).strip()
    toss_advantage = 1 if toss_winner == team1 else 0
    
    record = {
        "team1_form": get_form_before_match(team1, idx, n=5),
        "team2_form": get_form_before_match(team2, idx, n=5),
        "head_to_head": get_h2h_ratio(team1, team2, idx),
        "venue_win_rate_t1": get_venue_win_rate(team1, venue, idx),
        "venue_win_rate_t2": get_venue_win_rate(team2, venue, idx),
        "venue_avg_score": get_venue_avg_score(venue, idx),
        "toss_advantage": toss_advantage,
        "season": int(row["date"].year) if not pd.isna(row["date"]) else 2020,
        "target": target
    }
    final_data.append(record)

df = pd.DataFrame(final_data)
df["form_diff"] = df["team1_form"] - df["team2_form"]
df["venue_win_rate_diff"] = df["venue_win_rate_t1"] - df["venue_win_rate_t2"]
df["h2h_diff"] = df["head_to_head"] - 0.5
print("\n=== CORRELATION MATRIX ===")
print(df.corr()['target'])
