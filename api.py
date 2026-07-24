import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("CRICKET_API_KEY")

BASE_URL = "https://api.cricapi.com/v1"

# ─────────────────────────────────────────
# 1. Get Live/Current Matches
# ─────────────────────────────────────────
def get_live_matches(offset=0):
    url = f"{BASE_URL}/currentMatches"
    params = {"apikey": API_KEY, "offset": offset}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("status") == "success":
        return data.get("data", [])
    else:
        print("Error:", data.get("reason"))
        return []

# ─────────────────────────────────────────
# 2. Get IPL Series Info
# ─────────────────────────────────────────
def get_series_list(offset=0):
    url = f"{BASE_URL}/series"
    params = {"apikey": API_KEY, "offset": offset}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("status") == "success":
        # Filter for IPL
        all_series = data.get("data", [])
        ipl_series = [s for s in all_series if "IPL" in s.get("name", "")]
        return ipl_series
    return []

# ─────────────────────────────────────────
# 3. Get Match Info by ID
# ─────────────────────────────────────────
def get_match_info(match_id):
    url = f"{BASE_URL}/match_info"
    params = {"apikey": API_KEY, "id": match_id}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("status") == "success":
        return data.get("data", {})
    return {}

# ─────────────────────────────────────────
# 4. Get Player Info
# ─────────────────────────────────────────
def get_player_info(player_name):
    url = f"{BASE_URL}/players"
    params = {"apikey": API_KEY, "search": player_name}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("status") == "success":
        return data.get("data", [])
    return []

# ─────────────────────────────────────────
# 5. Get Upcoming Matches (Today's Schedule)
# ─────────────────────────────────────────
def get_upcoming_matches(offset=0):
    """
    Fetches upcoming/scheduled matches from CricAPI.
    Filters for IPL matches happening today or next.
    Returns a list of match dicts with name, date, teams, venue.
    """
    from datetime import datetime, timezone
    url = f"{BASE_URL}/matches"
    params = {"apikey": API_KEY, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=8)
        data = response.json()
        if data.get("status") == "success":
            all_matches = data.get("data", [])
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            ipl_upcoming = []
            for m in all_matches:
                name = m.get("name", "")
                date = m.get("date", "")          # format: "2025-05-22"
                match_type = m.get("matchType", "")
                # Keep only IPL matches scheduled today or upcoming
                is_ipl = "IPL" in name or "Indian Premier League" in name
                is_today_or_future = date >= today_str
                if is_ipl and is_today_or_future:
                    teams = m.get("teams", [])
                    ipl_upcoming.append({
                        "name":   name,
                        "date":   date,
                        "status": m.get("status", "Scheduled"),
                        "venue":  m.get("venue", "TBD"),
                        "teams":  teams,
                        "team1":  teams[0] if len(teams) > 0 else "TBD",
                        "team2":  teams[1] if len(teams) > 1 else "TBD",
                        "time":   m.get("dateTimeGMT", ""),
                    })
            return ipl_upcoming
        else:
            print("Upcoming matches error:", data.get("reason"))
            return []
    except Exception as e:
        print(f"get_upcoming_matches failed: {e}")
        return []


# ─────────────────────────────────────────
# TEST - Run to verify data is pulling
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("=== LIVE MATCHES ===")
    matches = get_live_matches()
    for m in matches[:5]:  # Show first 5
        print(f"  {m.get('name')} | Status: {m.get('status')}")

    print("\n=== IPL SERIES ===")
    series = get_series_list()
    for s in series:
        print(f"  {s.get('name')} | ID: {s.get('id')}")
